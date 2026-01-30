#!/usr/bin/env python3
"""
Parallel Video URL Scraper

Fast parallel version using threading to scrape multiple episodes simultaneously.
MUCH faster than sequential version (5-10x speedup).

Usage:
    python video_url_scraper_parallel.py --input anime_data/episodes
    python video_url_scraper_parallel.py --input anime_data/episodes --workers 10 --limit 100
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
import logging
import os
from typing import List, Dict, Optional
from pathlib import Path
from urllib.parse import urljoin
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
        logging.FileHandler('video_url_scraper_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ParallelVideoUrlScraper:
    """Fast parallel scraper for extracting iframe URLs"""
    
    def __init__(self, output_dir: str = "video_data", workers: int = 5, delay: float = 0.1, output_format: str = "json"):
        """
        Initialize the parallel scraper.
        
        Args:
            output_dir: Directory to save video URL data
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
        self.videos_dir = self.output_dir / "videos"
        self.videos_dir.mkdir(exist_ok=True)
        
        # Progress tracking with thread safety
        self.progress_file = self.output_dir / "progress.json"
        self.completed = self.load_progress()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_iframes': 0,
            'total_episodes': 0,
            'failed_episodes': 0
        }
        self.stats_lock = threading.Lock()
        
    def create_session(self):
        """Create a new session for thread safety"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://zoroto.com.in/'
        })
        return session
    
    def load_progress(self) -> set:
        """Load previously completed anime"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('completed', []))
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        return set()
    
    def save_progress(self, anime_file: str):
        """Save progress (thread-safe)"""
        with self.lock:
            self.completed.add(anime_file)
            try:
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump({'completed': list(self.completed)}, f, indent=2)
            except Exception as e:
                logger.error(f"Could not save progress: {e}")
    
    def fetch_episode_page(self, url: str, session: requests.Session) -> Optional[BeautifulSoup]:
        """Fetch an episode page"""
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_iframe_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract iframe URLs from page"""
        iframe_urls = []
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
            if src:
                full_url = urljoin(base_url, src)
                if full_url not in iframe_urls:
                    iframe_urls.append(full_url)
        return iframe_urls
    
    def scrape_episode(self, episode: Dict[str, str], session: requests.Session) -> Dict[str, any]:
        """Scrape a single episode"""
        url = episode['url']
        
        # Fetch page
        soup = self.fetch_episode_page(url, session)
        
        if not soup:
            return {
                'episode_number': episode.get('episode_number'),
                'episode_url': url,
                'iframe_urls': [],
                'error': 'Failed to fetch'
            }
        
        # Extract iframes
        iframe_urls = self.extract_iframe_urls(soup, url)
        
        # Update stats
        with self.stats_lock:
            self.stats['total_episodes'] += 1
            self.stats['total_iframes'] += len(iframe_urls)
            if not iframe_urls:
                self.stats['failed_episodes'] += 1
        
        # Rate limiting per worker
        time.sleep(self.delay)
        
        return {
            'episode_number': episode.get('episode_number'),
            'episode_url': url,
            'iframe_urls': iframe_urls
        }
    
    def scrape_anime_parallel(self, anime_data: Dict[str, any]) -> Dict[str, any]:
        """
        Scrape all episodes of an anime in parallel.
        
        Args:
            anime_data: Anime data with episodes
            
        Returns:
            Complete anime data with iframe URLs
        """
        title = anime_data.get('title', 'Unknown')
        episodes = anime_data.get('episodes', [])
        
        logger.info(f"Scraping {len(episodes)} episodes with {self.workers} workers")
        
        episodes_with_iframes = []
        
        # Process episodes in parallel
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Create a session per thread
            sessions = {}
            
            def get_session():
                thread_id = threading.get_ident()
                if thread_id not in sessions:
                    sessions[thread_id] = self.create_session()
                return sessions[thread_id]
            
            # Submit all episodes
            future_to_episode = {
                executor.submit(self.scrape_episode, episode, get_session()): episode
                for episode in episodes
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_episode):
                try:
                    result = future.result()
                    episodes_with_iframes.append(result)
                except Exception as e:
                    episode = future_to_episode[future]
                    logger.error(f"Error scraping episode {episode.get('episode_number')}: {e}")
                    episodes_with_iframes.append({
                        'episode_number': episode.get('episode_number'),
                        'episode_url': episode.get('url'),
                        'iframe_urls': [],
                        'error': str(e)
                    })
        
        # Sort by episode number for consistent output
        episodes_with_iframes.sort(key=lambda x: str(x.get('episode_number', '')))
        
        result = {
            'anime_title': title,
            'total_episodes': len(episodes),
            'episodes': episodes_with_iframes
        }
        
        return result
    
    def save_video_data(self, video_data: Dict[str, any], original_filename: str):
        """Save video URL data"""
        # Adjust extension based on format
        if self.output_format == 'toon':
            # Change extension to .toon
            base_name = original_filename.rsplit('.', 1)[0]
            output_file = self.videos_dir / f"{base_name}.toon"
        else:
            output_file = self.videos_dir / original_filename
        
        try:
            if self.output_format == 'toon' and TOON_AVAILABLE:
                toon_str = toon.encode(video_data)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(toon_str)
            else:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(video_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving video data: {e}")
    
    def load_episode_file(self, filepath: Path) -> Optional[Dict]:
        """Load episode data from JSON or TOON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if filepath.suffix == '.toon':
            if not TOON_AVAILABLE:
                logger.error("python-toon not installed. Run: pip install python-toon")
                return None
            return toon.decode(content)
            else:
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return None
    
    def scrape_all(self, episodes_dir: Path, limit: Optional[int] = None, resume: bool = True):
        """
        Scrape video URLs for all anime in parallel.
        
        Args:
            episodes_dir: Directory containing episode JSON or TOON files
            limit: Maximum number of anime to process
            resume: Whether to resume from previous run
        """
        # Get all episode files (JSON and TOON)
        episode_files = sorted(list(episodes_dir.glob('*.json')) + list(episodes_dir.glob('*.toon')))
        
        if not episode_files:
            logger.error(f"No JSON files found in {episodes_dir}")
            return
        
        total = len(episode_files)
        if limit:
            episode_files = episode_files[:limit]
            total = len(episode_files)
        
        completed_count = len(self.completed)
        logger.info(f"Starting parallel scraping of {total} anime ({completed_count} already completed)")
        logger.info(f"Using {self.workers} parallel workers")
        
        start_time = time.time()
        scraped = 0
        
        for i, episode_file in enumerate(episode_files, 1):
            filename = episode_file.name
            
            # Skip if already completed
            if resume and filename in self.completed:
                logger.info(f"[{i}/{total}] Skipping completed: {filename}")
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {i}/{total}: {filename}")
            logger.info(f"{'='*60}")
            
            try:
                # Load episode data
                anime_data = self.load_episode_file(episode_file)
                if not anime_data:
                    continue
                
                # Scrape in parallel
                video_data = self.scrape_anime_parallel(anime_data)
                
                # Save results
                self.save_video_data(video_data, filename)
                
                # Mark as completed
                self.save_progress(filename)
                scraped += 1
                
                # Count total iframes
                total_iframes = sum(len(ep.get('iframe_urls', [])) for ep in video_data.get('episodes', []))
                logger.info(f"✓ Successfully scraped: {anime_data.get('title')} ({total_iframes} iframe URLs)")
                
                # Show progress stats
                elapsed = time.time() - start_time
                avg_time = elapsed / scraped if scraped > 0 else 0
                remaining = (total - i) * avg_time
                logger.info(f"Progress: {scraped}/{total} | Avg: {avg_time:.1f}s/anime | ETA: {remaining/60:.1f}min")
                
            except Exception as e:
                logger.error(f"✗ Error processing {filename}: {e}", exc_info=True)
        
        # Final stats
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"Parallel scraping complete!")
        logger.info(f"Total processed: {scraped}")
        logger.info(f"Total episodes scraped: {self.stats['total_episodes']}")
        logger.info(f"Total iframe URLs found: {self.stats['total_iframes']}")
        logger.info(f"Failed episodes: {self.stats['failed_episodes']}")
        logger.info(f"Time taken: {elapsed/60:.1f} minutes")
        logger.info(f"Average: {elapsed/scraped:.1f}s per anime" if scraped > 0 else "")
        logger.info(f"Output directory: {self.videos_dir}")
        logger.info(f"{'='*60}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Fast parallel video URL scraper'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input directory with episode JSON files'
    )
    parser.add_argument(
        '-o', '--output',
        default='video_data',
        help='Output directory (default: video_data)'
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
        default=0.1,
        help='Delay between requests per worker in seconds (default: 0.1)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of anime to process'
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
    
    logger.info("Starting Parallel Video URL Scraper")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Delay per worker: {args.delay}s")
    
    episodes_dir = Path(args.input)
    if not episodes_dir.exists():
        logger.error(f"Input directory does not exist: {episodes_dir}")
        return
    
    # Initialize scraper
    scraper = ParallelVideoUrlScraper(
        output_dir=args.output,
        workers=args.workers,
        delay=args.delay,
        output_format=args.format
    )
    
    # Start scraping
    scraper.scrape_all(
        episodes_dir=episodes_dir,
        limit=args.limit,
        resume=args.resume
    )


if __name__ == "__main__":
    main()

