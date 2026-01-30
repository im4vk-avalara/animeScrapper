#!/usr/bin/env python3
"""
Unified Anime Scraper with Local LLM

Combines all scraping steps into one pipeline and uses a local LLM (Ollama)
for intelligent HTML extraction instead of manual parsing.

Features:
- Single unified pipeline (no separate steps)
- Local LLM extraction (Ollama) for flexible parsing
- Parallel processing throughout
- Resume capability
- JSON/TOON output support

Requirements:
    pip install requests ollama
    # Install Ollama: https://ollama.ai/download
    # Pull a model: ollama pull llama3.2:3b

Usage:
    python unified_scraper_llm.py --mode quick --limit 10
    python unified_scraper_llm.py --mode full --workers 5
    python unified_scraper_llm.py --mode quick --limit 5 --model llama3.2:3b
"""

import requests
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
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

# Try to import optional dependencies
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import toon
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not installed. Run: pip install transformers torch accelerate")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_scraper_llm.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Episode:
    """Episode data structure"""
    episode_number: str
    episode_url: str
    episode_title: Optional[str] = None
    iframe_urls: Optional[List[str]] = None


@dataclass
class Anime:
    """Anime data structure"""
    title: str
    url: str
    description: Optional[str] = None
    genres: Optional[List[str]] = None
    status: Optional[str] = None
    rating: Optional[str] = None
    episodes: Optional[List[Episode]] = None
    total_episodes: int = 0
    scraped_at: Optional[str] = None


class PythonLLMExtractor:
    """Uses HuggingFace Transformers for HTML extraction (no external server needed)"""
    
    # Small, efficient models for extraction tasks
    SUPPORTED_MODELS = {
        'qwen2-0.5b': 'Qwen/Qwen2-0.5B-Instruct',
        'qwen2-1.5b': 'Qwen/Qwen2-1.5B-Instruct', 
        'phi3-mini': 'microsoft/Phi-3-mini-4k-instruct',
        'tinyllama': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
        'smollm': 'HuggingFaceTB/SmolLM-1.7B-Instruct',
    }
    
    def __init__(self, model: str = "qwen2-0.5b"):
        """
        Initialize Python LLM extractor.
        
        Args:
            model: Model alias or HuggingFace model ID
        """
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("transformers not installed. Run: pip install transformers torch accelerate")
        
        # Resolve model name
        model_id = self.SUPPORTED_MODELS.get(model, model)
        logger.info(f"Loading model: {model_id}")
        
        # Detect device
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        logger.info(f"Using device: {device}")
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device != "cpu" else torch.float32,
            device_map="auto" if device != "cpu" else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        if device == "cpu":
            self.model = self.model.to(device)
        
        self.device = device
        self.model_id = model_id
        
        # Create pipeline for easier generation
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device_map="auto" if device != "cpu" else None,
        )
        
        logger.info(f"Model loaded successfully!")
    
    def _generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate text from prompt"""
        try:
            # Format as chat if model supports it
            if hasattr(self.tokenizer, 'apply_chat_template'):
                messages = [{"role": "user", "content": prompt}]
                formatted = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                formatted = prompt
            
            outputs = self.pipe(
                formatted,
                max_new_tokens=max_tokens,
                do_sample=False,
                temperature=0.1,
                return_full_text=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
            
            return outputs[0]['generated_text']
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return ""
    
    def extract_anime_list(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract anime list from HTML using LLM"""
        # Truncate HTML to fit context
        html_truncated = html[:8000]
        
        prompt = f"""Extract anime entries from this HTML. Return JSON array with title and url.

HTML:
{html_truncated}

Return ONLY valid JSON: [{{"title": "...", "url": "..."}}]"""

        result = self._generate(prompt, max_tokens=2048)
        return self._parse_json_array(result)
    
    def extract_anime_details(self, html: str, base_url: str) -> Dict[str, Any]:
        """Extract anime details and episodes from HTML using LLM"""
        html_truncated = html[:10000]
        
        prompt = f"""Extract from this HTML:
1. title, description, genres, status, rating
2. episodes list with episode_number, episode_url, episode_title

Base URL: {base_url}

HTML:
{html_truncated}

Return JSON: {{"title":"...","episodes":[{{"episode_number":"1","episode_url":"...","episode_title":"..."}}]}}"""

        result = self._generate(prompt, max_tokens=4096)
        return self._parse_json_object(result)
    
    def extract_iframe_urls(self, html: str, base_url: str) -> List[str]:
        """Extract iframe/video URLs from episode page"""
        html_truncated = html[:5000]
        
        prompt = f"""Extract all iframe src URLs from this HTML.

HTML:
{html_truncated}

Return JSON array of URLs only: ["url1", "url2"]"""

        result = self._generate(prompt, max_tokens=1024)
        urls = self._parse_json_array(result)
        return [url for url in urls if isinstance(url, str) and url.startswith('http')]
    
    def _parse_json_array(self, text: str) -> List:
        """Parse JSON array from text"""
        text = text.strip()
        if '```' in text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if match:
                text = match.group(1).strip()
        
        start = text.find('[')
        end = text.rfind(']')
        
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(text)
        except:
            return []
    
    def _parse_json_object(self, text: str) -> Dict:
        """Parse JSON object from text"""
        text = text.strip()
        if '```' in text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if match:
                text = match.group(1).strip()
        
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(text)
        except:
            return {}


