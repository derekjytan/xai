# 🔍 Grok Search

**Intelligent X/Twitter Search Powered by Grok**

A full-stack search system that leverages xAI's Grok API to provide intelligent discovery and retrieval of X/Twitter posts. Built for the xAI Technical Assessment.

![Grok Search](https://img.shields.io/badge/Powered%20by-Grok-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-teal)

## ✨ Features

### 🧠 Intelligent Query Processing
- **Query Enhancement**: Grok analyzes and improves search queries
- **Intent Recognition**: Understands user intent (find_opinions, find_news, etc.)
- **Query Expansion**: Automatically expands queries with related terms

### 🔎 Token-Based Retrieval
- **Full-Text Search**: SQLite FTS5 for fast, accurate text search
- **Boolean Operators**: Support for AND, OR, NOT queries
- **Filtering**: Filter by author, sentiment, date range

### 📝 AI-Generated Content Analysis
- **Post Descriptions**: Auto-generated summaries for each post
- **Topic Extraction**: Identifies key themes and topics
- **Sentiment Analysis**: Classifies posts as positive/negative/neutral/mixed
- **Entity Recognition**: Extracts people, companies, products

### 💬 Question Answering
- Ask natural language questions about the posts
- Grok synthesizes answers from search results
- Sources are cited for transparency

### 📊 Result Summarization
- AI-generated summaries of search results
- Key insights and themes across posts
- Suggested related queries

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Grok API Key from [console.x.ai](https://console.x.ai)

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/grok-search.git
cd grok-search

# Create environment file
echo "XAI_API_KEY=your_api_key_here" > .env
```

### 2. Run with Docker

```bash
# Build and start
docker-compose up --build

# The app will be available at http://localhost:8000
```

### 3. Load Sample Data

1. Open http://localhost:8000 in your browser
2. Click "Load Sample Posts" to populate the database
3. Start searching!

## 🛠️ Local Development

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export XAI_API_KEY=your_api_key_here

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (proxies to backend on :8000)
npm run dev
```

Visit http://localhost:3000 for frontend with hot reload.

## 📡 API Endpoints

### Search

```bash
# Simple search
GET /api/search?q=AI announcements

# Advanced search with filters
GET /api/search?q=startup advice&sort_by=likes&sentiment=positive&author=naval

# POST for complex queries
POST /api/search
{
  "query": "What are tech leaders saying about AGI?",
  "limit": 20,
  "sort_by": "relevance",
  "include_summary": true,
  "enhance_query": true
}
```

### Question Answering

```bash
POST /api/ask
{
  "question": "What are the latest AI developments?"
}
```

### Data Management

```bash
# Load sample data
POST /api/scrape
{"load_sample": true}

# Add custom post
POST /api/posts
{
  "post_id": "unique_id",
  "author_username": "user",
  "content": "Post content here",
  "likes": 100
}

# List posts
GET /api/posts?limit=50&author=elonmusk
```

### Statistics

```bash
GET /api/stats
```

### Health Check

```bash
GET /api/health
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                  React + Vite + Tailwind                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Routes    │  │   Search    │  │    Grok Client      │  │
│  │   (API)     │──│   Service   │──│   (Query/Summary)   │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────────┘  │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              SQLite + FTS5 Database                  │    │
│  │   Posts │ Metadata │ Search Index │ Query Logs       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       Grok API                               │
│            Query Enhancement │ Content Analysis              │
│            Summarization │ Question Answering                │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
grok-search/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── config.py        # Settings management
│   │   ├── database.py      # SQLAlchemy models & FTS5
│   │   ├── grok_client.py   # Grok API integration
│   │   ├── search.py        # Search service
│   │   ├── scraper.py       # Data collection
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── routes.py        # API endpoints
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── api.ts           # API client
│   │   ├── types.ts         # TypeScript types
│   │   └── index.css        # Tailwind styles
│   ├── package.json
│   └── vite.config.ts
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `XAI_API_KEY` | Your Grok API key | Yes |
| `DATABASE_URL` | SQLite database path | No (defaults to `./grok_search.db`) |
| `DEBUG` | Enable debug mode | No (defaults to `true`) |
| `HOST` | Server host | No (defaults to `0.0.0.0`) |
| `PORT` | Server port | No (defaults to `8000`) |

## 🎯 Example Queries

### Search Queries
- `"AI announcements from tech leaders"`
- `"startup advice and entrepreneurship tips"`
- `"machine learning developments"`
- `"what's new in AI"`

### Questions to Ask
- `"What are people saying about AGI?"`
- `"What startup advice do founders share?"`
- `"What AI tools are being announced?"`

## 🔧 Troubleshooting

### Grok API Issues

1. **"Grok Not Configured"**: Ensure `XAI_API_KEY` is set correctly
2. **Rate Limiting**: The app includes retry logic, but wait a moment if you hit limits
3. **API Errors**: Check the console for detailed error messages

### Database Issues

1. **Empty Results**: Load sample data first via the UI or API
2. **Search Errors**: The app falls back to LIKE search if FTS5 fails

### Docker Issues

1. **Build Failures**: Ensure Docker has enough memory (4GB+ recommended)
2. **Port Conflicts**: Change the port mapping in `docker-compose.yml`

## 📝 API Rate Limits

- Search: Uses Grok for query enhancement and summarization
- Each search makes 2-3 Grok API calls (query enhancement, summarization)
- Question answering makes 1-2 calls
- Consider setting `enhance_query=false` or `include_summary=false` to reduce API usage

## 🚧 Future Improvements

- [ ] Embedding-based semantic search
- [ ] Real-time X/Twitter API integration
- [ ] User authentication
- [ ] Saved searches and bookmarks
- [ ] Export functionality
- [ ] More advanced filtering options

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Grok](https://x.ai) by xAI
- FastAPI for the excellent web framework
- React + Vite for the frontend
- Tailwind CSS for styling

