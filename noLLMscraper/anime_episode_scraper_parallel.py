#!/usr/bin/env python3
"""
Parallel Anime Episode Scraper

Fast parallel version using threading to scrape multiple anime simultaneously.
MUCH faster than sequential version (5-10x speedup).

Usage:
    python anime_episode_scraper_parallel.py --input zoroto_complete.json
    python anime_episode_scraper_parallel.py --input zoroto_complete.json --workers 10 --limit 100
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
        logging.FileHandler('anime_episode_scraper_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ParallelAnimeEpisodeScraper:
    """Fast parallel scraper for extracting episode URLs from anime pages"""
    
    def __init__(self, output_dir: str = "anime_data", workers: int = 5, 
                 delay: float = 0.2, output_format: str = "json"):
        """
        Initialize the parallel scraper.
        
        Args:
            output_dir: Directory to save anime data
            workers: Number of parallel workers (threads)
            delay: Delay between requests per worker in seconds
            output_format: Output format - 'json' or 'toon'
        """
        self.output_dir = Path(output_dir)
        self.workers = workers
        self.delay = delay
        self.output_format = output_format
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.episodes_dir = self.output_dir / "episodes"
        self.episodes_dir.mkdir(exist_ok=True)
        
        # Progress tracking with thread safety
        self.progress_file = self.output_dir / "progress.json"
        self.completed = self.load_progress()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_anime': 0,
            'total_episodes': 0,
            'failed_anime': 0
        }
        self.stats_lock = threading.Lock()
    
    def create_session(self):
        """Create a new session for thread safety"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        return session
    
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
        """Save progress (thread-safe)"""
        with self.lock:
            self.completed.add(url)
            try:
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump({'completed': list(self.completed)}, f, indent=2)
            except Exception as e:
                logger.error(f"Could not save progress: {e}")
    
    def sanitize_filename(self, title: str) -> str:
        """Create a safe filename from anime title"""
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', '_', safe.strip())
        if len(safe) > 200:
            safe = safe[:200]
        return safe or "unnamed"
    
    def get_url_hash(self, url: str) -> str:
        """Get short hash of URL for unique identification"""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def fetch_anime_page(self, url: str, session: requests.Session) -> Optional[BeautifulSoup]:
        """Fetch an anime page"""
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_episodes(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract episode information from anime page"""
        episodes = []
        
        # Pattern 1: Episode list in <div class="eplister">
        eplister = soup.find('div', class_='eplister')
        if eplister:
            episode_links = eplister.find_all('a')
            for link in episode_links:
                href = link.get('href')
                if href:
                    ep_num_div = link.find('div', class_='epl-num')
                    ep_num = ep_num_div.get_text(strip=True) if ep_num_div else None
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
                    ep_match = re.search(r'ep(?:isode)?-?(\d+)', href, re.IGNORECASE)
                    ep_num = ep_match.group(1) if ep_match else None
                    episodes.append({
                        'episode_number': f"Episode {ep_num}" if ep_num else link.get_text(strip=True),
                        'episode_title': None,
                        'url': urljoin(base_url, href)
                    })
        
        return episodes
    
    def extract_anime_metadata(self, soup: BeautifulSoup) -> Dict[str, any]:
        """Extract metadata from anime page"""
        metadata = {}
        
        title_elem = soup.find('h1', class_='entry-title')
        if not title_elem:
            title_elem = soup.find('h1')
        metadata['title'] = title_elem.get_text(strip=True) if title_elem else None
        
        desc_elem = soup.find('div', class_='entry-content')
        if not desc_elem:
            desc_elem = soup.find('div', itemprop='description')
        metadata['description'] = desc_elem.get_text(strip=True) if desc_elem else None
        
        genres = []
        genre_links = soup.find_all('a', href=re.compile(r'/genre/'))
        for link in genre_links:
            genres.append(link.get_text(strip=True))
        metadata['genres'] = genres
        
        status_elem = soup.find('span', string=re.compile(r'Status', re.IGNORECASE))
        if status_elem:
            status_parent = status_elem.find_parent()
            if status_parent:
                metadata['status'] = status_parent.get_text(strip=True).replace('Status:', '').strip()
        
        rating_elem = soup.find('div', class_='rating')
        if rating_elem:
            score = rating_elem.find('div', class_='numscore')
            metadata['rating'] = score.get_text(strip=True) if score else None
        
        return metadata
    
    def scrape_single_anime(self, anime: Dict[str, str], session: requests.Session) -> Optional[Dict[str, any]]:
        """Scrape a single anime page (thread-safe)"""
        url = anime['url']
        title = anime['title']
        
        # Fetch page
        soup = self.fetch_anime_page(url, session)
        if not soup:
            with self.stats_lock:
                self.stats['failed_anime'] += 1
            return None
        
        # Extract data
        metadata = self.extract_anime_metadata(soup)
        episodes = self.extract_episodes(soup, url)
        
        # Update stats
        with self.stats_lock:
            self.stats['total_anime'] += 1
            self.stats['total_episodes'] += len(episodes)
        
        # Rate limiting per worker
        time.sleep(self.delay)
        
        return {
            'title': title,
            'url': url,
            'metadata': metadata,
            'episodes': episodes,
            'episode_count': len(episodes),
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def save_anime_data(self, anime_data: Dict[str, any]):
        """Save anime data to file (thread-safe)"""
        title = anime_data['title']
        url = anime_data['url']
        url_hash = self.get_url_hash(url)
        safe_title = self.sanitize_filename(title)
        
        filename = f"{safe_title}_{url_hash}"
        ext = '.toon' if self.output_format == 'toon' else '.json'
        episodes_file = self.episodes_dir / f"{filename}{ext}"
        
        try:
            with self.lock:
                if self.output_format == 'toon' and TOON_AVAILABLE:
                    toon_str = toon.encode(anime_data)
                    with open(episodes_file, 'w', encoding='utf-8') as f:
                        f.write(toon_str)
                else:
                    with open(episodes_file, 'w', encoding='utf-8') as f:
                        json.dump(anime_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving anime data: {e}")
    
    def scrape_all(self, anime_list: List[Dict[str, str]], limit: Optional[int] = None, resume: bool = True):
        """
        Scrape all anime in parallel.
        
        Args:
            anime_list: List of anime dictionaries
            limit: Maximum number of anime to process
            resume: Whether to resume from previous run
        """
        # Filter anime to scrape
        if resume:
            anime_to_scrape = [a for a in anime_list if a['url'] not in self.completed]
        else:
            anime_to_scrape = anime_list
        
        if limit:
            anime_to_scrape = anime_to_scrape[:limit]
        
        total = len(anime_to_scrape)
        completed_count = len(self.completed)
        
        logger.info(f"Starting parallel scraping of {total} anime ({completed_count} already completed)")
        logger.info(f"Using {self.workers} parallel workers")
        
        start_time = time.time()
        scraped = 0
        
        # Process anime in parallel
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Create a session per thread
            sessions = {}
            
            def get_session():
                thread_id = threading.get_ident()
                if thread_id not in sessions:
                    sessions[thread_id] = self.create_session()
                return sessions[thread_id]
            
            # Submit all anime
            future_to_anime = {
                executor.submit(self.scrape_single_anime, anime, get_session()): anime
                for anime in anime_to_scrape
            }
            
            # Collect results as they complete
            for i, future in enumerate(as_completed(future_to_anime), 1):
                anime = future_to_anime[future]
                try:
                    result = future.result()
                    if result:
                        # Save data
                        self.save_anime_data(result)
                        
                        # Mark as completed
                        self.save_progress(anime['url'])
                        scraped += 1
                        
                        logger.info(f"[{i}/{total}] ✓ {anime['title']} ({result['episode_count']} episodes)")
                    else:
                        logger.warning(f"[{i}/{total}] ✗ Failed: {anime['title']}")
                except Exception as e:
                    logger.error(f"[{i}/{total}] Error scraping {anime['title']}: {e}")
                
                # Show progress stats periodically
                if i % 50 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i if i > 0 else 0
                    remaining = (total - i) * avg_time
                    logger.info(f"Progress: {i}/{total} | Avg: {avg_time:.2f}s/anime | ETA: {remaining/60:.1f}min")
        
        # Final stats
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"Parallel scraping complete!")
        logger.info(f"Total scraped: {scraped}")
        logger.info(f"Total episodes found: {self.stats['total_episodes']}")
        logger.info(f"Failed: {self.stats['failed_anime']}")
        logger.info(f"Time taken: {elapsed/60:.1f} minutes")
        if scraped > 0:
            logger.info(f"Average: {elapsed/scraped:.2f}s per anime")
        logger.info(f"Output directory: {self.episodes_dir}")
        logger.info(f"{'='*60}")


def load_anime_list(filepath: str) -> List[Dict[str, str]]:
    """Load anime list from JSON or TOON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if filepath.endswith('.toon'):
            if not TOON_AVAILABLE:
                logger.error("python-toon not installed. Run: pip install python-toon")
                return []
            data = toon.decode(content)
            return data.get('anime_list', data) if isinstance(data, dict) else data
        else:
            return json.loads(content)
    except Exception as e:
        logger.error(f"Error loading anime list: {e}")
        return []


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Fast parallel anime episode scraper'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input JSON/TOON file with anime list'
    )
    parser.add_argument(
        '-o', '--output',
        default='anime_data',
        help='Output directory (default: anime_data)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers (default: 5, max recommended: 10)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.2,
        help='Delay between requests per worker in seconds (default: 0.2)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of anime to scrape'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run'
    )
    parser.add_argument(
        '--no-resume',
        dest='resume',
        action='store_false',
        help='Start fresh'
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
    """Main execution"""
    args = parse_args()
    
    logger.info("Starting Parallel Anime Episode Scraper")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Delay per worker: {args.delay}s")
    logger.info(f"Format: {args.format}")
    
    # Load anime list
    anime_list = load_anime_list(args.input)
    if not anime_list:
        logger.error("No anime found in input file!")
        return
    
    logger.info(f"Loaded {len(anime_list)} anime from list")
    
    # Initialize scraper
    scraper = ParallelAnimeEpisodeScraper(
        output_dir=args.output,
        workers=args.workers,
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
