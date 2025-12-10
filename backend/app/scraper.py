"""X/Twitter post scraper with real data collection and rate limiting.

Uses Nitter instances (privacy-friendly Twitter frontends) to fetch real posts.
Falls back to sample data if scraping fails.
"""

import asyncio
import json
import re
import xml.etree.ElementTree as ET
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
    """Scraper for X/Twitter posts using Nitter instances with rate limiting.
    
    Note: Many Nitter instances stopped working in Jan 2024 when Twitter
    discontinued guest accounts. This scraper tries multiple instances
    and falls back to sample data if scraping fails.
    """
    
    # Nitter instances to try (ordered by reliability as of late 2024)
    NITTER_INSTANCES = [
        "https://nitter.poast.org",
        "https://nitter.cz",
        "https://nitter.privacydev.net", 
        "https://nitter.net",
        "https://nitter.1d4.us",
    ]
    
    # Popular tech accounts to scrape
    POPULAR_ACCOUNTS = [
        "elonmusk",
        "sama",  # Sam Altman
        "karpathy",
        "naval",
        "paulg",
        "ylecun",
        "demaborwski",
        "lexfridman",
        "OpenAI",
        "xaboratory",  # xAI
    ]
    
    # Minimal fallback sample data (used only if JSON file unavailable)
    # Main data is in backend/data/sample_posts.json (100 posts)
    SAMPLE_POSTS = [
        {
            "post_id": "fallback_1",
            "author_username": "elonmusk",
            "author_display_name": "Elon Musk",
            "content": "Grok 2 is coming soon. The future of AI assistants is here.",
            "likes": 180000, "retweets": 25000, "replies": 12000, "views": 8000000,
            "posted_at": "2024-12-08T12:00:00Z"
        },
        {
            "post_id": "fallback_2",
            "author_username": "sama",
            "author_display_name": "Sam Altman",
            "content": "AI will be the most transformative technology in human history.",
            "likes": 85000, "retweets": 18000, "replies": 5200, "views": 4200000,
            "posted_at": "2024-12-06T14:00:00Z"
        },
        {
            "post_id": "fallback_3",
            "author_username": "karpathy",
            "author_display_name": "Andrej Karpathy",
            "content": "The hottest new programming language is English. LLMs changed everything.",
            "likes": 42000, "retweets": 9500, "replies": 2800, "views": 1800000,
            "posted_at": "2024-11-28T13:15:00Z"
        },
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.delay = self.settings.scrape_delay_seconds
        self.max_posts = self.settings.max_posts_per_account
        self.grok = get_grok_client()
        self._last_request_time = 0
        self._current_nitter_index = 0
        
    def _get_nitter_base(self) -> str:
        """Get next Nitter instance in rotation."""
        base = self.NITTER_INSTANCES[self._current_nitter_index]
        self._current_nitter_index = (self._current_nitter_index + 1) % len(self.NITTER_INSTANCES)
        return base
        
    async def _rate_limit(self):
        """Enforce rate limiting between requests (respectful scraping)."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def _fetch_rss(self, username: str) -> Optional[str]:
        """Fetch RSS feed for a user from Nitter."""
        for _ in range(len(self.NITTER_INSTANCES)):
            nitter_base = self._get_nitter_base()
            try:
                await self._rate_limit()
                async with httpx.AsyncClient(timeout=15.0) as client:
                    # Try RSS feed
                    url = f"{nitter_base}/{username}/rss"
                    response = await client.get(url, follow_redirects=True)
                    if response.status_code == 200:
                        return response.text
            except Exception as e:
                print(f"Nitter {nitter_base} failed for {username}: {e}")
                continue
        return None
    
    async def _fetch_html(self, username: str) -> Optional[str]:
        """Fetch HTML page for a user from Nitter."""
        for _ in range(len(self.NITTER_INSTANCES)):
            nitter_base = self._get_nitter_base()
            try:
                await self._rate_limit()
                async with httpx.AsyncClient(timeout=15.0) as client:
                    url = f"{nitter_base}/{username}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (compatible; GrokSearchBot/1.0)"
                    }
                    response = await client.get(url, headers=headers, follow_redirects=True)
                    if response.status_code == 200:
                        return response.text
            except Exception as e:
                print(f"Nitter HTML {nitter_base} failed for {username}: {e}")
                continue
        return None
    
    def _parse_rss(self, rss_content: str, username: str) -> List[Dict[str, Any]]:
        """Parse RSS feed content into post data."""
        posts = []
        try:
            root = ET.fromstring(rss_content)
            # RSS 2.0 namespace handling
            channel = root.find('channel')
            if channel is None:
                return posts
            
            for item in channel.findall('item'):
                try:
                    title = item.find('title')
                    link = item.find('link')
                    description = item.find('description')
                    pub_date = item.find('pubDate')
                    guid = item.find('guid')
                    
                    content = ""
                    if description is not None and description.text:
                        # Clean HTML from description
                        soup = BeautifulSoup(description.text, 'html.parser')
                        content = soup.get_text(separator=' ', strip=True)
                    elif title is not None and title.text:
                        content = title.text
                    
                    if not content or len(content) < 10:
                        continue
                    
                    # Extract post ID from link or guid
                    post_id = None
                    if guid is not None and guid.text:
                        # Extract tweet ID from URL like /username/status/1234567890
                        match = re.search(r'/status/(\d+)', guid.text)
                        if match:
                            post_id = match.group(1)
                    if not post_id and link is not None and link.text:
                        match = re.search(r'/status/(\d+)', link.text)
                        if match:
                            post_id = match.group(1)
                    if not post_id:
                        post_id = f"rss_{hash(content)}"
                    
                    # Parse date
                    posted_at = None
                    if pub_date is not None and pub_date.text:
                        try:
                            # RSS date format: "Mon, 09 Dec 2024 15:30:00 GMT"
                            from email.utils import parsedate_to_datetime
                            posted_at = parsedate_to_datetime(pub_date.text).isoformat()
                        except:
                            pass
                    
                    # Check for media
                    has_media = 'pic.twitter.com' in content or 'video' in content.lower()
                    
                    posts.append({
                        "post_id": post_id,
                        "author_username": username,
                        "author_display_name": username,
                        "content": content[:1000],  # Limit content length
                        "likes": 0,  # Not available in RSS
                        "retweets": 0,
                        "replies": 0,
                        "views": 0,
                        "posted_at": posted_at,
                        "has_media": has_media,
                        "source": "rss"
                    })
                except Exception as e:
                    print(f"Error parsing RSS item: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error parsing RSS feed: {e}")
        
        return posts
    
    def _parse_html(self, html_content: str, username: str) -> List[Dict[str, Any]]:
        """Parse Nitter HTML page into post data."""
        posts = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all timeline items (tweets)
            timeline_items = soup.find_all('div', class_='timeline-item')
            
            for item in timeline_items:
                try:
                    # Get tweet content
                    content_div = item.find('div', class_='tweet-content')
                    if not content_div:
                        continue
                    content = content_div.get_text(strip=True)
                    if not content or len(content) < 10:
                        continue
                    
                    # Get tweet link for ID
                    tweet_link = item.find('a', class_='tweet-link')
                    post_id = None
                    if tweet_link and tweet_link.get('href'):
                        match = re.search(r'/status/(\d+)', tweet_link['href'])
                        if match:
                            post_id = match.group(1)
                    if not post_id:
                        post_id = f"html_{hash(content)}"
                    
                    # Get stats if available
                    stats = {}
                    stat_container = item.find('div', class_='tweet-stats')
                    if stat_container:
                        for stat in stat_container.find_all('span', class_='tweet-stat'):
                            icon = stat.find('span', class_='icon-container')
                            value = stat.find('span', class_='tweet-stat-value')
                            if icon and value:
                                # Parse like, retweet, reply counts
                                icon_class = ' '.join(icon.get('class', []))
                                val = self._parse_stat_value(value.get_text(strip=True))
                                if 'heart' in icon_class or 'like' in icon_class:
                                    stats['likes'] = val
                                elif 'retweet' in icon_class:
                                    stats['retweets'] = val
                                elif 'comment' in icon_class or 'reply' in icon_class:
                                    stats['replies'] = val
                    
                    # Get timestamp
                    posted_at = None
                    time_elem = item.find('span', class_='tweet-date')
                    if time_elem:
                        a_tag = time_elem.find('a')
                        if a_tag and a_tag.get('title'):
                            try:
                                posted_at = datetime.strptime(
                                    a_tag['title'], 
                                    '%b %d, %Y · %I:%M %p %Z'
                                ).isoformat()
                            except:
                                pass
                    
                    # Get display name
                    display_name = username
                    fullname = item.find('a', class_='fullname')
                    if fullname:
                        display_name = fullname.get_text(strip=True)
                    
                    # Check for media
                    has_media = bool(item.find('div', class_='attachments'))
                    
                    posts.append({
                        "post_id": post_id,
                        "author_username": username,
                        "author_display_name": display_name,
                        "content": content[:1000],
                        "likes": stats.get('likes', 0),
                        "retweets": stats.get('retweets', 0),
                        "replies": stats.get('replies', 0),
                        "views": 0,
                        "posted_at": posted_at,
                        "has_media": has_media,
                        "source": "html"
                    })
                except Exception as e:
                    print(f"Error parsing tweet: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error parsing HTML: {e}")
        
        return posts
    
    def _parse_stat_value(self, value: str) -> int:
        """Parse stat value like '1.2K' or '15M' to integer."""
        if not value:
            return 0
        value = value.strip().upper()
        try:
            if 'K' in value:
                return int(float(value.replace('K', '')) * 1000)
            elif 'M' in value:
                return int(float(value.replace('M', '')) * 1000000)
            else:
                return int(value.replace(',', ''))
        except:
            return 0
    
    async def scrape_account(
        self,
        username: str,
        db: AsyncSession,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape posts from an X account.
        
        Tries real scraping via Nitter first, falls back to sample data.
        """
        limit = limit or self.max_posts
        posts = []
        
        # Try RSS first (faster, more reliable)
        print(f"Scraping @{username} via RSS...")
        rss_content = await self._fetch_rss(username)
        if rss_content:
            posts = self._parse_rss(rss_content, username)
            print(f"  Got {len(posts)} posts from RSS")
        
        # Try HTML if RSS failed or returned few posts
        if len(posts) < 3:
            print(f"Scraping @{username} via HTML...")
            html_content = await self._fetch_html(username)
            if html_content:
                html_posts = self._parse_html(html_content, username)
                # Deduplicate by post_id
                existing_ids = {p['post_id'] for p in posts}
                for p in html_posts:
                    if p['post_id'] not in existing_ids:
                        posts.append(p)
                print(f"  Got {len(html_posts)} posts from HTML")
        
        # Fall back to sample data if scraping failed (for demo/dev when X API not available)
        if not posts:
            print(f"  Using sample data for @{username} (X API credentials required for live data)")
            posts = [
                p for p in self.SAMPLE_POSTS 
                if p["author_username"].lower() == username.lower()
            ]
        
        # Limit posts
        posts = posts[:limit]
        
        # Save posts to database
        saved_posts = []
        for post_data in posts:
            saved = await self._save_post(post_data, db)
            if saved:
                saved_posts.append(saved)
        
        await db.commit()
        return saved_posts
    
    async def scrape_popular_accounts(
        self,
        db: AsyncSession,
        accounts: Optional[List[str]] = None,
        limit_per_account: int = 10
    ) -> Dict[str, Any]:
        """Scrape posts from multiple popular accounts."""
        accounts = accounts or self.POPULAR_ACCOUNTS
        
        results = {
            "accounts_scraped": [],
            "total_posts": 0,
            "posts_by_account": {},
            "errors": []
        }
        
        for username in accounts:
            try:
                posts = await self.scrape_account(username, db, limit_per_account)
                results["accounts_scraped"].append(username)
                results["posts_by_account"][username] = len(posts)
                results["total_posts"] += len(posts)
                print(f"✓ @{username}: {len(posts)} posts")
            except Exception as e:
                results["errors"].append({"account": username, "error": str(e)})
                print(f"✗ @{username}: {e}")
            
            # Rate limit between accounts
            await self._rate_limit()
        
        return results
    
    async def load_sample_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Load sample posts from JSON file into the database."""
        import os
        saved_posts = []
        
        # Try to load from JSON file first (100 posts)
        json_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_posts.json')
        posts_to_load = []
        
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    posts_to_load = json.load(f)
                print(f"Loading {len(posts_to_load)} posts from sample_posts.json")
            except Exception as e:
                print(f"Error loading JSON file: {e}, falling back to inline data")
                posts_to_load = self.SAMPLE_POSTS
        else:
            print("sample_posts.json not found, using inline sample data")
            posts_to_load = self.SAMPLE_POSTS
        
        for post_data in posts_to_load:
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
        
        # Generate AI metadata using Grok
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
        
        # Handle search_tokens
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
        
        # Handle media
        has_media = post_data.get("has_media", False)
        if isinstance(has_media, bool):
            has_media = 1 if has_media else 0
        
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
            has_media=has_media,
            media_urls="[]",
            embedding=embedding_json
        )
        
        db.add(post)
        
        return {
            "post_id": post.post_id,
            "author_username": post.author_username,
            "content": post.content,
            "source": post_data.get("source", "sample"),
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
