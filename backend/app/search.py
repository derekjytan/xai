"""Search service with token-based retrieval and Grok intelligence."""

import json
import re
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, desc, asc, func
from datetime import datetime

from .database import Post, SearchQuery
from .grok_client import get_grok_client


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


class SearchService:
    """Intelligent search service combining FTS5, vector search, and Grok."""
    
    def __init__(self):
        self.grok = get_grok_client()
    
    async def search(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        author_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sentiment_filter: Optional[str] = None,
        include_summary: bool = True,
        enhance_query: bool = True,
        search_mode: str = "hybrid",  # "keyword", "semantic", or "hybrid"
    ) -> Dict[str, Any]:
        """
        Perform intelligent search with Grok enhancement.
        
        Args:
            query: User search query
            db: Database session
            limit: Max results to return
            offset: Pagination offset
            sort_by: Sort field (relevance, date, likes, retweets, views)
            sort_order: Sort direction (asc, desc)
            author_filter: Filter by author username
            date_from: Filter posts after this date
            date_to: Filter posts before this date
            sentiment_filter: Filter by sentiment
            include_summary: Whether to generate AI summary
            enhance_query: Whether to use Grok for query enhancement
        
        Returns:
            Search results with metadata and optional summary
        """
        # Step 1: Enhance query with Grok
        query_analysis = None
        search_query = query
        
        if enhance_query:
            try:
                query_analysis = await self.grok.enhance_query(query)
                # Use enhanced query for search
                enhanced = query_analysis.get("enhanced_query", query)
                keywords = query_analysis.get("keywords", [])
                expanded = query_analysis.get("expanded_terms", [])
                
                # Build comprehensive search query
                all_terms = [enhanced] + keywords + expanded
                search_query = " OR ".join(f'"{term}"' for term in all_terms if term)
            except Exception as e:
                print(f"Query enhancement error: {e}")
                query_analysis = {"error": str(e)}
        
        # Step 2: Perform search based on mode
        posts = []
        total_count = 0
        
        if search_mode == "semantic":
            # Pure semantic search using embeddings
            posts, total_count = await self._vector_search(
                query=query,
                db=db,
                limit=limit,
                offset=offset,
                author_filter=author_filter,
                sentiment_filter=sentiment_filter,
            )
        elif search_mode == "keyword":
            # Pure keyword search using FTS5
            posts, total_count = await self._fts_search(
                search_query=search_query,
                original_query=query,
                db=db,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
                author_filter=author_filter,
                date_from=date_from,
                date_to=date_to,
                sentiment_filter=sentiment_filter,
            )
        else:
            # Hybrid search: combine FTS5 + vector similarity
            fts_posts, fts_count = await self._fts_search(
                search_query=search_query,
                original_query=query,
                db=db,
                limit=limit * 2,  # Get more to merge
                offset=0,
                sort_by=sort_by,
                sort_order=sort_order,
                author_filter=author_filter,
                date_from=date_from,
                date_to=date_to,
                sentiment_filter=sentiment_filter,
            )
            
            vector_posts, _ = await self._vector_search(
                query=query,
                db=db,
                limit=limit * 2,
                offset=0,
                author_filter=author_filter,
                sentiment_filter=sentiment_filter,
            )
            
            # Merge and deduplicate results
            posts, total_count = self._merge_results(
                fts_posts, vector_posts, limit, offset
            )
        
        # Step 3: Generate summary if requested
        summary = None
        if include_summary and posts:
            try:
                intent = query_analysis.get("intent") if query_analysis else None
                summary = await self.grok.summarize_results(query, posts, intent)
            except Exception as e:
                print(f"Summary generation error: {e}")
                summary = {"error": str(e)}
        
        # Step 4: Log search query
        await self._log_search(
            db=db,
            original_query=query,
            enhanced_query=search_query,
            intent=query_analysis.get("intent") if query_analysis else None,
            result_count=total_count,
        )
        
        return {
            "query": query,
            "enhanced_query": search_query if enhance_query else None,
            "query_analysis": query_analysis,
            "results": posts,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "summary": summary,
        }
    
    async def _fts_search(
        self,
        search_query: str,
        original_query: str,
        db: AsyncSession,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        author_filter: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        sentiment_filter: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Perform FTS5 full-text search with filters."""
        
        # Escape special FTS5 characters
        fts_query = self._prepare_fts_query(search_query)
        
        # Build the query
        # First, try FTS match
        try:
            # FTS5 search query
            fts_sql = text("""
                SELECT p.*, 
                       bm25(posts_fts) as relevance_score
                FROM posts p
                JOIN posts_fts ON p.id = posts_fts.rowid
                WHERE posts_fts MATCH :query
            """)
            
            # Add filters
            filters = []
            params = {"query": fts_query}
            
            if author_filter:
                filters.append("p.author_username = :author")
                params["author"] = author_filter
            
            if date_from:
                filters.append("p.posted_at >= :date_from")
                params["date_from"] = date_from
            
            if date_to:
                filters.append("p.posted_at <= :date_to")
                params["date_to"] = date_to
            
            if sentiment_filter:
                filters.append("p.ai_sentiment = :sentiment")
                params["sentiment"] = sentiment_filter
            
            # Build full query
            base_query = """
                SELECT p.id, p.post_id, p.author_username, p.author_display_name,
                       p.content, p.likes, p.retweets, p.replies, p.views,
                       p.posted_at, p.scraped_at, p.ai_description, p.ai_topics,
                       p.ai_sentiment, p.ai_entities, p.has_media, p.media_urls
                FROM posts p
                JOIN posts_fts ON p.id = posts_fts.rowid
                WHERE posts_fts MATCH :query
            """
            
            if filters:
                base_query += " AND " + " AND ".join(filters)
            
            # Sorting
            sort_column = {
                "relevance": "bm25(posts_fts)",
                "date": "p.posted_at",
                "likes": "p.likes",
                "retweets": "p.retweets",
                "views": "p.views",
            }.get(sort_by, "bm25(posts_fts)")
            
            order = "DESC" if sort_order.lower() == "desc" else "ASC"
            if sort_by == "relevance":
                order = "ASC"  # BM25 scores are negative, lower is better
            
            base_query += f" ORDER BY {sort_column} {order}"
            base_query += " LIMIT :limit OFFSET :offset"
            
            params["limit"] = limit
            params["offset"] = offset
            
            result = await db.execute(text(base_query), params)
            rows = result.fetchall()
            
            # Get total count
            count_query = """
                SELECT COUNT(*) FROM posts p
                JOIN posts_fts ON p.id = posts_fts.rowid
                WHERE posts_fts MATCH :query
            """
            if filters:
                count_query += " AND " + " AND ".join(filters)
            
            count_result = await db.execute(text(count_query), {"query": fts_query, **{k: v for k, v in params.items() if k not in ["limit", "offset"]}})
            total_count = count_result.scalar() or 0
            
        except Exception as e:
            print(f"FTS search error, falling back to LIKE: {e}")
            # Fallback to LIKE search
            rows, total_count = await self._like_search(
                original_query, db, limit, offset, sort_by, sort_order,
                author_filter, date_from, date_to, sentiment_filter
            )
        
        # Format results
        posts = []
        for row in rows:
            # Handle dates - might be datetime objects or strings
            posted_at = row[9]
            if posted_at and hasattr(posted_at, 'isoformat'):
                posted_at = posted_at.isoformat()
            scraped_at = row[10]
            if scraped_at and hasattr(scraped_at, 'isoformat'):
                scraped_at = scraped_at.isoformat()
            
            post = {
                "id": row[0],
                "post_id": row[1],
                "author_username": row[2],
                "author_display_name": row[3],
                "content": row[4],
                "likes": row[5],
                "retweets": row[6],
                "replies": row[7],
                "views": row[8],
                "posted_at": posted_at,
                "scraped_at": scraped_at,
                "ai_description": row[11],
                "ai_topics": json.loads(row[12]) if row[12] else [],
                "ai_sentiment": row[13],
                "ai_entities": json.loads(row[14]) if row[14] else [],
                "has_media": bool(row[15]),
                "media_urls": json.loads(row[16]) if row[16] else [],
            }
            posts.append(post)
        
        return posts, total_count
    
    async def _like_search(
        self,
        query: str,
        db: AsyncSession,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        author_filter: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        sentiment_filter: Optional[str],
    ) -> Tuple[List, int]:
        """Fallback LIKE-based search."""
        
        conditions = ["(p.content LIKE :query OR p.ai_description LIKE :query OR p.author_username LIKE :query)"]
        params = {"query": f"%{query}%"}
        
        if author_filter:
            conditions.append("p.author_username = :author")
            params["author"] = author_filter
        
        if date_from:
            conditions.append("p.posted_at >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            conditions.append("p.posted_at <= :date_to")
            params["date_to"] = date_to
        
        if sentiment_filter:
            conditions.append("p.ai_sentiment = :sentiment")
            params["sentiment"] = sentiment_filter
        
        where_clause = " AND ".join(conditions)
        
        sort_column = {
            "relevance": "p.likes",  # Approximate relevance with likes
            "date": "p.posted_at",
            "likes": "p.likes",
            "retweets": "p.retweets",
            "views": "p.views",
        }.get(sort_by, "p.likes")
        
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        
        sql = f"""
            SELECT p.id, p.post_id, p.author_username, p.author_display_name,
                   p.content, p.likes, p.retweets, p.replies, p.views,
                   p.posted_at, p.scraped_at, p.ai_description, p.ai_topics,
                   p.ai_sentiment, p.ai_entities, p.has_media, p.media_urls
            FROM posts p
            WHERE {where_clause}
            ORDER BY {sort_column} {order}
            LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = limit
        params["offset"] = offset
        
        result = await db.execute(text(sql), params)
        rows = result.fetchall()
        
        # Count
        count_sql = f"SELECT COUNT(*) FROM posts p WHERE {where_clause}"
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
        count_result = await db.execute(text(count_sql), count_params)
        total = count_result.scalar() or 0
        
        return rows, total
    
    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5, handling special characters."""
        # Remove or escape special FTS5 characters
        special_chars = ['*', '"', '(', ')', '-', '+', ':', '^', '~', "'"]
        clean_query = query
        
        for char in special_chars:
            clean_query = clean_query.replace(char, ' ')
        
        # Split into words and filter out FTS operators that got through
        stopwords = {'or', 'and', 'not', 'the', 'a', 'an', 'is', 'are', 'was', 'were'}
        words = [w.strip() for w in clean_query.split() 
                 if w.strip() and w.strip().lower() not in stopwords and len(w.strip()) > 1]
        
        if not words:
            return '""'  # Empty query
        
        # Use OR to match any word, limit to first 10 unique words
        unique_words = list(dict.fromkeys(words))[:10]
        return " OR ".join(unique_words)
    
    async def _vector_search(
        self,
        query: str,
        db: AsyncSession,
        limit: int,
        offset: int = 0,
        author_filter: Optional[str] = None,
        sentiment_filter: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Perform semantic search using embeddings."""
        
        # Get query embedding
        try:
            query_embedding = await self.grok.get_single_embedding(query)
        except Exception as e:
            print(f"Error getting query embedding: {e}")
            return [], 0
        
        if not query_embedding:
            return [], 0
        
        # Get all posts with embeddings
        sql = """
            SELECT id, post_id, author_username, author_display_name,
                   content, likes, retweets, replies, views,
                   posted_at, scraped_at, ai_description, ai_topics,
                   ai_sentiment, ai_entities, has_media, media_urls, embedding
            FROM posts
            WHERE embedding IS NOT NULL
        """
        
        params = {}
        if author_filter:
            sql += " AND author_username = :author"
            params["author"] = author_filter
        if sentiment_filter:
            sql += " AND ai_sentiment = :sentiment"
            params["sentiment"] = sentiment_filter
        
        result = await db.execute(text(sql), params)
        rows = result.fetchall()
        
        # Calculate similarity for each post
        scored_posts = []
        for row in rows:
            embedding_json = row[17]  # embedding column
            if not embedding_json:
                continue
            
            try:
                post_embedding = json.loads(embedding_json)
                similarity = cosine_similarity(query_embedding, post_embedding)
                
                # Handle dates
                posted_at = row[9]
                if posted_at and hasattr(posted_at, 'isoformat'):
                    posted_at = posted_at.isoformat()
                scraped_at = row[10]
                if scraped_at and hasattr(scraped_at, 'isoformat'):
                    scraped_at = scraped_at.isoformat()
                
                post = {
                    "id": row[0],
                    "post_id": row[1],
                    "author_username": row[2],
                    "author_display_name": row[3],
                    "content": row[4],
                    "likes": row[5],
                    "retweets": row[6],
                    "replies": row[7],
                    "views": row[8],
                    "posted_at": posted_at,
                    "scraped_at": scraped_at,
                    "ai_description": row[11],
                    "ai_topics": json.loads(row[12]) if row[12] else [],
                    "ai_sentiment": row[13],
                    "ai_entities": json.loads(row[14]) if row[14] else [],
                    "has_media": bool(row[15]),
                    "media_urls": json.loads(row[16]) if row[16] else [],
                    "similarity_score": similarity,
                }
                scored_posts.append(post)
            except Exception as e:
                print(f"Error processing embedding for post {row[1]}: {e}")
                continue
        
        # Sort by similarity (highest first)
        scored_posts.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        # Apply pagination
        total_count = len(scored_posts)
        paginated = scored_posts[offset:offset + limit]
        
        return paginated, total_count
    
    def _merge_results(
        self,
        fts_posts: List[Dict[str, Any]],
        vector_posts: List[Dict[str, Any]],
        limit: int,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Merge and deduplicate FTS5 and vector search results."""
        
        # Use dict to deduplicate by post_id
        merged = {}
        
        # Add FTS posts with position-based score
        for i, post in enumerate(fts_posts):
            post_id = post["post_id"]
            fts_score = 1.0 / (i + 1)  # Position-based score
            merged[post_id] = {
                **post,
                "fts_rank": i,
                "combined_score": fts_score,
            }
        
        # Add/update with vector posts
        for i, post in enumerate(vector_posts):
            post_id = post["post_id"]
            vector_score = post.get("similarity_score", 0)
            
            if post_id in merged:
                # Combine scores: average of normalized ranks
                fts_rank = merged[post_id].get("fts_rank", len(fts_posts))
                fts_score = 1.0 / (fts_rank + 1)
                combined = (fts_score + vector_score) / 2
                merged[post_id]["combined_score"] = combined
                merged[post_id]["similarity_score"] = vector_score
            else:
                merged[post_id] = {
                    **post,
                    "vector_rank": i,
                    "combined_score": vector_score * 0.8,  # Slightly lower weight for vector-only
                }
        
        # Sort by combined score
        sorted_posts = sorted(
            merged.values(),
            key=lambda x: x.get("combined_score", 0),
            reverse=True
        )
        
        # Apply pagination
        total_count = len(sorted_posts)
        paginated = sorted_posts[offset:offset + limit]
        
        return paginated, total_count
    
    async def _log_search(
        self,
        db: AsyncSession,
        original_query: str,
        enhanced_query: str,
        intent: Optional[str],
        result_count: int,
    ):
        """Log search query for analytics."""
        search_log = SearchQuery(
            original_query=original_query,
            enhanced_query=enhanced_query,
            intent=intent,
            result_count=result_count,
        )
        db.add(search_log)
    
    async def get_suggestions(
        self,
        partial_query: str,
        db: AsyncSession,
        limit: int = 5,
    ) -> List[str]:
        """Get search suggestions based on partial query."""
        # Get recent successful queries
        result = await db.execute(
            select(SearchQuery.original_query)
            .where(SearchQuery.original_query.ilike(f"%{partial_query}%"))
            .where(SearchQuery.result_count > 0)
            .order_by(desc(SearchQuery.created_at))
            .limit(limit)
        )
        
        suggestions = [row[0] for row in result.fetchall()]
        return list(set(suggestions))[:limit]
    
    async def answer_question(
        self,
        question: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Answer a question using search results and Grok.
        """
        # First, search for relevant posts
        search_results = await self.search(
            query=question,
            db=db,
            limit=15,
            include_summary=False,
            enhance_query=True,
        )
        
        posts = search_results.get("results", [])
        
        if not posts:
            return {
                "question": question,
                "answer": "I couldn't find any relevant posts to answer your question.",
                "sources": [],
                "query_analysis": search_results.get("query_analysis"),
            }
        
        # Use Grok to answer
        answer = await self.grok.answer_question(question, posts)
        
        return {
            "question": question,
            "answer": answer,
            "sources": posts[:5],
            "query_analysis": search_results.get("query_analysis"),
        }


def get_search_service() -> SearchService:
    """Get search service instance."""
    return SearchService()

