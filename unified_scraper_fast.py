#!/usr/bin/env python3
"""
Unified Fast Anime Scraper

Combines all scraping steps into one fast pipeline using smart HTML parsing.
No heavy LLM required - uses intelligent pattern matching.

Features:
- Single unified pipeline (no separate steps)
- Smart HTML parsing with multiple fallback patterns
- Parallel processing throughout
- Data rotation (old→deleted, current→old, new→current)
- JSON/TOON output support

Usage:
    python unified_scraper_fast.py
    python unified_scraper_fast.py --mode full --no-rotate
"""

import os
import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
import logging
import re
import hashlib
from typing import List, Dict, Optional, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib.parse import urljoin

try:
    import toon
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False


# =============================================================================
# CONFIGURATION - All inputs in one place
# =============================================================================

class Config:
    """All configurable parameters in one place"""
    
    # --- Website Configuration ---
    BASE_URL = "https://zoroto.com.in"           # Target website base URL
    AZ_LIST_PATH = "/anime/list-mode/"           # Path to A-Z anime list
    
    # --- Scraping Configuration ---
    MODE = "quick"                               # "quick" = limited anime, "full" = all anime
    LIMIT = None                                # Limit number of anime (None = no limit)
    QUICK_LIMIT = 20                            # In quick mode, limit to this many anime
    MAX_EPISODES_PER_ANIME = 9999               # Max episodes to scrape per anime
    MAX_PAGES_PER_LETTER = 5000                 # Max pages to scrape per letter in full mode
    
    # --- Parallel Processing ---
    WORKERS = 7                                  # Number of parallel workers for anime
    EPISODE_WORKERS = 5                          # Number of parallel workers for episodes WITHIN each anime
    DELAY = 0.3                                  # Delay between requests (seconds)
    REQUEST_TIMEOUT = 30                         # Request timeout (seconds)
    
    # --- Output Configuration ---
    OUTPUT_DIR = "scraped_data"                  # Base output directory
    OUTPUT_FORMAT = "json"                       # "json" or "toon"
    LOG_FILE = "unified_scraper_fast.log"        # Log file name
    ROTATE_DATA = True                           # Rotate: old→deleted, current→old, new→current
    
    # --- CI/GitHub Actions ---
    IS_CI = bool(os.environ.get('GITHUB_ACTIONS'))  # Auto-detect GitHub Actions only
    
    # --- HTTP Headers ---
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ACCEPT_LANGUAGE = "en-US,en;q=0.5"


# =============================================================================
# END OF CONFIGURATION
# =============================================================================


# Setup logging (stdout only in CI, file+stdout locally)
_log_handlers = [logging.StreamHandler()]
if not Config.IS_CI:
    _log_handlers.append(logging.FileHandler(Config.LOG_FILE))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=_log_handlers
)
logger = logging.getLogger(__name__)


