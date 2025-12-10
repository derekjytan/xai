"""Main FastAPI application for Grok Search."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .database import init_db
from .routes import router


# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    print("🚀 Starting Grok Search API...")
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down Grok Search API...")


# Create FastAPI app
app = FastAPI(
    title="Grok Search API",
    description="""
    🔍 **Grok-Powered Intelligent Search for X/Twitter Posts**
    
    This API enables intelligent discovery and retrieval of posts using Grok's
    advanced language understanding capabilities.
    
    ## Features
    
    - **Intelligent Query Processing**: Grok enhances your search queries with
      intent recognition and query expansion
    - **Token-Based Retrieval**: Fast full-text search using SQLite FTS5
    - **AI-Generated Summaries**: Get contextual summaries of search results
    - **Question Answering**: Ask questions and get answers based on posts
    - **Sentiment Analysis**: Posts are analyzed for sentiment and topics
    
    ## Quick Start
    
    1. Load sample data: `POST /api/scrape` with `{"load_sample": true}`
    2. Search posts: `GET /api/search?q=your query here`
    3. Ask questions: `POST /api/ask` with `{"question": "your question"}`
    
    ## Authentication
    
    Configure your Grok API key in the `.env` file:
    ```
    XAI_API_KEY=your_key_here
    ```
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")

# Serve static files if available (production build)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve frontend for all non-API routes."""
        # Check if it's a static file
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Grok Search API",
            "version": "1.0.0",
            "description": "Intelligent search for X/Twitter posts powered by Grok",
            "docs": "/docs",
            "health": "/api/health",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

