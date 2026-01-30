# Video URL Scraper

A Python scraper that extracts video iframe/stream URLs from anime episode pages.

## Features

- 📺 **Video URL Extraction**: Finds iframe and video source URLs
- 🎬 **Multiple Patterns**: Supports various video player implementations
- 🏷️ **Quality Detection**: Extracts quality info (720p, 1080p, HD, etc.)
- 🖥️ **Server Detection**: Identifies video hosting servers
- 💾 **Organized Storage**: Saves in structured JSON format
- 🔄 **Resume Capability**: Can resume interrupted scraping sessions
- 📊 **Progress Tracking**: Saves progress after each anime
- 🛡️ **Error Handling**: Robust error handling with logging
- ⏱️ **Rate Limiting**: Respectful delays between requests

## Installation

```bash
# Already installed with previous scrapers
pip install requests beautifulsoup4
```

## Usage

### Basic Usage
```bash
python video_url_scraper.py --input anime_data/episodes
```

### With Options
```bash
# Test with first 5 anime
python video_url_scraper.py --input anime_data/episodes --limit 5

# Custom output directory
python video_url_scraper.py --input anime_data/episodes --output my_video_data

# Increase delay between requests
python video_url_scraper.py --input anime_data/episodes --delay 3.0

# Start fresh (ignore previous progress)
python video_url_scraper.py --input anime_data/episodes --no-resume

# Resume from previous run (default)
python video_url_scraper.py --input anime_data/episodes --resume
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input` | Input directory with episode JSON files | **Required** |
| `-o, --output` | Output directory for video data | `video_data` |
| `--limit` | Limit number of anime to process | `None` (all) |
| `--delay` | Delay between requests (seconds) | `2.0` |
| `--resume` | Resume from previous run | `True` |
| `--no-resume` | Start fresh, ignore progress | `False` |

## Input Format

Reads episode JSON files created by `anime_episode_scraper.py`:
```json
{
  "title": "One Piece",
  "episodes": [
    {
      "episode_number": "1",
      "episode_title": "Episode 1",
      "url": "https://zoroto.com.in/one-piece-episode-1/"
    }
  ]
}
```

## Output Structure

```
video_data/
├── videos/
│   ├── One_Piece_a1b2c3d4.json
│   ├── Naruto_e5f6g7h8.json
│   └── ...
├── progress.json
└── video_url_scraper.log
```

## Output Format

Each video JSON file contains:

```json
{
  "anime_title": "One Piece",
  "anime_url": "https://zoroto.com.in/anime/one-piece/",
  "metadata": {
    "title": "One Piece",
    "description": "...",
    "genres": ["Action", "Adventure"]
  },
  "total_episodes": 1000,
  "episodes_with_videos": [
    {
      "episode_number": "1",
      "episode_title": "Episode 1",
      "episode_url": "https://zoroto.com.in/one-piece-episode-1/",
      "video_sources": [
        {
          "type": "iframe",
          "url": "https://example.com/embed/video123",
          "quality": "1080p",
          "server": "server1"
        },
        {
          "type": "iframe",
          "url": "https://example.com/embed/video456",
          "quality": "720p",
          "server": "server2"
        }
      ],
      "source_count": 2,
      "scraped_at": "2025-10-17 20:30:45"
    }
  ],
  "total_video_sources": 2000,
  "scraped_at": "2025-10-17 20:30:45",
  "source_file": "One_Piece_a1b2c3d4.json"
}
```

## Video Source Types

The scraper detects multiple source types:

1. **iframe**: Video embedded in iframe tags
2. **server_option**: Server selection buttons with data attributes
3. **direct_video**: Direct `<video>` tag sources
4. **video_source**: `<source>` tags within video elements
5. **data_attribute**: Links with data-src/data-video attributes
6. **streaming_link**: Links to streaming.php or embed URLs

## Extraction Patterns

### Pattern 1: iframes
```html
<iframe src="https://example.com/embed/video"></iframe>
```

### Pattern 2: Server Buttons
```html
<li data-video="https://server1.com/video">Server 1</li>
```

### Pattern 3: Video Tags
```html
<video src="https://example.com/video.mp4">
  <source src="https://example.com/video.mp4" label="1080p">
</video>
```

### Pattern 4: Data Attributes
```html
<div data-src="https://example.com/embed/video"></div>
```

### Pattern 5: Streaming Links
```html
<a href="https://site.com/streaming.php?id=123">Watch</a>
```

## Quality Detection

Automatically detects quality from:
- URL patterns: `720p`, `1080p`, `4K`
- Keywords: `HD`, `SD`, `FHD`, `UHD`
- Query parameters: `quality=high`
- HTML attributes: `data-quality="1080p"`

## Server Detection

Identifies servers from:
- Domain names
- Query parameters: `?server=server1`
- Button text
- URL paths

