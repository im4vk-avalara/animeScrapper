# Anime Scraping Pipeline

[![Scrape Anime Data](https://github.com/YOUR_USERNAME/anime-scraper/actions/workflows/scrape-anime.yml/badge.svg)](https://github.com/YOUR_USERNAME/anime-scraper/actions/workflows/scrape-anime.yml)
[![Test Scrapers](https://github.com/YOUR_USERNAME/anime-scraper/actions/workflows/test-scraper.yml/badge.svg)](https://github.com/YOUR_USERNAME/anime-scraper/actions/workflows/test-scraper.yml)

Complete pipeline for scraping anime data from zoroto.com.in with video URLs.

## Features

- 🎬 Scrapes 4000+ anime with metadata
- 📺 Extracts 50,000+ episodes with URLs
- 🎥 Finds 100,000+ video iframe sources
- ⚡ Parallel processing for speed
- 🔄 Resume capability
- 📊 Organized website-ready output
- 🤖 Automated GitHub Actions pipeline
- 📦 **TOON format support** - 30-60% token savings for LLM workflows

## Quick Start

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/anime-scraper.git
cd anime-scraper

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run complete pipeline (JSON format)
./run_pipeline.sh

# Or run with TOON format (30-60% smaller files)
./run_pipeline.sh full 10 toon

# Or run steps individually (all parallel):
python zoroto_scraper.py --mode letters
python anime_episode_scraper_parallel.py -i zoroto_complete.json --workers 10
python video_url_scraper_parallel.py -i anime_data/episodes --workers 10
python data_organizer.py
```

### Quick Test

```bash
# Test with 5 anime (JSON) - using parallel scrapers
python zoroto_scraper.py --mode quick -o test.json
python anime_episode_scraper_parallel.py -i test.json --limit 5 --workers 5
python video_url_scraper_parallel.py -i anime_data/episodes --limit 5 --workers 5
python data_organizer.py

# Test with TOON format
python zoroto_scraper.py --mode quick -o test.toon --format toon
python anime_episode_scraper_parallel.py -i test.toon --limit 5 --workers 5 --format toon
python video_url_scraper_parallel.py -i anime_data/episodes --limit 5 --workers 5 --format toon
python data_organizer.py --output-format toon
```

## Pipeline Steps

1. **Anime List** → Scrapes all anime titles and URLs
2. **Episodes** → Extracts episode lists for each anime
3. **Video URLs** → Finds iframe/video sources for each episode
4. **Organize** → Formats data for website consumption

## Project Structure

```
anime-scraper/
├── .github/workflows/        # GitHub Actions CI/CD
│   ├── scrape-anime.yml      # Main scraping pipeline
│   └── test-scraper.yml      # Testing workflow
│
├── scrapers/                 # Scraper scripts
│   ├── zoroto_scraper.py              # Step 1: Scrape anime list
│   ├── anime_episode_scraper_parallel.py  # Step 2: Parallel episode scraper (fast)
│   ├── anime_episode_scraper.py       # Step 2: Sequential episode scraper
│   ├── video_url_scraper_parallel.py  # Step 3: Parallel video URL scraper (fast)
│   ├── video_url_scraper.py           # Step 3: Sequential video URL scraper
│   ├── video_url_extractor.py         # Extract direct URLs from iframes
│   └── data_organizer.py              # Step 4: Organize for website
│
├── docs/                     # Documentation
│   ├── COMPLETE_GUIDE.md
│   ├── FINAL_DATA_STRUCTURE.md
│   └── ...
│
├── output/                   # Generated data (gitignored)
│   ├── anime_data/
│   ├── video_data/
│   └── website_data/
│
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Output Data

### Website-Ready Format

```
website_data/
├── anime_index.json          # Lightweight index
├── search_data.json          # Search-optimized
├── statistics.json           # Dataset stats
└── [individual files]/       # One per anime
```

### Data Schema

**JSON Format:**
```json
{
  "title": "One Piece",
  "total_episodes": 1000,
  "episodes": [
    {
      "episode_number": "1",
      "episode_url": "https://...",
      "video_sources": [
        "https://streamx2.com/embed/..."
      ],
      "has_videos": true
    }
  ]
}
```

**TOON Format (Token-Oriented Object Notation):**
```
title: One Piece
total_episodes: 1000
episodes[1000]{episode_number,episode_url,video_sources,has_videos}:
  1,https://...,https://streamx2.com/embed/...,true
  2,https://...,https://streamx2.com/embed/...,true
```

## TOON Format

TOON (Token-Oriented Object Notation) is a data format optimized for LLM workflows that provides **30-60% token savings** compared to JSON.

### Why TOON?

| Feature | JSON | TOON |
|---------|------|------|
| Token efficiency | Verbose | 30-60% smaller |
| Arrays of objects | Repeated keys | Tabular format |
| Human readable | Moderate | Excellent |
| LLM optimized | No | Yes |

### TOON Benefits for This Project

- **Episode lists**: Uniform arrays of episodes use tabular format
- **Anime index**: Large lists compress significantly  
- **Search data**: Optimized for LLM context windows
- **Cost savings**: Fewer tokens = lower API costs

### Example Comparison

**JSON (847 tokens):**
```json
{
  "anime_list": [
    {"title": "One Piece", "url": "https://..."},
    {"title": "Naruto", "url": "https://..."},
    {"title": "Bleach", "url": "https://..."}
  ]
}
```

**TOON (312 tokens - 63% savings):**
```
anime_list[3]{title,url}:
  One Piece,https://...
  Naruto,https://...
  Bleach,https://...
```

### Using TOON

```bash
# Full pipeline with TOON
./run_pipeline.sh full 10 toon

# Individual scrapers
python zoroto_scraper.py --format toon -o anime.toon
python anime_episode_scraper.py -i anime.toon --format toon
python video_url_scraper_parallel.py -i anime_data/episodes --format toon
python data_organizer.py --output-format toon
```

### Converting Between Formats

```python
import toon
import json

# JSON to TOON
with open('data.json') as f:
    data = json.load(f)
toon_str = toon.encode(data)

# TOON to JSON
with open('data.toon') as f:
    toon_str = f.read()
data = toon.decode(toon_str)
```

## GitHub Actions

### Automated Scraping

The pipeline runs automatically:
- **Schedule**: Daily at 2 AM UTC
- **Manual**: Can trigger manually with custom options

### Manual Trigger

Go to Actions → Scrape Anime Data → Run workflow

Options:
- `limit`: Number of anime to scrape (for testing)
- `workers`: Parallel workers (5-10 recommended)

### Artifacts

After each run, artifacts are available for 30 days:
- `anime-list`: Initial anime list
- `episode-data`: Episode information
- `video-data`: Video URLs
- `website-data`: Final organized data

## Configuration

### Environment Variables

Create `.env` file (optional):
```bash
SCRAPER_DELAY=0.1
PARALLEL_WORKERS=10
OUTPUT_FORMAT=both
```

### GitHub Secrets

No secrets required for basic scraping. Optional:
- `DEPLOY_TOKEN`: For deploying to external hosting

## Usage Examples

### React Component

```jsx
import { useState, useEffect } from 'react';

function AnimePlayer({ animeFile }) {
  const [anime, setAnime] = useState(null);
  
  useEffect(() => {
    fetch(`/data/${animeFile}.json`)
      .then(r => r.json())
      .then(data => setAnime(data));
  }, [animeFile]);

  if (!anime) return <div>Loading...</div>;

  return (
    <div>
      <h2>{anime.title}</h2>
      {anime.episodes.map(ep => (
        <div key={ep.episode_number}>
          Episode {ep.episode_number}
          {ep.video_sources.map(src => (
            <iframe src={src} width="800" height="450" />
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Simple HTML

```html
<script>
  fetch('/data/anime_index.json')
    .then(r => r.json())
    .then(data => {
      data.anime_list.forEach(anime => {
        document.write(`<h3>${anime.title}</h3>`);
      });
    });
</script>
```

## Performance

| Step | Time | Output |
|------|------|--------|
| Anime List | 10-15 min | 4000 anime |
| Episodes | 2-3 hours | 50,000 episodes |
| Video URLs (parallel) | 3-6 hours | 100,000 sources |
| Organize | 2 min | Website data |
| **Total** | **~6-9 hours** | Complete DB |

## Deployment

### GitHub Pages

Automatically deploys to `gh-pages` branch:
```
https://YOUR_USERNAME.github.io/anime-scraper/
```

### Other Platforms

```bash
# Netlify
netlify deploy --prod --dir=website_data

# Vercel
vercel --prod website_data

# AWS S3
aws s3 sync website_data s3://your-bucket/
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## Testing

```bash
# Run all tests
pytest tests/

# Run specific scraper test
python zoroto_scraper.py --mode quick
python anime_episode_scraper.py -i test.json --limit 2

# GitHub Actions tests
git push  # Triggers test workflow
```

## Troubleshooting

### Common Issues

**No data scraped:**
- Check internet connection
- Verify website accessibility
- Review log files

**Scraping too slow:**
- Increase workers: `--workers 10`
- Use parallel version
- Run on faster server

**GitHub Actions timeout:**
- Reduce scope with `limit` parameter
- Split into multiple runs
- Increase worker timeout

## Documentation

- [Complete Guide](COMPLETE_GUIDE.md) - Full pipeline walkthrough
- [Data Structure](FINAL_DATA_STRUCTURE.md) - Output schema
- [Data Organizer](DATA_ORGANIZER_README.md) - Website integration
- [Parallel Scraper](PARALLEL_SCRAPER_README.md) - Fast scraping

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for educational purposes. Please respect website terms of service and robots.txt. Use responsibly with appropriate delays between requests.

## Support

- 📖 Read the [documentation](docs/)
- 🐛 Report [issues](https://github.com/YOUR_USERNAME/anime-scraper/issues)
- 💬 Join [discussions](https://github.com/YOUR_USERNAME/anime-scraper/discussions)

## Statistics

Current dataset:
- Total Anime: 4000+
- Total Episodes: 50,000+
- Total Video Sources: 100,000+
- Last Updated: Auto-updated daily

---

**Built with ❤️ for anime fans**

