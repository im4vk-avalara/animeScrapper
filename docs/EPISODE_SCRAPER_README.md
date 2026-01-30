# Anime Episode Scraper

A Python scraper that reads an anime list (JSON) and extracts episode URLs for each anime.

## Features

- 📋 **Reads Anime List**: Processes JSON file with anime URLs
- 🎬 **Episode Extraction**: Finds all episode URLs from each anime page
- 💾 **Organized Storage**: Saves data in structured folder hierarchy
- 🔄 **Resume Capability**: Can resume interrupted scraping sessions
- 📊 **Progress Tracking**: Saves progress after each anime
- 🛡️ **Error Handling**: Robust error handling with logging
- ⏱️ **Rate Limiting**: Respectful delays between requests
- 🏷️ **Metadata Extraction**: Extracts title, description, genres, rating, etc.
- 📝 **Comprehensive Logging**: Both file and console logging

## Installation

```bash
# Already installed with previous scrapers
pip install requests beautifulsoup4
```

## Usage

### Basic Usage
```bash
python anime_episode_scraper.py --input zoroto_complete.json
```

### With Options
```bash
# Limit to first 10 anime (testing)
python anime_episode_scraper.py --input zoroto_complete.json --limit 10

# Custom output directory
python anime_episode_scraper.py --input zoroto_complete.json --output my_anime_data

# Increase delay between requests
python anime_episode_scraper.py --input zoroto_complete.json --delay 2.0

# Start fresh (ignore previous progress)
python anime_episode_scraper.py --input zoroto_complete.json --no-resume

# Resume from previous run (default)
python anime_episode_scraper.py --input zoroto_complete.json --resume
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input` | Input JSON file with anime list | **Required** |
| `-o, --output` | Output directory for anime data | `anime_data` |
| `--limit` | Limit number of anime to scrape | `None` (all) |
| `--delay` | Delay between requests (seconds) | `1.5` |
| `--resume` | Resume from previous run | `True` |
| `--no-resume` | Start fresh, ignore progress | `False` |

## Output Structure

```
anime_data/
├── episodes/
│   ├── One_Piece_a1b2c3d4.json
│   ├── Naruto_e5f6g7h8.json
│   └── ...
├── html/ (reserved for future use)
├── progress.json
└── anime_episode_scraper.log
```

### episodes/ Directory
Contains JSON files for each anime with:
- Anime metadata (title, description, genres, rating, status)
- List of all episodes with URLs
- Scraping timestamp

### progress.json
Tracks which anime have been successfully scraped. Format:
```json
{
  "completed": [
    "https://zoroto.com.in/anime/one-piece/",
    "https://zoroto.com.in/anime/naruto/"
  ]
}
```

### Log File
All scraping activity is logged to `anime_episode_scraper.log`

## Output Format

Each anime JSON file contains:

```json
{
  "title": "One Piece",
  "url": "https://zoroto.com.in/anime/one-piece/",
  "metadata": {
    "title": "One Piece",
    "description": "Monkey D. Luffy refuses to let...",
    "genres": ["Action", "Adventure", "Fantasy", "Shounen"],
    "status": "Ongoing",
    "rating": "8.72"
  },
  "episodes": [
    {
      "episode_number": "Episode 1",
      "episode_title": "I'm Luffy! The Man Who Will Become Pirate King!",
      "url": "https://zoroto.com.in/one-piece-episode-1/"
    },
    {
      "episode_number": "Episode 2",
      "episode_title": "The Great Swordsman Appears!",
      "url": "https://zoroto.com.in/one-piece-episode-2/"
    }
  ],
  "episode_count": 1000,
  "scraped_at": "2025-10-17 15:30:45"
}
```

## Episode Extraction Patterns

The scraper uses multiple patterns to find episodes:

1. **Pattern 1**: `<div class="eplister">` structure (most common)
2. **Pattern 2**: `<ul>` lists with episode class
3. **Pattern 3**: Links with `data-episode` attributes
4. **Pattern 4**: Direct episode links matching URL patterns

