# Git Repository Setup Guide

Complete guide to set up your anime scraper as a Git repository with CI/CD.

## Initial Setup

### 1. Initialize Git Repository

```bash
cd /Users/avinash.kumar2/Downloads/GenAI/beverage-alc-genai/animewebsite

# Initialize git
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Anime scraping pipeline"
```

### 2. Create GitHub Repository

**Option A: Using GitHub CLI**
```bash
# Install GitHub CLI: https://cli.github.com/
gh repo create anime-scraper --public --source=. --remote=origin

# Push code
git push -u origin main
```

**Option B: Using GitHub Website**
1. Go to https://github.com/new
2. Create repository named `anime-scraper`
3. Don't initialize with README (we already have one)
4. Copy the remote URL

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/anime-scraper.git

# Push code
git branch -M main
git push -u origin main
```

## GitHub Actions Setup

### Enable GitHub Actions

1. Go to repository → Settings → Actions → General
2. Allow all actions and reusable workflows
3. Save

### Enable GitHub Pages (Optional)

1. Go to Settings → Pages
2. Source: Deploy from a branch
3. Branch: `gh-pages`
4. Save

Your data will be available at:
```
https://YOUR_USERNAME.github.io/anime-scraper/
```

## Running the Pipeline

### Manual Trigger

1. Go to Actions tab
2. Select "Scrape Anime Data" workflow
3. Click "Run workflow"
4. Optional: Set limit for testing
5. Click "Run workflow"

### Automated Runs

Pipeline runs automatically:
- **Daily at 2 AM UTC**
- Updates data automatically
- Deploys to GitHub Pages

## Local Development

### Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/anime-scraper.git
cd anime-scraper
```

### Setup Environment

```bash
# Run setup script
chmod +x setup.sh
./setup.sh

# Or manually:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Pipeline Locally

```bash
# Full pipeline
./run_pipeline.sh full

# Test mode (5 anime only)
./run_pipeline.sh test

# With custom workers
./run_pipeline.sh full 10
```

## Workflow Files

### Main Scraping Pipeline

`.github/workflows/scrape-anime.yml`

Jobs:
1. **scrape-anime-list** - Gets all anime URLs
2. **scrape-episodes** - Gets episode lists
3. **scrape-videos** - Gets video iframe URLs
4. **organize-data** - Formats for website
5. **deploy-to-pages** - Deploys to GitHub Pages

### Testing Pipeline

`.github/workflows/test-scraper.yml`

Runs on every push/PR:
- Tests all scrapers
- Verifies outputs
- Ensures no breaking changes

## Git Workflow

### Feature Development

```bash
# Create feature branch
git checkout -b feature/new-scraper

# Make changes
# ... edit files ...

# Commit
git add .
git commit -m "Add new scraper feature"

# Push
git push origin feature/new-scraper

# Create Pull Request on GitHub
```

### Update Main Branch

```bash
# Switch to main
git checkout main

# Pull latest
git pull origin main

# Merge feature
git merge feature/new-scraper

# Push
git push origin main
```

## Branching Strategy

```
main          - Production-ready code
├── develop   - Development branch
├── feature/* - Feature branches
└── hotfix/*  - Quick fixes
```

### Recommended Workflow

```bash
# Always work on feature branches
git checkout -b feature/my-feature

# Regular commits
git commit -m "Work in progress"

# Push to remote
git push origin feature/my-feature

# Create PR when ready
gh pr create --title "My Feature" --body "Description"
```

## Environment Secrets

### Adding Secrets (if needed)

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add secrets:
   - `DEPLOY_TOKEN` - For external deployment
   - Custom API keys if needed

### Using Secrets in Workflows

```yaml
- name: Deploy
  env:
    DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
  run: |
    ./deploy.sh
```

## CI/CD Best Practices

### 1. Test Before Merge

Always run tests:
```bash
git push  # Triggers test workflow
```

Wait for ✅ before merging.

### 2. Use Artifacts

Download artifacts from Actions:
- Go to Actions → Select run → Artifacts
- Download `website-data` for latest data

### 3. Monitor Workflows

Check workflow status:
- Actions tab shows all runs
- Email notifications on failure
- Add status badges to README

### 4. Caching

GitHub Actions caches:
- Python dependencies
- pip packages
- Reduces workflow time

## Deployment Options

### GitHub Pages (Automatic)

Already configured in workflow. Data available at:
```
https://YOUR_USERNAME.github.io/anime-scraper/
```

### Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod --dir=website_data
```

### Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod website_data
```

### AWS S3

```bash
# Configure AWS CLI
aws configure

# Sync data
aws s3 sync website_data s3://your-bucket/ --acl public-read
```

## Monitoring

### GitHub Actions Status

Add badges to README:
```markdown
[![Scrape Anime Data](https://github.com/USER/anime-scraper/actions/workflows/scrape-anime.yml/badge.svg)](https://github.com/USER/anime-scraper/actions/workflows/scrape-anime.yml)
```

### Check Logs

```bash
# View workflow logs
gh run list
gh run view <run-id>
gh run view <run-id> --log
```

### Statistics

Check `website_data/statistics.json` after each run.

## Troubleshooting

### Workflow Fails

1. Check logs in Actions tab
2. Common issues:
   - Timeout (increase in workflow)
   - Rate limiting (reduce workers)
   - Network errors (retry)

### Can't Push

```bash
# Pull latest first
git pull origin main --rebase

# Then push
git push origin main
```

### Merge Conflicts

```bash
# Resolve conflicts
git mergetool

# Or manually edit files
git add resolved_file.py
git commit -m "Resolve conflicts"
```

## Maintenance

### Update Dependencies

```bash
pip list --outdated
pip install --upgrade package_name
pip freeze > requirements.txt
git commit -am "Update dependencies"
```

### Clean Up

```bash
# Remove old artifacts (manually in GitHub)
# Delete old branches
git branch -d feature/old-feature
git push origin --delete feature/old-feature
```

## Advanced: Self-Hosted Runners

For faster/private scraping:

1. Go to Settings → Actions → Runners
2. Click "New self-hosted runner"
3. Follow instructions
4. Run on your own server

Benefits:
- Faster execution
- No GitHub Actions limits
- More control

## Summary

You now have:
- ✅ Git repository with full history
- ✅ GitHub Actions CI/CD pipeline
- ✅ Automated daily scraping
- ✅ Automated deployment
- ✅ Testing on every push
- ✅ Artifacts for easy download

**Your anime scraper is production-ready!** 🚀

