"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


# ============== Search Schemas ==============

class SearchRequest(BaseModel):
    """Search request schema."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    sort_by: str = Field(default="relevance", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort direction")
    author_filter: Optional[str] = Field(None, description="Filter by author")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    sentiment_filter: Optional[str] = Field(None, description="Filter by sentiment")
    include_summary: bool = Field(default=True, description="Include AI summary")
    enhance_query: bool = Field(default=True, description="Use Grok query enhancement")
    search_mode: str = Field(default="hybrid", description="Search mode: keyword, semantic, or hybrid")


class PostResponse(BaseModel):
    """Post response schema."""
    id: int
    post_id: str
    author_username: str
    author_display_name: Optional[str]
    content: str
    likes: int
    retweets: int
    replies: int
    views: int
    posted_at: Optional[str]
    scraped_at: Optional[str]
    ai_description: Optional[str]
    ai_topics: List[str]
    ai_sentiment: Optional[str]
    ai_entities: List[str]
    has_media: bool
    media_urls: List[str]


class QueryAnalysis(BaseModel):
    """Query analysis from Grok."""
    enhanced_query: str
    intent: str
    keywords: List[str]
    expanded_terms: List[str]
    filters: Dict[str, Any]
    clarification_needed: bool
    clarification_question: Optional[str] = None


class SearchSummary(BaseModel):
    """Search results summary from Grok."""
    summary: str
    key_insights: List[str]
    themes: List[str]
    notable_posts: List[int]
    suggested_queries: List[str]


class SearchResponse(BaseModel):
    """Search response schema."""
    query: str
    enhanced_query: Optional[str]
    query_analysis: Optional[Dict[str, Any]]
    results: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int
    summary: Optional[Dict[str, Any]]


# ============== Question Answering Schemas ==============

class QuestionRequest(BaseModel):
    """Question request schema."""
    question: str = Field(..., min_length=1, max_length=1000, description="Question to answer")


class QuestionResponse(BaseModel):
    """Question response schema."""
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    query_analysis: Optional[Dict[str, Any]]


# ============== Scraper Schemas ==============

class ScrapeRequest(BaseModel):
    """Scrape request schema."""
    username: Optional[str] = Field(None, description="X username to scrape")
    load_sample: bool = Field(default=False, description="Load sample data")
    scrape_popular: bool = Field(default=False, description="Scrape from popular tech accounts")


class ScrapeResponse(BaseModel):
    """Scrape response schema."""
    success: bool
    message: str
    posts_added: int
    posts: List[Dict[str, Any]]


class AddPostRequest(BaseModel):
    """Add custom post request."""
    post_id: str = Field(..., description="Unique post ID")
    author_username: str = Field(..., description="Author username")
    author_display_name: Optional[str] = Field(None, description="Author display name")
    content: str = Field(..., min_length=1, description="Post content")
    likes: int = Field(default=0, ge=0)
    retweets: int = Field(default=0, ge=0)
    replies: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    posted_at: Optional[str] = Field(None, description="ISO timestamp")


# ============== Stats Schemas ==============

class StatsResponse(BaseModel):
    """Database stats response."""
    total_posts: int
    total_authors: int
    total_searches: int
    sentiment_distribution: Dict[str, int]
    top_authors: List[Dict[str, Any]]
    recent_searches: List[Dict[str, Any]]


# ============== Health Check ==============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    grok_api: str
    version: str

