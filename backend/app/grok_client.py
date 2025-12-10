"""Grok API client for intelligent search operations."""

import json
import httpx
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings


class GrokClient:
    """Client for interacting with Grok API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.xai_api_base
        self.api_key = self.settings.xai_api_key
        self.model = self.settings.xai_model
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Make a chat completion request to Grok API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def get_embeddings(
        self,
        texts: List[str],
        model: str = "v1"
    ) -> List[List[float]]:
        """
        Get embeddings for a list of texts.
        Tries xAI's embedding API first, falls back to local TF-IDF.
        """
        # Try xAI API first
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self._get_headers(),
                    json={
                        "input": texts,
                        "model": f"embedding-{model}",
                    },
                )
                response.raise_for_status()
                data = response.json()
                embeddings = sorted(data["data"], key=lambda x: x["index"])
                return [e["embedding"] for e in embeddings]
        except Exception as e:
            # Fall back to local embeddings
            from .embeddings import get_local_embedder
            embedder = get_local_embedder()
            return embedder.get_embeddings(texts)
    
    async def get_single_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        try:
            embeddings = await self.get_embeddings([text])
            return embeddings[0] if embeddings else []
        except Exception as e:
            # Fall back to local embeddings
            from .embeddings import get_local_embedder
            embedder = get_local_embedder()
            return embedder.get_embedding(text)
    
    async def enhance_query(self, query: str) -> Dict[str, Any]:
        """
        Use Grok to enhance and understand user search query.
        Returns enhanced query, intent, and expanded terms.
        """
        system_prompt = """You are a search query analyzer for X/Twitter posts. 
Analyze the user's query and return a JSON object with:
- "enhanced_query": An improved, more searchable version of the query
- "intent": The user's search intent (e.g., "find_opinions", "find_news", "find_tutorials", "find_discussions", "find_announcements")
- "keywords": A list of key search terms extracted
- "expanded_terms": Additional related terms to include in search
- "filters": Any implicit filters (e.g., {"date": "recent", "author": null})
- "clarification_needed": Boolean if query is ambiguous
- "clarification_question": Question to ask if clarification needed

Return ONLY valid JSON, no markdown or explanation."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this search query: {query}"}
        ]
        
        try:
            response = await self._chat_completion(messages, temperature=0.3)
            # Clean response if wrapped in markdown
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            # Fallback if parsing fails
            return {
                "enhanced_query": query,
                "intent": "general_search",
                "keywords": query.split(),
                "expanded_terms": [],
                "filters": {},
                "clarification_needed": False,
                "error": str(e)
            }
    
    async def generate_post_metadata(self, content: str, author: str) -> Dict[str, Any]:
        """
        Use Grok to generate rich metadata for a post.
        Returns description, topics, sentiment, and entities.
        """
        system_prompt = """You are a content analyzer for X/Twitter posts.
Analyze the post and return a JSON object with:
- "description": A brief, searchable description of the post (1-2 sentences)
- "topics": List of 3-5 main topics/themes
- "sentiment": One of "positive", "negative", "neutral", "mixed"
- "entities": List of named entities (people, companies, products, etc.)
- "content_type": One of "opinion", "news", "tutorial", "question", "announcement", "discussion", "humor", "other"
- "search_tokens": Additional keywords for searchability

Return ONLY valid JSON, no markdown or explanation."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Author: @{author}\n\nPost content:\n{content}"}
        ]
        
        try:
            response = await self._chat_completion(messages, temperature=0.3, max_tokens=512)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "description": content[:200],
                "topics": [],
                "sentiment": "neutral",
                "entities": [],
                "content_type": "other",
                "search_tokens": "",
                "error": str(e)
            }
    
    async def summarize_results(
        self,
        query: str,
        posts: List[Dict[str, Any]],
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use Grok to create an intelligent summary of search results.
        """
        # Format posts for context
        posts_context = "\n\n".join([
            f"[@{p.get('author_username', 'unknown')}]: {p.get('content', '')[:500]}"
            for p in posts[:10]  # Limit context size
        ])
        
        system_prompt = """You are a search results summarizer for X/Twitter posts.
Given a search query and matching posts, provide:
- "summary": A concise summary of what the search results show (2-3 sentences)
- "key_insights": List of 3-5 main takeaways from the results
- "themes": Common themes across the posts
- "notable_posts": List of 1-3 post indices that are most relevant/interesting
- "suggested_queries": 2-3 related queries the user might want to try

Return ONLY valid JSON, no markdown or explanation."""

        user_content = f"""Search Query: {query}
User Intent: {intent or 'general search'}

Matching Posts:
{posts_context}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        try:
            response = await self._chat_completion(messages, temperature=0.5, max_tokens=1024)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "summary": f"Found {len(posts)} posts matching your query.",
                "key_insights": [],
                "themes": [],
                "notable_posts": [],
                "suggested_queries": [],
                "error": str(e)
            }
    
    async def answer_question(self, query: str, posts: List[Dict[str, Any]]) -> str:
        """
        Use Grok to directly answer a question based on search results.
        """
        posts_context = "\n\n".join([
            f"[@{p.get('author_username', 'unknown')} - {p.get('posted_at', 'unknown date')}]: {p.get('content', '')}"
            for p in posts[:15]
        ])
        
        system_prompt = """You are an intelligent assistant that answers questions based on X/Twitter posts.
Use the provided posts to answer the user's question. Be concise and cite sources when possible.
If the posts don't contain enough information to answer, say so clearly."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {query}\n\nRelevant posts:\n{posts_context}"}
        ]
        
        return await self._chat_completion(messages, temperature=0.7, max_tokens=1024)


# Singleton instance
_grok_client: Optional[GrokClient] = None


def get_grok_client() -> GrokClient:
    """Get or create Grok client instance."""
    global _grok_client
    if _grok_client is None:
        _grok_client = GrokClient()
    return _grok_client