class LLMExtractor:
    """Uses local LLM (Ollama) for HTML extraction"""
    
    def __init__(self, model: str = "llama3.2:3b", timeout: int = 60):
        """
        Initialize LLM extractor.
        
        Args:
            model: Ollama model to use (e.g., llama3.2:3b, mistral, phi3)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.timeout = timeout
        self.client = ollama.Client() if OLLAMA_AVAILABLE else None
        
        # Check if model is available
        if self.client:
            try:
                models = self.client.list()
                model_names = [m['name'] for m in models.get('models', [])]
                if not any(self.model in name for name in model_names):
                    logger.warning(f"Model {self.model} not found. Available: {model_names}")
                    logger.info(f"Pull the model with: ollama pull {self.model}")
            except Exception as e:
                logger.warning(f"Could not check Ollama models: {e}")
    
    def extract_anime_list(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract anime list from HTML using LLM"""
        prompt = f"""Extract all anime entries from this HTML. For each anime, extract:
- title: The anime title
- url: The full URL to the anime page

Return as JSON array: [{{"title": "...", "url": "..."}}]

HTML (truncated):
{html[:15000]}

Return ONLY the JSON array, no other text."""

        return self._extract_json_array(prompt)
    
    def extract_anime_details(self, html: str, base_url: str) -> Dict[str, Any]:
        """Extract anime details and episodes from HTML using LLM"""
        prompt = f"""Extract anime information from this HTML page:

1. Anime metadata:
   - title: Anime title
   - description: Short description (max 200 chars)
   - genres: List of genres
   - status: Ongoing/Completed/etc
   - rating: Rating if available

2. Episodes list - for each episode:
   - episode_number: Episode number or name
   - episode_url: Full URL to episode page
   - episode_title: Episode title if available

Return as JSON:
{{
    "title": "...",
    "description": "...",
    "genres": ["..."],
    "status": "...",
    "rating": "...",
    "episodes": [
        {{"episode_number": "1", "episode_url": "https://...", "episode_title": "..."}}
    ]
}}

Base URL for relative links: {base_url}

HTML (truncated):
{html[:20000]}

Return ONLY valid JSON, no other text."""

        return self._extract_json_object(prompt)
    
    def extract_iframe_urls(self, html: str, base_url: str) -> List[str]:
        """Extract iframe/video URLs from episode page using LLM"""
        prompt = f"""Extract all video iframe URLs from this HTML page.
Look for:
- <iframe> tags with src attributes
- Video player embed URLs
- Streaming URLs

Return as JSON array of URLs: ["url1", "url2", ...]

Base URL for relative links: {base_url}

HTML (truncated):
{html[:10000]}

Return ONLY the JSON array, no other text."""

        result = self._extract_json_array(prompt)
        return [url for url in result if isinstance(url, str) and url.startswith('http')]
    
    def _extract_json_array(self, prompt: str) -> List:
        """Send prompt to LLM and extract JSON array from response"""
        if not self.client:
            return []
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,  # Low temperature for consistent extraction
                    'num_predict': 4096,
                }
            )
            
            text = response.get('response', '')
            return self._parse_json_array(text)
            
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return []
    
    def _extract_json_object(self, prompt: str) -> Dict:
        """Send prompt to LLM and extract JSON object from response"""
        if not self.client:
            return {}
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'num_predict': 8192,
                }
            )
            
            text = response.get('response', '')
            return self._parse_json_object(text)
            
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {}
    
    def _parse_json_array(self, text: str) -> List:
        """Parse JSON array from text, handling common issues"""
        # Try to find JSON array in text
        text = text.strip()
        
        # Remove markdown code blocks if present
        if '```' in text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if match:
                text = match.group(1).strip()
        
        # Find array brackets
        start = text.find('[')
        end = text.rfind(']')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try parsing the whole text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []
    
    def _parse_json_object(self, text: str) -> Dict:
        """Parse JSON object from text, handling common issues"""
        text = text.strip()
        
        # Remove markdown code blocks if present
        if '```' in text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if match:
                text = match.group(1).strip()
        
        # Find object brackets
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try parsing the whole text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


