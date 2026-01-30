// Configuration - Path to scraped data
// Works both locally (serve.py) and on GitHub Pages
const DATA_PATH = './scraped_data/current';

console.log('App.js loaded, DATA_PATH:', DATA_PATH);

// State
let animeIndex = [];
let animeCache = {};
let currentAnime = null;
let currentEpisodeIndex = 0;
let currentPage = 1;
let currentEpisodePage = 1;
let currentHeroIndex = 0;
let heroInterval = null;
const ITEMS_PER_PAGE = 24;
const EPISODES_PER_PAGE = 50;
const HERO_COUNT = 5; // Number of featured anime in hero
const ROW_COUNT = 15; // Number of anime per row

// DOM Elements
const searchInput = document.getElementById('searchInput');

// Initialize
document.addEventListener('DOMContentLoaded', init);

async function init() {
    console.log('Initializing app...');
    setupEventListeners();
    setupBrowserNavigation();
    await loadAnimeIndex();
    console.log('Index loaded, rendering home with', animeIndex.length, 'anime');
    renderHome();
}

// Handle browser back/forward buttons
function setupBrowserNavigation() {
    window.addEventListener('popstate', (event) => {
        // Stop any playing video when navigating with browser buttons
        stopVideo();
        
        if (event.state) {
            if (event.state.page === 'anime' && event.state.title) {
                showAnime(encodeURIComponent(event.state.title));
            } else if (event.state.page === 'player') {
                // Don't auto-play when going back to player
                showPage('animePage');
            } else {
                showPage('homePage');
            }
        } else {
            showPage('homePage');
        }
    });
    
    // Set initial state
    history.replaceState({ page: 'home' }, '', '');
}

