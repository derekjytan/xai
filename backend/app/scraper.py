"""X/Twitter post scraper with rate limiting."""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import get_settings
from .database import Post
from .grok_client import get_grok_client


class XScraper:
    """Scraper for X/Twitter posts with respectful rate limiting."""
    
    # Sample data to use when scraping is not possible
    # In production, this would be replaced with actual scraping or API access
    SAMPLE_POSTS = [
        {
            "post_id": "sample_1",
            "author_username": "elonmusk",
            "author_display_name": "Elon Musk",
            "content": "The thing I love most about X is the real-time nature of it. Breaking news happens here first, often by minutes or hours before traditional media picks it up.",
            "likes": 125000,
            "retweets": 15000,
            "replies": 8500,
            "views": 5000000,
            "posted_at": "2024-12-01T10:30:00Z"
        },
        {
            "post_id": "sample_2",
            "author_username": "OpenAI",
            "author_display_name": "OpenAI",
            "content": "Introducing GPT-4 Turbo with 128k context window. Now available in the API. Build more powerful applications with longer context and improved performance.",
            "likes": 45000,
            "retweets": 12000,
            "replies": 3200,
            "views": 2000000,
            "posted_at": "2024-11-15T14:00:00Z"
        },
        {
            "post_id": "sample_3",
            "author_username": "xaboratory",
            "author_display_name": "xAI",
            "content": "Grok is now available to all X Premium subscribers! Ask Grok anything - it has real-time access to information via the X platform and web search.",
            "likes": 35000,
            "retweets": 8000,
            "replies": 2100,
            "views": 1500000,
            "posted_at": "2024-11-20T09:00:00Z"
        },
        {
            "post_id": "sample_4",
            "author_username": "naval",
            "author_display_name": "Naval",
            "content": "The most important skill for getting rich is becoming a perpetual learner. You have to know how to learn anything you want to learn.",
            "likes": 28000,
            "retweets": 6500,
            "replies": 1200,
            "views": 800000,
            "posted_at": "2024-12-05T16:45:00Z"
        },
        {
            "post_id": "sample_5",
            "author_username": "paulg",
            "author_display_name": "Paul Graham",
            "content": "The best startup ideas are things the founders want for themselves. The reason is simple: if you want something, there's a good chance others do too.",
            "likes": 18000,
            "retweets": 4200,
            "replies": 850,
            "views": 600000,
            "posted_at": "2024-12-03T11:20:00Z"
        },
        {
            "post_id": "sample_6",
            "author_username": "karpathy",
            "author_display_name": "Andrej Karpathy",
            "content": "The hottest new programming language is English. With LLMs, you can now describe what you want in plain language and get working code. The barrier to entry for programming has never been lower.",
            "likes": 42000,
            "retweets": 9500,
            "replies": 2800,
            "views": 1800000,
            "posted_at": "2024-11-28T13:15:00Z"
        },
        {
            "post_id": "sample_7",
            "author_username": "ylecun",
            "author_display_name": "Yann LeCun",
            "content": "Auto-regressive LLMs are not the path to AGI. We need architectures that can plan, reason about the physical world, and have persistent memory. Current LLMs are just very sophisticated pattern matchers.",
            "likes": 15000,
            "retweets": 3800,
            "replies": 2100,
            "views": 500000,
            "posted_at": "2024-12-02T08:30:00Z"
        },
        {
            "post_id": "sample_8",
            "author_username": "sama",
            "author_display_name": "Sam Altman",
            "content": "AI will be the most transformative technology in human history. But we need to get safety right. At OpenAI, we're committed to developing AGI that benefits all of humanity.",
            "likes": 55000,
            "retweets": 11000,
            "replies": 4500,
            "views": 2500000,
            "posted_at": "2024-11-25T15:00:00Z"
        },
        {
            "post_id": "sample_9",
            "author_username": "elonmusk",
            "author_display_name": "Elon Musk",
            "content": "Grok 2 is coming soon. It will be significantly more capable with improved reasoning and real-time information access. The future of AI assistants is here.",
            "likes": 180000,
            "retweets": 25000,
            "replies": 12000,
            "views": 8000000,
            "posted_at": "2024-12-08T12:00:00Z"
        },
        {
            "post_id": "sample_10",
            "author_username": "github",
            "author_display_name": "GitHub",
            "content": "GitHub Copilot now supports multi-file editing! Work across your entire codebase with AI assistance. Available today for all Copilot users.",
            "likes": 22000,
            "retweets": 5500,
            "replies": 1800,
            "views": 900000,
            "posted_at": "2024-12-06T10:00:00Z"
        },
        {
            "post_id": "sample_11",
            "author_username": "lexfridman",
            "author_display_name": "Lex Fridman",
            "content": "Just finished a 4-hour conversation with Elon Musk about Mars, AI, consciousness, and the future of humanity. This might be the most important podcast I've ever done. Episode drops tomorrow.",
            "likes": 65000,
            "retweets": 8500,
            "replies": 3200,
            "views": 2200000,
            "posted_at": "2024-12-07T22:30:00Z"
        },
        {
            "post_id": "sample_12",
            "author_username": "pmarca",
            "author_display_name": "Marc Andreessen",
            "content": "We are in the middle of the most important technology revolution since the internet. AI is going to touch every industry, every company, every job. Adapt or become irrelevant.",
            "likes": 32000,
            "retweets": 7200,
            "replies": 1900,
            "views": 1100000,
            "posted_at": "2024-12-04T14:45:00Z"
        },
        {
            "post_id": "sample_13",
            "author_username": "satloyd",
            "author_display_name": "Satya Nadella",
            "content": "Microsoft Copilot is now integrated across our entire product suite. From Windows to Office to Azure, AI assistance is everywhere. This is the new era of computing.",
            "likes": 28000,
            "retweets": 4800,
            "replies": 1500,
            "views": 950000,
            "posted_at": "2024-11-30T11:00:00Z"
        },
        {
            "post_id": "sample_14",
            "author_username": "xaboratory",
            "author_display_name": "xAI",
            "content": "We're hiring! Looking for exceptional ML engineers, researchers, and infrastructure engineers to help build the future of AI at xAI. Join us in making AGI a reality.",
            "likes": 12000,
            "retweets": 3500,
            "replies": 850,
            "views": 450000,
            "posted_at": "2024-12-09T09:00:00Z"
        },
        {
            "post_id": "sample_15",
            "author_username": "ID_AA_Carmack",
            "author_display_name": "John Carmack",
            "content": "I've been working on AGI for over a year now. The progress in reasoning capabilities over the last few months has been remarkable. We're closer than most people think.",
            "likes": 38000,
            "retweets": 6200,
            "replies": 2400,
            "views": 1300000,
            "posted_at": "2024-12-05T19:30:00Z"
        },
        {
            "post_id": "sample_16",
            "author_username": "naval",
            "author_display_name": "Naval",
            "content": "AI won't replace humans, but humans using AI will replace humans not using AI. Learn to leverage these tools or get left behind.",
            "likes": 45000,
            "retweets": 11000,
            "replies": 2100,
            "views": 1600000,
            "posted_at": "2024-12-06T08:15:00Z"
        },
        {
            "post_id": "sample_17",
            "author_username": "GoogleAI",
            "author_display_name": "Google AI",
            "content": "Introducing Gemini 2.0 - our most capable AI model yet. With native multimodality, improved reasoning, and enhanced safety. Available now through Google AI Studio.",
            "likes": 52000,
            "retweets": 13000,
            "replies": 3800,
            "views": 2800000,
            "posted_at": "2024-12-04T17:00:00Z"
        },
        {
            "post_id": "sample_18",
            "author_username": "balaborwi",
            "author_display_name": "Balaji Srinivasan",
            "content": "The network state is coming. Decentralized communities organized around shared values, enabled by blockchain and AI. This is the future of human organization.",
            "likes": 15000,
            "retweets": 4200,
            "replies": 1100,
            "views": 520000,
            "posted_at": "2024-12-01T20:00:00Z"
        },
        {
            "post_id": "sample_19",
            "author_username": "paulg",
            "author_display_name": "Paul Graham",
            "content": "The best essays are explorations, not presentations. You start with a question and see where it leads. That's why writing is thinking.",
            "likes": 21000,
            "retweets": 5800,
            "replies": 920,
            "views": 720000,
            "posted_at": "2024-12-07T10:45:00Z"
        },
        {
            "post_id": "sample_20",
            "author_username": "karpathy",
            "author_display_name": "Andrej Karpathy",
            "content": "LLMs are essentially knowledge compression algorithms. They compress the internet into a model that can generate relevant outputs. The question is: what knowledge gets lost in compression?",
            "likes": 35000,
            "retweets": 8200,
            "replies": 2500,
            "views": 1400000,
            "posted_at": "2024-12-08T16:20:00Z"
        },
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.delay = self.settings.scrape_delay_seconds
        self.max_posts = self.settings.max_posts_per_account
        self.grok = get_grok_client()
        self._last_request_time = 0
        
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def scrape_account(
        self,
        username: str,
        db: AsyncSession,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape posts from an X account.
        
        Note: Due to X's API restrictions, this uses sample data.
        In production, you would use the X API or authorized scraping.
        """
        limit = limit or self.max_posts
        
        # Filter sample posts by username (case-insensitive)
        user_posts = [
            p for p in self.SAMPLE_POSTS 
            if p["author_username"].lower() == username.lower()
        ][:limit]
        
        saved_posts = []
        for post_data in user_posts:
            saved = await self._save_post(post_data, db)
            if saved:
                saved_posts.append(saved)
            await self._rate_limit()
        
        return saved_posts
    
    async def load_sample_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Load all sample posts into the database."""
        saved_posts = []
        
        for post_data in self.SAMPLE_POSTS:
            saved = await self._save_post(post_data, db)
            if saved:
                saved_posts.append(saved)
        
        await db.commit()
        return saved_posts
    
    async def _save_post(
        self,
        post_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Save a post to the database with AI-generated metadata."""
        
        # Check if post already exists
        existing = await db.execute(
            select(Post).where(Post.post_id == post_data["post_id"])
        )
        if existing.scalar_one_or_none():
            return None
        
        # Generate AI metadata
        try:
            metadata = await self.grok.generate_post_metadata(
                post_data["content"],
                post_data["author_username"]
            )
        except Exception as e:
            print(f"Error generating metadata: {e}")
            metadata = {
                "description": post_data["content"][:200],
                "topics": [],
                "sentiment": "neutral",
                "entities": [],
                "search_tokens": ""
            }
        
        # Parse posted_at
        posted_at = None
        if post_data.get("posted_at"):
            try:
                posted_at = datetime.fromisoformat(
                    post_data["posted_at"].replace("Z", "+00:00")
                )
            except:
                pass
        
        # Handle search_tokens - might be list or string
        search_tokens = metadata.get("search_tokens", "")
        if isinstance(search_tokens, list):
            search_tokens = " ".join(search_tokens)
        
        # Generate embedding for semantic search
        embedding_json = None
        try:
            embedding = await self.grok.get_single_embedding(post_data["content"])
            if embedding:
                embedding_json = json.dumps(embedding)
        except Exception as e:
            print(f"Error generating embedding: {e}")
        
        # Create post record
        post = Post(
            post_id=post_data["post_id"],
            author_username=post_data["author_username"],
            author_display_name=post_data.get("author_display_name"),
            content=post_data["content"],
            likes=post_data.get("likes", 0),
            retweets=post_data.get("retweets", 0),
            replies=post_data.get("replies", 0),
            views=post_data.get("views", 0),
            posted_at=posted_at,
            ai_description=metadata.get("description"),
            ai_topics=json.dumps(metadata.get("topics", [])),
            ai_sentiment=metadata.get("sentiment"),
            ai_entities=json.dumps(metadata.get("entities", [])),
            search_tokens=search_tokens,
            has_media=0,
            media_urls="[]",
            embedding=embedding_json
        )
        
        db.add(post)
        
        return {
            "post_id": post.post_id,
            "author_username": post.author_username,
            "content": post.content,
            "ai_metadata": metadata,
            "has_embedding": embedding_json is not None
        }
    
    async def add_custom_post(
        self,
        post_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Add a custom post to the database."""
        return await self._save_post(post_data, db)


def get_scraper() -> XScraper:
    """Get scraper instance."""
    return XScraper()

