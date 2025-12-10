#!/bin/bash

# Grok Search - Local Development Start Script

set -e

echo "🚀 Starting Grok Search..."

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from example..."
    echo "XAI_API_KEY=" > .env
    echo "📝 Please edit .env and add your XAI_API_KEY"
    exit 1
fi

# Check if XAI_API_KEY is set
if ! grep -q "XAI_API_KEY=." .env 2>/dev/null; then
    echo "❌ XAI_API_KEY not set in .env file"
    echo "📝 Please add your Grok API key to .env"
    exit 1
fi

# Export environment variables
export $(grep -v '^#' .env | xargs)

# Start backend
echo "📦 Starting backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Grok Search is running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop..."

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