// Load anime index
async function loadAnimeIndex() {
    try {
        const heroSection = document.getElementById('heroSection');
        heroSection.innerHTML = '<div class="loading" data-text="Loading anime..."></div>';
        
        console.log('Fetching from:', `${DATA_PATH}/anime_index.json`);
        const response = await fetch(`${DATA_PATH}/anime_index.json`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Loaded data:', data);
        
        animeIndex = data.anime_list || [];
        console.log('Anime count:', animeIndex.length);
        
    } catch (error) {
        console.error('Error loading anime index:', error);
        const heroSection = document.getElementById('heroSection');
        heroSection.innerHTML = `<div class="no-results" style="padding: 4rem;">
            Failed to load anime data.<br>
            <small style="color: #666;">Error: ${error.message}</small><br>
            <small style="color: #666;">Path: ${DATA_PATH}/anime_index.json</small>
        </div>`;
    }
}

// Render entire home page
async function renderHome() {
    await loadHeroData();
    renderHero();
    renderContentRows();
    startHeroAutoRotate();
}

// Load full data for hero anime (to get descriptions)
let heroAnimeData = [];
async function loadHeroData() {
    const featuredAnime = animeIndex.slice(0, HERO_COUNT);
    heroAnimeData = [];
    
    // Load all hero data in parallel
    const promises = featuredAnime.map(async (anime) => {
        try {
            // Generate filename using same logic as Python scraper
            const urlHash = hashString(anime.url);
            const safeTitle = sanitizeFilename(anime.title);
            const filename = `${safeTitle}_${urlHash}.json`;
            
            console.log('Loading hero anime:', filename);
            const response = await fetch(`${DATA_PATH}/anime/${filename}`);
            if (response.ok) {
                const data = await response.json();
                console.log('Loaded description for:', anime.title, data.description ? 'YES' : 'NO');
                return { ...anime, ...data };
            } else {
                console.log('Failed to load:', filename, response.status);
                return anime;
            }
        } catch (e) {
            console.log('Error loading hero data for:', anime.title, e);
            return anime;
        }
    });
    
    heroAnimeData = await Promise.all(promises);
    console.log('Hero data loaded:', heroAnimeData.length, 'items');
}

// Render Hero Section
function renderHero() {
    const heroSection = document.getElementById('heroSection');
    
    if (heroAnimeData.length === 0) {
        heroSection.innerHTML = '<div class="no-results">No anime available</div>';
        return;
    }
    
    const anime = heroAnimeData[currentHeroIndex];
    
    heroSection.innerHTML = `
        <div class="hero-backdrop" style="background-image: url('${anime.cover_image || ''}')"></div>
        <div class="hero-content">
            <h1 class="hero-title">${escapeHtml(anime.title)}</h1>
            <div class="hero-meta">
                ${anime.status ? `<span class="hero-status">${escapeHtml(anime.status)}</span>` : ''}
                ${anime.type ? `<span class="hero-meta-item">${escapeHtml(anime.type)}</span>` : ''}
                <span class="hero-meta-item">${anime.available_episodes || 0} Episodes</span>
            </div>
            <p class="hero-description">${escapeHtml(anime.description || 'No description available.')}</p>
            <div class="hero-buttons">
                <button class="hero-btn hero-btn-primary" onclick="showAnime('${encodeURIComponent(anime.title)}')">
                    ▶ Watch Now
                </button>
                <button class="hero-btn hero-btn-secondary" onclick="showAnime('${encodeURIComponent(anime.title)}')">
                    ℹ More Info
                </button>
            </div>
            ${anime.genres && anime.genres.length > 0 ? `
                <div class="hero-genres">
                    ${anime.genres.slice(0, 4).map(g => `<span class="hero-genre">${escapeHtml(g)}</span>`).join('')}
                </div>
            ` : ''}
        </div>
        <button class="hero-arrow hero-arrow-left" onclick="changeHero(-1)">‹</button>
        <button class="hero-arrow hero-arrow-right" onclick="changeHero(1)">›</button>
        <div class="hero-nav">
            ${heroAnimeData.map((_, i) => `
                <div class="hero-dot ${i === currentHeroIndex ? 'active' : ''}" onclick="goToHero(${i})"></div>
            `).join('')}
        </div>
    `;
}

// Change hero slide
function changeHero(direction) {
    const featuredCount = heroAnimeData.length;
    if (featuredCount === 0) return;
    currentHeroIndex = (currentHeroIndex + direction + featuredCount) % featuredCount;
    renderHero();
    resetHeroAutoRotate();
}

// Go to specific hero
function goToHero(index) {
    currentHeroIndex = index;
    renderHero();
    resetHeroAutoRotate();
}

// Auto-rotate hero
function startHeroAutoRotate() {
    if (heroInterval) clearInterval(heroInterval);
    heroInterval = setInterval(() => {
        changeHero(1);
    }, 8000); // Change every 8 seconds
}

function resetHeroAutoRotate() {
    startHeroAutoRotate();
}

// Render content rows
function renderContentRows() {
    // Get anime by status
    const ongoingAnime = animeIndex.filter(a => a.status && a.status.toLowerCase().includes('ongoing')).slice(0, ROW_COUNT);
    const completedAnime = animeIndex.filter(a => a.status && a.status.toLowerCase().includes('completed')).slice(0, ROW_COUNT);
    const latestAnime = animeIndex.slice(0, ROW_COUNT);
    
    // Render each row
    renderRow('latestRow', latestAnime);
    renderRow('ongoingRow', ongoingAnime);
    renderRow('completedRow', completedAnime);
    
    // Hide sections with no content
    document.getElementById('ongoingSection').style.display = ongoingAnime.length > 0 ? 'block' : 'none';
    document.getElementById('completedSection').style.display = completedAnime.length > 0 ? 'block' : 'none';
}

// Render a single row
function renderRow(rowId, animeList) {
    const row = document.getElementById(rowId);
    if (!row) return;
    
    if (animeList.length === 0) {
        row.innerHTML = '<div class="no-results">No anime found</div>';
        return;
    }
    
    row.innerHTML = animeList.map(anime => `
        <div class="row-card" onclick="showAnime('${encodeURIComponent(anime.title)}')">
            <div class="row-card-image">
                ${anime.cover_image 
                    ? `<img src="${escapeHtml(anime.cover_image)}" alt="${escapeHtml(anime.title)}" loading="lazy" onerror="this.style.display='none';" />`
                    : '<span style="font-size: 3rem;">🎬</span>'
                }
            </div>
            <div class="row-card-info">
                <div class="row-card-title">${escapeHtml(anime.title)}</div>
                <div class="row-card-meta">${anime.available_episodes || 0} eps</div>
            </div>
        </div>
    `).join('');
}

// Scroll row left/right
function scrollRow(rowId, direction) {
    const row = document.getElementById(rowId);
    if (!row) return;
    
    const scrollAmount = 400;
    row.scrollBy({
        left: direction * scrollAmount,
        behavior: 'smooth'
    });
}

// Render search results
function renderSearchResults(searchTerm) {
    const searchSection = document.getElementById('searchResults');
    const searchGrid = document.getElementById('searchGrid');
    const contentSections = document.querySelectorAll('.content-section:not(#searchResults)');
    const heroSection = document.getElementById('heroSection');
    
    if (!searchTerm) {
        // Hide search, show normal content
        searchSection.style.display = 'none';
        contentSections.forEach(s => s.style.display = 'block');
        heroSection.style.display = 'block';
        renderContentRows();
        return;
    }
    
    // Show search, hide normal content
    searchSection.style.display = 'block';
    contentSections.forEach(s => s.style.display = 'none');
    heroSection.style.display = 'none';
    
    // Filter anime
    const results = animeIndex.filter(anime => 
        anime.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    if (results.length === 0) {
        searchGrid.innerHTML = '<div class="no-results">No anime found matching your search</div>';
        return;
    }
    
    searchGrid.innerHTML = results.map(anime => `
        <div class="row-card" onclick="showAnime('${encodeURIComponent(anime.title)}')">
            <div class="row-card-image">
                ${anime.cover_image 
                    ? `<img src="${escapeHtml(anime.cover_image)}" alt="${escapeHtml(anime.title)}" loading="lazy" onerror="this.style.display='none';" />`
                    : '<span style="font-size: 3rem;">🎬</span>'
                }
            </div>
            <div class="row-card-info">
                <div class="row-card-title">${escapeHtml(anime.title)}</div>
                <div class="row-card-meta">${anime.available_episodes || 0} eps</div>
            </div>
        </div>
    `).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Search functionality - works from any page
    searchInput.addEventListener('input', debounce(() => {
        const searchTerm = searchInput.value.trim();
        
        // If searching, navigate to home page first
        const homePage = document.getElementById('homePage');
        if (!homePage.classList.contains('active')) {
            stopVideo(); // Stop any playing video
            showPage('homePage'); // Switch to home page
            history.pushState({ page: 'home' }, '', '#'); // Update URL
        }
        
        renderSearchResults(searchTerm);
    }, 300));
    
    // Focus on search box navigates to home if on other pages
    searchInput.addEventListener('focus', () => {
        const homePage = document.getElementById('homePage');
        if (!homePage.classList.contains('active')) {
            stopVideo();
            showPage('homePage');
            renderSearchResults(''); // Show normal home content
            history.pushState({ page: 'home' }, '', '#'); // Update URL
        }
    });
}


// Show anime detail page
async function showAnime(encodedTitle, pushHistory = true) {
    const title = decodeURIComponent(encodedTitle);
    currentAnime = title;
    
    // Find anime in index
    const animeInfo = animeIndex.find(a => a.title === title);
    if (!animeInfo) {
        alert('Anime not found');
        return;
    }
    
    // Stop any playing video
    stopVideo();
    
    // Show anime page
    showPage('animePage');
    
    // Update browser history
    if (pushHistory) {
        history.pushState({ page: 'anime', title: title }, '', `#anime/${encodeURIComponent(title)}`);
    }
    
    const animeDetail = document.getElementById('animeDetail');
    animeDetail.innerHTML = '<div class="loading" data-text="Loading details..."></div>';
    
    // Load full anime data
    try {
        const animeData = await loadAnimeData(animeInfo);
        renderAnimeDetail(animeData);
    } catch (error) {
        console.error('Error loading anime:', error);
        animeDetail.innerHTML = '<div class="no-results">Failed to load anime details</div>';
    }
}

// Load anime data from JSON file
async function loadAnimeData(animeInfo) {
    // Check cache
    if (animeCache[animeInfo.title]) {
        return animeCache[animeInfo.title];
    }
    
    // Generate filename from URL (same logic as scraper)
    const urlHash = hashString(animeInfo.url);
    const safeTitle = sanitizeFilename(animeInfo.title);
    const filename = `${safeTitle}_${urlHash}.json`;
    console.log('Loading anime file:', filename);
    
    try {
        const response = await fetch(`${DATA_PATH}/anime/${filename}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        animeCache[animeInfo.title] = data;
        return data;
    } catch (error) {
        console.error(`Could not load ${filename}:`, error);
        throw error;
    }
}

// MD5 hash function (matches Python's hashlib.md5[:8])
function hashString(str) {
    // Simple MD5 implementation for browser
    function md5(string) {
        function rotateLeft(x, n) {
            return (x << n) | (x >>> (32 - n));
        }
        function addUnsigned(x, y) {
            const x8 = (x & 0x80000000);
            const y8 = (y & 0x80000000);
            const x4 = (x & 0x40000000);
            const y4 = (y & 0x40000000);
            const result = (x & 0x3FFFFFFF) + (y & 0x3FFFFFFF);
            if (x4 & y4) return (result ^ 0x80000000 ^ x8 ^ y8);
            if (x4 | y4) {
                if (result & 0x40000000) return (result ^ 0xC0000000 ^ x8 ^ y8);
                else return (result ^ 0x40000000 ^ x8 ^ y8);
            } else return (result ^ x8 ^ y8);
        }
        function F(x, y, z) { return (x & y) | ((~x) & z); }
        function G(x, y, z) { return (x & z) | (y & (~z)); }
        function H(x, y, z) { return (x ^ y ^ z); }
        function I(x, y, z) { return (y ^ (x | (~z))); }
        function FF(a, b, c, d, x, s, ac) {
            a = addUnsigned(a, addUnsigned(addUnsigned(F(b, c, d), x), ac));
            return addUnsigned(rotateLeft(a, s), b);
        }
        function GG(a, b, c, d, x, s, ac) {
            a = addUnsigned(a, addUnsigned(addUnsigned(G(b, c, d), x), ac));
            return addUnsigned(rotateLeft(a, s), b);
        }
        function HH(a, b, c, d, x, s, ac) {
            a = addUnsigned(a, addUnsigned(addUnsigned(H(b, c, d), x), ac));
            return addUnsigned(rotateLeft(a, s), b);
        }
        function II(a, b, c, d, x, s, ac) {
            a = addUnsigned(a, addUnsigned(addUnsigned(I(b, c, d), x), ac));
            return addUnsigned(rotateLeft(a, s), b);
        }
        function convertToWordArray(str) {
            const lWordCount = (((str.length + 8) - ((str.length + 8) % 64)) / 64 + 1) * 16;
            const lWordArray = new Array(lWordCount - 1);
            let lByteCount = 0, lWordArrayIndex = 0;
            while (lByteCount < str.length) {
                lWordArrayIndex = (lByteCount - (lByteCount % 4)) / 4;
                const lBytePosition = (lByteCount % 4) * 8;
                lWordArray[lWordArrayIndex] = (lWordArray[lWordArrayIndex] | (str.charCodeAt(lByteCount) << lBytePosition));
                lByteCount++;
            }
            lWordArrayIndex = (lByteCount - (lByteCount % 4)) / 4;
            const lBytePosition = (lByteCount % 4) * 8;
            lWordArray[lWordArrayIndex] = lWordArray[lWordArrayIndex] | (0x80 << lBytePosition);
            lWordArray[lWordCount - 2] = str.length << 3;
            lWordArray[lWordCount - 1] = str.length >>> 29;
            return lWordArray;
        }
        function wordToHex(val) {
            let result = '', temp = '';
            for (let i = 0; i <= 3; i++) {
                temp = ((val >>> (i * 8)) & 255).toString(16);
                result += (temp.length === 1) ? '0' + temp : temp;
            }
            return result;
        }
        const x = convertToWordArray(string);
        let a = 0x67452301, b = 0xEFCDAB89, c = 0x98BADCFE, d = 0x10325476;
        const S11=7, S12=12, S13=17, S14=22, S21=5, S22=9, S23=14, S24=20;
        const S31=4, S32=11, S33=16, S34=23, S41=6, S42=10, S43=15, S44=21;
        for (let k = 0; k < x.length; k += 16) {
            const AA = a, BB = b, CC = c, DD = d;
            a=FF(a,b,c,d,x[k+0],S11,0xD76AA478); d=FF(d,a,b,c,x[k+1],S12,0xE8C7B756);
            c=FF(c,d,a,b,x[k+2],S13,0x242070DB); b=FF(b,c,d,a,x[k+3],S14,0xC1BDCEEE);
            a=FF(a,b,c,d,x[k+4],S11,0xF57C0FAF); d=FF(d,a,b,c,x[k+5],S12,0x4787C62A);
            c=FF(c,d,a,b,x[k+6],S13,0xA8304613); b=FF(b,c,d,a,x[k+7],S14,0xFD469501);
            a=FF(a,b,c,d,x[k+8],S11,0x698098D8); d=FF(d,a,b,c,x[k+9],S12,0x8B44F7AF);
            c=FF(c,d,a,b,x[k+10],S13,0xFFFF5BB1); b=FF(b,c,d,a,x[k+11],S14,0x895CD7BE);
            a=FF(a,b,c,d,x[k+12],S11,0x6B901122); d=FF(d,a,b,c,x[k+13],S12,0xFD987193);
            c=FF(c,d,a,b,x[k+14],S13,0xA679438E); b=FF(b,c,d,a,x[k+15],S14,0x49B40821);
            a=GG(a,b,c,d,x[k+1],S21,0xF61E2562); d=GG(d,a,b,c,x[k+6],S22,0xC040B340);
            c=GG(c,d,a,b,x[k+11],S23,0x265E5A51); b=GG(b,c,d,a,x[k+0],S24,0xE9B6C7AA);
            a=GG(a,b,c,d,x[k+5],S21,0xD62F105D); d=GG(d,a,b,c,x[k+10],S22,0x2441453);
            c=GG(c,d,a,b,x[k+15],S23,0xD8A1E681); b=GG(b,c,d,a,x[k+4],S24,0xE7D3FBC8);
            a=GG(a,b,c,d,x[k+9],S21,0x21E1CDE6); d=GG(d,a,b,c,x[k+14],S22,0xC33707D6);
            c=GG(c,d,a,b,x[k+3],S23,0xF4D50D87); b=GG(b,c,d,a,x[k+8],S24,0x455A14ED);
            a=GG(a,b,c,d,x[k+13],S21,0xA9E3E905); d=GG(d,a,b,c,x[k+2],S22,0xFCEFA3F8);
            c=GG(c,d,a,b,x[k+7],S23,0x676F02D9); b=GG(b,c,d,a,x[k+12],S24,0x8D2A4C8A);
            a=HH(a,b,c,d,x[k+5],S31,0xFFFA3942); d=HH(d,a,b,c,x[k+8],S32,0x8771F681);
            c=HH(c,d,a,b,x[k+11],S33,0x6D9D6122); b=HH(b,c,d,a,x[k+14],S34,0xFDE5380C);
            a=HH(a,b,c,d,x[k+1],S31,0xA4BEEA44); d=HH(d,a,b,c,x[k+4],S32,0x4BDECFA9);
            c=HH(c,d,a,b,x[k+7],S33,0xF6BB4B60); b=HH(b,c,d,a,x[k+10],S34,0xBEBFBC70);
            a=HH(a,b,c,d,x[k+13],S31,0x289B7EC6); d=HH(d,a,b,c,x[k+0],S32,0xEAA127FA);
            c=HH(c,d,a,b,x[k+3],S33,0xD4EF3085); b=HH(b,c,d,a,x[k+6],S34,0x4881D05);
            a=HH(a,b,c,d,x[k+9],S31,0xD9D4D039); d=HH(d,a,b,c,x[k+12],S32,0xE6DB99E5);
            c=HH(c,d,a,b,x[k+15],S33,0x1FA27CF8); b=HH(b,c,d,a,x[k+2],S34,0xC4AC5665);
            a=II(a,b,c,d,x[k+0],S41,0xF4292244); d=II(d,a,b,c,x[k+7],S42,0x432AFF97);
            c=II(c,d,a,b,x[k+14],S43,0xAB9423A7); b=II(b,c,d,a,x[k+5],S44,0xFC93A039);
            a=II(a,b,c,d,x[k+12],S41,0x655B59C3); d=II(d,a,b,c,x[k+3],S42,0x8F0CCC92);
            c=II(c,d,a,b,x[k+10],S43,0xFFEFF47D); b=II(b,c,d,a,x[k+1],S44,0x85845DD1);
            a=II(a,b,c,d,x[k+8],S41,0x6FA87E4F); d=II(d,a,b,c,x[k+15],S42,0xFE2CE6E0);
            c=II(c,d,a,b,x[k+6],S43,0xA3014314); b=II(b,c,d,a,x[k+13],S44,0x4E0811A1);
            a=II(a,b,c,d,x[k+4],S41,0xF7537E82); d=II(d,a,b,c,x[k+11],S42,0xBD3AF235);
            c=II(c,d,a,b,x[k+2],S43,0x2AD7D2BB); b=II(b,c,d,a,x[k+9],S44,0xEB86D391);
            a=addUnsigned(a,AA); b=addUnsigned(b,BB); c=addUnsigned(c,CC); d=addUnsigned(d,DD);
        }
        return (wordToHex(a) + wordToHex(b) + wordToHex(c) + wordToHex(d)).toLowerCase();
    }
    return md5(str).substring(0, 8);
}

// Render anime detail
function renderAnimeDetail(anime) {
    const animeDetail = document.getElementById('animeDetail');
    
    const genres = anime.genres && anime.genres.length > 0 
        ? anime.genres.map(g => `<span class="genre-tag">${escapeHtml(g)}</span>`).join('')
        : '<span class="genre-tag">Unknown</span>';
    
    const episodes = anime.episodes || [];
    const sortedEpisodes = [...episodes].sort((a, b) => {
        const numA = parseInt(a.episode_number) || 0;
        const numB = parseInt(b.episode_number) || 0;
        return numA - numB;
    });
    
    // Build metadata items
    const metaItems = [];
    if (anime.status) metaItems.push(`<span class="meta-item"><strong>Status:</strong> ${escapeHtml(anime.status)}</span>`);
    if (anime.type) metaItems.push(`<span class="meta-item"><strong>Type:</strong> ${escapeHtml(anime.type)}</span>`);
    if (anime.studio) metaItems.push(`<span class="meta-item"><strong>Studio:</strong> ${escapeHtml(anime.studio)}</span>`);
    if (anime.duration) metaItems.push(`<span class="meta-item"><strong>Duration:</strong> ${escapeHtml(anime.duration)}</span>`);
    if (anime.season) metaItems.push(`<span class="meta-item"><strong>Season:</strong> ${escapeHtml(anime.season)}</span>`);
    if (anime.released) metaItems.push(`<span class="meta-item"><strong>Released:</strong> ${escapeHtml(anime.released)}</span>`);
    
    // Build producers list
    const producers = anime.producers && anime.producers.length > 0
        ? `<span class="meta-item"><strong>Producers:</strong> ${anime.producers.map(p => escapeHtml(p)).join(', ')}</span>`
        : '';
    
    // Cover image or placeholder
    const coverImage = anime.cover_image 
        ? `<img src="${escapeHtml(anime.cover_image)}" alt="${escapeHtml(anime.title)}" class="poster-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" /><div class="poster-placeholder" style="display:none;">🎬</div>`
        : '<div class="poster-placeholder">🎬</div>';
    
    // Alternative titles
    const altTitles = anime.alternative_titles 
        ? `<p class="anime-alt-titles">${escapeHtml(anime.alternative_titles)}</p>` 
        : '';
    
    animeDetail.innerHTML = `
        <div class="anime-header">
            <div class="anime-poster">${coverImage}</div>
            <div class="anime-info">
                <h1 class="anime-title">${escapeHtml(anime.title)}</h1>
                ${altTitles}
                <p class="anime-description">${escapeHtml(anime.description || 'No description available.')}</p>
                
                <div class="anime-meta">
                    ${metaItems.join('')}
                    ${producers}
                </div>
                
                <div class="anime-stats">
                    <div class="stat">
                        <div class="stat-value">${anime.total_episodes || 0}</div>
                        <div class="stat-label">Total Episodes</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${anime.available_episodes || 0}</div>
                        <div class="stat-label">Available</div>
                    </div>
                </div>
                <div class="anime-genres">${genres}</div>
            </div>
        </div>
        
        <div class="episodes-section">
            <h2 class="episodes-title">Episodes</h2>
            <div id="episodesGrid" class="episodes-grid"></div>
            <div id="episodePagination" class="pagination"></div>
        </div>
    `;
    
    // Store sorted episodes for pagination
    window.currentSortedEpisodes = sortedEpisodes;
    window.currentAnimeTitle = anime.title;
    currentEpisodePage = 1;
    renderEpisodes();
}

// Render episodes with pagination
function renderEpisodes() {
    const episodes = window.currentSortedEpisodes || [];
    const totalPages = Math.ceil(episodes.length / EPISODES_PER_PAGE);
    
    // Only show pagination if more than one page
    const needsPagination = totalPages > 1;
    
    // Get episodes for current page
    const startIndex = (currentEpisodePage - 1) * EPISODES_PER_PAGE;
    const endIndex = startIndex + EPISODES_PER_PAGE;
    const pageEpisodes = episodes.slice(startIndex, endIndex);
    
    const episodesGrid = document.getElementById('episodesGrid');
    const episodePagination = document.getElementById('episodePagination');
    
    // Render episode buttons
    episodesGrid.innerHTML = pageEpisodes.map((ep, idx) => {
        const actualIndex = startIndex + idx;
        return `
            <button class="episode-btn ${ep.has_videos ? '' : 'no-video'}" 
                    onclick="${ep.has_videos ? `playEpisode('${encodeURIComponent(window.currentAnimeTitle)}', ${actualIndex})` : ''}"
                    ${ep.has_videos ? '' : 'disabled'}>
                <div class="ep-number">EP ${ep.episode_number}</div>
                <div class="ep-status">${ep.has_videos ? '▶ Play' : 'N/A'}</div>
            </button>
        `;
    }).join('');
    
    // Render pagination if needed
    if (needsPagination) {
        let html = `<div class="pagination-info">Episodes ${startIndex + 1}-${Math.min(endIndex, episodes.length)} of ${episodes.length}</div>`;
        html += '<div class="pagination-controls">';
        
        html += `<button class="page-btn" onclick="goToEpisodePage(${currentEpisodePage - 1})" ${currentEpisodePage === 1 ? 'disabled' : ''}>← Prev</button>`;
        
        for (let i = 1; i <= totalPages; i++) {
            html += `<button class="page-btn ${i === currentEpisodePage ? 'active' : ''}" onclick="goToEpisodePage(${i})">${i}</button>`;
        }
        
        html += `<button class="page-btn" onclick="goToEpisodePage(${currentEpisodePage + 1})" ${currentEpisodePage === totalPages ? 'disabled' : ''}>Next →</button>`;
        html += '</div>';
        
        episodePagination.innerHTML = html;
    } else {
        episodePagination.innerHTML = '';
    }
}

// Go to episode page
function goToEpisodePage(page) {
    const episodes = window.currentSortedEpisodes || [];
    const totalPages = Math.ceil(episodes.length / EPISODES_PER_PAGE);
    if (page < 1 || page > totalPages) return;
    
    currentEpisodePage = page;
    renderEpisodes();
    
    // Scroll to episodes section
    document.querySelector('.episodes-section')?.scrollIntoView({ behavior: 'smooth' });
}

// Video API endpoint (for fetching streaming URLs on-demand)
const VIDEO_API_URL = '/api/watch';

// Play episode
async function playEpisode(encodedTitle, episodeIndex, pushHistory = true) {
    const title = decodeURIComponent(encodedTitle);
    currentAnime = title;
    currentEpisodeIndex = episodeIndex;
    
    // Get anime data
    const animeInfo = animeIndex.find(a => a.title === title);
    if (!animeInfo) return;
    
    const animeData = animeCache[title];
    if (!animeData) return;
    
    const sortedEpisodes = [...(animeData.episodes || [])].sort((a, b) => {
        const numA = parseInt(a.episode_number) || 0;
        const numB = parseInt(b.episode_number) || 0;
        return numA - numB;
    });
    
    const episode = sortedEpisodes[episodeIndex];
    if (!episode) {
        alert('Episode not found');
        return;
    }
    
    // Check if episode has video sources (old format) or episode_id (new format)
    const hasOldFormat = episode.video_sources && episode.video_sources.length > 0;
    const hasNewFormat = episode.episode_id;
    
    if (!hasOldFormat && !hasNewFormat) {
        alert('No video source available');
        return;
    }
    
    // Stop any existing video before loading new one
    stopVideo();
    
    // Show player page
    showPage('playerPage');
    
    // Update browser history
    if (pushHistory) {
        history.pushState(
            { page: 'player', title: title, episode: episodeIndex }, 
            '', 
            `#watch/${encodeURIComponent(title)}/${episodeIndex}`
        );
    }
    
    const playerContainer = document.getElementById('playerContainer');
    
    // Show loading state
    playerContainer.innerHTML = `
        <button class="back-btn" onclick="goBackToAnime()">← Back to Episodes</button>
        <h2 class="player-title">${escapeHtml(animeData.title)} - Episode ${episode.episode_number}</h2>
        <div class="player-wrapper">
            <div class="loading" data-text="Loading video..."></div>
        </div>
    `;
    
    if (hasOldFormat) {
        // Old format: Use iframe directly
        const videoUrl = episode.video_sources[0];
        renderPlayer(playerContainer, animeData, episode, episodeIndex, sortedEpisodes.length, 'iframe', videoUrl);
    } else {
        // New format: Fetch streaming URL from API
        try {
            const response = await fetch(`${VIDEO_API_URL}?episodeId=${encodeURIComponent(episode.episode_id)}`);
            if (!response.ok) throw new Error('Failed to fetch video');
            
            const data = await response.json();
            
            if (data.sources && data.sources.length > 0) {
                const source = data.sources[0];
                if (source.isM3U8) {
                    // HLS stream - use video player with HLS.js
                    renderPlayer(playerContainer, animeData, episode, episodeIndex, sortedEpisodes.length, 'hls', source.url, data);
                } else {
                    // Direct video URL
                    renderPlayer(playerContainer, animeData, episode, episodeIndex, sortedEpisodes.length, 'video', source.url);
                }
            } else {
                throw new Error('No video sources found');
            }
        } catch (error) {
            console.error('Error loading video:', error);
            playerContainer.innerHTML = `
                <button class="back-btn" onclick="goBackToAnime()">← Back to Episodes</button>
                <h2 class="player-title">${escapeHtml(animeData.title)} - Episode ${episode.episode_number}</h2>
                <div class="player-wrapper">
                    <div class="no-results">Failed to load video: ${error.message}</div>
                </div>
            `;
        }
    }
}

// Render video player
function renderPlayer(container, animeData, episode, episodeIndex, totalEpisodes, type, url, extraData = null) {
    let playerHtml = '';
    
    if (type === 'iframe') {
        playerHtml = `
            <iframe src="${url}" 
                    allowfullscreen 
                    allow="autoplay; fullscreen"
                    frameborder="0">
            </iframe>
        `;
    } else if (type === 'hls') {
        // HLS video with subtitles
        const subtitles = extraData?.subtitles?.filter(s => s.kind === 'captions') || [];
        const subtitleTracks = subtitles.map(s => 
            `<track kind="captions" src="${s.url}" srclang="${s.lang?.substring(0,2) || 'en'}" label="${s.lang || 'English'}">`
        ).join('');
        
        playerHtml = `
            <video id="videoPlayer" controls autoplay crossorigin="anonymous">
                ${subtitleTracks}
            </video>
            <script>
                (function() {
                    const video = document.getElementById('videoPlayer');
                    if (Hls.isSupported()) {
                        const hls = new Hls();
                        hls.loadSource('${url}');
                        hls.attachMedia(video);
                        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
                    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                        video.src = '${url}';
                        video.play();
                    }
                })();
            </script>
        `;
    } else {
        playerHtml = `
            <video src="${url}" controls autoplay></video>
        `;
    }
    
    container.innerHTML = `
        <button class="back-btn" onclick="goBackToAnime()">← Back to Episodes</button>
        <h2 class="player-title">${escapeHtml(animeData.title)} - Episode ${episode.episode_number}</h2>
        <div class="player-wrapper">
            ${playerHtml}
        </div>
        <div class="episode-nav">
            <button class="nav-btn" onclick="playPrevious()" ${episodeIndex === 0 ? 'disabled' : ''}>
                ← Previous Episode
            </button>
            <button class="nav-btn" onclick="playNext()" ${episodeIndex >= totalEpisodes - 1 ? 'disabled' : ''}>
                Next Episode →
            </button>
        </div>
    `;
}

// Navigate episodes
function playPrevious() {
    if (currentEpisodeIndex > 0) {
        playEpisode(encodeURIComponent(currentAnime), currentEpisodeIndex - 1);
    }
}

function playNext() {
    const animeData = animeCache[currentAnime];
    if (animeData && currentEpisodeIndex < (animeData.episodes?.length || 0) - 1) {
        playEpisode(encodeURIComponent(currentAnime), currentEpisodeIndex + 1);
    }
}

// Stop any playing video
function stopVideo() {
    const playerContainer = document.getElementById('playerContainer');
    if (playerContainer) {
        // Remove iframe to stop video/audio
        playerContainer.innerHTML = '';
    }
}

// Show specific page
function showPage(pageId) {
    // Stop video when leaving player page
    const currentPage = document.querySelector('.page.active');
    if (currentPage && currentPage.id === 'playerPage' && pageId !== 'playerPage') {
        stopVideo();
    }
    
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    window.scrollTo(0, 0);
}

// Show home page
function showHome() {
    stopVideo();
    searchInput.value = '';
    renderSearchResults(''); // Reset to show normal content
    showPage('homePage');
    history.pushState({ page: 'home' }, '', '#');
}

// Go back to anime detail page
function goBackToAnime() {
    stopVideo();
    if (currentAnime) {
        showPage('animePage');
    } else {
        showPage('homePage');
    }
}

// Utility functions

// Sanitize filename - matches Python scraper's sanitize_filename()
function sanitizeFilename(title) {
    return title
        .replace(/[<>:"/\\|?*]/g, '')  // Remove invalid chars
        .replace(/\s+/g, '_')           // Replace spaces with underscores
        .trim()
        .substring(0, 200);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
