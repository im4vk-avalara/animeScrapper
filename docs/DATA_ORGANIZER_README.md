# Anime Data Organizer

Organizes all scraped anime data into clean, website-ready formats.

## What It Does

Combines data from all scraping steps into unified, easy-to-consume formats:
- ✅ Clean JSON structure
- ✅ Searchable index
- ✅ Combined or separate files
- ✅ Statistics and metadata
- ✅ Ready for website/API use

## Usage

```bash
# Organize all data (default: creates both separate and combined files)
python data_organizer.py

# Custom input/output directories
python data_organizer.py --input video_data/videos --output website_data

# Only combined file
python data_organizer.py --format combined

# Only separate files
python data_organizer.py --format separate
```

## Output Structure

```
website_data/
├── Individual anime files (if format=separate or both)
│   ├── One_Piece_a1b2c3d4.json
│   ├── Naruto_e5f6g7h8.json
│   └── ... (1000+ files)
│
├── all_anime.json              # All anime in one file (if format=combined or both)
├── anime_index.json            # Searchable index
├── search_data.json            # Optimized for search
└── statistics.json             # Dataset statistics
```

## Output Formats

### 1. Individual Anime File

**File**: `One_Piece_a1b2c3d4.json`

```json
{
  "title": "One Piece",
  "total_episodes": 1000,
  "available_episodes": 1000,
  "episodes": [
    {
      "episode_number": "1",
      "episode_url": "https://zoroto.com.in/one-piece-episode-1/",
      "video_sources": [
        "https://streamx2.com/embed/video123",
        "https://server2.com/embed/video456"
      ],
      "has_videos": true
    },
    {
      "episode_number": "2",
      "episode_url": "https://zoroto.com.in/one-piece-episode-2/",
      "video_sources": [
        "https://streamx2.com/embed/video789"
      ],
      "has_videos": true
    }
  ]
}
```

### 2. Combined File

**File**: `all_anime.json`

Contains array of all anime:
```json
[
  {
    "title": "One Piece",
    "total_episodes": 1000,
    "available_episodes": 1000,
    "episodes": [...]
  },
  {
    "title": "Naruto",
    "total_episodes": 220,
    "available_episodes": 220,
    "episodes": [...]
  }
]
```

### 3. Anime Index

**File**: `anime_index.json`

Lightweight index for listing:
```json
{
  "total_anime": 1000,
  "total_episodes": 50000,
  "anime_list": [
    {
      "title": "One Piece",
      "total_episodes": 1000,
      "available_episodes": 1000
    },
    {
      "title": "Naruto",
      "total_episodes": 220,
      "available_episodes": 220
    }
  ]
}
```

### 4. Search Data

**File**: `search_data.json`

Optimized for search functionality:
```json
[
  {
    "title": "One Piece",
    "title_lower": "one piece",
    "total_episodes": 1000,
    "available_episodes": 1000
  }
]
```

### 5. Statistics

**File**: `statistics.json`

Dataset statistics:
```json
{
  "total_anime": 1000,
  "total_episodes": 50000,
  "available_episodes": 48000,
  "total_video_sources": 100000,
  "avg_episodes_per_anime": 50.0,
  "avg_sources_per_episode": 2.0,
  "anime_with_most_episodes": {
    "title": "One Piece",
    "episodes": 1000
  }
}
```

## Website Integration Examples

### Example 1: List All Anime (React)

```javascript
// Fetch anime index
fetch('/data/anime_index.json')
  .then(res => res.json())
  .then(data => {
    const animeList = data.anime_list;
    animeList.forEach(anime => {
      console.log(`${anime.title} - ${anime.total_episodes} episodes`);
    });
  });
```

### Example 2: Show Anime Details

```javascript
// Fetch specific anime
fetch('/data/One_Piece_a1b2c3d4.json')
  .then(res => res.json())
  .then(anime => {
    console.log(`Title: ${anime.title}`);
    console.log(`Episodes: ${anime.total_episodes}`);
    
    anime.episodes.forEach(ep => {
      console.log(`Episode ${ep.episode_number}: ${ep.video_sources.length} sources`);
    });
  });
```

### Example 3: Search Functionality

```javascript
// Load search data
fetch('/data/search_data.json')
  .then(res => res.json())
  .then(searchData => {
    const query = 'naruto';
    const results = searchData.filter(anime => 
      anime.title_lower.includes(query.toLowerCase())
    );
    console.log('Search results:', results);
  });
```

### Example 4: Video Player

```javascript
// Load anime and play episode
fetch('/data/Naruto_e5f6g7h8.json')
  .then(res => res.json())
  .then(anime => {
    const episode = anime.episodes[0]; // First episode
    const videoSources = episode.video_sources;
    
    // Create video player with sources
    videoSources.forEach(src => {
      const iframe = document.createElement('iframe');
      iframe.src = src;
      document.body.appendChild(iframe);
    });
  });
```

### Example 5: Statistics Dashboard

```javascript
// Show statistics
fetch('/data/statistics.json')
  .then(res => res.json())
  .then(stats => {
    console.log(`Total Anime: ${stats.total_anime}`);
    console.log(`Total Episodes: ${stats.total_episodes}`);
    console.log(`Total Videos: ${stats.total_video_sources}`);
    console.log(`Most Episodes: ${stats.anime_with_most_episodes.title}`);
  });
```

## API Usage

### Express.js API Example

