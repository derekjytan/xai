import { useState, useEffect } from 'react';
import {
  Search,
  Loader2,
  Sparkles,
  MessageCircle,
  Heart,
  Repeat2,
  Eye,
  Database,
  Brain,
  ChevronDown,
  ChevronUp,
  Zap,
  AlertCircle,
  CheckCircle,
  Filter,
  TrendingUp,
  Users,
} from 'lucide-react';
import { search, askQuestion, loadSampleData, getStats, healthCheck } from './api';
import { SearchResponse, QuestionResponse, Stats, Post } from './types';

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Unknown date';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function SentimentBadge({ sentiment }: { sentiment: string | null }) {
  const colors: Record<string, string> = {
    positive: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    negative: 'bg-red-500/20 text-red-400 border-red-500/30',
    neutral: 'bg-x-gray-500/20 text-x-gray-400 border-x-gray-500/30',
    mixed: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  };
  
  if (!sentiment) return null;
  
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full border ${colors[sentiment] || colors.neutral}`}>
      {sentiment}
    </span>
  );
}

function PostCard({ post, index }: { post: Post; index: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="gradient-border p-5 animate-in"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-grok-500 to-grok-700 flex items-center justify-center text-white font-semibold text-sm">
          {post.author_username[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-white">
              {post.author_display_name || post.author_username}
            </span>
            <span className="text-x-gray-500">@{post.author_username}</span>
            <span className="text-x-gray-600">·</span>
            <span className="text-x-gray-500 text-sm">{formatDate(post.posted_at)}</span>
            <SentimentBadge sentiment={post.ai_sentiment} />
          </div>
          
          <p className="mt-2 text-x-gray-200 whitespace-pre-wrap">{post.content}</p>
          
          {post.ai_description && (
            <div className="mt-3 p-3 rounded-lg bg-grok-950/50 border border-grok-800/30">
              <div className="flex items-center gap-1.5 text-grok-400 text-xs font-medium mb-1">
                <Sparkles className="w-3 h-3" />
                AI Summary
              </div>
              <p className="text-sm text-x-gray-300">{post.ai_description}</p>
            </div>
          )}
          
          {expanded && post.ai_topics && post.ai_topics.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {post.ai_topics.map((topic, i) => (
                <span
                  key={i}
                  className="px-2 py-1 text-xs rounded-full bg-x-gray-800 text-x-gray-300 border border-x-gray-700"
                >
                  {topic}
                </span>
              ))}
            </div>
          )}
          
          <div className="mt-3 flex items-center gap-6 text-x-gray-500">
            <button className="flex items-center gap-1.5 hover:text-grok-400 transition-colors">
              <MessageCircle className="w-4 h-4" />
              <span className="text-sm">{formatNumber(post.replies)}</span>
            </button>
            <button className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors">
              <Repeat2 className="w-4 h-4" />
              <span className="text-sm">{formatNumber(post.retweets)}</span>
            </button>
            <button className="flex items-center gap-1.5 hover:text-rose-400 transition-colors">
              <Heart className="w-4 h-4" />
              <span className="text-sm">{formatNumber(post.likes)}</span>
            </button>
            <div className="flex items-center gap-1.5">
              <Eye className="w-4 h-4" />
              <span className="text-sm">{formatNumber(post.views)}</span>
            </div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="ml-auto text-xs text-x-gray-500 hover:text-grok-400 transition-colors flex items-center gap-1"
            >
              {expanded ? (
                <>
                  Less <ChevronUp className="w-3 h-3" />
                </>
              ) : (
                <>
                  More <ChevronDown className="w-3 h-3" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SearchSummaryCard({ summary, suggestedQueries, onQueryClick }: {
  summary: SearchResponse['summary'];
  suggestedQueries?: string[];
  onQueryClick: (query: string) => void;
}) {
  if (!summary) return null;

  return (
    <div className="gradient-border p-5 mb-6 glow">
      <div className="flex items-center gap-2 text-grok-400 font-medium mb-3">
        <Brain className="w-5 h-5" />
        AI Summary
      </div>
      
      <p className="text-x-gray-200 mb-4">{summary.summary}</p>
      
      {summary.key_insights && summary.key_insights.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-x-gray-400 mb-2">Key Insights</h4>
          <ul className="space-y-1">
            {summary.key_insights.map((insight, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-x-gray-300">
                <Zap className="w-3 h-3 text-grok-500 mt-1 flex-shrink-0" />
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {summary.themes && summary.themes.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {summary.themes.map((theme, i) => (
            <span
              key={i}
              className="px-2.5 py-1 text-xs rounded-full bg-grok-950 text-grok-300 border border-grok-800"
            >
              {theme}
            </span>
          ))}
        </div>
      )}
      
      {suggestedQueries && suggestedQueries.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-x-gray-400 mb-2">Related Searches</h4>
          <div className="flex flex-wrap gap-2">
            {suggestedQueries.map((query, i) => (
              <button
                key={i}
                onClick={() => onQueryClick(query)}
                className="px-3 py-1.5 text-sm rounded-lg bg-x-gray-800 text-x-gray-300 hover:bg-x-gray-700 hover:text-white transition-colors"
              >
                {query}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AnswerCard({ response }: { response: QuestionResponse }) {
  return (
    <div className="gradient-border p-6 mb-6 glow">
      <div className="flex items-center gap-2 text-grok-400 font-medium mb-4">
        <MessageCircle className="w-5 h-5" />
        Answer from Grok
      </div>
      <div className="prose prose-invert max-w-none">
        <p className="text-x-gray-200 whitespace-pre-wrap">{response.answer}</p>
      </div>
      {response.sources.length > 0 && (
        <div className="mt-4 pt-4 border-t border-x-gray-800">
          <p className="text-sm text-x-gray-500 mb-2">
            Based on {response.sources.length} source{response.sources.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </div>
  );
}

function StatsPanel({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div className="gradient-border p-4">
        <div className="flex items-center gap-2 text-x-gray-400 text-sm mb-1">
          <Database className="w-4 h-4" />
          Posts
        </div>
        <div className="text-2xl font-bold text-white">{formatNumber(stats.total_posts)}</div>
      </div>
      <div className="gradient-border p-4">
        <div className="flex items-center gap-2 text-x-gray-400 text-sm mb-1">
          <Users className="w-4 h-4" />
          Authors
        </div>
        <div className="text-2xl font-bold text-white">{stats.total_authors}</div>
      </div>
      <div className="gradient-border p-4">
        <div className="flex items-center gap-2 text-x-gray-400 text-sm mb-1">
          <Search className="w-4 h-4" />
          Searches
        </div>
        <div className="text-2xl font-bold text-white">{stats.total_searches}</div>
      </div>
      <div className="gradient-border p-4">
        <div className="flex items-center gap-2 text-x-gray-400 text-sm mb-1">
          <TrendingUp className="w-4 h-4" />
          Top Author
        </div>
        <div className="text-lg font-bold text-white truncate">
          @{stats.top_authors[0]?.username || 'N/A'}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'search' | 'ask'>('search');
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [answerResult, setAnswerResult] = useState<QuestionResponse | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [health, setHealth] = useState<{ status: string; database: string; grok_api: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    sortBy: 'relevance',
    sortOrder: 'desc',
    sentiment: '',
    author: '',
    searchMode: 'hybrid' as 'keyword' | 'semantic' | 'hybrid',
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  // Auto-refresh search when filters change (with debounce)
  useEffect(() => {
    // Only trigger if there's an active query
    if (!query.trim()) return;
    
    const debounceTimer = setTimeout(() => {
      handleSearch();
    }, 300); // 300ms debounce
    
    return () => clearTimeout(debounceTimer);
  }, [filters.sortBy, filters.sortOrder, filters.sentiment, filters.author, filters.searchMode]);

  async function loadInitialData() {
    try {
      const [healthData, statsData] = await Promise.all([
        healthCheck(),
        getStats(),
      ]);
      setHealth(healthData);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  }

  async function handleSearch(searchQuery?: string) {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    setSearchResults(null);
    setAnswerResult(null);

    try {
      if (mode === 'search') {
        const results = await search({
          query: q,
          sortBy: filters.sortBy,
          sortOrder: filters.sortOrder,
          sentiment: filters.sentiment || undefined,
          author: filters.author || undefined,
          mode: filters.searchMode,
        });
        setSearchResults(results);
      } else {
        const result = await askQuestion(q);
        setAnswerResult(result);
      }
      loadInitialData(); // Refresh stats
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadSampleData() {
    setLoading(true);
    setError(null);
    try {
      await loadSampleData();
      await loadInitialData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sample data');
    } finally {
      setLoading(false);
    }
  }

  function handleSuggestedQuery(q: string) {
    setQuery(q);
    handleSearch(q);
  }

  return (
    <div className="min-h-screen">
      {/* Gradient Background */}
      <div className="fixed inset-0 bg-gradient-to-br from-x-gray-950 via-x-gray-900 to-grok-950/20 -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-grok-900/20 via-transparent to-transparent -z-10" />

      {/* Header */}
      <header className="border-b border-x-gray-800/50 glass sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-grok-500 to-grok-700 flex items-center justify-center">
                <Search className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Grok Search</h1>
                <p className="text-xs text-x-gray-500">Intelligent X/Twitter Discovery</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {health && (
                <div className="flex items-center gap-2 text-sm">
                  {health.status === 'healthy' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-500" />
                  )}
                  <span className="text-x-gray-400">
                    {health.grok_api === 'configured' ? 'Grok Ready' : 'Grok Not Configured'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Stats */}
        {stats && stats.total_posts > 0 && <StatsPanel stats={stats} />}

        {/* Load Sample Data Button */}
        {stats && stats.total_posts === 0 && (
          <div className="gradient-border p-8 text-center mb-8">
            <Database className="w-12 h-12 text-grok-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Posts Yet</h2>
            <p className="text-x-gray-400 mb-4">
              Load sample data to get started with searching
            </p>
            <button
              onClick={handleLoadSampleData}
              disabled={loading}
              className="px-6 py-3 bg-gradient-to-r from-grok-600 to-grok-500 text-white font-medium rounded-xl hover:from-grok-500 hover:to-grok-400 transition-all disabled:opacity-50 flex items-center gap-2 mx-auto"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Database className="w-5 h-5" />
              )}
              Load Sample Posts
            </button>
          </div>
        )}

        {/* Search Box */}
        <div className="mb-8">
          {/* Mode Toggle */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setMode('search')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                mode === 'search'
                  ? 'bg-grok-600 text-white'
                  : 'bg-x-gray-800 text-x-gray-400 hover:text-white'
              }`}
            >
              <Search className="w-4 h-4 inline mr-2" />
              Search
            </button>
            <button
              onClick={() => setMode('ask')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                mode === 'ask'
                  ? 'bg-grok-600 text-white'
                  : 'bg-x-gray-800 text-x-gray-400 hover:text-white'
              }`}
            >
              <MessageCircle className="w-4 h-4 inline mr-2" />
              Ask Grok
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={
                mode === 'search'
                  ? 'Search posts... (e.g., "AI announcements from tech leaders")'
                  : 'Ask a question... (e.g., "What are people saying about AGI?")'
              }
              className="w-full px-5 py-4 pl-12 bg-x-gray-900 border border-x-gray-700 rounded-xl text-white placeholder-x-gray-500 focus:outline-none focus:border-grok-500 input-glow transition-all"
            />
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-x-gray-500" />
            <button
              onClick={() => handleSearch()}
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-grok-600 text-white rounded-lg hover:bg-grok-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {mode === 'search' ? 'Search' : 'Ask'}
            </button>
          </div>

          {/* Filters */}
          {mode === 'search' && (
            <div className="mt-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 text-sm text-x-gray-400 hover:text-white transition-colors"
              >
                <Filter className="w-4 h-4" />
                Filters
                {showFilters ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {showFilters && (
                <div className="mt-3 p-4 bg-x-gray-900 rounded-xl border border-x-gray-800 grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-x-gray-500 mb-1">Sort By</label>
                    <select
                      value={filters.sortBy}
                      onChange={(e) => setFilters({ ...filters, sortBy: e.target.value })}
                      className="w-full px-3 py-2 bg-x-gray-800 border border-x-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-grok-500"
                    >
                      <option value="relevance">Relevance</option>
                      <option value="date">Date</option>
                      <option value="likes">Likes</option>
                      <option value="retweets">Retweets</option>
                      <option value="views">Views</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-x-gray-500 mb-1">Order</label>
                    <select
                      value={filters.sortOrder}
                      onChange={(e) => setFilters({ ...filters, sortOrder: e.target.value })}
                      className="w-full px-3 py-2 bg-x-gray-800 border border-x-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-grok-500"
                    >
                      <option value="desc">Descending</option>
                      <option value="asc">Ascending</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-x-gray-500 mb-1">Sentiment</label>
                    <select
                      value={filters.sentiment}
                      onChange={(e) => setFilters({ ...filters, sentiment: e.target.value })}
                      className="w-full px-3 py-2 bg-x-gray-800 border border-x-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-grok-500"
                    >
                      <option value="">All</option>
                      <option value="positive">Positive</option>
                      <option value="negative">Negative</option>
                      <option value="neutral">Neutral</option>
                      <option value="mixed">Mixed</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-x-gray-500 mb-1">Author</label>
                    <input
                      type="text"
                      value={filters.author}
                      onChange={(e) => setFilters({ ...filters, author: e.target.value })}
                      placeholder="@username"
                      className="w-full px-3 py-2 bg-x-gray-800 border border-x-gray-700 rounded-lg text-white text-sm placeholder-x-gray-600 focus:outline-none focus:border-grok-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-x-gray-500 mb-1">Search Mode</label>
                    <select
                      value={filters.searchMode}
                      onChange={(e) => setFilters({ ...filters, searchMode: e.target.value as 'keyword' | 'semantic' | 'hybrid' })}
                      className="w-full px-3 py-2 bg-x-gray-800 border border-x-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-grok-500"
                    >
                      <option value="hybrid">🔗 Hybrid</option>
                      <option value="semantic">🧠 Semantic</option>
                      <option value="keyword">🔤 Keyword</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Results */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-grok-500 animate-spin" />
          </div>
        )}

        {!loading && answerResult && <AnswerCard response={answerResult} />}

        {!loading && searchResults && (
          <>
            {/* Query Analysis */}
            {searchResults.query_analysis && (
              <div className="mb-4 flex items-center gap-2 text-sm text-x-gray-400">
                <Brain className="w-4 h-4 text-grok-500" />
                Intent: <span className="text-grok-400">{searchResults.query_analysis.intent}</span>
                {searchResults.enhanced_query && searchResults.enhanced_query !== searchResults.query && (
                  <>
                    <span className="mx-2">•</span>
                    Enhanced: <span className="text-x-gray-300">{searchResults.enhanced_query}</span>
                  </>
                )}
              </div>
            )}

            {/* Summary */}
            <SearchSummaryCard
              summary={searchResults.summary}
              suggestedQueries={searchResults.summary?.suggested_queries}
              onQueryClick={handleSuggestedQuery}
            />

            {/* Results Count */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-x-gray-400">
                Found <span className="text-white font-medium">{searchResults.total_count}</span> posts
              </p>
            </div>

            {/* Posts */}
            <div className="space-y-4">
              {searchResults.results.map((post, index) => (
                <PostCard key={post.post_id} post={post} index={index} />
              ))}
            </div>

            {searchResults.results.length === 0 && (
              <div className="text-center py-12">
                <Search className="w-12 h-12 text-x-gray-700 mx-auto mb-4" />
                <p className="text-x-gray-500">No posts found matching your query</p>
              </div>
            )}
          </>
        )}

        {/* Example Queries */}
        {!loading && !searchResults && !answerResult && stats && stats.total_posts > 0 && (
          <div className="gradient-border p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Try these searches</h3>
            <div className="grid md:grid-cols-2 gap-3">
              {[
                'AI announcements and updates',
                'What are tech leaders saying about AGI?',
                'startup advice and entrepreneurship',
                'Latest developments in machine learning',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSuggestedQuery(suggestion)}
                  className="p-3 text-left bg-x-gray-800/50 hover:bg-x-gray-800 rounded-lg text-x-gray-300 hover:text-white transition-colors flex items-center gap-2"
                >
                  <Search className="w-4 h-4 text-grok-500" />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-x-gray-800/50 mt-12 py-6">
        <div className="max-w-5xl mx-auto px-4 text-center text-x-gray-500 text-sm">
          <p>
            Built with <span className="text-grok-500">Grok</span> • xAI Technical Assessment
          </p>
        </div>
      </footer>
    </div>
  );
}

