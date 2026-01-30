# Complete Anime Scraping Pipeline

## Overview

A 3-step pipeline to build a complete anime database with video URLs.

## Pipeline Steps

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Anime List Scraper (zoroto_scraper.py)                │
│  Input:  None                                                   │
│  Output: zoroto_complete.json (~4000 anime with URLs)          │
│  Time:   10-15 minutes                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Episode Scraper (anime_episode_scraper.py)            │
│  Input:  zoroto_complete.json                                  │
│  Output: anime_data/episodes/*.json (4000 files)               │
│  Time:   2-3 hours                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Video URL Scraper (video_url_scraper.py)              │
│  Input:  anime_data/episodes/*.json                            │
│  Output: video_data/videos/*.json (4000 files)                 │
│  Time:   20-40 hours (4-5 days!)                                │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start (Testing)

### Test the Complete Pipeline (5 minutes)
```bash
cd /Users/avinash.kumar2/Downloads/GenAI/beverage-alc-genai/animewebsite

# Step 1: Get anime list (first page)
python zoroto_scraper.py --mode quick --output test_list.json

# Step 2: Get episodes (5 anime)
python anime_episode_scraper.py --input test_list.json --limit 5 --output test_anime

# Step 3: Get video URLs (5 anime)
python video_url_scraper.py --input test_anime/episodes --limit 5 --output test_videos
```

## Production Run

### Complete Pipeline (Several Days)
```bash
# Step 1: Get complete anime list (10-15 min)
python zoroto_scraper.py --mode letters --output zoroto_complete.json

# Step 2: Get all episodes (2-3 hours, resumable)
python anime_episode_scraper.py --input zoroto_complete.json --output anime_data

# Step 3: Get all video URLs (20-40 hours, run in batches)
# Option A: All at once (run overnight for days)
python video_url_scraper.py --input anime_data/episodes --output video_data

# Option B: In batches of 100 (recommended)
python video_url_scraper.py --input anime_data/episodes --limit 100 --output video_data
# Run multiple times, it will auto-resume!
```

## Data Flow

### Step 1 Output (Anime List)
```json
[
  {
    "title": "One Piece",
    "url": "https://zoroto.com.in/anime/one-piece/"
  }
]
```

### Step 2 Output (Episodes)
```json
{
  "title": "One Piece",
  "episodes": [
    {
      "episode_number": "1",
      "url": "https://zoroto.com.in/one-piece-episode-1/"
    }
  ]
}
```

### Step 3 Output (Video URLs)
```json
{
  "anime_title": "One Piece",
  "episodes_with_videos": [
    {
      "episode_number": "1",
      "video_sources": [
        {
          "type": "iframe",
          "url": "https://server.com/embed/video123",
          "quality": "1080p",
          "server": "server1"
        }
      ]
    }
  ]
}
```

## Time Estimates

| Step | Quick Test | Production | Resumable |
|------|------------|------------|-----------|
| **Step 1** | 2 seconds | 10-15 min | No |
| **Step 2** | 10 seconds | 2-3 hours | Yes ✅ |
| **Step 3** | 30 seconds | 20-40 hours | Yes ✅ |
| **Total** | ~1 minute | ~22-43 hours | - |

## Disk Space Requirements

| Step | Output Size |
|------|-------------|
| Step 1 | ~140 KB |
| Step 2 | ~50-200 MB |
| Step 3 | ~100-500 MB |
| **Total** | **~150-700 MB** |

## Resume Capability

| Step | Resumable | Progress File |
|------|-----------|---------------|
| Step 1 | ❌ No | N/A |
| Step 2 | ✅ Yes | `anime_data/progress.json` |
| Step 3 | ✅ Yes | `video_data/progress.json` |

## Recommended Approach

### For Testing (Quick Validation)
```bash
# Test complete pipeline in 5 minutes
python zoroto_scraper.py --mode quick -o test.json
python anime_episode_scraper.py -i test.json --limit 5
python video_url_scraper.py -i anime_data/episodes --limit 5
```

### For Production (Best Practice)

#### Day 1: Steps 1-2 (~3-4 hours)
```bash
# Morning: Get anime list
python zoroto_scraper.py --mode letters -o zoroto_complete.json

# Afternoon: Get all episodes
python anime_episode_scraper.py -i zoroto_complete.json
```

#### Days 2-6: Step 3 (Process in batches)
```bash
# Run daily in batches of 100 anime
# Each batch takes ~2-4 hours
for day in {1..40}; do
  echo "Processing batch $day"
  python video_url_scraper.py -i anime_data/episodes --resume
  # It will auto-resume from where it left off!
done
```

## Monitoring Progress

### Check Completion Status
```bash
# Step 1: Check anime count
cat zoroto_complete.json | grep "title" | wc -l

# Step 2: Check episodes scraped
ls -1 anime_data/episodes/*.json | wc -l

# Step 3: Check video URLs scraped
ls -1 video_data/videos/*.json | wc -l
```

### View Logs
```bash
# Step 2 logs
tail -f anime_episode_scraper.log

# Step 3 logs
tail -f video_url_scraper.log
```

### Check Progress Files
```bash
# Step 2 progress
cat anime_data/progress.json | grep "completed" | wc -l

# Step 3 progress
cat video_data/progress.json | grep "completed" | wc -l
```

## Error Recovery

All steps handle errors gracefully:

1. **Network Issues**: Logged and skipped, can resume
2. **Parsing Errors**: Logged, empty data saved
3. **Timeouts**: Automatic 30s timeout, then skip
4. **Interruptions**: Just re-run with same command

## Batch Processing Script

Create `run_pipeline.sh`:
```bash
#!/bin/bash

echo "=== Step 1: Get Anime List ==="
python zoroto_scraper.py --mode letters -o zoroto_complete.json

echo "=== Step 2: Get Episodes ==="
python anime_episode_scraper.py -i zoroto_complete.json

echo "=== Step 3: Get Video URLs (Batch Mode) ==="
for i in {1..40}; do
  echo "Batch $i/40"
  python video_url_scraper.py -i anime_data/episodes --resume
  if [ $? -eq 0 ]; then
    echo "Batch $i complete"
  else
    echo "Batch $i had errors, check logs"
  fi
  sleep 300  # 5 min break between batches
done

echo "=== Pipeline Complete! ==="
```

## Output Structure

```
animewebsite/
├── zoroto_complete.json              # Step 1 output
├── anime_data/                        # Step 2 output
│   ├── episodes/
│   │   └── *.json (4000 files)
│   ├── progress.json
│   └── anime_episode_scraper.log
└── video_data/                        # Step 3 output
    ├── videos/
    │   └── *.json (4000 files)
    ├── progress.json
    └── video_url_scraper.log
```

## Common Issues

### Issue 1: Step 2 or 3 Interrupted
**Solution**: Just run the same command again with `--resume`
```bash
python anime_episode_scraper.py -i zoroto_complete.json --resume
python video_url_scraper.py -i anime_data/episodes --resume
```

### Issue 2: Running Out of Time
**Solution**: Use `--limit` to process in smaller batches
```bash
python video_url_scraper.py -i anime_data/episodes --limit 100 --resume
```

### Issue 3: Want to Start Over
**Solution**: Use `--no-resume` flag
```bash
python video_url_scraper.py -i anime_data/episodes --no-resume
```

### Issue 4: Too Slow
**Solution**: Reduce delay (but be respectful!)
```bash
python video_url_scraper.py -i anime_data/episodes --delay 1.5
```

## Best Practices

1. ✅ **Always test first** with `--limit 5`
2. ✅ **Use resume** for Steps 2 and 3
3. ✅ **Monitor logs** regularly
4. ✅ **Process Step 3 in batches** (100-200 at a time)
5. ✅ **Run overnight** for large batches
6. ✅ **Keep backups** of completed data
7. ✅ **Check disk space** before starting
8. ✅ **Respect rate limits** (use default delays)

## Performance Tips

- **Step 1**: Fast, no optimization needed
- **Step 2**: Run during off-peak hours
- **Step 3**: 
  - Process in batches
  - Run overnight
  - Consider cloud VM for 24/7 running

## Cloud Deployment (Optional)

For Step 3 (long-running), consider AWS/GCP/Azure:
```bash
# Upload to cloud VM
scp -r animewebsite/ user@vm:/home/user/

# SSH and run
ssh user@vm
cd animewebsite
nohup python video_url_scraper.py -i anime_data/episodes --resume &

# Check progress remotely
tail -f video_url_scraper.log
```

## Final Result

After completing all 3 steps, you'll have:

- ✅ 4000+ anime with metadata
- ✅ 200,000+ episodes with URLs
- ✅ 1,000,000+ video source URLs
- ✅ Quality and server information
- ✅ Complete searchable database

## What's Next?

After completing the pipeline:
1. Build search API
2. Create web interface
3. Add video quality filtering
4. Extract direct download links
5. Add subtitle support
6. Build mobile app
7. Add recommendation system

## Support Files

- `QUICK_START.md` - Quick start guide
- `ZOROTO_SCRAPER_README.md` - Step 1 docs
- `EPISODE_SCRAPER_README.md` - Step 2 docs
- `VIDEO_SCRAPER_README.md` - Step 3 docs
- `PROJECT_SUMMARY.md` - Project overview

---

**Happy Scraping! 🎬📺🍿**

Remember: Be patient, be respectful, and use resume!

