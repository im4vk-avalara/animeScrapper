#!/usr/bin/env python3
"""
Zoroto Anime List Scraper

Scrapes all anime titles and URLs from zoroto.com.in anime list page.
Handles pagination and saves results to JSON file.

Usage:
    python zoroto_scraper.py
    python zoroto_scraper.py --output anime_list.json --max-pages 10
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin
import sys

try:
    import toon
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZorotoAnimeListScraper:
    """Scraper for zoroto.com.in anime list"""
    
    def __init__(self, base_url: str = "https://zoroto.com.in/az-list/", 
                 delay: float = 1.0):
        """
        Initialize the scraper.
        
        Args:
            base_url: Base URL for the anime list page
            delay: Delay between requests in seconds (be respectful!)
        """
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def fetch_page(self, page_num: Optional[int] = None, letter: Optional[str] = None) -> Optional[BeautifulSoup]:
        """
        Fetch a page from the anime list.
        
        Args:
            page_num: Page number to fetch (None for first page)
            letter: Letter filter to apply (e.g., 'A', '0-9')
            
        Returns:
            BeautifulSoup object or None if request failed
        """
        try:
            if letter:
                if page_num and page_num > 1:
                    url = f"{self.base_url}page/{page_num}/?show={letter}"
                else:
                    url = f"{self.base_url}?show={letter}"
            elif page_num and page_num > 1:
                url = f"{self.base_url}page/{page_num}/"
            else:
                url = self.base_url
                
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return BeautifulSoup(response.text, 'html.parser')
            
        except requests.RequestException as e:
            logger.error(f"Error fetching page {page_num}: {e}")
            return None
    
    def extract_anime_list(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract anime titles and URLs from a page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of dictionaries with 'title' and 'url' keys
        """
        anime_list = []
        
        # Find all anime article items: <article class="bs">
        articles = soup.find_all('article', class_='bs')
        
        if not articles:
            logger.warning("Could not find anime articles on page")
            return anime_list
        
        # Extract all anime items
        for article in articles:
            # Find the link inside <div class="bsx">
            bsx = article.find('div', class_='bsx')
            if bsx:
                link = bsx.find('a', itemprop='url')
                if link:
                    title = link.get('title', '')
                    url = link.get('href', '')
                    
                    # Also try to get title from h2 if not available
                    if not title:
                        h2 = link.find('h2', itemprop='headline')
                        if h2:
                            title = h2.get_text(strip=True)
                    
                    if url and title:
                        anime_list.append({
                            'title': title,
                            'url': url
                        })
        
        logger.info(f"Found {len(anime_list)} anime on this page")
        return anime_list
    
    def get_max_page_number(self, soup: BeautifulSoup) -> int:
        """
        Determine the maximum page number from pagination.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Maximum page number
        """
        try:
            # Find pagination: <div class="pagination">
            pagination = soup.find('div', class_='pagination')
            if not pagination:
                logger.warning("No pagination found, assuming single page")
                return 1
            
            # Find all page number links
            page_links = pagination.find_all('a', class_='page-numbers')
            max_page = 1
            
            for link in page_links:
                # Skip "Next" links
                if 'next' in link.get_text(strip=True).lower():
                    continue
                    
                # Try to extract page number from href
                href = link.get('href', '')
                if '/page/' in href:
                    try:
                        # Extract number from URL like /page/2/
                        page_part = href.split('/page/')[-1]
                        page_num = int(page_part.rstrip('/').split('/')[0].split('?')[0])
                        max_page = max(max_page, page_num)
                    except (ValueError, IndexError):
                        pass
                
                # Also try to get from text
                text = link.get_text(strip=True)
                if text.isdigit():
                    max_page = max(max_page, int(text))
            
            # Check for current page span
            current_span = pagination.find('span', class_='current')
            if current_span:
                text = current_span.get_text(strip=True)
                if text.isdigit():
                    max_page = max(max_page, int(text))
            
            logger.info(f"Detected maximum page number: {max_page}")
            return max_page
            
        except Exception as e:
            logger.error(f"Error detecting max page: {e}")
            return 1
    
    def scrape_all_pages(self, max_pages: Optional[int] = None, letter: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Scrape all pages of the anime list.
        
        Args:
            max_pages: Maximum number of pages to scrape (None for all)
            letter: Optional letter filter
            
        Returns:
            List of all anime with titles and URLs
        """
        all_anime = []
        
        # Fetch first page to determine total pages
        logger.info("Fetching first page to detect total pages...")
        first_page = self.fetch_page(letter=letter)
        
        if not first_page:
            logger.error("Failed to fetch first page")
            return all_anime
        
        # Extract anime from first page
        anime_list = self.extract_anime_list(first_page)
        all_anime.extend(anime_list)
        
        # Determine total pages
        total_pages = self.get_max_page_number(first_page)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        logger.info(f"Will scrape {total_pages} pages total")
        
        # Scrape remaining pages
        for page_num in range(2, total_pages + 1):
            # Rate limiting
            time.sleep(self.delay)
            
            soup = self.fetch_page(page_num, letter=letter)
            if soup:
                anime_list = self.extract_anime_list(soup)
                all_anime.extend(anime_list)
            else:
                logger.warning(f"Skipping page {page_num} due to fetch error")
        
        logger.info(f"Total anime scraped: {len(all_anime)}")
        return all_anime
    
    def scrape_by_letter(self, letter: str, max_pages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Scrape anime list filtered by first letter.
        
        Args:
            letter: Letter to filter by (A-Z, 0-9, or '.')
            max_pages: Maximum pages to scrape for this letter
            
        Returns:
            List of anime starting with that letter
        """
        all_anime = []
        
        if letter.upper() == 'ALL':
            letter = None
        elif letter in '0123456789':
            letter = '0-9'
        
        logger.info(f"Fetching anime starting with '{letter}'...")
        
        # Scrape all pages for this letter
        all_anime = self.scrape_all_pages(max_pages=max_pages, letter=letter)
        
        return all_anime
    
    def scrape_all_letters(self, max_pages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Scrape all anime by iterating through all letters A-Z and 0-9.
        This is more thorough than just pagination.
        
        Args:
            max_pages: Maximum pages per letter
            
        Returns:
            Complete list of all anime
        """
        all_anime = []
        seen_urls = set()
        
        letters = ['.', '0-9'] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        
        for letter in letters:
            logger.info(f"\n{'='*50}")
            logger.info(f"Scraping anime starting with: {letter}")
            logger.info(f"{'='*50}")
            
            anime_list = self.scrape_by_letter(letter, max_pages=max_pages)
            
            # Deduplicate
            for anime in anime_list:
                if anime['url'] not in seen_urls:
                    all_anime.append(anime)
                    seen_urls.add(anime['url'])
            
            logger.info(f"Total unique anime so far: {len(all_anime)}")
            
            # Be respectful with delays between letter categories
            time.sleep(self.delay * 2)
        
        return all_anime
    
    def save_to_json(self, anime_list: List[Dict[str, str]], filename: str):
        """
        Save anime list to JSON file.
        
        Args:
            anime_list: List of anime dictionaries
            filename: Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(anime_list, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(anime_list)} anime to {filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def save_to_csv(self, anime_list: List[Dict[str, str]], filename: str):
        """
        Save anime list to CSV file.
        
        Args:
            anime_list: List of anime dictionaries
            filename: Output filename
        """
        try:
            import csv
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'url'])
                writer.writeheader()
                writer.writerows(anime_list)
            logger.info(f"Saved {len(anime_list)} anime to {filename}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
    
    def save_to_toon(self, anime_list: List[Dict[str, str]], filename: str):
        """
        Save anime list to TOON (Token-Oriented Object Notation) file.
        
        Args:
            anime_list: List of anime dictionaries
            filename: Output filename
        """
        if not TOON_AVAILABLE:
            logger.error("pytoon not installed. Run: pip install pytoon")
            return
        
        try:
            # Wrap in object for TOON format
            data = {'anime_list': anime_list}
            toon_str = toon.encode(data)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(toon_str)
            logger.info(f"Saved {len(anime_list)} anime to {filename}")
        except Exception as e:
            logger.error(f"Error saving to TOON: {e}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Scrape anime list from zoroto.com.in'
    )
    parser.add_argument(
        '-o', '--output',
        default='zoroto_anime_list.json',
        help='Output filename (default: zoroto_anime_list.json)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['json', 'csv', 'toon'],
        default='json',
        help='Output format: json, csv, or toon (default: json)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to scrape per section (default: all)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--mode',
        choices=['pagination', 'letters', 'quick'],
        default='quick',
        help='Scraping mode: pagination (simple), letters (complete), quick (first page only)'
    )
    parser.add_argument(
        '--letter',
        help='Scrape only anime starting with specific letter (A-Z, 0-9, or .)'
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_args()
    
    logger.info("Starting Zoroto Anime List Scraper")
    logger.info(f"Output: {args.output} ({args.format})")
    logger.info(f"Mode: {args.mode}")
    
    # Initialize scraper
    scraper = ZorotoAnimeListScraper(delay=args.delay)
    
    # Scrape based on mode
    if args.letter:
        logger.info(f"Scraping anime starting with letter: {args.letter}")
        anime_list = scraper.scrape_by_letter(args.letter, max_pages=args.max_pages)
    elif args.mode == 'quick':
        logger.info("Quick mode: Scraping first page only")
        soup = scraper.fetch_page()
        anime_list = scraper.extract_anime_list(soup) if soup else []
    elif args.mode == 'letters':
        logger.info("Complete mode: Scraping all letters A-Z, 0-9, and special")
        anime_list = scraper.scrape_all_letters(max_pages=args.max_pages)
    else:  # pagination
        logger.info("Pagination mode: Scraping all pages")
        anime_list = scraper.scrape_all_pages(max_pages=args.max_pages)
    
    # Save results
    if anime_list:
        if args.format == 'csv':
            scraper.save_to_csv(anime_list, args.output)
        elif args.format == 'toon':
            scraper.save_to_toon(anime_list, args.output)
        else:
            scraper.save_to_json(anime_list, args.output)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Scraping completed successfully!")
        logger.info(f"Total anime collected: {len(anime_list)}")
        logger.info(f"Output file: {args.output}")
        logger.info(f"{'='*50}")
    else:
        logger.error("No anime data collected!")
        sys.exit(1)


if __name__ == "__main__":
    main()