## Examples

### Example 1: Test with 5 Anime
```bash
python video_url_scraper.py \
  --input anime_data/episodes \
  --limit 5 \
  --output test_video_data
```

### Example 2: Resume Scraping
```bash
# Start scraping
python video_url_scraper.py --input anime_data/episodes

# If interrupted, resume with same command
python video_url_scraper.py --input anime_data/episodes
```

### Example 3: Slower Scraping
```bash
python video_url_scraper.py \
  --input anime_data/episodes \
  --delay 3.0
```

### Example 4: Fresh Start
```bash
python video_url_scraper.py \
  --input anime_data/episodes \
  --no-resume
```

## Workflow

1. **Load Episode Files**: Reads all JSON files from input directory
2. **Check Progress**: Loads previous progress (if resume enabled)
3. **For Each Anime**:
   - Skip if already completed (resume mode)
   - For each episode:
     - Fetch episode page HTML
     - Extract all video iframe/source URLs
     - Detect quality and server info
     - Apply rate limiting
   - Save complete anime video data
   - Update progress
4. **Complete**: Log summary statistics

## Performance

- **Speed**: ~2-3 seconds per episode (configurable)
- **For 1 anime** (13 episodes): ~30-45 seconds
- **For 100 anime** (avg 50 eps): ~2-4 hours
- **For 1000 anime**: ~20-40 hours

**Note**: This is much slower than episode scraping because we need to visit EVERY episode page!

## Resume Capability

The scraper saves progress after each completed anime:
- Progress stored in `progress.json`
- On restart, skips completed anime files
- Can disable with `--no-resume`
- Safe to interrupt at any time

## Error Handling

- Network errors: Logged and episode marked with error
- Parsing errors: Logged, empty sources list
- Missing sources: Logged as warning
- Timeouts: 30 second timeout per request
- Invalid URLs: Skipped with warning

## Best Practices

1. **Start Small**: Test with `--limit 5` first
2. **Monitor Progress**: Check log file regularly
3. **Use Resume**: Always use resume for large batches
4. **Be Patient**: This takes MUCH longer than previous steps
5. **Respect Delays**: Keep delay at 2+ seconds
6. **Run Overnight**: For large batches, run overnight

## Troubleshooting

**No video sources found?**
- Check if episode page structure has changed
- Look at log file for errors
- Visit episode URL manually to verify
- Check if iframe is loaded dynamically (JavaScript)

**Scraper very slow?**
- This is expected! Each episode requires separate request
- Consider running in batches with `--limit`
- Run overnight for full scrape

**Progress not saving?**
- Check write permissions
- Verify disk space
- Check log for errors

**Getting blocked?**
- Increase `--delay` to 3-5 seconds
- Use VPN if necessary
- Scrape during off-peak hours

## Integration with Pipeline

Complete workflow:
```bash
# Step 1: Get anime list (10-15 min)
python zoroto_scraper.py --mode letters -o zoroto_complete.json

# Step 2: Get episodes for each anime (2-3 hours)
python anime_episode_scraper.py --input zoroto_complete.json

# Step 3: Get video URLs for each episode (20-40 hours!)
python video_url_scraper.py --input anime_data/episodes

# Result: Complete database with video URLs!
```

## Realistic Timeline

For **4000 anime** with average **50 episodes each**:
- Total episodes: ~200,000
- Time per episode: 2 seconds
- **Total time: ~110 hours** (4-5 days)

**Recommendation**: Run in batches using `--limit`

## Batch Processing Example

```bash
# Process 100 anime at a time
for i in {0..40}; do
  start=$((i * 100))
  echo "Processing batch $i (starting at $start)"
  python video_url_scraper.py \
    --input anime_data/episodes \
    --limit 100 \
    --resume
  echo "Batch $i complete. Sleeping 5 minutes..."
  sleep 300
done
```

## Output Statistics

After completion, each anime file shows:
- Total episodes processed
- Total video sources found
- Sources per episode (average)
- Failed episodes (if any)

## Data Size

Expected disk usage:
- Each video JSON: 10-100KB (depends on episode count)
- Total for 4000 anime: ~100-500MB

## Logging

All activities are logged:
- Console output (INFO level)
- File logging with timestamps
- Progress indicators
- Error messages with stack traces
- Summary statistics

## Notes

- Default delay is 2 seconds (respectful)
- Each episode requires separate page fetch
- This is the slowest step in the pipeline
- Progress persists across runs
- All data saved in UTF-8 encoding
- Duplicate URLs are automatically removed

## Future Enhancements

- Multi-threading for faster scraping
- Direct video URL extraction (bypass embed)
- Download quality selection
- Subtitle URL extraction
- Video file metadata
- M3U8 playlist parsing
- Direct download links

