#!/bin/bash
# Setup script for anime scraper project

set -e

echo "=========================================="
echo "Anime Scraper - Setup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.7 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create directory structure
echo ""
echo "Creating directory structure..."
mkdir -p anime_data/episodes
mkdir -p video_data/videos
mkdir -p website_data
touch anime_data/.gitkeep
touch video_data/.gitkeep
touch website_data/.gitkeep
echo "✓ Directories created"

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x run_pipeline.sh
chmod +x setup.sh
echo "✓ Scripts are executable"

# Test installation
echo ""
echo "Testing installation..."
python -c "import requests; import bs4; print('✓ All imports successful')"

echo ""
echo "=========================================="
echo "Setup Complete! 🎉"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run test: ./run_pipeline.sh test"
echo "  3. Run full: ./run_pipeline.sh full"
echo ""
echo "Or run individual scrapers:"
echo "  python zoroto_scraper.py --mode quick"
echo "  python anime_episode_scraper.py -i zoroto_complete.json --limit 5"
echo "  python video_url_scraper_parallel.py -i anime_data/episodes --limit 5"
echo "  python data_organizer.py"
echo ""

