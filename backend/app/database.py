"""Database configuration and models for Grok Search."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Index, event
from datetime import datetime
from typing import AsyncGenerator

from .config import get_settings


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Post(Base):
    """Model representing a scraped X/Twitter post."""
    
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), unique=True, nullable=False, index=True)
    author_username = Column(String(255), nullable=False, index=True)
    author_display_name = Column(String(255))
    content = Column(Text, nullable=False)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    views = Column(Integer, default=0)
    
    # Timestamps
    posted_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # AI-generated metadata
    ai_description = Column(Text)
    ai_topics = Column(Text)  # JSON array as string
    ai_sentiment = Column(String(50))
    ai_entities = Column(Text)  # JSON array as string
    
    # Search optimization
    search_tokens = Column(Text)  # Tokenized content for FTS
    
    # Media
    has_media = Column(Integer, default=0)  # Boolean as int
    media_urls = Column(Text)  # JSON array as string
    
    # Embedding for semantic search
    embedding = Column(Text)  # JSON array of floats
    
    __table_args__ = (
        Index('idx_posted_at', 'posted_at'),
        Index('idx_author_posted', 'author_username', 'posted_at'),
    )


class PostFTS(Base):
    """Full-text search virtual table for posts."""
    
    __tablename__ = "posts_fts"
    
    rowid = Column(Integer, primary_key=True)
    content = Column(Text)
    author_username = Column(String(255))
    ai_description = Column(Text)
    ai_topics = Column(Text)
    search_tokens = Column(Text)


class SearchQuery(Base):
    """Model to track search queries for analytics."""
    
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_query = Column(Text, nullable=False)
    enhanced_query = Column(Text)
    intent = Column(String(100))
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database engine and session
settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables and FTS."""
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Create FTS5 virtual table if not exists
        await conn.execute(text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                content,
                author_username,
                ai_description,
                ai_topics,
                search_tokens,
                content='posts',
                content_rowid='id'
            );
            """
        ))
        
        # Create triggers to keep FTS in sync
        await conn.execute(text(
            """
            CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
                INSERT INTO posts_fts(rowid, content, author_username, ai_description, ai_topics, search_tokens)
                VALUES (new.id, new.content, new.author_username, new.ai_description, new.ai_topics, new.search_tokens);
            END;
            """
        ))
        
        await conn.execute(text(
            """
            CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, content, author_username, ai_description, ai_topics, search_tokens)
                VALUES ('delete', old.id, old.content, old.author_username, old.ai_description, old.ai_topics, old.search_tokens);
            END;
            """
        ))
        
        await conn.execute(text(
            """
            CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, content, author_username, ai_description, ai_topics, search_tokens)
                VALUES ('delete', old.id, old.content, old.author_username, old.ai_description, old.ai_topics, old.search_tokens);
                INSERT INTO posts_fts(rowid, content, author_username, ai_description, ai_topics, search_tokens)
                VALUES (new.id, new.content, new.author_username, new.ai_description, new.ai_topics, new.search_tokens);
            END;
            """
        ))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

