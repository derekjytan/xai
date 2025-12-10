import { SearchResponse, QuestionResponse, Stats, Post } from './types';

const API_BASE = '/api';

export async function search(params: {
  query: string;
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder?: string;
  author?: string;
  sentiment?: string;
  includeSummary?: boolean;
  enhanceQuery?: boolean;
  mode?: 'keyword' | 'semantic' | 'hybrid';
}): Promise<SearchResponse> {
  const searchParams = new URLSearchParams({
    q: params.query,
    limit: String(params.limit || 20),
    offset: String(params.offset || 0),
    sort_by: params.sortBy || 'relevance',
    sort_order: params.sortOrder || 'desc',
    include_summary: String(params.includeSummary ?? true),
    enhance_query: String(params.enhanceQuery ?? true),
    mode: params.mode || 'hybrid',
  });

  if (params.author) searchParams.set('author', params.author);
  if (params.sentiment) searchParams.set('sentiment', params.sentiment);

  const response = await fetch(`${API_BASE}/search?${searchParams}`);
  if (!response.ok) throw new Error('Search failed');
  return response.json();
}

export async function askQuestion(question: string): Promise<QuestionResponse> {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error('Question failed');
  return response.json();
}

export async function loadSampleData(): Promise<{ success: boolean; posts_added: number }> {
  const response = await fetch(`${API_BASE}/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ load_sample: true }),
  });
  if (!response.ok) throw new Error('Failed to load sample data');
  return response.json();
}

export async function getStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) throw new Error('Failed to get stats');
  return response.json();
}

export async function getPosts(params: {
  limit?: number;
  offset?: number;
  author?: string;
}): Promise<{ posts: Post[]; total: number }> {
  const searchParams = new URLSearchParams({
    limit: String(params.limit || 50),
    offset: String(params.offset || 0),
  });
  if (params.author) searchParams.set('author', params.author);

  const response = await fetch(`${API_BASE}/posts?${searchParams}`);
  if (!response.ok) throw new Error('Failed to get posts');
  return response.json();
}

export async function healthCheck(): Promise<{
  status: string;
  database: string;
  grok_api: string;
}> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
}

