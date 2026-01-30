#!/usr/bin/env node
/**
 * InAnime Scraper - Using @consumet/extensions with AnimeKai provider
 * 
 * Usage:
 *   node scraper.js              # Quick scrape (100 anime)
 *   node scraper.js --limit 50   # Custom limit
 *   node scraper.js --full       # Full scrape (all anime)
 */

import { ANIME } from '@consumet/extensions';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

// Configuration
const CONFIG = {
  outputDir: '../scraped_data/current',
  animeDir: '../scraped_data/current/anime',
  indexFile: '../scraped_data/current/anime_index.json',
  defaultLimit: 100,
  concurrency: 5,
  delayMs: 300,
  categories: ['tv', 'movies', 'ova', 'ona', 'specials']
};

// Parse command line arguments
const args = process.argv.slice(2);
const isFullScrape = args.includes('--full');
const limitIndex = args.indexOf('--limit');
const customLimit = limitIndex !== -1 ? parseInt(args[limitIndex + 1]) : null;
const limit = isFullScrape ? null : (customLimit || CONFIG.defaultLimit);

// Initialize AnimeKai provider
const animekai = new ANIME.AnimeKai();

// Utility functions
function sanitizeFilename(title) {
  let safe = title.replace(/[<>:"/\\|?*]/g, '');
  safe = safe.replace(/\s+/g, '_').trim();
  return safe.substring(0, 200);
}

function getHash(str) {
  return crypto.createHash('md5').update(str).digest('hex').substring(0, 8);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function log(message) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${message}`);
}

// Fetch functions
async function fetchAnimeList(category, maxPages = null) {
  const animeList = [];
  let page = 1;
  let hasMore = true;
  
  while (hasMore) {
    try {
      let data;
      switch (category) {
        case 'tv': data = await animekai.fetchTV(page); break;
        case 'movies': data = await animekai.fetchMovie(page); break;
        case 'ova': data = await animekai.fetchOVA(page); break;
        case 'ona': data = await animekai.fetchONA(page); break;
        case 'specials': data = await animekai.fetchSpecial(page); break;
        default: data = await animekai.fetchTV(page);
      }
      
      if (!data.results || data.results.length === 0) {
        hasMore = false;
        break;
      }
      
      animeList.push(...data.results);
      hasMore = data.hasNextPage && (maxPages === null || page < maxPages);
      page++;
      
      await sleep(CONFIG.delayMs);
    } catch (error) {
      log(`Error fetching ${category} page ${page}: ${error.message}`);
      hasMore = false;
    }
  }
  
  return animeList;
}

async function fetchAnimeInfo(animeId) {
  try {
    const info = await animekai.fetchAnimeInfo(animeId);
    return info;
  } catch (error) {
    log(`Error fetching info for ${animeId}: ${error.message}`);
    return null;
  }
}

// Fetch video sources for an episode
async function fetchEpisodeSources(episodeId) {
  try {
    const sources = await animekai.fetchEpisodeSources(episodeId);
    return sources;
  } catch (error) {
    // Silently fail for individual episodes
    return null;
  }
}

// Process anime data into our format
function processAnimeData(basicInfo, detailedInfo) {
  const episodes = (detailedInfo?.episodes || []).map(ep => ({
    episode_number: String(ep.number || ''),
    episode_id: ep.id,
    episode_title: ep.title || `Episode ${ep.number}`,
    has_videos: true
  }));
  
  return {
    title: detailedInfo?.title || basicInfo.title,
    animekai_id: basicInfo.id,
    url: basicInfo.url || detailedInfo?.url,
    alternative_titles: detailedInfo?.japaneseTitle || basicInfo.japaneseTitle || '',
    description: detailedInfo?.description || '',
    cover_image: detailedInfo?.image || basicInfo.image,
    genres: detailedInfo?.genres || [],
    status: detailedInfo?.status || '',
    type: basicInfo.type || detailedInfo?.type || '',
    studio: detailedInfo?.studios?.join(', ') || '',
    duration: detailedInfo?.duration || '',
    season: detailedInfo?.season || '',
    released: detailedInfo?.releaseDate || '',
    producers: detailedInfo?.producers || [],
    rating: detailedInfo?.rating || null,
    total_episodes: detailedInfo?.totalEpisodes || basicInfo.episodes || episodes.length,
    available_episodes: episodes.length,
    sub_episodes: basicInfo.sub || 0,
    dub_episodes: basicInfo.dub || 0,
    episodes: episodes,
    scraped_at: new Date().toISOString()
  };
}

// Save anime to file
function saveAnime(animeData) {
  const filename = `${sanitizeFilename(animeData.title)}_${getHash(animeData.animekai_id)}.json`;
  const filepath = path.join(CONFIG.animeDir, filename);
  
  fs.writeFileSync(filepath, JSON.stringify(animeData, null, 2));
  return filename;
}

// Create index file
function createIndex(animeList) {
  const index = {
    total_anime: animeList.length,
    total_episodes: animeList.reduce((sum, a) => sum + (a.available_episodes || 0), 0),
    last_updated: new Date().toISOString(),
    anime_list: animeList.map(a => ({
      title: a.title,
      animekai_id: a.animekai_id,
      cover_image: a.cover_image,
      status: a.status,
      type: a.type,
      genres: a.genres,
      total_episodes: a.total_episodes,
      available_episodes: a.available_episodes
    }))
  };
  
  fs.writeFileSync(CONFIG.indexFile, JSON.stringify(index, null, 2));
  return index;
}

// Process batch of anime concurrently
async function processBatch(batch) {
  const results = [];
  
  for (const anime of batch) {
    try {
      log(`  Fetching info: ${anime.title}`);
      const info = await fetchAnimeInfo(anime.id);
      const processed = processAnimeData(anime, info);
      saveAnime(processed);
      results.push(processed);
      await sleep(CONFIG.delayMs);
    } catch (error) {
      log(`  Error processing ${anime.title}: ${error.message}`);
    }
  }
  
  return results;
}

// Main scraper function
async function main() {
  log('='.repeat(60));
  log('InAnime Scraper - Using @consumet/extensions');
  log(`Mode: ${isFullScrape ? 'FULL' : `LIMITED (${limit} anime)`}`);
  log('='.repeat(60));
  
  // Create directories
  fs.mkdirSync(CONFIG.animeDir, { recursive: true });
  
  // Step 1: Fetch anime list from all categories
  log('\n[Step 1] Fetching anime list from all categories...');
  const allAnime = new Map();
  
  for (const category of CONFIG.categories) {
    log(`  Category: ${category.toUpperCase()}`);
    const maxPages = isFullScrape ? null : 3; // Limit pages for quick scrape
    const animeList = await fetchAnimeList(category, maxPages);
    
    for (const anime of animeList) {
      if (!allAnime.has(anime.id)) {
        allAnime.set(anime.id, anime);
      }
    }
    
    log(`    Found: ${animeList.length} anime (Total unique: ${allAnime.size})`);
  }
  
  // Apply limit
  let animeToProcess = Array.from(allAnime.values());
  if (limit && animeToProcess.length > limit) {
    animeToProcess = animeToProcess.slice(0, limit);
    log(`\n  Limiting to ${limit} anime`);
  }
  
  log(`\n[Step 2] Processing ${animeToProcess.length} anime...`);
  
  // Step 2: Fetch detailed info for each anime
  const processedAnime = [];
  const batchSize = CONFIG.concurrency;
  
  for (let i = 0; i < animeToProcess.length; i += batchSize) {
    const batch = animeToProcess.slice(i, i + batchSize);
    const progress = Math.min(i + batchSize, animeToProcess.length);
    log(`\n  Progress: ${progress}/${animeToProcess.length}`);
    
    const results = await processBatch(batch);
    processedAnime.push(...results);
  }
  
  // Step 3: Create index
  log('\n[Step 3] Creating index...');
  const index = createIndex(processedAnime);
  
  // Summary
  log('\n' + '='.repeat(60));
  log('SCRAPING COMPLETE');
  log('='.repeat(60));
  log(`Total anime scraped: ${processedAnime.length}`);
  log(`Total episodes: ${index.total_episodes}`);
  log(`Output directory: ${CONFIG.animeDir}`);
  log(`Index file: ${CONFIG.indexFile}`);
}

// Run
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
