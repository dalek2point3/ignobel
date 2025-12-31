"""
Collect citations for Ig Nobel papers using OpenAlex API.
Works for papers with DOIs (direct lookup) and without DOIs (search by title/authors).
"""

import pandas as pd
import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# OpenAlex configuration
OPENALEX_BASE = "https://api.openalex.org"
MAILTO = "researcher@ignobel-citations.org"  # Polite pool access
HEADERS = {
    'User-Agent': f'IgNobelCitationStudy/1.0 (mailto:{MAILTO})'
}


class OpenAlexCitationCollector:
    """Collect citations using OpenAlex API."""

    def __init__(self, mailto: str = MAILTO):
        self.mailto = mailto
        self.base_url = OPENALEX_BASE
        self.headers = HEADERS
        self.stats = {
            'papers_processed': 0,
            'papers_found_in_openalex': 0,
            'papers_not_found': 0,
            'total_citations_collected': 0,
            'api_calls': 0,
            'errors': 0
        }

    def get_work_by_doi(self, doi: str) -> Optional[Dict]:
        """Get OpenAlex work object by DOI."""
        if not doi:
            return None

        try:
            # Clean DOI
            doi = doi.strip()

            # Try full DOI URL format first
            url = f"{self.base_url}/works/https://doi.org/{doi}"
            params = {'mailto': self.mailto}

            # Disable proxy to avoid connection issues
            response = requests.get(url, params=params, headers=self.headers, timeout=30, proxies={'http': None, 'https': None})
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                return response.json()

            # Try filter format as fallback
            url = f"{self.base_url}/works"
            params = {'filter': f'doi:{doi}', 'mailto': self.mailto}

            response = requests.get(url, params=params, headers=self.headers, timeout=30, proxies={'http': None, 'https': None})
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    return results[0]

            return None

        except Exception as e:
            print(f"  Error fetching by DOI {doi}: {e}")
            self.stats['errors'] += 1
            return None

    def search_work_by_title(self, title: str, authors: str = None, year: int = None) -> Optional[Dict]:
        """Search for work by title and optionally authors/year."""
        if not title or len(title) < 10:
            return None

        try:
            # Build search query
            search_query = title.strip()[:200]  # Limit length

            url = f"{self.base_url}/works"
            params = {
                'search': search_query,
                'mailto': self.mailto,
                'per-page': 5  # Only get top 5 matches
            }

            # Add year filter if available
            if year and year > 1900:
                params['filter'] = f'publication_year:{year}'

            response = requests.get(url, params=params, headers=self.headers, timeout=30, proxies={'http': None, 'https': None})
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                if results:
                    # Return the first result (best match)
                    # TODO: Could add fuzzy title matching here for better accuracy
                    return results[0]

            return None

        except Exception as e:
            print(f"  Error searching by title: {e}")
            self.stats['errors'] += 1
            return None

    def get_citing_papers(self, openalex_id: str, max_citations: int = 10000) -> List[Dict]:
        """Get all papers that cite the given OpenAlex work using cursor pagination."""
        citations = []

        try:
            # Use the cites filter
            url = f"{self.base_url}/works"
            params = {
                'filter': f'cites:{openalex_id}',
                'per-page': 200,  # Maximum allowed
                'cursor': '*',  # Start cursor
                'mailto': self.mailto
            }

            while True:
                response = requests.get(url, params=params, headers=self.headers, timeout=60, proxies={'http': None, 'https': None})
                self.stats['api_calls'] += 1

                if response.status_code != 200:
                    print(f"  Error getting citations (status {response.status_code})")
                    break

                data = response.json()
                results = data.get('results', [])

                if not results:
                    break

                citations.extend(results)

                # Check if we've hit the max or if there's no next page
                if len(citations) >= max_citations:
                    citations = citations[:max_citations]
                    break

                # Get next cursor
                next_cursor = data.get('meta', {}).get('next_cursor')
                if not next_cursor:
                    break

                params['cursor'] = next_cursor
                time.sleep(0.11)  # Rate limiting: ~9 req/sec to be safe

            return citations

        except Exception as e:
            print(f"  Error getting citing papers: {e}")
            self.stats['errors'] += 1
            return citations

    def extract_citation_data(self, citing_work: Dict, focal_paper_id: str, focal_paper_doi: str,
                             award_year: int) -> Dict:
        """Extract relevant fields from a citing work."""

        # Extract publication year
        pub_year = citing_work.get('publication_year')
        pub_date = citing_work.get('publication_date')

        # Extract authors
        authorships = citing_work.get('authorships', [])
        authors = [a.get('author', {}).get('display_name', '') for a in authorships if a.get('author')]

        # Extract DOI
        citing_doi = citing_work.get('doi')
        if citing_doi and citing_doi.startswith('https://doi.org/'):
            citing_doi = citing_doi.replace('https://doi.org/', '')

        # Extract source (journal/venue)
        primary_location = citing_work.get('primary_location', {})
        source = primary_location.get('source', {})
        source_name = source.get('display_name', '')

        # Calculate years since award
        years_since_award = None
        if pub_year and award_year:
            years_since_award = pub_year - award_year

        return {
            'focal_paper_id': focal_paper_id,
            'focal_paper_doi': focal_paper_doi,
            'award_year': award_year,
            'citing_paper_openalex_id': citing_work.get('id', ''),
            'citing_paper_doi': citing_doi,
            'citing_paper_title': citing_work.get('title', ''),
            'publication_year': pub_year,
            'publication_date': pub_date,
            'years_since_award': years_since_award,
            'authors': '; '.join(authors[:10]) if authors else '',  # Limit to first 10
            'author_count': len(authors),
            'source': source_name,
            'source_type': source.get('type', ''),
            'cited_by_count': citing_work.get('cited_by_count', 0),
            'type': citing_work.get('type', ''),
            'is_oa': citing_work.get('open_access', {}).get('is_oa', False),
            'oa_status': citing_work.get('open_access', {}).get('oa_status', ''),
        }

    def process_paper(self, paper_row: Dict) -> List[Dict]:
        """Process a single Ig Nobel paper and collect its citations."""
        paper_id = paper_row.get('paper_id', f"paper_{paper_row.get('year')}_{paper_row.get('category')}")

        # Handle NaN values from pandas (which are floats)
        doi_raw = paper_row.get('doi')
        if pd.isna(doi_raw) or not doi_raw:
            doi = None
        else:
            doi = str(doi_raw).strip()

        title = paper_row.get('description', '') or paper_row.get('authors', '')
        year = paper_row.get('year')

        print(f"\n  Processing: {paper_id}")
        print(f"    Year: {year}, Category: {paper_row.get('category')}")

        # Try to find the work in OpenAlex
        work = None

        if doi:
            print(f"    Looking up by DOI: {doi}")
            work = self.get_work_by_doi(doi)
            time.sleep(0.11)  # Rate limiting

        if not work and title:
            print(f"    DOI lookup failed, trying title search...")
            work = self.search_work_by_title(title, paper_row.get('authors'), year)
            time.sleep(0.11)

        if not work:
            print(f"    ✗ Not found in OpenAlex")
            self.stats['papers_not_found'] += 1
            return []

        # Extract OpenAlex ID
        openalex_id = work.get('id', '')
        if openalex_id.startswith('https://openalex.org/'):
            openalex_id = openalex_id.split('/')[-1]

        cited_by_count = work.get('cited_by_count', 0)
        print(f"    ✓ Found in OpenAlex: {openalex_id}")
        print(f"    Cited by: {cited_by_count} papers")

        self.stats['papers_found_in_openalex'] += 1

        if cited_by_count == 0:
            return []

        # Get citing papers
        print(f"    Fetching citations...")
        citing_works = self.get_citing_papers(openalex_id)

        print(f"    ✓ Collected {len(citing_works)} citations")

        # Extract citation data
        citations = []
        for citing_work in citing_works:
            citation_data = self.extract_citation_data(
                citing_work,
                paper_id,
                doi or '',
                year
            )
            citations.append(citation_data)

        self.stats['total_citations_collected'] += len(citations)

        return citations

    def collect_all_citations(self, papers_df: pd.DataFrame, test_mode: bool = False,
                             test_limit: int = 10) -> pd.DataFrame:
        """Collect citations for all papers."""

        if test_mode:
            print(f"\n{'='*70}")
            print(f"TEST MODE: Processing first {test_limit} papers")
            print(f"{'='*70}")
            papers_df = papers_df.head(test_limit)

        all_citations = []

        for idx, row in tqdm(papers_df.iterrows(), total=len(papers_df),
                            desc="Collecting citations"):
            self.stats['papers_processed'] += 1

            citations = self.process_paper(row.to_dict())
            all_citations.extend(citations)

            # Save progress periodically
            if len(all_citations) > 0 and len(all_citations) % 1000 == 0:
                self._save_progress(all_citations, suffix='_progress')

        # Convert to DataFrame
        if all_citations:
            citations_df = pd.DataFrame(all_citations)
        else:
            citations_df = pd.DataFrame()

        return citations_df

    def _save_progress(self, citations: List[Dict], suffix: str = ''):
        """Save progress to avoid data loss."""
        if not citations:
            return

        df = pd.DataFrame(citations)
        output_file = OUTPUT_DIR / f"openalex_citations{suffix}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')

    def print_stats(self):
        """Print collection statistics."""
        print(f"\n{'='*70}")
        print("COLLECTION STATISTICS")
        print(f"{'='*70}")
        print(f"Papers processed: {self.stats['papers_processed']}")
        print(f"Papers found in OpenAlex: {self.stats['papers_found_in_openalex']}")
        print(f"Papers not found: {self.stats['papers_not_found']}")
        print(f"Total citations collected: {self.stats['total_citations_collected']}")
        print(f"Total API calls: {self.stats['api_calls']}")
        print(f"Errors: {self.stats['errors']}")

        if self.stats['papers_found_in_openalex'] > 0:
            avg_citations = self.stats['total_citations_collected'] / self.stats['papers_found_in_openalex']
            print(f"Average citations per found paper: {avg_citations:.1f}")

        print(f"{'='*70}\n")


