# Quick Git Setup (5 Minutes)

Get your anime scraper on GitHub with automated CI/CD.

## Step 1: Initialize Git (1 min)

```bash
cd /Users/avinash.kumar2/Downloads/GenAI/beverage-alc-genai/animewebsite

# Initialize repository
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: Complete anime scraping pipeline"
```

## Step 2: Create GitHub Repository (2 min)

### Option A: GitHub CLI (Easiest)

```bash
# Install: brew install gh (Mac) or https://cli.github.com/
gh auth login
gh repo create anime-scraper --public --source=. --remote=origin
git push -u origin main
```

### Option B: Manual

1. Go to https://github.com/new
2. Repository name: `anime-scraper`
3. Public/Private: Choose
4. DON'T initialize with README
5. Create repository
6. Copy the commands shown, or:

```bash
git remote add origin https://github.com/YOUR_USERNAME/anime-scraper.git
git branch -M main
git push -u origin main
```

## Step 3: Verify Setup (30 seconds)

Visit your repository:
```
https://github.com/YOUR_USERNAME/anime-scraper
```

You should see:
- ✅ README.md with project info
- ✅ All scraper scripts
- ✅ .github/workflows/ directory
- ✅ GitHub Actions tab

## Step 4: Test GitHub Actions (2 min)

1. Go to **Actions** tab
2. You'll see two workflows:
   - "Scrape Anime Data"
   - "Test Scrapers"

3. Click "Test Scrapers"
4. Click "Run workflow" → "Run workflow"
5. Wait ~2-3 minutes
6. Should show ✅ green checkmark

## Step 5: Run Full Scraping (Optional)

1. Go to Actions → "Scrape Anime Data"
2. Click "Run workflow"
3. Set options:
   - `limit`: 5 (for testing)
   - `workers`: 5
4. Click "Run workflow"
5. Watch it run!

After ~10 minutes:
- Go to run details
- Download "website-data" artifact
- You have website-ready data!

## Local Testing

```bash
# Setup environment
./setup.sh

# Run test (5 anime)
./run_pipeline.sh test

# Run full pipeline
./run_pipeline.sh full 10
```

## What You Get

### Automated Features ✨

1. **Daily Updates** (2 AM UTC)
   - Automatically scrapes new anime
   - Updates video URLs
   - Regenerates website data

2. **Manual Triggers**
   - Run anytime from Actions tab
   - Set custom parameters
   - Download artifacts

3. **Testing**
   - Auto-tests on every push
   - Ensures scrapers work
   - Prevents broken code

4. **GitHub Pages** (Optional)
   - Auto-deploys to gh-pages
   - Data available at:
   ```
   https://YOUR_USERNAME.github.io/anime-scraper/
   ```

### File Structure

```
anime-scraper/
├── .github/workflows/
│   ├── scrape-anime.yml        ← Main pipeline
│   └── test-scraper.yml        ← Testing
├── *.py                        ← Scraper scripts
├── *.md                        ← Documentation
├── run_pipeline.sh             ← Run locally
├── setup.sh                    ← Setup script
├── requirements.txt            ← Dependencies
└── .gitignore                  ← Git ignore
```

## Enable GitHub Pages

1. Settings → Pages
2. Source: `gh-pages` branch
3. Save
4. Wait 2-3 minutes
5. Visit: `https://YOUR_USERNAME.github.io/anime-scraper/`

## Useful Commands

```bash
# Check status
git status

# See changes
git diff

# Commit changes
git add .
git commit -m "Update scrapers"
git push

# Pull latest
git pull

# View logs
git log --oneline

# Create branch
git checkout -b feature/new-feature
```

## Troubleshooting

**Can't push?**
```bash
git pull --rebase
git push
```

**Actions failing?**
- Check Actions tab for logs
- Common: timeout, rate limit
- Solution: Reduce limit or workers

**No gh command?**
```bash
# Mac
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
```

## Next Steps

1. ✅ **Local Test**: `./run_pipeline.sh test`
2. ✅ **GitHub Test**: Trigger test workflow
3. ✅ **Full Run**: Trigger scrape workflow with limit=10
4. ✅ **Build Website**: Use website_data/ artifacts
5. ✅ **Auto-update**: Enable scheduled runs

## Summary

You now have:
- ✅ Git repository
- ✅ GitHub hosted
- ✅ Automated CI/CD
- ✅ Daily updates
- ✅ Easy deployment
- ✅ Version control

**Total setup time: 5 minutes** ⏱️

**Your anime scraper is production-ready!** 🚀

---

**Need help?** Check [GIT_SETUP.md](GIT_SETUP.md) for detailed guide.