class SmartHTMLExtractor:
    """
    Smart HTML extractor using BeautifulSoup with multiple fallback patterns.
    Handles various HTML structures intelligently.
    """
    
    def __init__(self):
        pass
    
    def extract_anime_list(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract anime list from HTML using multiple patterns"""
        soup = BeautifulSoup(html, 'html.parser')
        anime_list = []
        seen_urls = set()
        
        # Pattern 0: List-mode page (all anime in <ul><li><a> format)
        # This handles /anime/list-mode/ which shows ALL anime on one page
        for li in soup.find_all('li'):
            link = li.find('a', href=True)
            if link:
                url = link.get('href', '')
                # Only match actual anime URLs (not categories, genres, etc.)
                if '/anime/' in url and url.count('/') >= 4:
                    title = link.get_text(strip=True)
                    if title and len(title) > 1 and url not in seen_urls:
                        # Skip navigation/category links
                        if not any(skip in url.lower() for skip in ['/genre/', '/tag/', '/type/', '/status/', '/list-mode']):
                            anime_list.append({'title': title, 'url': urljoin(base_url, url)})
                            seen_urls.add(url)
        
        # If list-mode found anime, return them
        if anime_list:
            return anime_list
        
        # Pattern 1: Article with bs class (zoroto card style)
        for article in soup.find_all('article', class_='bs'):
            bsx = article.find('div', class_='bsx')
            if bsx:
                link = bsx.find('a')
                if link:
                    title = link.get('title') or ''
                    url = link.get('href', '')
                    if not title:
                        h2 = link.find(['h2', 'h3', 'span'])
                        if h2:
                            title = h2.get_text(strip=True)
                    if url and title and url not in seen_urls:
                        anime_list.append({'title': title, 'url': url})
                        seen_urls.add(url)
        
        if anime_list:
            return anime_list
        
        # Pattern 2: Generic anime card divs
        for card in soup.find_all(['div', 'li'], class_=re.compile(r'anime|card|item|movie', re.I)):
            link = card.find('a', href=True)
            if link:
                url = link.get('href', '')
                title = link.get('title') or link.get_text(strip=True)
                if '/anime/' in url and url not in seen_urls and title:
                    anime_list.append({'title': title, 'url': urljoin(base_url, url)})
                    seen_urls.add(url)
        
        if anime_list:
            return anime_list
        
        # Pattern 3: Any link with /anime/ in href (fallback)
        for link in soup.find_all('a', href=re.compile(r'/anime/[^/]+/?$')):
            url = link.get('href', '')
            title = link.get('title') or link.get_text(strip=True)
            if url not in seen_urls and title and len(title) > 2:
                anime_list.append({'title': title, 'url': urljoin(base_url, url)})
                seen_urls.add(url)
        
        return anime_list
    
    def extract_anime_details(self, html: str, base_url: str) -> Dict[str, Any]:
        """Extract anime details and episodes from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'title': None,
            'description': None,
            'genres': [],
            'status': None,
            'rating': None,
            'episodes': []
        }
        
        # Extract title
        for selector in ['h1.entry-title', 'h1', '.title', '.anime-title']:
            elem = soup.select_one(selector)
            if elem:
                result['title'] = elem.get_text(strip=True)
                break
        
        # Extract description
        for selector in ['.entry-content', '[itemprop="description"]', '.synopsis', '.description']:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)[:500]
                result['description'] = text
                break
        
        # Extract genres
        for link in soup.find_all('a', href=re.compile(r'/genre/')):
            genre = link.get_text(strip=True)
            if genre and genre not in result['genres']:
                result['genres'].append(genre)
        
        # Extract episodes - Pattern 1: Episode list container
        eplister = soup.find('div', class_='eplister')
        if eplister:
            for link in eplister.find_all('a', href=True):
                ep_url = link.get('href')
                if ep_url:
                    # Get episode number
                    ep_num_elem = link.find(['div', 'span'], class_=re.compile(r'num|number', re.I))
                    ep_num = ep_num_elem.get_text(strip=True) if ep_num_elem else None
                    
                    # Get episode title
                    ep_title_elem = link.find(['div', 'span'], class_=re.compile(r'title|name', re.I))
                    ep_title = ep_title_elem.get_text(strip=True) if ep_title_elem else None
                    
                    if not ep_num:
                        # Try to extract from URL
                        match = re.search(r'episode[- _]?(\d+)', ep_url, re.I)
                        ep_num = match.group(1) if match else str(len(result['episodes']) + 1)
                    
                    result['episodes'].append({
                        'episode_number': ep_num,
                        'episode_url': urljoin(base_url, ep_url),
                        'episode_title': ep_title
                    })
        
        # Pattern 2: Episode list in ul/ol
        if not result['episodes']:
            for ul in soup.find_all(['ul', 'ol'], class_=re.compile(r'episode|eps', re.I)):
                for link in ul.find_all('a', href=True):
                    ep_url = link.get('href')
                    if ep_url and ('episode' in ep_url.lower() or 'ep' in ep_url.lower()):
                        text = link.get_text(strip=True)
                        match = re.search(r'(\d+)', text)
                        ep_num = match.group(1) if match else str(len(result['episodes']) + 1)
                        
                        result['episodes'].append({
                            'episode_number': ep_num,
                            'episode_url': urljoin(base_url, ep_url),
                            'episode_title': text if text != ep_num else None
                        })
        
        # Pattern 3: Any links with episode in URL
        if not result['episodes']:
            seen_urls = set()
            for link in soup.find_all('a', href=re.compile(r'episode', re.I)):
                ep_url = link.get('href')
                if ep_url and ep_url not in seen_urls:
                    seen_urls.add(ep_url)
                    match = re.search(r'episode[- _]?(\d+)', ep_url, re.I)
                    ep_num = match.group(1) if match else str(len(result['episodes']) + 1)
                    
                    result['episodes'].append({
                        'episode_number': ep_num,
                        'episode_url': urljoin(base_url, ep_url),
                        'episode_title': link.get_text(strip=True) or None
                    })
        
        return result
    
    def extract_iframe_urls(self, html: str, base_url: str) -> List[str]:
        """Extract iframe/video URLs from episode page"""
        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        seen = set()
        
        # Pattern 1: Direct iframes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
            if src and src not in seen:
                full_url = urljoin(base_url, src)
                if 'http' in full_url:
                    urls.append(full_url)
                    seen.add(src)
        
        # Pattern 2: Look for embed URLs in scripts
        for script in soup.find_all('script'):
            text = script.string or ''
            # Find URLs that look like video embeds
            matches = re.findall(r'["\']?(https?://[^"\'<>\s]+(?:embed|streaming|player|video)[^"\'<>\s]*)["\']?', text, re.I)
            for url in matches:
                if url not in seen:
                    urls.append(url)
                    seen.add(url)
        
        # Pattern 3: Look for data attributes with URLs
        for elem in soup.find_all(attrs={'data-src': True}):
            src = elem.get('data-src')
            if src and 'http' in src and src not in seen:
                urls.append(src)
                seen.add(src)
        
        return urls