def main(test_mode: bool = True, test_limit: int = 10):
    """Main execution function."""
    print("="*70)
    print("OPENALEX CITATION COLLECTION")
    print("="*70)

    # Load awarded papers
    papers_file = DATA_DIR / "all_ig_nobel_winners.csv"

    if not papers_file.exists():
        print(f"\nError: {papers_file} not found")
        print("Please run parse_html_winners.py first")
        return

    papers_df = pd.read_csv(papers_file)
    print(f"\nLoaded {len(papers_df)} Ig Nobel papers")
    print(f"Papers with DOI: {papers_df['doi'].notna().sum()}")
    print(f"Papers without DOI: {papers_df['doi'].isna().sum()}")

    # Initialize collector
    collector = OpenAlexCitationCollector()

    # Collect citations
    citations_df = collector.collect_all_citations(papers_df, test_mode=test_mode,
                                                   test_limit=test_limit)

    # Print statistics
    collector.print_stats()

    # Save results
    if not citations_df.empty:
        output_file = OUTPUT_DIR / "openalex_citations.csv"
        citations_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {len(citations_df)} citations to {output_file}")

        # Save JSON version
        json_file = OUTPUT_DIR / "openalex_citations.json"
        citations_df.to_json(json_file, orient='records', indent=2)
        print(f"Also saved to {json_file}")

        # Generate summary by year
        if 'publication_year' in citations_df.columns:
            year_summary = citations_df.groupby('publication_year').size().sort_index()
            print(f"\nCitations by year:")
            print(year_summary.to_string())

    else:
        print("\nNo citations collected")

    print(f"\n{'='*70}")
    print("COLLECTION COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Start with test mode
    import sys

    test_mode = '--full' not in sys.argv
    test_limit = 10

    if '--limit' in sys.argv:
        try:
            idx = sys.argv.index('--limit')
            test_limit = int(sys.argv[idx + 1])
        except:
            pass

    main(test_mode=test_mode, test_limit=test_limit)