```javascript
const express = require('express');
const fs = require('fs');
const app = express();

// Serve static data files
app.use('/data', express.static('website_data'));

// Get all anime list
app.get('/api/anime', (req, res) => {
  const index = JSON.parse(fs.readFileSync('website_data/anime_index.json'));
  res.json(index.anime_list);
});

// Get specific anime
app.get('/api/anime/:filename', (req, res) => {
  const file = `website_data/${req.params.filename}.json`;
  if (fs.existsSync(file)) {
    const anime = JSON.parse(fs.readFileSync(file));
    res.json(anime);
  } else {
    res.status(404).json({ error: 'Anime not found' });
  }
});

// Search anime
app.get('/api/search', (req, res) => {
  const query = req.query.q.toLowerCase();
  const searchData = JSON.parse(fs.readFileSync('website_data/search_data.json'));
  const results = searchData.filter(a => a.title_lower.includes(query));
  res.json(results);
});

app.listen(3000, () => console.log('API running on port 3000'));
```

### Python Flask API Example

```python
from flask import Flask, jsonify, request
import json
from pathlib import Path

app = Flask(__name__)
data_dir = Path('website_data')

@app.route('/api/anime')
def get_anime_list():
    with open(data_dir / 'anime_index.json') as f:
        index = json.load(f)
    return jsonify(index['anime_list'])

@app.route('/api/anime/<filename>')
def get_anime(filename):
    file_path = data_dir / f'{filename}.json'
    if file_path.exists():
        with open(file_path) as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/search')
def search_anime():
    query = request.args.get('q', '').lower()
    with open(data_dir / 'search_data.json') as f:
        search_data = json.load(f)
    results = [a for a in search_data if query in a['title_lower']]
    return jsonify(results)

if __name__ == '__main__':
    app.run(port=3000)
```

## Format Options

### Separate Files (format=separate)
- **Pros**: 
  - Fast individual anime loading
  - Small file sizes
  - Easy to cache
- **Cons**: 
  - Many files to manage
  - No single source

**Use when**: Building dynamic website with lazy loading

### Combined File (format=combined)
- **Pros**: 
  - Single file to manage
  - Easy to distribute
  - Simple deployment
- **Cons**: 
  - Large file size (~50-200MB)
  - Slow initial load
  - High memory usage

**Use when**: Building static site or need offline access

### Both (format=both - Default)
- **Pros**: 
  - Flexibility
  - Best of both worlds
- **Cons**: 
  - Uses more disk space

**Use when**: Not sure which format you'll need

## Performance Considerations

### File Sizes

| Format | Size per File | Total Size |
|--------|---------------|------------|
| Individual | 5-50KB | ~20-200MB |
| Combined | 50-200MB | 50-200MB |
| Index | ~50-500KB | ~500KB |
| Search | ~50-500KB | ~500KB |
| Stats | ~5KB | ~5KB |

### Loading Strategy

**For Large Datasets (1000+ anime):**
1. Load `anime_index.json` first (fast)
2. Load individual anime files on demand
3. Use `search_data.json` for search
4. Cache loaded files in browser

**For Small Datasets (<100 anime):**
1. Can load `all_anime.json` directly
2. Simple and fast enough

## Deployment

### Static Website (Netlify, Vercel, GitHub Pages)

```bash
# 1. Organize data
python data_organizer.py --format separate

# 2. Copy to public folder
cp -r website_data public/data/

# 3. Deploy
# Your website can now fetch from /data/*.json
```

### Dynamic Website (Node.js, Python)

```bash
# 1. Organize data
python data_organizer.py --format both

# 2. Place in server directory
mv website_data server/public/data/

# 3. Serve via API or static files
```

### CDN Deployment

```bash
# 1. Organize data
python data_organizer.py --format separate

# 2. Upload to S3/Cloud Storage
aws s3 sync website_data s3://your-bucket/anime-data/

# 3. Access via CDN URL
# https://cdn.example.com/anime-data/anime_index.json
```

## Best Practices

1. **Use separate format** for production websites
2. **Cache aggressively** - data doesn't change often
3. **Lazy load** individual anime files as needed
4. **Use index** for listings and navigation
5. **Use search data** for search functionality
6. **Compress** JSON files with gzip
7. **Add ETags** for cache validation
8. **Use CDN** for faster global access

## Caching Strategy

```javascript
// Example: Cache with service worker
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/data/')) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request).then((fetchResponse) => {
          return caches.open('anime-data').then((cache) => {
            cache.put(event.request, fetchResponse.clone());
            return fetchResponse;
          });
        });
      })
    );
  }
});
```

## Quick Start

```bash
# 1. Organize your data
python data_organizer.py

# 2. Check the output
ls -lh website_data/
cat website_data/statistics.json

# 3. Test with simple web server
cd website_data
python -m http.server 8000

# 4. Access in browser
# http://localhost:8000/anime_index.json
```

## File Size Optimization

### Enable Gzip

```bash
# Compress all JSON files
find website_data -name "*.json" -exec gzip -k {} \;

# Serve .json.gz files with proper headers
# Content-Encoding: gzip
```

### Minify JSON (optional)

```bash
# Remove formatting to save space
python -c "
import json
from pathlib import Path

for f in Path('website_data').glob('*.json'):
    data = json.loads(f.read_text())
    f.write_text(json.dumps(data, ensure_ascii=False))
"
```

## Summary

The organized data is:
- ✅ Clean and structured
- ✅ Ready for website use
- ✅ Multiple format options
- ✅ Searchable and indexable
- ✅ API-friendly
- ✅ Performance optimized

**Next steps**: Build your website/API using the organized data!

