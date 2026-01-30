#!/bin/bash
# Complete Anime Scraping Pipeline
# Usage: ./run_pipeline.sh [test|full] [workers] [json|toon]

set -e  # Exit on error

MODE=${1:-full}
WORKERS=${2:-10}
FORMAT=${3:-json}

echo "=========================================="
echo "Anime Scraping Pipeline"
echo "=========================================="
echo "Mode: $MODE"
echo "Workers: $WORKERS"
echo "Format: $FORMAT"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_step() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Python installation
if ! command -v python &> /dev/null; then
    log_error "Python not found. Please install Python 3.7+"
    exit 1
fi

# Check dependencies
log_step "Checking dependencies..."
if ! python -c "import requests" 2>/dev/null; then
    log_error "Dependencies not installed. Run: pip install -r requirements.txt"
    exit 1
fi
log_success "Dependencies OK"

# Determine file extension
if [ "$FORMAT" = "toon" ]; then
    EXT="toon"
else
    EXT="json"
fi

# Step 1: Scrape anime list
log_step "Step 1/4: Scraping anime list..."
if [ "$MODE" = "test" ]; then
    python zoroto_scraper.py --mode quick --output zoroto_complete.$EXT --format $FORMAT
else
    python zoroto_scraper.py --mode letters --output zoroto_complete.$EXT --format $FORMAT
fi
log_success "Anime list scraped"

# Check output
if [ "$FORMAT" = "toon" ]; then
    ANIME_COUNT=$(grep -c "title:" zoroto_complete.$EXT 2>/dev/null || echo "0")
else
    ANIME_COUNT=$(cat zoroto_complete.$EXT | grep -o "\"title\"" | wc -l)
fi
echo "   Found: $ANIME_COUNT anime"

# Step 2: Scrape episodes (parallel)
log_step "Step 2/4: Scraping episodes (parallel with $WORKERS workers)..."
if [ "$MODE" = "test" ]; then
    python anime_episode_scraper_parallel.py -i zoroto_complete.$EXT --limit 5 --workers $WORKERS --format $FORMAT
else
    python anime_episode_scraper_parallel.py -i zoroto_complete.$EXT --resume --workers $WORKERS --format $FORMAT
fi
log_success "Episodes scraped"

# Check output
EPISODE_FILES=$(find anime_data/episodes -name "*.$EXT" 2>/dev/null | wc -l)
echo "   Files: $EPISODE_FILES anime processed"

# Step 3: Scrape video URLs
log_step "Step 3/4: Scraping video URLs (parallel with $WORKERS workers)..."
if [ "$MODE" = "test" ]; then
    python video_url_scraper_parallel.py -i anime_data/episodes --limit 5 --workers $WORKERS --format $FORMAT
else
    python video_url_scraper_parallel.py -i anime_data/episodes --workers $WORKERS --resume --format $FORMAT
fi
log_success "Video URLs scraped"

# Check output
VIDEO_FILES=$(find video_data/videos -name "*.$EXT" 2>/dev/null | wc -l)
echo "   Files: $VIDEO_FILES anime with videos"

# Step 4: Organize data
log_step "Step 4/4: Organizing data for website..."
python data_organizer.py -i video_data/videos -o website_data --format both --output-format $FORMAT
log_success "Data organized"

# Show statistics
echo ""
echo "=========================================="
echo "Pipeline Complete! 🎉"
echo "=========================================="
echo ""

if [ -f website_data/statistics.$EXT ]; then
    log_step "Statistics:"
    if [ "$FORMAT" = "toon" ]; then
        cat website_data/statistics.$EXT
    else
        cat website_data/statistics.$EXT | python -m json.tool
    fi
    echo ""
fi

echo "Output directory: website_data/"
echo ""
echo "Next steps:"
echo "  1. Check data: ls -lh website_data/"
echo "  2. Test locally: cd website_data && python -m http.server 8000"
echo "  3. Deploy: Copy website_data/ to your hosting"
echo ""
echo "Done! ✨"

