# Simplified Video URL Scraper Output

## Changes Made

✅ **Removed unnecessary metadata**: No more quality, server, type info  
✅ **Just iframe URLs**: Simple list of all iframe sources found  
✅ **Cleaner structure**: Minimal, easy-to-parse format  
✅ **All iframes included**: Captures ALL iframe sources, not just specific servers

## New Output Format

```json
{
  "anime_title": "One Piece",
  "total_episodes": 1000,
  "episodes": [
    {
      "episode_number": "1",
      "episode_url": "https://zoroto.com.in/one-piece-episode-1/",
      "iframe_urls": [
        "https://streamx2.com/embed/video123",
        "https://server2.com/embed/video456",
        "https://anothersource.com/player/xyz"
      ]
    },
    {
      "episode_number": "2",
      "episode_url": "https://zoroto.com.in/one-piece-episode-2/",
      "iframe_urls": [
        "https://streamx2.com/embed/video789",
        "https://server2.com/embed/video012"
      ]
    }
  ]
}
```

## What Gets Captured

The scraper now finds ALL iframes from:
- `<iframe src="...">`
- `<iframe data-src="...">`
- `<iframe data-lazy-src="...">`

Including servers like:
- streamx2.com
- Any other video hosting services
- All embed URLs
- All player URLs

## Usage

```bash
# Same command as before
python video_url_scraper.py --input anime_data/episodes --limit 5

# Test with existing data
python video_url_scraper.py --input anime_data/episodes --limit 5 --no-resume
```

## Comparison

### Old Format (Complex)
```json
{
  "anime_title": "One Piece",
  "anime_url": "https://...",
  "metadata": {...},
  "total_episodes": 1000,
  "episodes_with_videos": [
    {
      "episode_number": "1",
      "episode_title": "Episode 1",
      "episode_url": "https://...",
      "video_sources": [
        {
          "type": "iframe",
          "url": "https://streamx2.com/...",
          "quality": "1080p",
          "server": "streamx2"
        }
      ],
      "source_count": 1,
      "scraped_at": "2025-10-17 20:30:45"
    }
  ],
  "total_video_sources": 1000,
  "scraped_at": "2025-10-17 20:30:45",
  "source_file": "One_Piece.json"
}
```

### New Format (Simple) ✅
```json
{
  "anime_title": "One Piece",
  "total_episodes": 1000,
  "episodes": [
    {
      "episode_number": "1",
      "episode_url": "https://...",
      "iframe_urls": [
        "https://streamx2.com/...",
        "https://server2.com/...",
        "https://anothersource.com/..."
      ]
    }
  ]
}
```

## Benefits

1. **Simpler**: Less metadata clutter
2. **Smaller file size**: ~50-70% smaller JSON files
3. **Easier to parse**: Direct access to iframe URLs
4. **All sources**: Doesn't filter by server name
5. **Cleaner**: No redundant timestamps and counters

## Quick Test

```bash
# Clear old test data
rm -rf test_videos

# Run with simplified scraper
python video_url_scraper.py \
  --input anime_data/episodes \
  --limit 5 \
  --output test_videos

# Check the output
cat test_videos/videos/*.json | head -50
```

## Processing Existing Data

To re-scrape with new simplified format:
```bash
# Clear progress to start fresh
rm video_data/progress.json

# Or use --no-resume flag
python video_url_scraper.py \
  --input anime_data/episodes \
  --no-resume
```

