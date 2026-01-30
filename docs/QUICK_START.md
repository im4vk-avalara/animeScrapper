# Quick Start Guide - Complete Anime Scraping Pipeline

This guide walks you through the complete process of scraping anime data from zoroto.com.in.

## Overview

The pipeline consists of 2 main steps:
1. **Get Anime List** - Scrape all anime titles and URLs
2. **Get Episodes** - For each anime, scrape episode URLs

## Prerequisites

```bash
cd /Users/avinash.kumar2/Downloads/GenAI/beverage-alc-genai/animewebsite
pip install -r requirements.txt
```

## Step 1: Get Anime List

### Option A: Quick Test (Recommended First)
```bash
# Get first page only (~50 anime)
python zoroto_scraper.py --mode quick
```

### Option B: Complete List (Takes 10-15 minutes)
```bash
# Get all anime A-Z + numbers + special
python zoroto_scraper.py --mode letters --output zoroto_complete.json
```

**Output**: `zoroto_complete.json` with ~4000+ anime

## Step 2: Get Episodes for Each Anime

### Option A: Test with 5 Anime (Recommended First!)
```bash
# Test with just 5 anime to see the output
python anime_episode_scraper.py \
  --input zoroto_complete.json \
  --limit 5 \
  --output test_anime_data
```

Check the output in `test_anime_data/episodes/` - you should see JSON files for each anime with episode URLs!

### Option B: Get All Episodes (Takes 2-3 hours for 4000 anime)
```bash
# Scrape all anime episodes
python anime_episode_scraper.py \
  --input zoroto_complete.json \
  --output anime_data
```

**Output**: `anime_data/` folder with:
- `episodes/` - JSON files for each anime
- `progress.json` - Resume tracking
- `anime_episode_scraper.log` - Detailed logs

## Resume After Interruption

If the scraper gets interrupted (network issue, etc.), simply run the same command again:

```bash
# Automatically resumes from last completed anime
python anime_episode_scraper.py --input zoroto_complete.json
```

The scraper tracks progress and skips already-completed anime!

## Check Progress

```bash
# View the log file
tail -f anime_episode_scraper.log

# Count completed anime
cat anime_data/episodes/*.json | grep "title" | wc -l
```

## Example Output

After running the complete pipeline, you'll have:

```
animewebsite/
├── zoroto_complete.json          # 4000+ anime with URLs
└── anime_data/
    ├── episodes/
    │   ├── One_Piece_a1b2c3d4.json     # 1000+ episodes
    │   ├── Naruto_e5f6g7h8.json        # 220 episodes
    │   ├── Attack_on_Titan_f9g0h1i2.json
    │   └── ... (4000+ files)
    ├── progress.json                    # Resume tracking
    └── anime_episode_scraper.log        # Detailed logs
```

Each episode JSON looks like:
```json
{
  "title": "One Piece",
  "url": "https://zoroto.com.in/anime/one-piece/",
  "metadata": {
    "title": "One Piece",
    "description": "...",
    "genres": ["Action", "Adventure"],
    "rating": "8.72"
  },
  "episodes": [
    {
      "episode_number": "Episode 1",
      "episode_title": "I'm Luffy!",
      "url": "https://zoroto.com.in/one-piece-episode-1/"
    }
  ],
  "episode_count": 1000
}
```

## Recommended Workflow

### For Testing (5 minutes):
```bash
# 1. Get first page of anime list
python zoroto_scraper.py --mode quick --output test_list.json

# 2. Get episodes for first 5 anime
python anime_episode_scraper.py --input test_list.json --limit 5
```

### For Production (3-4 hours):
```bash
# 1. Get complete anime list (10-15 min)
python zoroto_scraper.py --mode letters --output zoroto_complete.json

# 2. Get all episodes (2-3 hours, can resume)
python anime_episode_scraper.py --input zoroto_complete.json

# If interrupted, just run again - it will resume!
```

## Tips & Best Practices

1. **Always test first**: Use `--limit 5` before running full scrape
2. **Monitor progress**: Keep an eye on the log file
3. **Be patient**: Scraping 4000+ anime takes time
4. **Resume is your friend**: Don't worry about interruptions
5. **Respect the server**: Don't reduce delay below 1 second

## Common Commands

```bash
# Quick test
python anime_episode_scraper.py --input zoroto_complete.json --limit 5

# Full scrape with custom delay
python anime_episode_scraper.py --input zoroto_complete.json --delay 2.0

# Fresh start (ignore previous progress)
python anime_episode_scraper.py --input zoroto_complete.json --no-resume

# Check how many completed
ls -1 anime_data/episodes/*.json | wc -l
```

## What's Next?

After scraping, you can:
- Query the JSON files to find anime
- Build a search interface
- Extract video stream URLs
- Create a local anime database
- Build a web UI to browse the data

## Troubleshooting

**Problem**: No episodes found
- **Solution**: Check log file, website structure may have changed

**Problem**: Scraper seems stuck
- **Solution**: Check log file for errors, press Ctrl+C and resume

**Problem**: Running out of disk space
- **Solution**: Use `--limit` to scrape in batches

**Problem**: Getting blocked
- **Solution**: Increase `--delay` to 2-3 seconds

## File Sizes

Expected disk usage:
- `zoroto_complete.json`: ~140KB
- Each episode JSON: ~5-50KB (depends on episode count)
- Total for 4000 anime: ~50-200MB

## Time Estimates

| Task | Time |
|------|------|
| Get anime list (quick) | 2 seconds |
| Get anime list (complete) | 10-15 minutes |
| Get episodes (5 anime) | 10 seconds |
| Get episodes (100 anime) | 3-5 minutes |
| Get episodes (4000 anime) | 2-3 hours |

## Support

Check these files for more details:
- `ZOROTO_SCRAPER_README.md` - Anime list scraper docs
- `EPISODE_SCRAPER_README.md` - Episode scraper docs
- `SCRAPER_COMPARISON.md` - Comparison with gogoanime scraper

