## Local testing

pip install -r requirements-fast.txt
python serve.py

## Deployment

git add .
git commit -m "Deployment"
git push origin main




Good question! Sites like anikai.to typically work as aggregators, not hosts:
How Anime Streaming Sites Work
1. Anime Metadata (titles, descriptions, images)
They scrape or sync from:
MyAnimeList (MAL) - largest anime database
AniList - another popular database
Kitsu - anime tracking API
Or maintain their own database built from these sources
2. Video Sources
They don't host videos themselves. Instead they:
Link to third-party video hosting services like:
Megacloud
Vidcloud / VidStreaming
RapidCloud
Filemoon
StreamSB
And many others
The Flow
User clicks "Play Episode 1"    ↓Site calls /ajax/links/list?token=xxx    ↓Returns list of servers (Megacloud, Vidcloud, etc.)    ↓User selects server → loads iframe from that provider    ↓Third-party player streams the video
That's why we saw the API returning "server" options - each server is a different video host. The actual video decryption/streaming happens on those third-party services, which have their own protections.
For your existing scraper (hianime.phtm), it likely uses similar third-party embed sources. Want me to check how your current scraper handles video URLs?
help me do that same, tell me steps

I'll help you build a proper anime aggregator. Here's the plan:
Step 1: Get Anime Metadata (Legal APIs)
Option A: AniList GraphQL API (Free, no key needed)
Anime titles, descriptions, images, genres, episodes
https://anilist.co/graphiql
Option B: Jikan API (Unofficial MAL API, free)
https://api.jikan.moe/v4/
Rate limited but comprehensive
Option C: Kitsu API (Free)
https://kitsu.docs.apiary.io/
Step 2: Get Video Embeds
This is where it gets tricky. Options:
Scrape existing aggregator sites for their embed URLs (what we tried)
Use consumet API - open-source anime API that handles this
Use aniwatch-api - another open-source solution
Step 3: Combine into Your Site
Recommended Approach: Use Consumet API - it's an open-source project that already handles:
Multiple anime sources (Gogoanime, Zoro, etc.)
Episode lists
Video streaming URLs
All the hard scraping work
Want me to:
Set up Consumet API locally and integrate it with your website?
Use AniList API for better metadata + Consumet for videos?
Show you how your current scraper works first for comparison?




How it works:
Get anime info → Returns episode list with IDs
For each episode → Call /watch/:episodeId → Get M3U8 streaming URL
The reality:
Factor	Impact
~13,410 anime	Many API calls for info
Episodes per anime	1 to 1000+ episodes each
Estimated total episodes	Could be 100,000+
API calls needed	13,410 (info) + 100,000+ (watch)
Time	Hours to days
Important limitation:
Video URLs are temporary - They expire after some time (usually hours). So storing them isn't practical for long-term use.
Better approach:
Store only:
Anime metadata (title, image, description)
Episode IDs
Then fetch video URLs on-demand when user clicks play.
Want me to demonstrate fetching all episodes for one anime (like One Piece with 1155 episodes)?
okay few questions, the meta deta will also be fetched on demand or we will have to store those?

Great question! Here's the breakdown:
What to STORE (static/rarely changes):
Data	Why Store
Anime title, image, description	Doesn't change
Genres, type, status	Rarely changes
Episode list (IDs, titles, numbers)	Changes only when new episodes release
Total episode count	Update periodically
What to FETCH ON DEMAND (dynamic/expires):
Data	Why On-Demand
Video streaming URLs (M3U8)	Expire in hours
Subtitle URLs	May expire
Download links	May expire
Recommended Architecture:
┌─────────────────────────────────────────────────────┐│                    YOUR DATABASE                     ││  (JSON files / SQLite / MongoDB)                    ││                                                      ││  • Anime metadata (title, image, description)       ││  • Episode list (ID, title, number)                 ││  • Updated weekly via scraper                       │└─────────────────────────────────────────────────────┘                         │                         ▼┌─────────────────────────────────────────────────────┐│                   USER CLICKS PLAY                   ││                                                      ││  → Call Consumet API: /watch/:episodeId             ││  → Get fresh M3U8 URL                               ││  → Play in video player                             │└─────────────────────────────────────────────────────┘
Benefits:
Fast browsing (metadata already loaded)
Always fresh video URLs
Reduced API calls (only when playing)
Want me to set this up for your website?
great understood. Now how will I call this consumenet API via github actions?

Good question! There are 3 options for using Consumet API in GitHub Actions:
Option 1: Deploy Consumet API (Recommended)
Deploy to a free hosting service, then call it from GitHub Actions.
Service	Free Tier	Setup
Vercel	Yes	vercel deploy
Railway	$5 credit/month	One-click deploy
Render	Yes	Docker deploy
# In your GitHub Action- name: Scrape anime data  run: |    curl "https://your-consumet-api.vercel.app/anime/animekai/tv" > data.json
Option 2: Run API Inside GitHub Actions
Start the Consumet server as part of your workflow:
1
jobs:  scrape:    runs-on: ubuntu-latest    steps:      - uses: actions/checkout@v4            - name: Setup Node.js        uses: actions/setup-node@v4        with:          node-version: '18'            - name: Clone & Start Consumet API        run: |          git clone --depth 1 https://github.com/consumet/api.git consumet-api          cd consumet-api && npm install && npm start &          sleep 10  # Wait for server to start            - name: Run Scraper        run: python scraper.py  # Calls localhost:3000
Option 3: Use Consumet Library Directly (No API needed)
Use the @consumet/extensions npm package directly:
const { ANIME } = require('@consumet/extensions');const animekai = new ANIME.AnimeKai();// Searchconst results = await animekai.search('One Piece');// Get infoconst info = await animekai.fetchAnimeInfo('one-piece-dk6r');// Get streaming URLconst sources = await animekai.fetchEpisodeSources(episodeId);
Which option would you prefer?
Deploy to Vercel (easiest, always available)
Run in GitHub Actions (no external dependency)
Use library directly (most control, no server needed)