class FallbackExtractor:
    """Fallback BeautifulSoup-based extractor when LLM is not available"""
    
    def __init__(self):
        from bs4 import BeautifulSoup
        self.BeautifulSoup = BeautifulSoup
    
    def extract_anime_list(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract anime list using BeautifulSoup"""
        soup = self.BeautifulSoup(html, 'html.parser')
        anime_list = []
        
        articles = soup.find_all('article', class_='bs')
        for article in articles:
            bsx = article.find('div', class_='bsx')
            if bsx:
                link = bsx.find('a', itemprop='url')
                if link:
                    title = link.get('title', '')
                    url = link.get('href', '')
                    if not title:
                        h2 = link.find('h2', itemprop='headline')
                        if h2:
                            title = h2.get_text(strip=True)
                    if url and title:
                        anime_list.append({'title': title, 'url': url})
        
        return anime_list
    
    def extract_anime_details(self, html: str, base_url: str) -> Dict[str, Any]:
        """Extract anime details using BeautifulSoup"""
        soup = self.BeautifulSoup(html, 'html.parser')
        
        result = {
            'title': None,
            'description': None,
            'genres': [],
            'status': None,
            'rating': None,
            'episodes': []
        }
        
        # Title
        title_elem = soup.find('h1', class_='entry-title') or soup.find('h1')
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
        
        # Episodes
        eplister = soup.find('div', class_='eplister')
        if eplister:
            for link in eplister.find_all('a'):
                href = link.get('href')
                if href:
                    ep_num_div = link.find('div', class_='epl-num')
                    ep_num = ep_num_div.get_text(strip=True) if ep_num_div else f"Episode {len(result['episodes']) + 1}"
                    ep_title_div = link.find('div', class_='epl-title')
                    ep_title = ep_title_div.get_text(strip=True) if ep_title_div else None
                    
                    result['episodes'].append({
                        'episode_number': ep_num,
                        'episode_url': urljoin(base_url, href),
                        'episode_title': ep_title
                    })
        
        return result
    
    def extract_iframe_urls(self, html: str, base_url: str) -> List[str]:
        """Extract iframe URLs using BeautifulSoup"""
        soup = self.BeautifulSoup(html, 'html.parser')
        urls = []
        
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
            if src:
                full_url = urljoin(base_url, src)
                if full_url not in urls:
                    urls.append(full_url)
        
        return urls


class UnifiedAnimeScraper:
    """Unified scraper that combines all steps with LLM extraction"""
    
    def __init__(self, 
                 output_dir: str = "scraped_data",
                 workers: int = 5,
                 delay: float = 0.3,
                 output_format: str = "json",
                 use_llm: bool = True,
                 llm_model: str = "llama3.2:3b"):
        """
        Initialize the unified scraper.
        
        Args:
            output_dir: Directory to save all data
            workers: Number of parallel workers
            delay: Delay between requests per worker
            output_format: 'json' or 'toon'
            use_llm: Whether to use LLM for extraction
            llm_model: Ollama model to use
        """
        self.output_dir = Path(output_dir)
        self.workers = workers
        self.delay = delay
        self.output_format = output_format
        self.use_llm = use_llm and OLLAMA_AVAILABLE
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.anime_dir = self.output_dir / "anime"
        self.anime_dir.mkdir(exist_ok=True)
        
        # Initialize extractor
        if self.use_llm:
            # Check if model is a Python model alias
            if llm_model in PythonLLMExtractor.SUPPORTED_MODELS or '/' in llm_model:
                if TRANSFORMERS_AVAILABLE:
                    self.extractor = PythonLLMExtractor(model=llm_model)
                    logger.info(f"Using Python LLM extractor with model: {llm_model}")
                else:
                    logger.warning("transformers not available, falling back to BeautifulSoup")
                    self.extractor = FallbackExtractor()
            elif OLLAMA_AVAILABLE:
                self.extractor = LLMExtractor(model=llm_model)
                logger.info(f"Using Ollama LLM extractor with model: {llm_model}")
            else:
                logger.warning("No LLM backend available, falling back to BeautifulSoup")
                self.extractor = FallbackExtractor()
        else:
            self.extractor = FallbackExtractor()
            logger.info("Using BeautifulSoup fallback extractor")
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.completed = self.load_progress()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'anime_scraped': 0,
            'episodes_found': 0,
            'video_urls_found': 0,
            'failed': 0
        }
        self.stats_lock = threading.Lock()
        
        # Base URL
        self.base_url = "https://zoroto.com.in"
    
    def create_session(self) -> requests.Session:
        """Create a new HTTP session"""
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
            except Exception:
                pass
        return set()
    
    def save_progress(self, url: str):
        """Save progress (thread-safe)"""
        with self.lock:
            self.completed.add(url)
            try:
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump({'completed': list(self.completed)}, f)
            except Exception:
                pass
    
    def fetch_page(self, url: str, session: requests.Session) -> Optional[str]:
        """Fetch a page and return HTML"""
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def sanitize_filename(self, title: str) -> str:
        """Create safe filename from title"""
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', '_', safe.strip())
        return safe[:200] or "unnamed"
    
    def get_url_hash(self, url: str) -> str:
        """Get short hash of URL"""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def scrape_anime_list(self, session: requests.Session, mode: str = "quick") -> List[Dict[str, str]]:
        """
        Step 1: Scrape the anime list from zoroto.com.in
        
        Args:
            session: HTTP session
            mode: 'quick' (first page only) or 'full' (all pages A-Z)
        """
        logger.info(f"Step 1: Scraping anime list (mode: {mode})...")
        
        all_anime = []
        seen_urls = set()
        
        if mode == "quick":
            # Just fetch first page
            url = f"{self.base_url}/az-list/"
            html = self.fetch_page(url, session)
            if html:
                anime_list = self.extractor.extract_anime_list(html, url)
                for anime in anime_list:
                    if anime.get('url') and anime['url'] not in seen_urls:
                        all_anime.append(anime)
                        seen_urls.add(anime['url'])
        else:
            # Fetch all letters
            letters = ['.', '0-9'] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]
            
            for letter in letters:
                logger.info(f"Fetching letter: {letter}")
                url = f"{self.base_url}/az-list/?show={letter}"
                
                page = 1
                while True:
                    page_url = url if page == 1 else f"{self.base_url}/az-list/page/{page}/?show={letter}"
                    html = self.fetch_page(page_url, session)
                    
                    if not html:
                        break
                    
                    anime_list = self.extractor.extract_anime_list(html, page_url)
                    
                    if not anime_list:
                        break
                    
                    new_count = 0
                    for anime in anime_list:
                        if anime.get('url') and anime['url'] not in seen_urls:
                            all_anime.append(anime)
                            seen_urls.add(anime['url'])
                            new_count += 1
                    
                    logger.info(f"  Page {page}: Found {len(anime_list)} anime ({new_count} new)")
                    
                    # Check if there are more pages
                    if 'page-numbers' not in html or new_count == 0:
                        break
                    
                    page += 1
                    time.sleep(self.delay)
                
                time.sleep(self.delay)
        
        logger.info(f"Total anime found: {len(all_anime)}")
        return all_anime
    
    def scrape_single_anime(self, anime: Dict[str, str], session: requests.Session) -> Optional[Dict[str, Any]]:
        """
        Steps 2+3: Scrape anime details, episodes, and video URLs
        
        Returns complete anime data with episodes and video URLs
        """
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
        
        episodes = details.get('episodes', [])
        
        # For each episode, extract video URLs
        episodes_with_videos = []
        for ep in episodes:
            ep_url = ep.get('episode_url')
            if ep_url:
                # Fetch episode page
                ep_html = self.fetch_page(ep_url, session)
                iframe_urls = []
                
                if ep_html:
                    iframe_urls = self.extractor.extract_iframe_urls(ep_html, ep_url)
                
                episodes_with_videos.append({
                    'episode_number': ep.get('episode_number'),
                    'episode_url': ep_url,
                    'episode_title': ep.get('episode_title'),
                    'video_sources': iframe_urls,
                    'has_videos': len(iframe_urls) > 0
                })
                
                with self.stats_lock:
                    self.stats['video_urls_found'] += len(iframe_urls)
                
                time.sleep(self.delay)
        
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
    
    def run(self, mode: str = "quick", limit: Optional[int] = None, resume: bool = True):
        """
        Run the complete unified pipeline.
        
        Args:
            mode: 'quick' or 'full'
            limit: Maximum anime to scrape
            resume: Whether to skip already completed
        """
        start_time = time.time()
        
        logger.info("="*60)
        logger.info("UNIFIED ANIME SCRAPER WITH LLM")
        logger.info("="*60)
        logger.info(f"Mode: {mode}")
        logger.info(f"Workers: {self.workers}")
        logger.info(f"Output format: {self.output_format}")
        logger.info(f"Using LLM: {self.use_llm}")
        logger.info("="*60)
        
        # Create main session for anime list
        session = self.create_session()
        
        # Step 1: Get anime list
        anime_list = self.scrape_anime_list(session, mode)
        
        if not anime_list:
            logger.error("No anime found!")
            return
        
        # Filter if resuming
        if resume:
            anime_list = [a for a in anime_list if a['url'] not in self.completed]
        
        # Apply limit
        if limit:
            anime_list = anime_list[:limit]
        
        total = len(anime_list)
        logger.info(f"\nStep 2-3: Scraping {total} anime with episodes and video URLs...")
        logger.info(f"Using {self.workers} parallel workers\n")
        
        # Process anime in parallel
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            sessions = {}
            
            def get_session():
                thread_id = threading.get_ident()
                if thread_id not in sessions:
                    sessions[thread_id] = self.create_session()
                return sessions[thread_id]
            
            # Submit all anime
            future_to_anime = {
                executor.submit(self.scrape_single_anime, anime, get_session()): anime
                for anime in anime_list
            }
            
            # Collect results
            for i, future in enumerate(as_completed(future_to_anime), 1):
                anime = future_to_anime[future]
                try:
                    result = future.result()
                    if result:
                        self.save_anime_data(result)
                        self.save_progress(anime['url'])
                        
                        logger.info(f"[{i}/{total}] ✓ {anime['title']} "
                                  f"({result['total_episodes']} eps, "
                                  f"{result['available_episodes']} with videos)")
                    else:
                        logger.warning(f"[{i}/{total}] ✗ Failed: {anime['title']}")
                except Exception as e:
                    logger.error(f"[{i}/{total}] Error: {anime['title']} - {e}")
                
                # Progress update
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (total - i) / rate if rate > 0 else 0
                    logger.info(f"Progress: {i}/{total} | Rate: {rate:.1f}/min | ETA: {eta:.1f}min")
        
        # Step 4: Create index and statistics
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
        logger.info(f"Time taken: {elapsed/60:.1f} minutes")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("="*60)
    
    def _create_index(self):
        """Create index and statistics files"""
        logger.info("\nStep 4: Creating index and statistics...")
        
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
                    
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
        
        # Sort by title
        all_anime.sort(key=lambda x: x.get('title', '').lower())
        
        # Save index
        index = {
            'total_anime': len(all_anime),
            'total_episodes': total_episodes,
            'total_video_sources': total_videos,
            'anime_list': all_anime
        }
        
        index_path = self.output_dir / f"anime_index{ext}"
        if self.output_format == 'toon' and TOON_AVAILABLE:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(toon.encode(index))
        else:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        
        # Save statistics
        stats = {
            'total_anime': len(all_anime),
            'total_episodes': total_episodes,
            'total_video_sources': total_videos,
            'avg_episodes_per_anime': round(total_episodes / len(all_anime), 1) if all_anime else 0,
        }
        
        stats_path = self.output_dir / f"statistics{ext}"
        if self.output_format == 'toon' and TOON_AVAILABLE:
            with open(stats_path, 'w', encoding='utf-8') as f:
                f.write(toon.encode(stats))
        else:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Created index with {len(all_anime)} anime")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Unified Anime Scraper with Local LLM'
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'full'],
        default='quick',
        help='Scraping mode: quick (first page) or full (all pages)'
    )
    parser.add_argument(
        '-o', '--output',
        default='scraped_data',
        help='Output directory (default: scraped_data)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers (default: 5)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.3,
        help='Delay between requests in seconds (default: 0.3)'
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
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--use-llm',
        action='store_true',
        default=True,
        help='Use local LLM for extraction (default: True)'
    )
    parser.add_argument(
        '--no-llm',
        dest='use_llm',
        action='store_false',
        help='Use BeautifulSoup fallback instead of LLM'
    )
    parser.add_argument(
        '--model',
        default='qwen2-0.5b',
        help='LLM model to use. Python models: qwen2-0.5b, qwen2-1.5b, phi3-mini, tinyllama, smollm. Ollama: llama3.2:3b, mistral, etc. (default: qwen2-0.5b)'
    )
    parser.set_defaults(resume=True)
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Check Ollama availability
    if args.use_llm and not OLLAMA_AVAILABLE:
        logger.warning("Ollama not available. Install with: pip install ollama")
        logger.info("Falling back to BeautifulSoup extractor")
        args.use_llm = False
    
    # Initialize and run scraper
    scraper = UnifiedAnimeScraper(
        output_dir=args.output,
        workers=args.workers,
        delay=args.delay,
        output_format=args.format,
        use_llm=args.use_llm,
        llm_model=args.model
    )
    
    scraper.run(
        mode=args.mode,
        limit=args.limit,
        resume=args.resume
    )


if __name__ == "__main__":
    main()
