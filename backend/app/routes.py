"""API routes for Grok Search."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional
from datetime import datetime

from .database import get_db, Post, SearchQuery
from .search import get_search_service, SearchService
from .scraper import get_scraper, XScraper
from .grok_client import get_grok_client, GrokClient
from .schemas import (
    SearchRequest, SearchResponse,
    QuestionRequest, QuestionResponse,
    ScrapeRequest, ScrapeResponse, AddPostRequest,
    StatsResponse, HealthResponse,
)

router = APIRouter()


# ============== Search Endpoints ==============

@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_posts(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Search posts with intelligent query processing.
    
    Uses Grok to enhance queries, perform intent recognition,
    and generate contextual summaries of results.
    """
    try:
        results = await search_service.search(
            query=request.query,
            db=db,
            limit=request.limit,
            offset=request.offset,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            author_filter=request.author_filter,
            date_from=request.date_from,
            date_to=request.date_to,
            sentiment_filter=request.sentiment_filter,
            include_summary=request.include_summary,
            enhance_query=request.enhance_query,
            search_mode=request.search_mode,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_posts_get(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="relevance"),
    sort_order: str = Query(default="desc"),
    author: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    include_summary: bool = Query(default=True),
    enhance_query: bool = Query(default=True),
    mode: str = Query(default="hybrid", description="Search mode: keyword, semantic, or hybrid"),
    db: AsyncSession = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Search posts (GET endpoint for simple queries).
    
    Modes:
    - keyword: Traditional FTS5 full-text search
    - semantic: Embedding-based similarity search
    - hybrid: Combines both for best results (default)
    """
    try:
        results = await search_service.search(
            query=q,
            db=db,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            author_filter=author,
            sentiment_filter=sentiment,
            include_summary=include_summary,
            enhance_query=enhance_query,
            search_mode=mode,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/suggestions", tags=["Search"])
async def get_suggestions(
    q: str = Query(..., min_length=1, description="Partial query"),
    limit: int = Query(default=5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
):
    """Get search suggestions based on partial query."""
    suggestions = await search_service.get_suggestions(q, db, limit)
    return {"suggestions": suggestions}


# ============== Question Answering ==============

@router.post("/ask", response_model=QuestionResponse, tags=["AI"])
async def ask_question(
    request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Ask a question and get an AI-generated answer based on posts.
    
    Uses search to find relevant posts, then Grok to synthesize an answer.
    """
    try:
        result = await search_service.answer_question(request.question, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Data Management ==============

@router.post("/scrape", response_model=ScrapeResponse, tags=["Data"])
async def scrape_posts(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
    scraper: XScraper = Depends(get_scraper),
):
    """
    Scrape posts from X or load sample data.
    
    Set load_sample=true to load demo data, or provide username to scrape.
    """
    try:
        if request.load_sample:
            posts = await scraper.load_sample_data(db)
            await db.commit()
            return {
                "success": True,
                "message": f"Loaded {len(posts)} sample posts",
                "posts_added": len(posts),
                "posts": posts,
            }
        elif request.username:
            posts = await scraper.scrape_account(request.username, db)
            await db.commit()
            return {
                "success": True,
                "message": f"Scraped {len(posts)} posts from @{request.username}",
                "posts_added": len(posts),
                "posts": posts,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide username or set load_sample=true"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts", tags=["Data"])
async def add_post(
    request: AddPostRequest,
    db: AsyncSession = Depends(get_db),
    scraper: XScraper = Depends(get_scraper),
):
    """Add a custom post to the database."""
    try:
        post_data = request.model_dump()
        result = await scraper.add_custom_post(post_data, db)
        await db.commit()
        
        if result:
            return {"success": True, "post": result}
        else:
            return {"success": False, "message": "Post already exists"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts", tags=["Data"])
async def list_posts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    author: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all posts in the database."""
    query = select(Post).limit(limit).offset(offset)
    
    if author:
        query = query.where(Post.author_username == author)
    
    query = query.order_by(Post.posted_at.desc())
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Post.id))
    if author:
        count_query = count_query.where(Post.author_username == author)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return {
        "posts": [
            {
                "id": p.id,
                "post_id": p.post_id,
                "author_username": p.author_username,
                "author_display_name": p.author_display_name,
                "content": p.content,
                "likes": p.likes,
                "retweets": p.retweets,
                "replies": p.replies,
                "views": p.views,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                "ai_description": p.ai_description,
                "ai_sentiment": p.ai_sentiment,
            }
            for p in posts
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/posts/{post_id}", tags=["Data"])
async def get_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific post by ID."""
    result = await db.execute(
        select(Post).where(Post.post_id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": post.id,
        "post_id": post.post_id,
        "author_username": post.author_username,
        "author_display_name": post.author_display_name,
        "content": post.content,
        "likes": post.likes,
        "retweets": post.retweets,
        "replies": post.replies,
        "views": post.views,
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "scraped_at": post.scraped_at.isoformat() if post.scraped_at else None,
        "ai_description": post.ai_description,
        "ai_topics": post.ai_topics,
        "ai_sentiment": post.ai_sentiment,
        "ai_entities": post.ai_entities,
        "has_media": post.has_media,
        "media_urls": post.media_urls,
    }


# ============== Statistics ==============

@router.get("/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get database statistics."""
    # Total posts
    posts_result = await db.execute(select(func.count(Post.id)))
    total_posts = posts_result.scalar() or 0
    
    # Total unique authors
    authors_result = await db.execute(
        select(func.count(func.distinct(Post.author_username)))
    )
    total_authors = authors_result.scalar() or 0
    
    # Total searches
    searches_result = await db.execute(select(func.count(SearchQuery.id)))
    total_searches = searches_result.scalar() or 0
    
    # Sentiment distribution
    sentiment_result = await db.execute(
        select(Post.ai_sentiment, func.count(Post.id))
        .group_by(Post.ai_sentiment)
    )
    sentiment_dist = {row[0] or "unknown": row[1] for row in sentiment_result.fetchall()}
    
    # Top authors
    authors_result = await db.execute(
        select(Post.author_username, func.count(Post.id).label("count"))
        .group_by(Post.author_username)
        .order_by(text("count DESC"))
        .limit(10)
    )
    top_authors = [
        {"username": row[0], "post_count": row[1]}
        for row in authors_result.fetchall()
    ]
    
    # Recent searches
    recent_result = await db.execute(
        select(SearchQuery)
        .order_by(SearchQuery.created_at.desc())
        .limit(10)
    )
    recent_searches = [
        {
            "query": sq.original_query,
            "intent": sq.intent,
            "result_count": sq.result_count,
            "created_at": sq.created_at.isoformat() if sq.created_at else None,
        }
        for sq in recent_result.scalars().all()
    ]
    
    return {
        "total_posts": total_posts,
        "total_authors": total_authors,
        "total_searches": total_searches,
        "sentiment_distribution": sentiment_dist,
        "top_authors": top_authors,
        "recent_searches": recent_searches,
    }


# ============== Health Check ==============

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system health."""
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Grok API
    try:
        grok = get_grok_client()
        if grok.api_key:
            grok_status = "configured"
        else:
            grok_status = "not_configured"
    except Exception as e:
        grok_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "grok_api": grok_status,
        "version": "1.0.0",
    }

