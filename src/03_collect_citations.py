"""
Collect all citations to Ig Nobel prize-winning papers.
Uses multiple APIs to ensure comprehensive citation coverage.
"""

import pandas as pd
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional
import json
from tqdm import tqdm
from datetime import datetime


DATA_DIR = Path(__file__).parent.parent / "data"


class CitationCollector:
    """Collect citations for focal papers from multiple sources."""

    def __init__(self):
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1/paper/"
        self.opencitations_base = "https://opencitations.net/index/api/v1/citations/"
        self.headers = {
            'User-Agent': 'IgNobelResearch/1.0 (mailto:researcher@example.com)'
        }
        self.all_citations = []

    def get_semantic_scholar_citations(self, doi: str, paper_id: str) -> List[Dict]:
        """Get citations from Semantic Scholar API."""
        citations = []

        try:
            # Use the new Semantic Scholar Graph API
            url = f"{self.semantic_scholar_base}DOI:{doi}/citations"
            params = {
                'fields': 'title,year,authors,venue,citationCount,paperId,externalIds',
                'limit': 1000  # Maximum allowed
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=60)

            if response.status_code == 200:
                data = response.json()
                citing_papers = data.get('data', [])

                for item in citing_papers:
                    citing_paper = item.get('citingPaper', {})

                    # Extract author names
                    authors = '; '.join([
                        author.get('name', '')
                        for author in citing_paper.get('authors', [])
                    ])

                    # Get DOI if available
                    citing_doi = None
                    external_ids = citing_paper.get('externalIds', {})
                    if external_ids:
                        citing_doi = external_ids.get('DOI')

                    citation = {
                        'focal_paper_id': paper_id,
                        'focal_paper_doi': doi,
                        'citing_paper_id': citing_paper.get('paperId', ''),
                        'citing_paper_doi': citing_doi,
                        'citing_paper_title': citing_paper.get('title', ''),
                        'citation_year': citing_paper.get('year'),
                        'authors': authors,
                        'journal': citing_paper.get('venue', ''),
                        'citation_count': citing_paper.get('citationCount', 0),
                        'source': 'semantic_scholar'
                    }

                    citations.append(citation)

                print(f"  Found {len(citations)} citations from Semantic Scholar")

            elif response.status_code == 404:
                print(f"  Paper not found in Semantic Scholar: {doi}")
            else:
                print(f"  Semantic Scholar API error ({response.status_code}): {response.text[:100]}")

        except Exception as e:
            print(f"  Error fetching Semantic Scholar citations for {doi}: {e}")

        return citations

    def get_opencitations_citations(self, doi: str, paper_id: str) -> List[Dict]:
        """Get citations from OpenCitations API."""
        citations = []

        try:
            url = f"{self.opencitations_base}{doi}"
            response = requests.get(url, headers=self.headers, timeout=60)

            if response.status_code == 200:
                data = response.json()

                for item in data:
                    citation = {
                        'focal_paper_id': paper_id,
                        'focal_paper_doi': doi,
                        'citing_paper_doi': item.get('citing', ''),
                        'citation_year': item.get('creation', ''),
                        'source': 'opencitations'
                    }

                    citations.append(citation)

                print(f"  Found {len(citations)} citations from OpenCitations")

            elif response.status_code == 404:
                print(f"  Paper not found in OpenCitations: {doi}")

        except Exception as e:
            print(f"  Error fetching OpenCitations citations for {doi}: {e}")

        return citations

    def get_crossref_citations(self, doi: str, paper_id: str) -> List[Dict]:
        """Get citations from CrossRef API (papers that cite this DOI)."""
        citations = []

        try:
            # CrossRef doesn't directly provide forward citations (who cites this paper)
            # But we can search for papers that reference this DOI
            url = "https://api.crossref.org/works"
            params = {
                'filter': f'doi:{doi}',
                'select': 'DOI,title,author,published-print,container-title',
                'rows': 1000
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=60)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                for item in items:
                    # Extract author names
                    authors = '; '.join([
                        f"{author.get('given', '')} {author.get('family', '')}"
                        for author in item.get('author', [])
                    ])

                    # Get publication year
                    pub_year = None
                    if item.get('published-print'):
                        pub_year = item['published-print'].get('date-parts', [[None]])[0][0]

                    citation = {
                        'focal_paper_id': paper_id,
                        'focal_paper_doi': doi,
                        'citing_paper_doi': item.get('DOI'),
                        'citing_paper_title': item.get('title', [''])[0] if item.get('title') else '',
                        'citation_year': pub_year,
                        'authors': authors,
                        'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                        'source': 'crossref'
                    }

                    citations.append(citation)

                print(f"  Found {len(citations)} citations from CrossRef")

        except Exception as e:
            print(f"  Error fetching CrossRef citations for {doi}: {e}")

        return citations

    def merge_citations(self, citations_lists: List[List[Dict]]) -> List[Dict]:
        """Merge citations from different sources, removing duplicates."""
        all_citations = []

        for citations in citations_lists:
            all_citations.extend(citations)

        # Deduplicate based on citing DOI (if available)
        seen_dois = set()
        unique_citations = []

        for citation in all_citations:
            citing_doi = citation.get('citing_paper_doi')

            # If no DOI, use title and year as key
            if not citing_doi:
                key = (
                    citation.get('citing_paper_title', '').lower().strip(),
                    citation.get('citation_year')
                )
            else:
                key = citing_doi

            if key and key not in seen_dois:
                seen_dois.add(key)
                unique_citations.append(citation)

        return unique_citations

    def collect_citations_for_paper(self, paper_row: Dict) -> List[Dict]:
        """Collect all citations for a single paper from multiple sources."""
        doi = paper_row.get('doi')
        paper_id = paper_row.get('paper_id')

        if not doi:
            print(f"No DOI for {paper_id}, skipping citation collection")
            return []

        print(f"\nCollecting citations for: {paper_id} ({doi})")

        all_citations = []

        # Collect from Semantic Scholar
        ss_citations = self.get_semantic_scholar_citations(doi, paper_id)
        all_citations.append(ss_citations)
        time.sleep(3)  # Rate limiting

        # Collect from OpenCitations
        oc_citations = self.get_opencitations_citations(doi, paper_id)
        all_citations.append(oc_citations)
        time.sleep(2)  # Rate limiting

        # Merge and deduplicate
        merged = self.merge_citations(all_citations)
        print(f"  Total unique citations: {len(merged)}")

        return merged

    def process_all_papers(self, input_file: str = "awarded_papers.csv"):
        """Process all awarded papers and collect their citations."""
        input_path = DATA_DIR / input_file

        if not input_path.exists():
            # Try JSON version
            json_path = DATA_DIR / input_file.replace('.csv', '.json')
            if json_path.exists():
                df = pd.read_json(json_path)
            else:
                raise FileNotFoundError(f"No input file found at {input_path}")
        else:
            df = pd.read_csv(input_path)

        print(f"Processing {len(df)} papers for citation collection...\n")

        all_citations = []

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Collecting citations"):
            citations = self.collect_citations_for_paper(row.to_dict())
            all_citations.extend(citations)
            time.sleep(5)  # Be very polite to APIs

        self.all_citations = all_citations
        return all_citations

    def save_citations(self, filename: str = "citations.csv"):
        """Save collected citations to file."""
        if not self.all_citations:
            print("No citations to save")
            return

        df = pd.DataFrame(self.all_citations)
        output_path = DATA_DIR / filename

        # Select and order columns
        columns = [
            'focal_paper_id', 'focal_paper_doi', 'citing_paper_id',
            'citing_paper_doi', 'citing_paper_title', 'citation_year',
            'authors', 'journal', 'citation_count', 'source'
        ]

        available_columns = [col for col in columns if col in df.columns]
        df_output = df[available_columns]

        df_output.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\nSaved {len(df_output)} citations to {output_path}")

        # Also save as JSON
        json_path = DATA_DIR / filename.replace('.csv', '.json')
        df_output.to_json(json_path, orient='records', indent=2)
        print(f"Also saved to {json_path}")

        # Print summary statistics
        print(f"\n=== Citation Summary ===")
        print(f"Total citations collected: {len(df_output)}")
        print(f"Unique focal papers cited: {df_output['focal_paper_id'].nunique()}")
        print(f"Citations with year data: {df_output['citation_year'].notna().sum()}")

        # Year distribution
        if 'citation_year' in df_output.columns:
            year_dist = df_output['citation_year'].value_counts().sort_index()
            print(f"\nCitations by year (top 10):")
            print(year_dist.head(10))

        return df_output


def main():
    """Main execution function."""
    print("=== Collecting Citations to Ig Nobel Papers ===\n")
    print("This process may take a while due to API rate limits...")
    print("Please be patient!\n")

    collector = CitationCollector()

    try:
        citations = collector.process_all_papers()
        collector.save_citations()
        print("\n=== Citation Collection Complete ===")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease run 02_enrich_papers.py first to create awarded_papers.csv")
        return
    except Exception as e:
        print(f"\nError during citation collection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
