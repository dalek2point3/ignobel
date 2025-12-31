"""
Enrich Ig Nobel winner data with full publication details using DOIs.
Fetches metadata from CrossRef, Semantic Scholar, and other scholarly databases.
"""

import pandas as pd
import requests
import time
from pathlib import Path
from typing import Dict, Optional
import json
from tqdm import tqdm


DATA_DIR = Path(__file__).parent.parent / "data"


class PaperEnricher:
    """Enrich paper data with publication metadata."""

    def __init__(self):
        self.crossref_base = "https://api.crossref.org/works/"
        self.semantic_scholar_base = "https://api.semanticscholar.org/v1/paper/"
        self.headers = {
            'User-Agent': 'IgNobelResearch/1.0 (mailto:researcher@example.com)'
        }

    def get_crossref_metadata(self, doi: str) -> Optional[Dict]:
        """Fetch paper metadata from CrossRef using DOI."""
        try:
            url = f"{self.crossref_base}{doi}"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                work = data.get('message', {})

                return {
                    'title': work.get('title', [''])[0] if work.get('title') else '',
                    'journal': work.get('container-title', [''])[0] if work.get('container-title') else '',
                    'publication_year': work.get('published-print', {}).get('date-parts', [[None]])[0][0] or
                                       work.get('published-online', {}).get('date-parts', [[None]])[0][0],
                    'publisher': work.get('publisher', ''),
                    'authors_detailed': work.get('author', []),
                    'citations_count': work.get('is-referenced-by-count', 0),
                    'url': work.get('URL', ''),
                    'type': work.get('type', '')
                }
        except Exception as e:
            print(f"Error fetching CrossRef data for {doi}: {e}")

        return None

    def get_semantic_scholar_metadata(self, doi: str) -> Optional[Dict]:
        """Fetch paper metadata from Semantic Scholar using DOI."""
        try:
            url = f"{self.semantic_scholar_base}{doi}"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data.get('title', ''),
                    'year': data.get('year'),
                    'citations_count': len(data.get('citations', [])),
                    'references_count': len(data.get('references', [])),
                    'influential_citation_count': data.get('influentialCitationCount', 0),
                    'semantic_scholar_id': data.get('paperId', ''),
                    'venue': data.get('venue', ''),
                    'authors_detailed': data.get('authors', [])
                }
        except Exception as e:
            print(f"Error fetching Semantic Scholar data for {doi}: {e}")

        return None

    def clean_doi(self, doi: str) -> str:
        """Clean and normalize DOI."""
        if not doi:
            return ""

        doi = str(doi).strip()

        # Remove common prefixes
        prefixes = ['https://doi.org/', 'http://dx.doi.org/', 'doi:', 'DOI:']
        for prefix in prefixes:
            if doi.startswith(prefix):
                doi = doi[len(prefix):]

        return doi.strip()

    def enrich_paper(self, paper_row: Dict) -> Dict:
        """Enrich a single paper with metadata from scholarly sources."""
        enriched = paper_row.copy()

        doi = self.clean_doi(paper_row.get('doi', ''))

        if not doi:
            print(f"No DOI for {paper_row.get('category', '')} ({paper_row.get('year', '')})")
            return enriched

        print(f"Enriching: {doi}")

        # Try CrossRef first
        crossref_data = self.get_crossref_metadata(doi)
        if crossref_data:
            enriched.update({k: v for k, v in crossref_data.items() if v})

        time.sleep(0.5)  # Rate limiting

        # Try Semantic Scholar for additional data
        ss_data = self.get_semantic_scholar_metadata(doi)
        if ss_data:
            # Merge data, preferring CrossRef for core metadata
            for key, value in ss_data.items():
                if key not in enriched or not enriched[key]:
                    enriched[key] = value

        # Create paper_id
        enriched['paper_id'] = f"ig_{enriched['year']}_{enriched['category'].lower().replace(' ', '_')}"

        return enriched

    def process_winners(self, input_file: str = "raw_winners.csv") -> pd.DataFrame:
        """Process all winners and enrich with metadata."""
        input_path = DATA_DIR / input_file

        # Try CSV first, then JSON
        if input_path.exists():
            df = pd.read_csv(input_path)
        else:
            json_path = DATA_DIR / input_file.replace('.csv', '.json')
            if json_path.exists():
                df = pd.read_json(json_path)
            else:
                # Try manual_winners.json as fallback
                manual_path = DATA_DIR / "manual_winners.json"
                if manual_path.exists():
                    df = pd.read_json(manual_path)
                else:
                    raise FileNotFoundError(f"No input file found at {input_path} or {json_path}")

        print(f"Processing {len(df)} papers...")

        enriched_papers = []
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Enriching papers"):
            enriched = self.enrich_paper(row.to_dict())
            enriched_papers.append(enriched)
            time.sleep(1)  # Be polite to APIs

        return pd.DataFrame(enriched_papers)

    def save_enriched_papers(self, df: pd.DataFrame, filename: str = "awarded_papers.csv"):
        """Save enriched papers to file."""
        output_path = DATA_DIR / filename

        # Select and order columns
        columns = [
            'paper_id', 'year', 'category', 'title', 'description',
            'authors', 'affiliation', 'doi', 'publication_year',
            'journal', 'publisher', 'citations_count', 'url', 'source'
        ]

        # Only include columns that exist
        available_columns = [col for col in columns if col in df.columns]
        df_output = df[available_columns]

        df_output.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\nSaved enriched papers to {output_path}")

        # Also save as JSON
        json_path = DATA_DIR / filename.replace('.csv', '.json')
        df_output.to_json(json_path, orient='records', indent=2)
        print(f"Also saved to {json_path}")

        # Print summary statistics
        print(f"\n=== Summary ===")
        print(f"Total papers: {len(df_output)}")
        print(f"Papers with DOI: {df_output['doi'].notna().sum()}")
        if 'title' in df_output.columns:
            print(f"Papers with title: {df_output['title'].notna().sum()}")
        if 'citations_count' in df_output.columns:
            print(f"Papers with citation data: {df_output['citations_count'].notna().sum()}")

        return df_output


def main():
    """Main execution function."""
    print("=== Enriching Ig Nobel Papers ===\n")

    enricher = PaperEnricher()

    try:
        df_enriched = enricher.process_winners()
        enricher.save_enriched_papers(df_enriched)
        print("\n=== Enrichment Complete ===")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease run 01_scrape_winners.py first, or ensure manual_winners.json exists.")
        return
    except Exception as e:
        print(f"\nError during enrichment: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
