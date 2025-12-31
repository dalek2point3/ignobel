"""
Parse the saved HTML file of Ig Nobel winners and extract all data to CSV.
"""

import re
from bs4 import BeautifulSoup
import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
HTML_FILE = DATA_DIR / "Past Ig Winners – Improbable Research.html"


def clean_text(text):
    """Clean extracted text."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
    return text.strip()


def extract_doi(text):
    """Extract DOI from text."""
    if not text:
        return None

    doi_patterns = [
        r'doi\.org/(10\.\d{4,}/[^\s\"\'\>\<]+)',
        r'<(10\.\d{4,}/[^\s\"\'\>]+)>',
        r'doi:\s*(10\.\d{4,}/[^\s\"\'\>]+)',
        r'(10\.\d{4,}/[\w\.\-\(\)]+)',
    ]

    for pattern in doi_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1)
            doi = doi.rstrip('.,;:>\)<')
            doi = doi.replace('&gt;', '').replace('%2F', '/')
            if doi.startswith('10.'):
                return doi

    return None


def parse_winners_html():
    """Parse the HTML file and extract all winners."""
    print(f"Reading HTML file: {HTML_FILE}")

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    winners = []

    # Find all elements (h2 and p tags) in order
    all_elements = soup.find_all(['h2', 'p'])

    current_year = None
    year_winners = []

    for element in all_elements:
        if element.name == 'h2':
            # Check if this is a year heading
            h2_text = element.get_text()
            year_match = re.search(r'(\d{4})\s+Ig Nobel Prize Winners', h2_text)

            if year_match:
                # Save previous year's winners
                if current_year and year_winners:
                    print(f"  Found {len(year_winners)} prizes for {current_year}")
                    winners.extend(year_winners)

                # Start new year
                current_year = int(year_match.group(1))
                year_winners = []
                print(f"\nProcessing year: {current_year}")

        elif element.name == 'p' and current_year:
            # Only process if we're in a year section
            p_html = str(element)
            p_text = element.get_text()

            # Look for PRIZE patterns in <strong> or <b> tags
            # Two formats:
            # 1. <strong>CATEGORY PRIZE</strong> (2007+)
            # 2. <strong>CATEGORY</strong>: (2006 and earlier)
            prize_pattern_with_prize = r'<(?:strong|b)>([A-Z\s&/]+?)\s+PRIZE(?:S)?\s*</(?:strong|b)>'
            prize_pattern_category_only = r'<(?:strong|b)>([A-Z\s&/]+?)\s*</(?:strong|b)>\s*:'

            prize_matches_with_prize = re.findall(prize_pattern_with_prize, p_html, re.IGNORECASE)
            prize_matches_category_only = re.findall(prize_pattern_category_only, p_html, re.IGNORECASE)

            # Combine and filter out non-category matches
            prize_matches = prize_matches_with_prize + prize_matches_category_only

            # Filter out common false matches
            false_positives = ['em', 'p', 'reference', 'published in']
            prize_matches = [m for m in prize_matches if m.lower() not in false_positives]

            if prize_matches:
                for category_raw in prize_matches:
                    category = clean_text(category_raw).title()

                    # Split content by prize tags to isolate each prize section
                    # Handle both formats
                    parts = re.split(r'<(?:strong|b)>[A-Z\s&/]+?(?:\s+PRIZE(?:S)?)?\s*</(?:strong|b)>\s*:?', p_html, flags=re.IGNORECASE)

                    prize_idx = prize_matches.index(category_raw)
                    if prize_idx + 1 < len(parts):
                        prize_html = parts[prize_idx + 1]
                    else:
                        prize_html = p_html

                    # Remove HTML tags for text extraction
                    prize_text_soup = BeautifulSoup(prize_html, 'html.parser')
                    prize_text = prize_text_soup.get_text()

                    # Extract country [COUNTRY]
                    country_match = re.search(r'\[([^\]]+)\]', prize_text)
                    country = country_match.group(1) if country_match else ''

                    # Split by REFERENCE: to separate authors/description from reference
                    ref_split = re.split(r'REFERENCE:', prize_text, flags=re.IGNORECASE)

                    # Authors/description is before REFERENCE
                    if len(ref_split) > 1:
                        authors_text = ref_split[0]
                        reference = 'REFERENCE: ' + ref_split[1]
                    else:
                        authors_text = prize_text
                        reference = ''

                    # Clean authors text
                    authors = clean_text(authors_text)
                    # Remove country info
                    authors = re.sub(r'\[.*?\]', '', authors).strip()

                    # Extract description (usually after "for")
                    description = ''
                    if ' for ' in authors:
                        parts = authors.split(' for ', 1)
                        author_names = parts[0]
                        description = parts[1] if len(parts) > 1 else ''
                    else:
                        author_names = authors

                    # Clean up
                    author_names = clean_text(author_names)[:500]
                    description = clean_text(description)[:1000]

                    # Extract DOI
                    doi = extract_doi(prize_html)

                    # Clean reference
                    reference_clean = clean_text(reference)[:1500]

                    year_winners.append({
                        'year': current_year,
                        'category': category,
                        'authors': author_names,
                        'description': description,
                        'country': clean_text(country),
                        'doi': doi,
                        'reference': reference_clean,
                        'source': 'improbable_html'
                    })

    # Don't forget the last year
    if current_year and year_winners:
        print(f"  Found {len(year_winners)} prizes for {current_year}")
        winners.extend(year_winners)

    # Deduplicate based on year + normalized category
    # (Some years have both "Category" and "Category Prize" which are the same)
    # Prefer the version WITH "Prize" in the name
    seen = {}  # key -> winner (keep best version)

    for winner in winners:
        # Normalize category by removing " Prize" suffix for comparison
        norm_category = winner['category'].replace(' Prize', '').strip()
        key = (winner['year'], norm_category.lower())

        if key not in seen:
            # First time seeing this category for this year
            seen[key] = winner
        else:
            # Already have this category - keep the one with " Prize" if possible
            existing = seen[key]
            # Prefer entries with " Prize" in the name
            if ' Prize' in winner['category'] and ' Prize' not in existing['category']:
                seen[key] = winner
            # Otherwise keep the first one

    unique_winners = list(seen.values())

    print(f"\nTotal unique winners extracted (after deduplication): {len(unique_winners)}")
    return unique_winners


def save_to_csv(winners, filename='all_ig_nobel_winners.csv'):
    """Save winners to CSV file."""
    df = pd.DataFrame(winners)

    # Sort by year (descending) and category
    df = df.sort_values(['year', 'category'], ascending=[False, True])

    output_file = DATA_DIR / filename
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nSaved to: {output_file}")

    # Also save as JSON
    json_file = DATA_DIR / filename.replace('.csv', '.json')
    df.to_json(json_file, orient='records', indent=2)
    print(f"Also saved to: {json_file}")

    # Print summary statistics
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total winners: {len(df)}")
    print(f"Year range: {df['year'].min()} - {df['year'].max()}")
    print(f"Winners with DOI: {df['doi'].notna().sum()}")
    print(f"Winners without DOI: {df['doi'].isna().sum()}")

    # Winners by year
    print(f"\nWinners by year:")
    year_counts = df.groupby('year').size().sort_index(ascending=False)
    print(year_counts.to_string())

    # Check for expected 10 per year
    unexpected = year_counts[year_counts != 10]
    if len(unexpected) > 0:
        print(f"\n⚠ Years without exactly 10 prizes:")
        print(unexpected.to_string())

    return df


def main():
    """Main execution."""
    print("="*70)
    print("PARSING IG NOBEL WINNERS FROM HTML FILE")
    print("="*70)

    if not HTML_FILE.exists():
        print(f"\nError: HTML file not found at {HTML_FILE}")
        print("Please ensure the file exists in the data/ directory")
        return

    winners = parse_winners_html()

    if winners:
        df = save_to_csv(winners)
        print(f"\n{'='*70}")
        print("SUCCESS!")
        print(f"{'='*70}\n")
    else:
        print("\nWarning: No winners were extracted")


if __name__ == "__main__":
    main()
