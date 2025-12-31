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

    # Find all year sections
    h2_tags = soup.find_all('h2')

    for h2 in h2_tags:
        h2_text = h2.get_text()

        # Check if this is a year heading
        year_match = re.search(r'(\d{4})\s+Ig Nobel Prize Winners', h2_text)
        if not year_match:
            continue

        year = int(year_match.group(1))
        print(f"\nProcessing year: {year}")

        # Find all <p> tags after this h2 until the next h2
        # Look for patterns like <strong>CATEGORY PRIZE</strong>
        current = h2.find_next('p')
        year_winners = []

        while current:
            # Stop if we hit another year heading
            if current.find_previous('h2') != h2:
                break

            # Get the paragraph HTML
            p_html = str(current)
            p_text = current.get_text()

            # Look for PRIZE patterns in <strong> tags
            # Match: <strong>CATEGORY PRIZE</strong> or <strong>CATEGORY  PRIZE </strong>
            prize_pattern = r'<strong>([A-Z\s&/]+?)\s+PRIZE\s*</strong>'
            prize_matches = re.findall(prize_pattern, p_html, re.IGNORECASE)

            if prize_matches:
                for category_raw in prize_matches:
                    category = clean_text(category_raw).title()

                    # Split content by <strong> tags to isolate each prize section
                    parts = re.split(r'<strong>[A-Z\s&/]+?\s+PRIZE\s*</strong>', p_html, flags=re.IGNORECASE)

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

                    # Extract first sentence/line as description
                    # Usually: "Name1, Name2, for doing something."
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
                        'year': year,
                        'category': category,
                        'authors': author_names,
                        'description': description,
                        'country': clean_text(country),
                        'doi': doi,
                        'reference': reference_clean,
                        'source': 'improbable_html'
                    })

            current = current.find_next_sibling('p')

        print(f"  Found {len(year_winners)} prizes for {year}")
        winners.extend(year_winners)

    print(f"\n\nTotal winners extracted: {len(winners)}")
    return winners


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