class UnifiedFastScraper:
    """Fast unified scraper that combines all steps"""
    
    def __init__(self, 
                 output_dir: str = None,
                 workers: int = None,
                 delay: float = None,
                 output_format: str = None,
                 rotate: bool = None):
        """
        Initialize the unified scraper.
        Uses Config defaults if parameters are not provided.
        
        Args:
            output_dir: Base directory for data (will have current/old subdirs)
            workers: Number of parallel workers
            delay: Delay between requests per worker
            output_format: 'json' or 'toon'
            rotate: Whether to rotate data (old→deleted, current→old, new→current)
        """
        # Use Config defaults if not provided
        self.base_dir = Path(output_dir or Config.OUTPUT_DIR)
        self.workers = workers or Config.WORKERS
        self.delay = delay or Config.DELAY
        self.output_format = output_format or Config.OUTPUT_FORMAT
        self.rotate = rotate if rotate is not None else Config.ROTATE_DATA
        
        # Setup directories with rotation
        self._setup_directories()
        
        # Initialize extractor
        self.extractor = SmartHTMLExtractor()
        
        # Thread lock for stats
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'anime_scraped': 0,
            'episodes_found': 0,
            'video_urls_found': 0,
            'failed': 0
        }
        self.stats_lock = threading.Lock()
    
    def _setup_directories(self):
        """Setup directories with rotation: old→deleted, current→old, new→current"""
        import shutil
        
        self.base_dir.mkdir(exist_ok=True)
        
        old_dir = self.base_dir / "old"
        current_dir = self.base_dir / "current"
        
        if self.rotate:
            logger.info("Rotating data directories...")
            
            # Step 1: Delete old if exists
            if old_dir.exists():
                logger.info(f"  Deleting old data: {old_dir}")
                shutil.rmtree(old_dir)
            
            # Step 2: Move current to old
            if current_dir.exists():
                logger.info(f"  Moving current → old")
                current_dir.rename(old_dir)
            
            # Step 3: Create new current
            logger.info(f"  Creating new current directory")
        
        # Set output_dir to current
        self.output_dir = current_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # Create anime subdirectory
        self.anime_dir = self.output_dir / "anime"
        self.anime_dir.mkdir(exist_ok=True)
        
        logger.info(f"Output directory: {self.output_dir}")
    
    def create_session(self) -> requests.Session:
        """Create a new HTTP session with larger connection pool"""
        session = requests.Session()
        
        # Increase connection pool size to handle parallel workers
        # Pool size = WORKERS * EPISODE_WORKERS + buffer
        pool_size = Config.WORKERS * Config.EPISODE_WORKERS + 10
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=0  # We handle retries ourselves
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': Config.ACCEPT,
            'Accept-Language': Config.ACCEPT_LANGUAGE,
        })
        return session
    
    def fetch_page(self, url: str, session: requests.Session) -> Optional[str]:
        """Fetch a page and return HTML"""
        try:
            response = session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None
    
    def sanitize_filename(self, title: str) -> str:
        """Create safe filename from title"""
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', '_', safe.strip())
        return safe[:200] or "unnamed"
    
    def get_url_hash(self, url: str) -> str:
        """Get short hash of URL"""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def get_max_page_number(self, html: str) -> int:
        """Detect max page number from pagination"""
        soup = BeautifulSoup(html, 'html.parser')
        max_page = 1
        
        pagination = soup.find('div', class_='pagination')
        if not pagination:
            return 1
        
        # Find all page links
        for link in pagination.find_all('a', class_='page-numbers'):
            text = link.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
            
            # Also check href for page numbers
            href = link.get('href', '')
            if '/page/' in href:
                try:
                    page_part = href.split('/page/')[-1]
                    page_num = int(page_part.rstrip('/').split('/')[0].split('?')[0])
                    max_page = max(max_page, page_num)
                except (ValueError, IndexError):
                    pass
        
        # Check current page span
        current = pagination.find('span', class_='current')
        if current:
            text = current.get_text(strip=True)
            if text.isdigit():
                max_page = max(max_page, int(text))
        
        return max_page
    
    def scrape_anime_list(self, session: requests.Session, mode: str = "quick") -> List[Dict[str, str]]:
        """Step 1: Scrape the anime list with FULL pagination"""
        logger.info(f"Step 1: Scraping anime list (mode: {mode})...")
        
        all_anime = []
        seen_urls = set()
        base_url = Config.BASE_URL
        az_path = Config.AZ_LIST_PATH
        
        # Check if using list-mode (no letter filtering) or az-list (letter filtering)
        use_letters = '/az-list' in az_path
        
        if mode == "quick":
            # Quick mode: just first page
            url = f"{base_url}{az_path}"
            html = self.fetch_page(url, session)
            if html:
                anime_list = self.extractor.extract_anime_list(html, url)
                for anime in anime_list:
                    if anime.get('url') and anime['url'] not in seen_urls:
                        all_anime.append(anime)
                        seen_urls.add(anime['url'])
        
        elif use_letters:
            # AZ-List mode: iterate through letters with pagination
            letters = ['.', '0-9'] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]
            
            for letter in letters:
                first_url = f"{base_url}{az_path}?show={letter}"
                html = self.fetch_page(first_url, session)
                
                if not html:
                    continue
                
                max_pages = min(self.get_max_page_number(html), Config.MAX_PAGES_PER_LETTER)
                logger.info(f"Fetching letter: {letter} ({max_pages} pages)")
                
                # Extract from first page
                anime_list = self.extractor.extract_anime_list(html, first_url)
                for anime in anime_list:
                    if anime.get('url') and anime['url'] not in seen_urls:
                        all_anime.append(anime)
                        seen_urls.add(anime['url'])
                
                # Fetch remaining pages for this letter
                for page in range(2, max_pages + 1):
                    page_url = f"{base_url}{az_path}page/{page}/?show={letter}"
                    html = self.fetch_page(page_url, session)
                    
                    if not html:
                        break
                    
                    anime_list = self.extractor.extract_anime_list(html, page_url)
                    if not anime_list:
                        break
                    
                    for anime in anime_list:
                        if anime.get('url') and anime['url'] not in seen_urls:
                            all_anime.append(anime)
                            seen_urls.add(anime['url'])
                    
                    time.sleep(self.delay)
                
                logger.info(f"  → Total unique anime so far: {len(all_anime)}")
                time.sleep(self.delay)
        
        else:
            # List-mode: simple pagination (no letters)
            first_url = f"{base_url}{az_path}"
            html = self.fetch_page(first_url, session)
            
            if html:
                max_pages = min(self.get_max_page_number(html), Config.MAX_PAGES_PER_LETTER)
                logger.info(f"Detected {max_pages} pages to scrape")
                
                # Extract from first page
                anime_list = self.extractor.extract_anime_list(html, first_url)
                for anime in anime_list:
                    if anime.get('url') and anime['url'] not in seen_urls:
                        all_anime.append(anime)
                        seen_urls.add(anime['url'])
                
                logger.info(f"Page 1: Found {len(all_anime)} anime")
                
                # Fetch remaining pages
                for page in range(2, max_pages + 1):
                    page_url = f"{base_url}{az_path}page/{page}/"
                    html = self.fetch_page(page_url, session)
                    
                    if not html:
                        logger.warning(f"Page {page} fetch failed, stopping")
                        break
                    
                    anime_list = self.extractor.extract_anime_list(html, page_url)
                    if not anime_list:
                        logger.info(f"Page {page} empty, stopping")
                        break
                    
                    prev_count = len(all_anime)
                    for anime in anime_list:
                        if anime.get('url') and anime['url'] not in seen_urls:
                            all_anime.append(anime)
                            seen_urls.add(anime['url'])
                    
                    new_count = len(all_anime) - prev_count
                    logger.info(f"Page {page}: +{new_count} anime (total: {len(all_anime)})")
                    
                    if new_count == 0:
                        break
                    
                    time.sleep(self.delay)
        
        logger.info(f"Total anime found: {len(all_anime)}")
        return all_anime
    
    def fetch_episode_video(self, ep: Dict[str, Any], session: requests.Session) -> Dict[str, Any]:
        """Fetch video URLs for a single episode (used for parallel processing)"""
        ep_url = ep.get('episode_url')
        iframe_urls = []
        
        if ep_url:
            ep_html = self.fetch_page(ep_url, session)
            if ep_html:
                iframe_urls = self.extractor.extract_iframe_urls(ep_html, ep_url)
        
        return {
            'episode_number': ep.get('episode_number'),
            'episode_url': ep_url,
            'episode_title': ep.get('episode_title'),
            'video_sources': iframe_urls,
            'has_videos': len(iframe_urls) > 0
        }
    
    def scrape_single_anime(self, anime: Dict[str, str], session: requests.Session) -> Optional[Dict[str, Any]]:
        """Steps 2+3: Scrape anime details, episodes, and video URLs (with parallel episode fetching)"""
        url = anime['url']
        title = anime['title']
        
        # Fetch anime page
        html = self.fetch_page(url, session)
        if not html:
            with self.stats_lock:
                self.stats['failed'] += 1
            return None
        
        # Extract details and episodes
        details = self.extractor.extract_anime_details(html, url)
        episodes = details.get('episodes', [])[:Config.MAX_EPISODES_PER_ANIME]
        
        # Fetch episodes in PARALLEL (key performance improvement)
        episodes_with_videos = []
        
        if episodes:
            # Use mini thread pool for episodes within this anime
            episode_workers = min(Config.EPISODE_WORKERS, len(episodes))
            
            with ThreadPoolExecutor(max_workers=episode_workers) as ep_executor:
                # Create sessions for episode workers
                ep_sessions = {}
                
                def get_ep_session():
                    tid = threading.get_ident()
                    if tid not in ep_sessions:
                        ep_sessions[tid] = self.create_session()
                    return ep_sessions[tid]
                
                # Submit all episode fetches
                future_to_ep = {
                    ep_executor.submit(self.fetch_episode_video, ep, get_ep_session()): ep
                    for ep in episodes
                }
                
                # Collect results
                for future in as_completed(future_to_ep):
                    try:
                        result = future.result()
                        episodes_with_videos.append(result)
                        
                        with self.stats_lock:
                            self.stats['video_urls_found'] += len(result.get('video_sources', []))
                    except Exception:
                        pass
        
        # Sort episodes by number
        episodes_with_videos.sort(key=lambda x: int(x.get('episode_number', 0)) if str(x.get('episode_number', '0')).isdigit() else 0)
        
        # Update stats
        with self.stats_lock:
            self.stats['anime_scraped'] += 1
            self.stats['episodes_found'] += len(episodes_with_videos)
        
        return {
            'title': title,
            'url': url,
            'description': details.get('description'),
            'genres': details.get('genres', []),
            'status': details.get('status'),
            'rating': details.get('rating'),
            'total_episodes': len(episodes_with_videos),
            'available_episodes': len([e for e in episodes_with_videos if e['has_videos']]),
            'episodes': episodes_with_videos,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def save_anime_data(self, anime_data: Dict[str, Any]):
        """Save anime data to file"""
        title = anime_data['title']
        url = anime_data['url']
        url_hash = self.get_url_hash(url)
        safe_title = self.sanitize_filename(title)
        
        filename = f"{safe_title}_{url_hash}"
        ext = '.toon' if self.output_format == 'toon' else '.json'
        filepath = self.anime_dir / f"{filename}{ext}"
        
        try:
            with self.lock:
                if self.output_format == 'toon' and TOON_AVAILABLE:
                    toon_str = toon.encode(anime_data)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(toon_str)
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(anime_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving anime data: {e}")
    
    def run(self, mode: str = "quick", limit: Optional[int] = None):
        """Run the complete unified pipeline (always fresh start)."""
        start_time = time.time()
        
        logger.info("="*60)
        logger.info("UNIFIED FAST ANIME SCRAPER")
        logger.info("="*60)
        logger.info(f"Mode: {mode}")
        logger.info(f"Workers: {self.workers}")
        logger.info(f"Output: {self.output_dir}")
        logger.info(f"Rotation: {'enabled' if self.rotate else 'disabled'}")
        logger.info("="*60)
        
        session = self.create_session()
        
        # Step 1: Get anime list
        anime_list = self.scrape_anime_list(session, mode)
        
        if not anime_list:
            logger.error("No anime found!")
            return
        
        logger.info(f"Total anime found: {len(anime_list)}")
        
        # Apply limit: explicit limit > quick mode limit > no limit
        if limit:
            anime_list = anime_list[:limit]
            logger.info(f"Applied explicit limit: {limit}")
        elif mode == "quick":
            anime_list = anime_list[:Config.QUICK_LIMIT]
            logger.info(f"Applied quick mode limit: {Config.QUICK_LIMIT}")
        
        total = len(anime_list)
        logger.info(f"\nStep 2-3: Scraping {total} anime...")
        
        # Process anime in parallel
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            sessions = {}
            
            def get_session():
                thread_id = threading.get_ident()
                if thread_id not in sessions:
                    sessions[thread_id] = self.create_session()
                return sessions[thread_id]
            
            future_to_anime = {
                executor.submit(self.scrape_single_anime, anime, get_session()): anime
                for anime in anime_list
            }
            
            for i, future in enumerate(as_completed(future_to_anime), 1):
                anime = future_to_anime[future]
                try:
                    result = future.result()
                    if result:
                        self.save_anime_data(result)
                        
                        logger.info(f"[{i}/{total}] ✓ {anime['title'][:40]} "
                                  f"({result['total_episodes']} eps, "
                                  f"{result['available_episodes']} with videos)")
                    else:
                        logger.warning(f"[{i}/{total}] ✗ {anime['title'][:40]}")
                except Exception as e:
                    logger.error(f"[{i}/{total}] Error: {anime['title'][:40]} - {e}")
        
        # Step 4: Create index
        self._create_index()
        
        # Final report
        elapsed = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("SCRAPING COMPLETE!")
        logger.info("="*60)
        logger.info(f"Anime scraped: {self.stats['anime_scraped']}")
        logger.info(f"Episodes found: {self.stats['episodes_found']}")
        logger.info(f"Video URLs found: {self.stats['video_urls_found']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        logger.info(f"Output: {self.output_dir}")
        logger.info("="*60)
    
    def _create_index(self):
        """Create index and statistics files"""
        logger.info("\nStep 4: Creating index...")
        
        ext = '.toon' if self.output_format == 'toon' else '.json'
        anime_files = list(self.anime_dir.glob(f'*{ext}'))
        
        all_anime = []
        total_episodes = 0
        total_videos = 0
        
        for filepath in anime_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if self.output_format == 'toon' and TOON_AVAILABLE:
                    data = toon.decode(content)
                else:
                    data = json.loads(content)
                
                all_anime.append({
                    'title': data.get('title'),
                    'url': data.get('url'),
                    'total_episodes': data.get('total_episodes', 0),
                    'available_episodes': data.get('available_episodes', 0)
                })
                
                total_episodes += data.get('total_episodes', 0)
                for ep in data.get('episodes', []):
                    total_videos += len(ep.get('video_sources', []))
                    
            except Exception:
                pass
        
        all_anime.sort(key=lambda x: x.get('title', '').lower())
        
        # Save index
        index = {
            'total_anime': len(all_anime),
            'total_episodes': total_episodes,
            'total_video_sources': total_videos,
            'anime_list': all_anime
        }
        
        index_path = self.output_dir / f"anime_index{ext}"
        with open(index_path, 'w', encoding='utf-8') as f:
            if self.output_format == 'toon' and TOON_AVAILABLE:
                f.write(toon.encode(index))
            else:
                json.dump(index, f, ensure_ascii=False, indent=2)
        
        # Save statistics
        stats = {
            'total_anime': len(all_anime),
            'total_episodes': total_episodes,
            'total_video_sources': total_videos,
            'avg_episodes_per_anime': round(total_episodes / len(all_anime), 1) if all_anime else 0,
        }
        
        stats_path = self.output_dir / f"statistics{ext}"
        with open(stats_path, 'w', encoding='utf-8') as f:
            if self.output_format == 'toon' and TOON_AVAILABLE:
                f.write(toon.encode(stats))
            else:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Created index with {len(all_anime)} anime")


def main():
    """
    Main entry point.
    Uses Config defaults for all values. Command line args override Config.
    """
    parser = argparse.ArgumentParser(
        description='Unified Fast Anime Scraper',
        epilog='Edit the Config class at the top of this file to change defaults.'
    )
    parser.add_argument('--mode', choices=['quick', 'full'], default=Config.MODE,
                        help=f'quick=first page, full=all pages A-Z (default: {Config.MODE})')
    parser.add_argument('-o', '--output', default=Config.OUTPUT_DIR, 
                        help=f'Base output directory (default: {Config.OUTPUT_DIR})')
    parser.add_argument('--workers', type=int, default=Config.WORKERS, 
                        help=f'Parallel workers (default: {Config.WORKERS})')
    parser.add_argument('--delay', type=float, default=Config.DELAY, 
                        help=f'Delay between requests (default: {Config.DELAY})')
    parser.add_argument('--limit', type=int, default=Config.LIMIT,
                        help=f'Limit number of anime (default: {Config.LIMIT})')
    parser.add_argument('--no-rotate', dest='rotate', action='store_false',
                        help='Disable data rotation (keep existing data)')
    parser.add_argument('-f', '--format', choices=['json', 'toon'], default=Config.OUTPUT_FORMAT,
                        help=f'Output format (default: {Config.OUTPUT_FORMAT})')
    parser.set_defaults(rotate=Config.ROTATE_DATA)
    
    args = parser.parse_args()
    
    # Create scraper with config/args
    scraper = UnifiedFastScraper(
        output_dir=args.output,
        workers=args.workers,
        delay=args.delay,
        output_format=args.format,
        rotate=args.rotate
    )
    
    # Run scraper (always fresh start)
    scraper.run(mode=args.mode, limit=args.limit)


if __name__ == "__main__":
    main()
