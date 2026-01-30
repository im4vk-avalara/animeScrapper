# Anime Scraper Comparison

This document compares the two anime scrapers in this project.

## Overview

| Feature | anime_scraper.py | zoroto_scraper.py |
|---------|------------------|-------------------|
| **Website** | gogoanimes.ca | zoroto.com.in |
| **Base URL** | `/anime-list/` | `/az-list/` |
| **Status** | Legacy | **Current** ✅ |
| **Default Output** | `gogoanime_list.json` | `zoroto_anime_list.json` |

## HTML Structure Differences

### anime_scraper.py (Gogoanime)
```html
<ul class="listing">
  <li>
    <a href="..." title="Anime Title">
      Anime Title
    </a>
  </li>
</ul>
```

### zoroto_scraper.py (Zoroto) ✅
```html
<article class="bs">
  <div class="bsx">
    <a href="..." title="..." itemprop="url">
      <h2 itemprop="headline">Anime Title</h2>
    </a>
  </div>
</article>
```

## Pagination Differences

### anime_scraper.py (Gogoanime)
- **URL Pattern**: `?anime_page=2`
- **Query Parameter**: Yes
- **Example**: `https://gogoanimes.ca/anime-list/?anime_page=2`
- **Detection**: `data-page` attribute

### zoroto_scraper.py (Zoroto) ✅
- **URL Pattern**: `/page/2/`
- **Query Parameter**: No (path-based)
- **Example**: `https://zoroto.com.in/az-list/page/2/`
- **Detection**: Parses from `href` URL

## Letter Filtering

### anime_scraper.py (Gogoanime)
```python
# Letters: A-Z, 0-9
letters = ['0-9'] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]
```

### zoroto_scraper.py (Zoroto) ✅
```python
# Letters: '.', 0-9, A-Z (includes special characters)
letters = ['.', '0-9'] + [chr(i) for i in range(ord('A'), ord('Z') + 1)]
```

## Usage Examples

### Quick Test
```bash
# Gogoanime
python anime_scraper.py --mode quick

# Zoroto ✅
python zoroto_scraper.py --mode quick
```

### Complete Scraping
```bash
# Gogoanime (all letters A-Z + numbers)
python anime_scraper.py --mode letters --output gogoanime_complete.json

# Zoroto ✅ (includes special chars)
python zoroto_scraper.py --mode letters --output zoroto_complete.json
```

### Specific Letter
```bash
# Gogoanime
python anime_scraper.py --letter A

# Zoroto ✅
python zoroto_scraper.py --letter A
```

## Which One to Use?

### Use `zoroto_scraper.py` ✅ if:
- You want to scrape current anime from zoroto.com.in
- You need the latest anime list
- The website structure matches the new home.html format
- You want special character filtering (.)

### Use `anime_scraper.py` if:
- You specifically need data from gogoanimes.ca
- You're working with legacy data
- The gogoanimes.ca structure hasn't changed

## Feature Parity

Both scrapers support:
- ✅ Multiple modes (quick, pagination, letters)
- ✅ JSON and CSV output
- ✅ Rate limiting and delays
- ✅ Error handling
- ✅ Progress logging
- ✅ Letter-based filtering
- ✅ Pagination handling
- ✅ Deduplication

## Migration Guide

If you're switching from `anime_scraper.py` to `zoroto_scraper.py`:

1. **Change the script name**:
   ```bash
   # Old
   python anime_scraper.py --mode letters
   
   # New ✅
   python zoroto_scraper.py --mode letters
   ```

2. **Update output filenames** (optional):
   ```bash
   python zoroto_scraper.py --mode letters -o zoroto_anime.json
   ```

3. **API is identical** - all command-line arguments work the same way!

## Performance Comparison

Both scrapers have similar performance:
- **Quick mode**: ~1-2 seconds
- **Pagination mode**: ~30-60 seconds (depends on pages)
- **Letters mode**: ~10-15 minutes (complete scrape)
- **Delay**: 1 second default (configurable)

## Recommendations

For **new projects**: Use `zoroto_scraper.py` ✅

For **existing projects**: 
- Check if your data source is still accessible
- Test both scrapers to see which provides better data
- Consider migrating to zoroto_scraper.py for future-proofing

## Sample Output Comparison

Both produce identical JSON structure:
```json
[
  {
    "title": "Anime Title",
    "url": "https://website.com/anime/anime-title/"
  }
]
```

Only the domain differs in the URLs.

