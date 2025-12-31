"""
Generate final dataset and perform initial analysis.
Creates summary statistics and visualizations.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns


DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class DatasetGenerator:
    """Generate final dataset and analysis."""

    def __init__(self):
        self.awarded_papers = None
        self.citations = None

    def load_data(self):
        """Load awarded papers and citations data."""
        print("Loading data...")

        # Load awarded papers
        awarded_path = DATA_DIR / "awarded_papers.csv"
        if awarded_path.exists():
            self.awarded_papers = pd.read_csv(awarded_path)
            print(f"Loaded {len(self.awarded_papers)} awarded papers")
        else:
            raise FileNotFoundError(f"Awarded papers not found at {awarded_path}")

        # Load citations
        citations_path = DATA_DIR / "citations.csv"
        if citations_path.exists():
            self.citations = pd.read_csv(citations_path)
            print(f"Loaded {len(self.citations)} citations")
        else:
            print("Warning: No citations data found")
            self.citations = pd.DataFrame()

    def create_yearly_citation_analysis(self) -> pd.DataFrame:
        """Create analysis of citations by year for each paper."""
        if self.citations.empty:
            print("No citations data available for yearly analysis")
            return pd.DataFrame()

        # Create yearly citation counts
        yearly_citations = self.citations.groupby(
            ['focal_paper_id', 'citation_year']
        ).size().reset_index(name='citation_count')

        # Merge with awarded papers to get award year
        yearly_citations = yearly_citations.merge(
            self.awarded_papers[['paper_id', 'year', 'category']],
            left_on='focal_paper_id',
            right_on='paper_id',
            how='left'
        )

        # Calculate years since award
        yearly_citations['years_since_award'] = (
            yearly_citations['citation_year'] - yearly_citations['year']
        )

        # Flag pre- and post-award
        yearly_citations['period'] = yearly_citations['years_since_award'].apply(
            lambda x: 'pre_award' if x < 0 else ('award_year' if x == 0 else 'post_award')
        )

        return yearly_citations

    def calculate_citation_metrics(self) -> pd.DataFrame:
        """Calculate citation metrics for each awarded paper."""
        if self.citations.empty:
            print("No citations data available for metrics")
            return self.awarded_papers

        metrics = []

        for _, paper in self.awarded_papers.iterrows():
            paper_citations = self.citations[
                self.citations['focal_paper_id'] == paper['paper_id']
            ].copy()

            award_year = paper['year']

            # Calculate various metrics
            total_citations = len(paper_citations)

            # Citations before award
            pre_award = paper_citations[
                paper_citations['citation_year'] < award_year
            ] if 'citation_year' in paper_citations.columns else pd.DataFrame()

            # Citations in award year
            award_year_cites = paper_citations[
                paper_citations['citation_year'] == award_year
            ] if 'citation_year' in paper_citations.columns else pd.DataFrame()

            # Citations after award (1 year, 2 years, 5 years)
            post_1yr = paper_citations[
                (paper_citations['citation_year'] > award_year) &
                (paper_citations['citation_year'] <= award_year + 1)
            ] if 'citation_year' in paper_citations.columns else pd.DataFrame()

            post_2yr = paper_citations[
                (paper_citations['citation_year'] > award_year) &
                (paper_citations['citation_year'] <= award_year + 2)
            ] if 'citation_year' in paper_citations.columns else pd.DataFrame()

            post_5yr = paper_citations[
                (paper_citations['citation_year'] > award_year) &
                (paper_citations['citation_year'] <= award_year + 5)
            ] if 'citation_year' in paper_citations.columns else pd.DataFrame()

            metrics.append({
                'paper_id': paper['paper_id'],
                'total_citations': total_citations,
                'citations_pre_award': len(pre_award),
                'citations_award_year': len(award_year_cites),
                'citations_post_1yr': len(post_1yr),
                'citations_post_2yr': len(post_2yr),
                'citations_post_5yr': len(post_5yr)
            })

        metrics_df = pd.DataFrame(metrics)

        # Merge with awarded papers
        result = self.awarded_papers.merge(metrics_df, on='paper_id', how='left')

        return result

    def generate_summary_statistics(self) -> Dict:
        """Generate summary statistics for the dataset."""
        stats = {
            'dataset_generated': datetime.now().isoformat(),
            'awarded_papers': {
                'total': len(self.awarded_papers),
                'with_doi': self.awarded_papers['doi'].notna().sum(),
                'year_range': f"{self.awarded_papers['year'].min()}-{self.awarded_papers['year'].max()}",
                'categories': self.awarded_papers['category'].nunique(),
            }
        }

        if not self.citations.empty:
            stats['citations'] = {
                'total': len(self.citations),
                'unique_citing_papers': self.citations['citing_paper_doi'].nunique(),
                'papers_with_citations': self.citations['focal_paper_id'].nunique(),
                'avg_citations_per_paper': len(self.citations) / len(self.awarded_papers),
            }

            if 'citation_year' in self.citations.columns:
                stats['citations']['year_range'] = (
                    f"{self.citations['citation_year'].min()}-"
                    f"{self.citations['citation_year'].max()}"
                )

        return stats

    def save_final_dataset(self):
        """Save the final cleaned dataset."""
        print("\nSaving final dataset...")

        # Save awarded papers with citation metrics
        papers_with_metrics = self.calculate_citation_metrics()
        papers_output = OUTPUT_DIR / "ig_nobel_awarded_papers.csv"
        papers_with_metrics.to_csv(papers_output, index=False, encoding='utf-8')
        print(f"Saved awarded papers to {papers_output}")

        # Save citations
        if not self.citations.empty:
            citations_output = OUTPUT_DIR / "ig_nobel_citations.csv"
            self.citations.to_csv(citations_output, index=False, encoding='utf-8')
            print(f"Saved citations to {citations_output}")

            # Save yearly citation analysis
            yearly_analysis = self.create_yearly_citation_analysis()
            if not yearly_analysis.empty:
                yearly_output = OUTPUT_DIR / "yearly_citation_analysis.csv"
                yearly_analysis.to_csv(yearly_output, index=False, encoding='utf-8')
                print(f"Saved yearly analysis to {yearly_output}")

        # Save summary statistics
        stats = self.generate_summary_statistics()
        stats_output = OUTPUT_DIR / "dataset_summary.json"
        with open(stats_output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"Saved summary statistics to {stats_output}")

        return stats

    def print_summary(self, stats: Dict):
        """Print summary statistics."""
        print("\n" + "="*60)
        print("DATASET SUMMARY")
        print("="*60)

        print(f"\nGenerated: {stats['dataset_generated']}")

        print("\nAWARDED PAPERS:")
        for key, value in stats['awarded_papers'].items():
            print(f"  {key}: {value}")

        if 'citations' in stats:
            print("\nCITATIONS:")
            for key, value in stats['citations'].items():
                print(f"  {key}: {value}")

        print("\n" + "="*60)


def main():
    """Main execution function."""
    print("=== Generating Final Ig Nobel Dataset ===\n")

    generator = DatasetGenerator()

    try:
        generator.load_data()
        stats = generator.save_final_dataset()
        generator.print_summary(stats)

        print("\n=== Dataset Generation Complete ===")
        print(f"\nFinal files saved to: {OUTPUT_DIR}")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease run the previous scripts first:")
        print("  1. 01_scrape_winners.py")
        print("  2. 02_enrich_papers.py")
        print("  3. 03_collect_citations.py")
        return
    except Exception as e:
        print(f"\nError during dataset generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
