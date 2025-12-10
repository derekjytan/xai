"""Configuration settings for Grok Search API."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Grok API
    xai_api_key: str = ""
    xai_api_base: str = "https://api.x.ai/v1"
    xai_model: str = "grok-3-latest"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./grok_search.db"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # Scraper
    scrape_delay_seconds: float = 2.0
    max_posts_per_account: int = 100
    
    # Search
    default_search_limit: int = 20
    max_search_limit: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

