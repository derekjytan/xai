# 🔍 Grok Search - Example Queries

This document demonstrates the search capabilities of Grok Search with example queries and expected responses.

## Search Queries

### 1. Basic Search

**Query:** `AI announcements`

```bash
curl "http://localhost:8000/api/search?q=AI%20announcements"
```

**What it does:**
- Grok enhances the query to include related terms
- FTS5 searches through post content, descriptions, and topics
- Returns posts about AI announcements with AI-generated summaries

### 2. Intent-Based Search

**Query:** `What are people saying about AGI?`

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are people saying about AGI?", "include_summary": true}'
```

**What it does:**
- Grok recognizes this as a "find_opinions" intent
- Enhances query with terms like "artificial general intelligence", "opinions", "views"
- Summarizes the discourse around AGI from multiple posts

### 3. Filtered Search

**Query:** `startup advice` from a specific author

```bash
curl "http://localhost:8000/api/search?q=startup%20advice&author=naval&sentiment=positive"
```

**What it does:**
- Filters results to only show posts from @naval
- Further filters to positive sentiment posts
- Returns actionable startup advice

### 4. Sorted by Engagement

**Query:** `machine learning` sorted by likes

```bash
curl "http://localhost:8000/api/search?q=machine%20learning&sort_by=likes&sort_order=desc"
```

**What it does:**
- Finds ML-related posts
- Sorts by highest engagement (likes)
- Shows the most popular takes on ML

## Question Answering

### 1. Direct Question

**Question:** `What AI tools are being announced recently?`

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What AI tools are being announced recently?"}'
```

**Response includes:**
- A synthesized answer based on post content
- Source posts used for the answer
- The original query analysis

### 2. Opinion Question

**Question:** `What do investors think about AI startups?`

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What do investors think about AI startups?"}'
```

**What it does:**
- Searches for posts from investors (VCs, angels)
- Synthesizes their opinions on AI startups
- Cites specific posts as sources

## Data Management

### Load Sample Data

```bash
curl -X POST "http://localhost:8000/api/scrape" \
  -H "Content-Type: application/json" \
  -d '{"load_sample": true}'
```

### Add Custom Post

```bash
curl -X POST "http://localhost:8000/api/posts" \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "custom_1",
    "author_username": "testuser",
    "author_display_name": "Test User",
    "content": "This is a test post about artificial intelligence and its future.",
    "likes": 100,
    "retweets": 50,
    "views": 1000,
    "posted_at": "2024-12-10T10:00:00Z"
  }'
```

### Get Statistics

```bash
curl "http://localhost:8000/api/stats"
```

**Response:**
```json
{
  "total_posts": 20,
  "total_authors": 15,
  "total_searches": 5,
  "sentiment_distribution": {
    "positive": 8,
    "neutral": 10,
    "mixed": 2
  },
  "top_authors": [
    {"username": "elonmusk", "post_count": 3},
    {"username": "naval", "post_count": 2}
  ]
}
```

## Advanced Features

### Query Enhancement Example

When you search for `"AI"`, Grok might enhance it to:

```json
{
  "enhanced_query": "artificial intelligence AI machine learning",
  "intent": "find_information",
  "keywords": ["AI", "artificial intelligence"],
  "expanded_terms": ["machine learning", "neural networks", "deep learning"],
  "filters": {},
  "clarification_needed": false
}
```

### Search Summary Example

After a search, you get an AI-generated summary:

```json
{
  "summary": "The search results show active discussions about AI developments, with tech leaders announcing new models and capabilities.",
  "key_insights": [
    "Multiple major AI announcements in the past month",
    "Focus on improved reasoning capabilities",
    "Growing interest in AGI development"
  ],
  "themes": ["AI development", "Tech announcements", "Future predictions"],
  "notable_posts": [0, 3, 7],
  "suggested_queries": [
    "AGI timeline predictions",
    "AI safety concerns",
    "New AI model capabilities"
  ]
}
```

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Server error |

## Rate Limiting

- The API includes built-in rate limiting
- Grok API calls are made for:
  - Query enhancement (1 call per search)
  - Result summarization (1 call per search with summary)
  - Post metadata generation (1 call per new post)
  - Question answering (1 call per question)

To reduce API usage, set `enhance_query=false` and `include_summary=false`:

```bash
curl "http://localhost:8000/api/search?q=test&enhance_query=false&include_summary=false"
```

