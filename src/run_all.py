"""
Orchestration script to run the entire Ig Nobel dataset creation pipeline.
Runs all steps in sequence with error handling and progress reporting.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
try:
    from src import scrape_winners as step1
    from src import enrich_papers as step2
    from src import collect_citations as step3
    from src import generate_dataset as step4
except ImportError:
    # Try without src prefix
    import scrape_winners as step1
    import enrich_papers as step2
    import collect_citations as step3
    import generate_dataset as step4


def print_header(step_num: int, title: str):
    """Print a formatted header for each step."""
    print("\n" + "="*70)
    print(f"STEP {step_num}: {title}")
    print("="*70 + "\n")


def print_separator():
    """Print a separator line."""
    print("\n" + "-"*70 + "\n")


def run_pipeline(skip_scraping: bool = False, skip_citations: bool = False):
    """
    Run the complete pipeline.

    Args:
        skip_scraping: Skip web scraping if data already exists
        skip_citations: Skip citation collection (very time-consuming)
    """
    start_time = datetime.now()
    print("\n" + "="*70)
    print("IG NOBEL PRIZE CITATION ANALYSIS - DATA PIPELINE")
    print("="*70)
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis pipeline will:")
    print("  1. Scrape Ig Nobel winners data")
    print("  2. Enrich papers with publication metadata")
    print("  3. Collect citations to awarded papers")
    print("  4. Generate final dataset and analysis")
    print("\n" + "="*70)

    # Step 1: Scrape winners
    if not skip_scraping:
        print_header(1, "Scraping Ig Nobel Winners")
        try:
            step1.main()
            print("\n✓ Step 1 completed successfully")
        except Exception as e:
            print(f"\n✗ Step 1 failed: {e}")
            print("\nYou can continue with manual data in data/manual_winners.json")
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                return
    else:
        print("\nSkipping Step 1 (scraping) - using existing data")

    print_separator()
    time.sleep(2)

    # Step 2: Enrich papers
    print_header(2, "Enriching Papers with Metadata")
    try:
        step2.main()
        print("\n✓ Step 2 completed successfully")
    except Exception as e:
        print(f"\n✗ Step 2 failed: {e}")
        print("\nCannot continue without enriched paper data")
        return

    print_separator()
    time.sleep(2)

    # Step 3: Collect citations
    if not skip_citations:
        print_header(3, "Collecting Citations")
        print("WARNING: This step may take a LONG time (hours) due to API rate limits")
        print("You can skip this step and run it separately later if needed.\n")

        response = input("Continue with citation collection? (y/n): ")
        if response.lower() == 'y':
            try:
                step3.main()
                print("\n✓ Step 3 completed successfully")
            except Exception as e:
                print(f"\n✗ Step 3 failed: {e}")
                print("\nYou can re-run this step later with: python src/03_collect_citations.py")
        else:
            print("\nSkipping citation collection")
            print("You can run it later with: python src/03_collect_citations.py")
    else:
        print("\nSkipping Step 3 (citation collection) - using existing data")

    print_separator()
    time.sleep(2)

    # Step 4: Generate final dataset
    print_header(4, "Generating Final Dataset")
    try:
        step4.main()
        print("\n✓ Step 4 completed successfully")
    except Exception as e:
        print(f"\n✗ Step 4 failed: {e}")
        print("\nCheck that previous steps completed successfully")
        return

    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*70)
    print("PIPELINE COMPLETE!")
    print("="*70)
    print(f"\nStarted:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print("\nOutput files are in the 'output/' directory")
    print("="*70 + "\n")


def main():
    """Main entry point with command-line argument handling."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Run the Ig Nobel citation analysis data pipeline'
    )
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Skip web scraping step (use existing data)'
    )
    parser.add_argument(
        '--skip-citations',
        action='store_true',
        help='Skip citation collection step (very time-consuming)'
    )

    args = parser.parse_args()

    run_pipeline(
        skip_scraping=args.skip_scraping,
        skip_citations=args.skip_citations
    )


if __name__ == "__main__":
    main()
