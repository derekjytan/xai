export interface Post {
  id: number;
  post_id: string;
  author_username: string;
  author_display_name: string | null;
  content: string;
  likes: number;
  retweets: number;
  replies: number;
  views: number;
  posted_at: string | null;
  scraped_at: string | null;
  ai_description: string | null;
  ai_topics: string[];
  ai_sentiment: string | null;
  ai_entities: string[];
  has_media: boolean;
  media_urls: string[];
}

export interface QueryAnalysis {
  enhanced_query: string;
  intent: string;
  keywords: string[];
  expanded_terms: string[];
  filters: Record<string, unknown>;
  clarification_needed: boolean;
  clarification_question?: string;
}

export interface SearchSummary {
  summary: string;
  key_insights: string[];
  themes: string[];
  notable_posts: number[];
  suggested_queries: string[];
}

export interface SearchResponse {
  query: string;
  enhanced_query: string | null;
  query_analysis: QueryAnalysis | null;
  results: Post[];
  total_count: number;
  limit: number;
  offset: number;
  summary: SearchSummary | null;
}

export interface QuestionResponse {
  question: string;
  answer: string;
  sources: Post[];
  query_analysis: QueryAnalysis | null;
}

export interface Stats {
  total_posts: number;
  total_authors: number;
  total_searches: number;
  sentiment_distribution: Record<string, number>;
  top_authors: { username: string; post_count: number }[];
  recent_searches: { query: string; intent: string; result_count: number; created_at: string }[];
}

