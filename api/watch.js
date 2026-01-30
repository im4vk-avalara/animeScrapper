/**
 * Vercel Serverless Function - Get Video Streaming URL
 * 
 * Endpoint: /api/watch?episodeId=xxx
 * Returns: { sources: [...], subtitles: [...] }
 */

import { ANIME } from '@consumet/extensions';

export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  // CORS headers
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  // Handle preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  try {
    const url = new URL(request.url);
    const episodeId = url.searchParams.get('episodeId');
    const dub = url.searchParams.get('dub') === 'true';

    if (!episodeId) {
      return new Response(
        JSON.stringify({ error: 'episodeId is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const animekai = new ANIME.AnimeKai();
    const sources = await animekai.fetchEpisodeSources(episodeId, undefined, dub ? 'dub' : 'sub');

    return new Response(
      JSON.stringify(sources),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error fetching sources:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to fetch video sources', message: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
}
