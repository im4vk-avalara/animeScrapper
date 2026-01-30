#!/usr/bin/env python3
"""
Video URL Scraper

Reads episode JSON files and extracts video iframe/stream URLs from episode pages.
Saves video URLs in organized format.

Usage:
    python video_url_scraper.py --input anime_data/episodes
    python video_url_scraper.py --input anime_data/episodes --limit 5 --resume
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
from urllib.parse import urljoin, urlparse, parse_qs
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_url_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VideoUrlScraper:
    """Scraper for extracting video URLs from episode pages"""
    
    def __init__(self, output_dir: str = "video_data", delay: float = 2.0):
        """
        Initialize the scraper.
        
        Args:
            output_dir: Directory to save video URL data
            delay: Delay between requests in seconds
        """
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://zoroto.com.in/'
        })
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.videos_dir = self.output_dir / "videos"
        self.videos_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.completed = self.load_progress()
        
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
        """Save progress after completing an anime"""
        self.completed.add(anime_file)
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump({'completed': list(self.completed)}, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
    def fetch_episode_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch an episode page.
        
        Args:
            url: URL of episode page
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_video_sources(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract iframe URLs from episode page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of iframe URLs
        """
        iframe_urls = []
        
        # Find ALL iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
            if src:
                full_url = urljoin(base_url, src)
                if full_url not in iframe_urls:
                    iframe_urls.append(full_url)
        
        logger.info(f"Found {len(iframe_urls)} iframe URLs")
        return iframe_urls
    
    
    def scrape_episode(self, episode: Dict[str, str]) -> Optional[Dict[str, any]]:
        """
        Scrape iframe URLs from a single episode.
        
        Args:
            episode: Episode dictionary with 'episode_number', 'episode_title', 'url'
            
        Returns:
            Dictionary with episode and iframe URLs or None if failed
        """
        url = episode['url']
        
        # Fetch page
        soup = self.fetch_episode_page(url)
        if not soup:
            return None
        
        # Extract iframe URLs
        iframe_urls = self.extract_video_sources(soup, url)
        
        if not iframe_urls:
            logger.warning(f"No iframes found for episode {episode.get('episode_number')}")
        
        # Prepare result
        result = {
            'episode_number': episode.get('episode_number'),
            'episode_url': url,
            'iframe_urls': iframe_urls
        }
        
        return result
    
    def scrape_anime_episodes(self, anime_data: Dict[str, any], anime_filename: str) -> Dict[str, any]:
        """
        Scrape iframe URLs for all episodes of an anime.
        
        Args:
            anime_data: Anime data with episodes
            anime_filename: Original anime filename for identification
            
        Returns:
            Simplified anime data with iframe URLs
        """
        title = anime_data.get('title', 'Unknown')
        episodes = anime_data.get('episodes', [])
        
        logger.info(f"Scraping iframe URLs for {len(episodes)} episodes")
        
        episodes_with_iframes = []
        for i, episode in enumerate(episodes, 1):
            logger.info(f"  Episode {i}/{len(episodes)}: {episode.get('episode_number')}")
            
            try:
                episode_data = self.scrape_episode(episode)
                if episode_data:
                    episodes_with_iframes.append(episode_data)
                    logger.info(f"    ✓ Found {len(episode_data['iframe_urls'])} iframe URLs")
                else:
                    logger.warning(f"    ✗ Failed to scrape episode")
                    episodes_with_iframes.append({
                        'episode_number': episode.get('episode_number'),
                        'episode_url': episode.get('url'),
                        'iframe_urls': []
                    })
                
            except Exception as e:
                logger.error(f"    ✗ Error scraping episode: {e}")
                episodes_with_iframes.append({
                    'episode_number': episode.get('episode_number'),
                    'episode_url': episode.get('url'),
                    'iframe_urls': [],
                    'error': str(e)
                })
            
            # Rate limiting between episodes
            if i < len(episodes):
                time.sleep(self.delay)
        
        # Compile results
        result = {
            'anime_title': title,
            'total_episodes': len(episodes),
            'episodes': episodes_with_iframes
        }
        
        return result
    
    def save_video_data(self, video_data: Dict[str, any], original_filename: str):
        """
        Save video URL data to file.
        
        Args:
            video_data: Dictionary with anime and video data
            original_filename: Original episode JSON filename
        """
        # Create output filename (same as input but in videos dir)
        output_file = self.videos_dir / original_filename
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(video_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved video data to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving video data: {e}")
    
    def scrape_all(self, episodes_dir: Path, limit: Optional[int] = None, resume: bool = True):
        """
        Scrape video URLs for all anime in episodes directory.
        
        Args:
            episodes_dir: Directory containing episode JSON files
            limit: Maximum number of anime to process (None for all)
            resume: Whether to resume from previous run
        """
        # Get all episode JSON files
        episode_files = sorted(episodes_dir.glob('*.json'))
        
        if not episode_files:
            logger.error(f"No JSON files found in {episodes_dir}")
            return
        
        total = len(episode_files)
        if limit:
            episode_files = episode_files[:limit]
            total = len(episode_files)
        
        completed_count = len(self.completed)
        logger.info(f"Starting video URL scraping for {total} anime ({completed_count} already completed)")
        
        scraped = 0
        for i, episode_file in enumerate(episode_files, 1):
            filename = episode_file.name
            
            # Skip if already completed and resume is enabled
            if resume and filename in self.completed:
                logger.info(f"[{i}/{total}] Skipping already completed: {filename}")
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {i}/{total}: {filename}")
            logger.info(f"{'='*60}")
            
            try:
                # Load episode data
                with open(episode_file, 'r', encoding='utf-8') as f:
                    anime_data = json.load(f)
                
                # Scrape video URLs
                video_data = self.scrape_anime_episodes(anime_data, filename)
                
                # Save results
                self.save_video_data(video_data, filename)
                
                # Mark as completed
                self.save_progress(filename)
                scraped += 1
                
                # Count total iframe URLs
                total_iframes = sum(len(ep.get('iframe_urls', [])) for ep in video_data.get('episodes', []))
                logger.info(f"✓ Successfully scraped: {anime_data.get('title')} "
                           f"({total_iframes} iframe URLs)")
                
            except Exception as e:
                logger.error(f"✗ Error processing {filename}: {e}", exc_info=True)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Video URL scraping complete!")
        logger.info(f"Total processed: {scraped}")
        logger.info(f"Total completed (including previous): {len(self.completed)}")
        logger.info(f"Output directory: {self.videos_dir}")
        logger.info(f"{'='*60}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Scrape video URLs from episode pages'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input directory with episode JSON files'
    )
    parser.add_argument(
        '-o', '--output',
        default='video_data',
        help='Output directory for video URL data (default: video_data)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of anime to process'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
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
    parser.set_defaults(resume=True)
    
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_args()
    
    logger.info("Starting Video URL Scraper")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    
    episodes_dir = Path(args.input)
    if not episodes_dir.exists():
        logger.error(f"Input directory does not exist: {episodes_dir}")
        return
    
    # Initialize scraper
    scraper = VideoUrlScraper(
        output_dir=args.output,
        delay=args.delay
    )
    
    # Start scraping
    scraper.scrape_all(
        episodes_dir=episodes_dir,
        limit=args.limit,
        resume=args.resume
    )


if __name__ == "__main__":
    main()

