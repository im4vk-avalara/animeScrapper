#!/usr/bin/env python3
"""
Anime Episode Scraper

Reads anime list from JSON and scrapes episode URLs for each anime.
Saves anime details and episodes in organized folder structure.

Usage:
    python anime_episode_scraper.py --input zoroto_complete.json
    python anime_episode_scraper.py --input zoroto_complete.json --limit 10 --resume
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
import logging
import os
import re
from typing import List, Dict, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse
import hashlib

try:
    import toon
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('anime_episode_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AnimeEpisodeScraper:
    """Scraper for extracting episode URLs from anime pages"""
    
    def __init__(self, output_dir: str = "anime_data", delay: float = 1.5, output_format: str = "json"):
        """
        Initialize the scraper.
        
        Args:
            output_dir: Directory to save anime data
            delay: Delay between requests in seconds
            output_format: Output format - 'json' or 'toon'
        """
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.output_format = output_format
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.html_dir = self.output_dir / "html"
        self.html_dir.mkdir(exist_ok=True)
        self.episodes_dir = self.output_dir / "episodes"
        self.episodes_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.completed = self.load_progress()
        
    def load_progress(self) -> set:
        """Load previously completed anime URLs"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('completed', []))
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        return set()
    
    def save_progress(self, url: str):
        """Save progress after completing an anime"""
        self.completed.add(url)
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump({'completed': list(self.completed)}, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
    def sanitize_filename(self, title: str) -> str:
        """
        Create a safe filename from anime title.
        
        Args:
            title: Anime title
            
        Returns:
            Safe filename string
        """
        # Remove or replace unsafe characters
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', '_', safe.strip())
        # Limit length
        if len(safe) > 200:
            safe = safe[:200]
        return safe or "unnamed"
    
    def get_url_hash(self, url: str) -> str:
        """Get short hash of URL for unique identification"""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def fetch_anime_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch an anime page.
        
        Args:
            url: URL of anime page
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_episodes(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """
        Extract episode information from anime page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of episode dictionaries with episode number and URL
        """
        episodes = []
        
        # Try multiple patterns for episode listings
        
        # Pattern 1: Episode list in <div class="eplister">
        eplister = soup.find('div', class_='eplister')
        if eplister:
            episode_links = eplister.find_all('a')
            for link in episode_links:
                href = link.get('href')
                if href:
                    # Try to extract episode number
                    ep_num_div = link.find('div', class_='epl-num')
                    ep_num = ep_num_div.get_text(strip=True) if ep_num_div else None
                    
                    # Try to get episode title
                    ep_title_div = link.find('div', class_='epl-title')
                    ep_title = ep_title_div.get_text(strip=True) if ep_title_div else None
                    
                    episodes.append({
                        'episode_number': ep_num or f"Episode {len(episodes) + 1}",
                        'episode_title': ep_title,
                        'url': urljoin(base_url, href)
                    })
        
        # Pattern 2: Episode list in <ul> with episode links
        if not episodes:
            episode_lists = soup.find_all('ul', class_=re.compile(r'episode|eps'))
            for ul in episode_lists:
                links = ul.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if href and ('episode' in href.lower() or 'ep' in href.lower()):
                        episodes.append({
                            'episode_number': text or f"Episode {len(episodes) + 1}",
                            'episode_title': None,
                            'url': urljoin(base_url, href)
                        })
        
        # Pattern 3: Episode links with data attributes
        if not episodes:
            ep_links = soup.find_all('a', {'data-episode': True})
            for link in ep_links:
                href = link.get('href')
                ep_num = link.get('data-episode')
                if href:
                    episodes.append({
                        'episode_number': ep_num or f"Episode {len(episodes) + 1}",
                        'episode_title': link.get_text(strip=True),
                        'url': urljoin(base_url, href)
                    })
        
        # Pattern 4: Direct episode links in the page
        if not episodes:
            all_links = soup.find_all('a', href=re.compile(r'episode|ep-?\d+', re.IGNORECASE))
            for link in all_links:
                href = link.get('href')
                if href:
                    # Extract episode number from URL or text
                    ep_match = re.search(r'ep(?:isode)?-?(\d+)', href, re.IGNORECASE)
                    ep_num = ep_match.group(1) if ep_match else None
                    
                    episodes.append({
                        'episode_number': f"Episode {ep_num}" if ep_num else link.get_text(strip=True),
                        'episode_title': None,
                        'url': urljoin(base_url, href)
                    })
        
        logger.info(f"Found {len(episodes)} episodes")
        return episodes
    
    def extract_anime_metadata(self, soup: BeautifulSoup) -> Dict[str, any]:
        """
        Extract metadata from anime page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Dictionary with anime metadata
        """
        metadata = {}
        
        # Try to get anime title
        title_elem = soup.find('h1', class_='entry-title')
        if not title_elem:
            title_elem = soup.find('h1')
        metadata['title'] = title_elem.get_text(strip=True) if title_elem else None
        
        # Try to get description
        desc_elem = soup.find('div', class_='entry-content')
        if not desc_elem:
            desc_elem = soup.find('div', itemprop='description')
        metadata['description'] = desc_elem.get_text(strip=True) if desc_elem else None
        
        # Try to get genres
        genres = []
        genre_links = soup.find_all('a', href=re.compile(r'/genre/'))
        for link in genre_links:
            genres.append(link.get_text(strip=True))
        metadata['genres'] = genres
        
        # Try to get status
        status_elem = soup.find('span', string=re.compile(r'Status', re.IGNORECASE))
        if status_elem:
            status_parent = status_elem.find_parent()
            if status_parent:
                metadata['status'] = status_parent.get_text(strip=True).replace('Status:', '').strip()
        
        # Try to get rating
        rating_elem = soup.find('div', class_='rating')
        if rating_elem:
            score = rating_elem.find('div', class_='numscore')
            metadata['rating'] = score.get_text(strip=True) if score else None
        
        return metadata
    
    def scrape_anime(self, anime: Dict[str, str]) -> Optional[Dict[str, any]]:
        """
        Scrape a single anime page.
        
        Args:
            anime: Dictionary with 'title' and 'url'
            
        Returns:
            Dictionary with anime data and episodes or None if failed
        """
        url = anime['url']
        title = anime['title']
        
        # Check if already completed
        if url in self.completed:
            logger.info(f"Skipping already completed: {title}")
            return None
        
        # Fetch page
        soup = self.fetch_anime_page(url)
        if not soup:
            return None
        
        # Extract data
        metadata = self.extract_anime_metadata(soup)
        episodes = self.extract_episodes(soup, url)
        
        # Prepare result
        result = {
            'title': title,
            'url': url,
            'metadata': metadata,
            'episodes': episodes,
            'episode_count': len(episodes),
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return result
    
    def save_anime_data(self, anime_data: Dict[str, any]):
        """
        Save anime data to files.
        
        Args:
            anime_data: Dictionary with anime data
        """
        title = anime_data['title']
        url = anime_data['url']
        url_hash = self.get_url_hash(url)
        safe_title = self.sanitize_filename(title)
        
        # Create filename with hash to ensure uniqueness
        filename = f"{safe_title}_{url_hash}"
        
        # Determine file extension based on format
        ext = '.toon' if self.output_format == 'toon' else '.json'
        episodes_file = self.episodes_dir / f"{filename}{ext}"
        
        try:
            if self.output_format == 'toon' and TOON_AVAILABLE:
                toon_str = toon.encode(anime_data)
                with open(episodes_file, 'w', encoding='utf-8') as f:
                    f.write(toon_str)
            else:
                with open(episodes_file, 'w', encoding='utf-8') as f:
                    json.dump(anime_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved episodes data to: {episodes_file}")
        except Exception as e:
            logger.error(f"Error saving episodes file: {e}")
    
    def scrape_all(self, anime_list: List[Dict[str, str]], limit: Optional[int] = None, resume: bool = True):
        """
        Scrape all anime from the list.
        
        Args:
            anime_list: List of anime dictionaries
            limit: Maximum number to scrape (None for all)
            resume: Whether to resume from previous run
        """
        total = len(anime_list)
        if limit:
            total = min(total, limit)
        
        completed_count = len(self.completed)
        logger.info(f"Starting scrape of {total} anime ({completed_count} already completed)")
        
        scraped = 0
        for i, anime in enumerate(anime_list[:limit] if limit else anime_list, 1):
            # Skip if already completed and resume is enabled
            if resume and anime['url'] in self.completed:
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {i}/{total}: {anime['title']}")
            logger.info(f"{'='*60}")
            
            try:
                # Scrape anime
                anime_data = self.scrape_anime(anime)
                
                if anime_data:
                    # Save data
                    self.save_anime_data(anime_data)
                    
                    # Mark as completed
                    self.save_progress(anime['url'])
                    scraped += 1
                    
                    logger.info(f"✓ Successfully scraped: {anime['title']} ({anime_data['episode_count']} episodes)")
                else:
                    logger.warning(f"✗ Failed to scrape: {anime['title']}")
                
            except Exception as e:
                logger.error(f"Error processing {anime['title']}: {e}", exc_info=True)
            
            # Rate limiting
            if i < total:
                time.sleep(self.delay)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping complete!")
        logger.info(f"Total processed: {scraped}")
        logger.info(f"Total completed (including previous): {len(self.completed)}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"{'='*60}")


def load_anime_list(filepath: str) -> List[Dict[str, str]]:
    """Load anime list from JSON or TOON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to detect format based on extension or content
        if filepath.endswith('.toon'):
            if not TOON_AVAILABLE:
                logger.error("python-toon not installed. Run: pip install python-toon")
                return []
            data = toon.decode(content)
            # Handle wrapped format
            return data.get('anime_list', data) if isinstance(data, dict) else data
        else:
            return json.loads(content)
    except Exception as e:
        logger.error(f"Error loading anime list: {e}")
        return []


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Scrape episode URLs for anime from list'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input JSON file with anime list'
    )
    parser.add_argument(
        '-o', '--output',
        default='anime_data',
        help='Output directory for anime data (default: anime_data)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of anime to scrape'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.5,
        help='Delay between requests in seconds (default: 1.5)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run (skip already completed)'
    )
    parser.add_argument(
        '--no-resume',
        dest='resume',
        action='store_false',
        help='Start fresh (ignore previous progress)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['json', 'toon'],
        default='json',
        help='Output format: json or toon (default: json)'
    )
    parser.set_defaults(resume=True)
    
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_args()
    
    logger.info("Starting Anime Episode Scraper")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Output directory: {args.output}")
    
    # Load anime list
    anime_list = load_anime_list(args.input)
    if not anime_list:
        logger.error("No anime found in input file!")
        return
    
    logger.info(f"Loaded {len(anime_list)} anime from list")
    
    # Initialize scraper
    scraper = AnimeEpisodeScraper(
        output_dir=args.output,
        delay=args.delay,
        output_format=args.format
    )
    
    # Start scraping
    scraper.scrape_all(
        anime_list=anime_list,
        limit=args.limit,
        resume=args.resume
    )


if __name__ == "__main__":
    main()

