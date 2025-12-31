"""
Enhanced scraper specifically for the Improbable Research Ig Nobel winners page.
Uses multiple strategies to bypass blocks and extract complete data.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import re
from typing import List, Dict

DATA_DIR = Path(__file__).parent.parent / "data"


def scrape_with_requests(url: str) -> str:
    """Try scraping with requests library."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

    try:
        print(f"Attempting to fetch {url}...")
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        print(f"✓ Successfully fetched page (status: {response.status_code})")
        return response.text
    except Exception as e:
        print(f"✗ Requests failed: {e}")
        return None


def scrape_with_selenium(url: str) -> str:
    """Try scraping with Selenium (for JavaScript-rendered content)."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        print("Attempting to fetch with Selenium...")

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # Wait for page to load
        time.sleep(3)

        # Get page source
        html = driver.page_source
        driver.quit()

        print("✓ Successfully fetched page with Selenium")
        return html

    except ImportError:
        print("✗ Selenium not available (install with: pip install selenium)")
        return None
    except Exception as e:
        print(f"✗ Selenium failed: {e}")
        return None


def parse_winners_page(html: str) -> List[Dict]:
    """Parse the Improbable Research winners page."""
    soup = BeautifulSoup(html, 'html.parser')
    winners = []

    # The page has links to individual year pages
    # Find all year links
    year_links = []

    # Look for links that contain year patterns
    for link in soup.find_all('a', href=True):
        text = link.get_text()
        href = link['href']

        # Match year patterns (1991-2024)
        year_match = re.search(r'(19\d{2}|20\d{2})', text)
        if year_match:
            year = int(year_match.group(1))
            if 1991 <= year <= 2024:
                year_links.append({
                    'year': year,
                    'url': href if href.startswith('http') else f"https://improbable.com{href}",
                    'text': text.strip()
                })

    # Remove duplicates and sort
    seen_years = set()
    unique_links = []
    for link in year_links:
        if link['year'] not in seen_years:
            seen_years.add(link['year'])
            unique_links.append(link)

    unique_links.sort(key=lambda x: x['year'], reverse=True)

    print(f"\nFound links to {len(unique_links)} year pages:")
    for link in unique_links:
        print(f"  {link['year']}: {link['url']}")

    return unique_links


def scrape_year_page(url: str, year: int) -> List[Dict]:
    """Scrape an individual year's winners page."""
    print(f"\nScraping {year} winners from: {url}")

    html = scrape_with_requests(url)
    if not html:
        html = scrape_with_selenium(url)

    if not html:
        print(f"  ✗ Could not fetch {year} page")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    winners = []

    # Find all prize categories and descriptions
    # The structure varies by year, so we'll use multiple strategies

    # Strategy 1: Look for headings with category names
    category_patterns = [
        'PHYSICS', 'CHEMISTRY', 'MEDICINE', 'BIOLOGY', 'PEACE', 'ECONOMICS',
        'LITERATURE', 'PUBLIC HEALTH', 'ENGINEERING', 'NUTRITION', 'PSYCHOLOGY',
        'MATHEMATICS', 'ENTOMOLOGY', 'FLUID DYNAMICS', 'INTERDISCIPLINARY',
        'ANATOMY', 'COMMUNICATION', 'DEMOGRAPHY', 'PHYSIOLOGY', 'PROBABILITY'
    ]

    # Look for paragraphs or divs containing prize information
    content_blocks = soup.find_all(['p', 'div', 'section'])

    current_category = None
    for block in content_blocks:
        text = block.get_text()

        # Check if this is a category heading
        for pattern in category_patterns:
            if pattern in text.upper():
                # Extract category
                category_match = re.search(rf'\b({pattern}[^:]*)', text.upper())
                if category_match:
                    current_category = category_match.group(1).title()

                    # Try to extract winners and description from same block or next blocks
                    description = text.strip()

                    # Look for DOI links
                    doi = None
                    doi_links = block.find_all('a', href=True)
                    for link in doi_links:
                        href = link['href']
                        if 'doi.org' in href or 'doi:' in href:
                            doi_match = re.search(r'10\.\d{4,}/[^\s\'"]+', href)
                            if doi_match:
                                doi = doi_match.group(0)
                                break

                    winners.append({
                        'year': year,
                        'category': current_category,
                        'description': description[:500],  # Limit length
                        'doi': doi,
                        'source': 'improbable_research'
                    })

    print(f"  Found {len(winners)} prizes for {year}")
    return winners


def main():
    """Main scraping function."""
    print("="*70)
    print("SCRAPING IG NOBEL WINNERS FROM IMPROBABLE RESEARCH")
    print("="*70)

    base_url = "https://improbable.com/ig/winners/"

    # First, get the main page to find all year links
    html = scrape_with_requests(base_url)
    if not html:
        html = scrape_with_selenium(base_url)

    if not html:
        print("\n✗ Failed to fetch main winners page")
        print("\nTrying alternative approach: scraping individual year pages directly...")

        # Fallback: try known year URLs
        year_links = []
        for year in range(1991, 2025):
            year_links.append({
                'year': year,
                'url': f"https://improbable.com/ig/winners/#{year}",
                'text': str(year)
            })
    else:
        year_links = parse_winners_page(html)

    # Scrape each year
    all_winners = []
    for link in year_links:
        year_winners = scrape_year_page(link['url'], link['year'])
        all_winners.extend(year_winners)
        time.sleep(2)  # Be polite

    # Save results
    if all_winners:
        output_file = DATA_DIR / "scraped_winners.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_winners, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"SUCCESS! Scraped {len(all_winners)} winners")
        print(f"Saved to: {output_file}")
        print(f"{'='*70}")
    else:
        print("\n✗ No winners were scraped")
        print("\nYou may need to:")
        print("1. Check your internet connection")
        print("2. Install Selenium: pip install selenium")
        print("3. Install ChromeDriver")
        print("4. Manually copy data from the website")


if __name__ == "__main__":
    main()
