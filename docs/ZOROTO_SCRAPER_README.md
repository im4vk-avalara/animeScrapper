# Zoroto Anime Scraper

A Python scraper to extract anime titles and URLs from zoroto.com.in.

## Features

- 🔍 **Multiple Scraping Modes**:
  - `quick` - Fast scraping of first page only
  - `pagination` - Scrape all pagination pages  
  - `letters` - Complete scraping by iterating A-Z, 0-9, and special characters (most thorough)
  
- 📄 **Multiple Output Formats**: JSON and CSV
- 🛡️ **Error Handling**: Robust error handling and retry logic
- ⏱️ **Rate Limiting**: Respectful delays between requests
- 📊 **Progress Logging**: Detailed logging of scraping progress
- 🎯 **Flexible Filtering**: Scrape by specific letter if needed
- 🌐 **Updated HTML Parser**: Works with zoroto.com.in's current structure

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install manually
pip install requests beautifulsoup4
```

## Usage

### Quick Start (First Page Only)
```bash
python zoroto_scraper.py --mode quick
```

### Scrape All Pages (Pagination)
```bash
python zoroto_scraper.py --mode pagination
```

### Complete Scraping (All Letters A-Z + Numbers + Special)
```bash
python zoroto_scraper.py --mode letters
```

### Custom Options
```bash
# Save to CSV format
python zoroto_scraper.py --mode letters --format csv --output anime_complete.csv

# Limit pages per section
python zoroto_scraper.py --mode pagination --max-pages 10

# Increase delay between requests
python zoroto_scraper.py --mode letters --delay 2.0

# Scrape specific letter only
python zoroto_scraper.py --letter A --output anime_a.json

# Scrape numbers
python zoroto_scraper.py --letter 0-9 --output anime_numbers.json
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output filename | `zoroto_anime_list.json` |
| `-f, --format` | Output format (json/csv) | `json` |
| `--mode` | Scraping mode (quick/pagination/letters) | `quick` |
| `--max-pages` | Max pages to scrape per section | `all` |
| `--delay` | Delay between requests (seconds) | `1.0` |
| `--letter` | Scrape specific letter only (A-Z, 0-9, or .) | `None` |

## Output Format

### JSON
```json
[
  {
    "title": "A Condition Called Love",
    "url": "https://zoroto.com.in/anime/a-condition-called-love/"
  },
  {
    "title": "One Piece",
    "url": "https://zoroto.com.in/anime/one-piece/"
  }
]
```

### CSV
```csv
title,url
A Condition Called Love,https://zoroto.com.in/anime/a-condition-called-love/
One Piece,https://zoroto.com.in/anime/one-piece/
```

## Examples

### Example 1: Quick Test
```bash
# Get first page quickly to test
python zoroto_scraper.py --mode quick --output test.json
```

### Example 2: Complete Database
```bash
# Scrape all anime (most thorough, takes longer)
python zoroto_scraper.py --mode letters --output complete_anime_list.json
```

### Example 3: Specific Category
```bash
# Get only anime starting with 'A'
python zoroto_scraper.py --letter A --output anime_starting_with_a.json

# Get anime starting with numbers
python zoroto_scraper.py --letter 0-9 --output anime_numbers.json

# Get anime with special characters
python zoroto_scraper.py --letter . --output anime_special.json
```

### Example 4: Export to CSV
```bash
# Export to CSV for Excel/spreadsheet use
python zoroto_scraper.py --mode pagination --format csv --output anime.csv
```

## How It Works

1. **Fetches HTML** from zoroto.com.in/az-list/
2. **Parses HTML** using BeautifulSoup to find `<article class="bs">` elements
3. **Extracts Data** from nested `<div class="bsx">` and `<a>` tags (title and URL)
4. **Handles Pagination** by detecting max pages from `/page/N/` URLs
5. **Rate Limiting** adds delays between requests to be respectful
6. **Deduplicates** entries when using letters mode
7. **Saves Output** to JSON or CSV format

## HTML Structure

The scraper targets the following structure:
```html
<article class="bs">
  <div class="bsx">
    <a href="https://zoroto.com.in/anime/..." title="Anime Title">
      <h2>Anime Title</h2>
    </a>
  </div>
</article>
```

Pagination structure:
```html
<div class="pagination">
  <span class="current">1</span>
  <a class="page-numbers" href=".../page/2/">2</a>
  <a class="page-numbers" href=".../page/3/">3</a>
  <a class="next page-numbers" href=".../page/2/">Next »</a>
</div>
```

## Key Differences from Gogoanime Scraper

- **Domain**: zoroto.com.in (instead of gogoanimes.ca)
- **URL Pattern**: `/az-list/page/2/` (instead of `?anime_page=2`)
- **HTML Structure**: `<article class="bs">` (instead of `<ul class="listing">`)
- **Letter Filter**: Includes '.' for special characters
- **Pagination**: Embedded in URL path rather than query parameter

## Notes

- The scraper includes a 1-second delay between requests by default (configurable)
- Using `--mode letters` is most thorough but takes longer
- The scraper respects the website by using proper User-Agent headers
- All progress is logged to console for monitoring
- Special characters (., #, etc.) can be scraped using `--letter .`

## Troubleshooting

**No anime found?**
- Check your internet connection
- Verify zoroto.com.in is accessible
- Try increasing `--delay` if getting blocked

**Scraping too slow?**
- Use `--mode quick` for fast testing
- Reduce `--delay` (but be respectful!)
- Use `--max-pages` to limit pages per section

**Want more data?**
- Use `--mode letters` for complete coverage
- Check pagination detection in logs
- Consider scraping during off-peak hours

## Comparison with Previous Scraper

| Feature | anime_scraper.py | zoroto_scraper.py |
|---------|------------------|-------------------|
| Website | gogoanimes.ca | zoroto.com.in |
| HTML Parser | `<ul class="listing">` | `<article class="bs">` |
| Pagination | Query param | URL path |
| Special Chars | No | Yes (.) |
| Status | Legacy | Current |