## Examples

### Example 1: Test with 5 Anime
```bash
python anime_episode_scraper.py \
  --input zoroto_complete.json \
  --limit 5 \
  --output test_data
```

### Example 2: Resume Scraping
```bash
# Start scraping
python anime_episode_scraper.py --input zoroto_complete.json

# If interrupted, resume with same command
python anime_episode_scraper.py --input zoroto_complete.json
```

### Example 3: Scrape with Longer Delays
```bash
# For slower/more respectful scraping
python anime_episode_scraper.py \
  --input zoroto_complete.json \
  --delay 3.0
```

### Example 4: Fresh Start
```bash
# Ignore previous progress and start over
python anime_episode_scraper.py \
  --input zoroto_complete.json \
  --no-resume
```

## Workflow

1. **Load Anime List**: Reads JSON file with anime URLs
2. **Check Progress**: Loads previous progress (if resume enabled)
3. **For Each Anime**:
   - Skip if already completed (resume mode)
   - Fetch anime page HTML
   - Extract metadata (title, description, genres, etc.)
   - Extract all episode URLs
   - Save to JSON file
   - Update progress
   - Apply rate limiting delay
4. **Complete**: Log summary statistics

## Resume Capability

The scraper automatically saves progress:
- After each successful anime scrape
- Progress stored in `progress.json`
- On restart, skips completed anime
- Can disable with `--no-resume`

## Error Handling

- Network errors: Logged and skipped
- Parsing errors: Logged with full traceback
- File I/O errors: Logged but doesn't stop scraping
- Invalid URLs: Skipped with warning
- Timeouts: 30 second timeout per request

## Performance

- **Speed**: ~1.5 seconds per anime (configurable)
- **Memory**: Minimal (processes one at a time)
- **Disk**: ~5-50KB per anime JSON file
- **Time Estimate**: 
  - 100 anime: ~3-5 minutes
  - 1000 anime: ~30-50 minutes
  - 4000 anime: ~2-3 hours

## Logging

All activities are logged:
- Console output (INFO level)
- File logging (with timestamps)
- Progress indicators
- Error messages with stack traces

## Best Practices

1. **Start with Limit**: Test with `--limit 10` first
2. **Use Resume**: Always use resume for large batches
3. **Monitor Logs**: Check log file for errors
4. **Respect Delays**: Don't reduce delay below 1 second
5. **Check Output**: Verify first few files before full run

## Troubleshooting

**No episodes found?**
- Check if anime page structure has changed
- Look at log file for parsing errors
- Try visiting URL manually to verify

**Scraper stops unexpectedly?**
- Check log file for errors
- Use `--resume` to continue
- Check network connection

**Progress not saving?**
- Check write permissions on output directory
- Verify disk space available

**Too slow?**
- Reduce `--delay` (but be respectful!)
- Use `--limit` for testing
- Check your internet speed

## Integration with Previous Scrapers

```bash
# Step 1: Get anime list
python zoroto_scraper.py --mode letters -o zoroto_complete.json

# Step 2: Get episodes for each anime
python anime_episode_scraper.py --input zoroto_complete.json

# Result: Complete database of anime with episode URLs!
```

## Future Enhancements

Potential additions:
- Download actual video pages HTML
- Extract video stream URLs
- Extract subtitle URLs
- Add multi-threading for faster scraping
- Add database storage option
- Add API endpoint for queries

## Safety Features

- Rate limiting to avoid overwhelming servers
- Progress tracking to avoid re-scraping
- Error recovery and logging
- Timeout on stuck requests
- Respectful User-Agent header

## Notes

- Default delay is 1.5 seconds (respectful)
- Progress persists across runs
- Each anime gets unique filename (title + URL hash)
- All data saved in UTF-8 encoding
- Filenames are sanitized for cross-platform compatibility

