#!/usr/bin/env python3
"""
Anime Data Organizer

Organizes all scraped anime data into a clean, website-ready format.
Combines anime list, episodes, and video URLs into unified structure.

Usage:
    python data_organizer.py
    python data_organizer.py --output-dir website_data --format combined
"""

import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import os

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


class AnimeDataOrganizer:
    """Organizes anime data for website consumption"""
    
    def __init__(self, video_data_dir: str = "video_data/videos", 
                 output_dir: str = "website_data",
                 output_format: str = "json"):
        """
        Initialize the organizer.
        
        Args:
            video_data_dir: Directory with video JSON/TOON files
            output_dir: Directory for organized output
            output_format: Output format - 'json' or 'toon'
        """
        self.video_data_dir = Path(video_data_dir)
        self.output_dir = Path(output_dir)
        self.output_format = output_format
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
    def load_video_data(self, video_file: Path) -> Optional[Dict]:
        """Load a single video data file (JSON or TOON)"""
        try:
            with open(video_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if video_file.suffix == '.toon':
            if not TOON_AVAILABLE:
                logger.error("python-toon not installed. Run: pip install python-toon")
                return None
            return toon.decode(content)
            else:
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading {video_file}: {e}")
            return None
    
    def save_data(self, data: Dict, filepath: Path):
        """Save data to JSON or TOON file based on output_format"""
        try:
            if self.output_format == 'toon' and TOON_AVAILABLE:
                toon_str = toon.encode(data)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(toon_str)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
    
    def organize_anime_data(self, video_data: Dict) -> Dict:
        """
        Organize anime data into clean website format.
        
        Args:
            video_data: Raw video data from scraper
            
        Returns:
            Clean, organized anime data
        """
        anime_title = video_data.get('anime_title', 'Unknown')
        episodes = video_data.get('episodes', [])
        
        # Organize episodes
        organized_episodes = []
        for ep in episodes:
            episode_data = {
                'episode_number': ep.get('episode_number'),
                'episode_url': ep.get('episode_url'),
                'video_sources': ep.get('iframe_urls', []),
                'has_videos': len(ep.get('iframe_urls', [])) > 0
            }
            organized_episodes.append(episode_data)
        
        # Create organized structure
        organized = {
            'title': anime_title,
            'total_episodes': len(episodes),
            'available_episodes': len([e for e in organized_episodes if e['has_videos']]),
            'episodes': organized_episodes
        }
        
        return organized
    
    def create_anime_index(self, all_anime: List[Dict]) -> Dict:
        """
        Create searchable index of all anime.
        
        Args:
            all_anime: List of all anime data
            
        Returns:
            Index dictionary
        """
        index = {
            'total_anime': len(all_anime),
            'total_episodes': sum(a.get('total_episodes', 0) for a in all_anime),
            'anime_list': []
        }
        
        for anime in all_anime:
            index['anime_list'].append({
                'title': anime.get('title'),
                'total_episodes': anime.get('total_episodes'),
                'available_episodes': anime.get('available_episodes')
            })
        
        # Sort by title
        index['anime_list'].sort(key=lambda x: x.get('title', '').lower())
        
        return index
    
    def create_search_data(self, all_anime: List[Dict]) -> List[Dict]:
        """
        Create search-optimized data.
        
        Args:
            all_anime: List of all anime data
            
        Returns:
            Search data list
        """
        search_data = []
        
        for anime in all_anime:
            title = anime.get('title', '')
            search_data.append({
                'title': title,
                'title_lower': title.lower(),
                'total_episodes': anime.get('total_episodes'),
                'available_episodes': anime.get('available_episodes')
            })
        
        return search_data
    
    def organize_all(self, format_type: str = "separate"):
        """
        Organize all anime data.
        
        Args:
            format_type: Output format - "separate", "combined", or "both"
        """
        logger.info("Starting data organization...")
        logger.info(f"Output format: {self.output_format}")
        
        # Get all video files (JSON and TOON)
        video_files = list(self.video_data_dir.glob('*.json')) + list(self.video_data_dir.glob('*.toon'))
        
        if not video_files:
            logger.error(f"No video data files found in {self.video_data_dir}")
            return
        
        logger.info(f"Found {len(video_files)} anime to organize")
        
        all_anime = []
        
        # Process each anime
        for i, video_file in enumerate(video_files, 1):
            if i % 100 == 0:
                logger.info(f"Processing {i}/{len(video_files)}...")
            
            video_data = self.load_video_data(video_file)
            if not video_data:
                continue
            
            organized = self.organize_anime_data(video_data)
            all_anime.append(organized)
            
            # Save individual anime files if requested
            if format_type in ["separate", "both"]:
                # Use correct extension based on output format
                ext = '.toon' if self.output_format == 'toon' else '.json'
                base_name = video_file.stem
                anime_file = self.output_dir / f"{base_name}{ext}"
                self.save_data(organized, anime_file)
        
        logger.info(f"Organized {len(all_anime)} anime")
        
        # Create combined file if requested
        if format_type in ["combined", "both"]:
            logger.info("Creating combined data file...")
            ext = '.toon' if self.output_format == 'toon' else '.json'
            combined_file = self.output_dir / f"all_anime{ext}"
            self.save_data({'anime': all_anime}, combined_file)
            logger.info(f"Saved combined data to: {combined_file}")
        
        # Determine file extension
        ext = '.toon' if self.output_format == 'toon' else '.json'
        
        # Create index
        logger.info("Creating anime index...")
        index = self.create_anime_index(all_anime)
        index_file = self.output_dir / f"anime_index{ext}"
        self.save_data(index, index_file)
        logger.info(f"Saved index to: {index_file}")
        
        # Create search data
        logger.info("Creating search data...")
        search_data = self.create_search_data(all_anime)
        search_file = self.output_dir / f"search_data{ext}"
        self.save_data({'search': search_data}, search_file)
        logger.info(f"Saved search data to: {search_file}")
        
        # Create statistics
        logger.info("Creating statistics...")
        stats = self.create_statistics(all_anime)
        stats_file = self.output_dir / f"statistics{ext}"
        self.save_data(stats, stats_file)
        logger.info(f"Saved statistics to: {stats_file}")
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("Data organization complete!")
        logger.info(f"Total anime: {len(all_anime)}")
        logger.info(f"Total episodes: {stats['total_episodes']}")
        logger.info(f"Total video sources: {stats['total_video_sources']}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"{'='*60}")
    
    def create_statistics(self, all_anime: List[Dict]) -> Dict:
        """Create statistics about the data"""
        total_episodes = sum(a.get('total_episodes', 0) for a in all_anime)
        available_episodes = sum(a.get('available_episodes', 0) for a in all_anime)
        
        # Count total video sources
        total_videos = 0
        for anime in all_anime:
            for episode in anime.get('episodes', []):
                total_videos += len(episode.get('video_sources', []))
        
        # Find anime with most episodes
        most_episodes = max(all_anime, key=lambda x: x.get('total_episodes', 0)) if all_anime else {}
        
        stats = {
            'total_anime': len(all_anime),
            'total_episodes': total_episodes,
            'available_episodes': available_episodes,
            'total_video_sources': total_videos,
            'avg_episodes_per_anime': round(total_episodes / len(all_anime), 1) if all_anime else 0,
            'avg_sources_per_episode': round(total_videos / total_episodes, 1) if total_episodes else 0,
            'anime_with_most_episodes': {
                'title': most_episodes.get('title'),
                'episodes': most_episodes.get('total_episodes')
            } if most_episodes else {}
        }
        
        return stats


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Organize anime data for website'
    )
    parser.add_argument(
        '-i', '--input',
        default='video_data/videos',
        help='Input directory with video JSON files (default: video_data/videos)'
    )
    parser.add_argument(
        '-o', '--output',
        default='website_data',
        help='Output directory (default: website_data)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['separate', 'combined', 'both'],
        default='both',
        help='Output format: separate files, combined file, or both (default: both)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'toon'],
        default='json',
        help='Data format: json or toon (default: json)'
    )
    
    return parser.parse_args()


def main():
    """Main execution"""
    args = parse_args()
    
    logger.info("Anime Data Organizer")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Format: {args.format}")
    logger.info(f"Output format: {args.output_format}")
    
    # Check input directory exists
    if not Path(args.input).exists():
        logger.error(f"Input directory does not exist: {args.input}")
        return
    
    # Initialize organizer
    organizer = AnimeDataOrganizer(
        video_data_dir=args.input,
        output_dir=args.output,
        output_format=args.output_format
    )
    
    # Organize data
    organizer.organize_all(format_type=args.format)


if __name__ == "__main__":
    main()

