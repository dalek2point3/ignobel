"""
Scrape Ig Nobel Prize winners from various sources.
Handles multiple fallback strategies for data collection.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import re

# Create data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class IgNobelScraper:
    """Scraper for Ig Nobel Prize winners."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.winners = []

    def scrape_wikipedia(self) -> List[Dict]:
        """Scrape Ig Nobel winners from Wikipedia."""
        url = "https://en.wikipedia.org/wiki/List_of_Ig_Nobel_Prize_winners"

        try:
            print(f"Attempting to scrape Wikipedia: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            winners = []

            # Find tables with class 'wikitable'
            tables = soup.find_all('table', {'class': 'wikitable'})

            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 3:
                        year_text = cols[0].get_text(strip=True)
                        category = cols[1].get_text(strip=True)
                        description = cols[2].get_text(strip=True)

                        # Extract year
                        year_match = re.search(r'(\d{4})', year_text)
                        year = int(year_match.group(1)) if year_match else None

                        # Look for DOI links
                        doi = None
                        links = cols[2].find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if 'doi.org' in href:
                                doi_match = re.search(r'10\.\d{4,}/[^\s]+', href)
                                if doi_match:
                                    doi = doi_match.group(0)
                                    break

                        winners.append({
                            'year': year,
                            'category': category,
                            'description': description,
                            'doi': doi,
                            'source': 'wikipedia'
                        })

            print(f"Successfully scraped {len(winners)} winners from Wikipedia")
            return winners

        except Exception as e:
            print(f"Error scraping Wikipedia: {e}")
            return []

    def scrape_improbable(self) -> List[Dict]:
        """Scrape Ig Nobel winners from improbable.com."""
        url = "https://improbable.com/ig/winners/"

        try:
            print(f"Attempting to scrape Improbable Research: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            winners = []

            # Parse the page structure (this will need adjustment based on actual HTML)
            # Look for year headings and prize information
            year_pattern = re.compile(r'(\d{4})')

            # Find all links that might lead to individual year pages
            year_links = soup.find_all('a', href=True)
            for link in year_links:
                year_match = year_pattern.search(link.get_text())
                if year_match:
                    year = int(year_match.group(1))
                    if 1991 <= year <= 2024:  # Ig Nobel started in 1991
                        print(f"Found year: {year}")

            print(f"Successfully scraped {len(winners)} winners from Improbable Research")
            return winners

        except Exception as e:
            print(f"Error scraping Improbable Research: {e}")
            return []

    def load_manual_data(self) -> List[Dict]:
        """Load manually curated data from JSON file."""
        manual_file = DATA_DIR / "manual_winners.json"

        if manual_file.exists():
            try:
                with open(manual_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"Loaded {len(data)} manually curated winners")
                return data
            except Exception as e:
                print(f"Error loading manual data: {e}")
                return []
        else:
            print(f"No manual data file found at {manual_file}")
            return []

    def save_winners(self, winners: List[Dict], filename: str = "raw_winners.csv"):
        """Save winners to CSV file."""
        if not winners:
            print("No winners to save")
            return

        df = pd.DataFrame(winners)
        output_file = DATA_DIR / filename
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {len(winners)} winners to {output_file}")

        # Also save as JSON for easier manual editing
        json_file = DATA_DIR / filename.replace('.csv', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(winners, f, indent=2, ensure_ascii=False)
        print(f"Also saved to {json_file}")

    def run(self):
        """Run the scraping process with multiple fallback strategies."""
        all_winners = []

        # Strategy 1: Try Wikipedia
        wikipedia_winners = self.scrape_wikipedia()
        if wikipedia_winners:
            all_winners.extend(wikipedia_winners)

        time.sleep(2)  # Be polite

        # Strategy 2: Try Improbable Research
        improbable_winners = self.scrape_improbable()
        if improbable_winners:
            all_winners.extend(improbable_winners)

        # Strategy 3: Load manual data
        manual_winners = self.load_manual_data()
        if manual_winners:
            all_winners.extend(manual_winners)

        # Remove duplicates based on year and category
        seen = set()
        unique_winners = []
        for winner in all_winners:
            key = (winner.get('year'), winner.get('category'))
            if key not in seen:
                seen.add(key)
                unique_winners.append(winner)

        print(f"\nTotal unique winners collected: {len(unique_winners)}")

        if unique_winners:
            self.save_winners(unique_winners)
        else:
            print("\nNo winners were collected. You may need to:")
            print("1. Check your internet connection")
            print("2. Use a VPN if the sites are blocked")
            print("3. Create a manual_winners.json file in the data/ directory")
            print("4. Use the provided template in data/manual_winners_template.json")


def main():
    """Main execution function."""
    print("=== Ig Nobel Prize Winners Scraper ===\n")

    scraper = IgNobelScraper()
    scraper.run()

    print("\n=== Scraping Complete ===")


if __name__ == "__main__":
    main()
