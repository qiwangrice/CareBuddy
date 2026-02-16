#!/bin/bash
# Start CareBuddy Frontend and Backend

echo "========================================"
echo "CareBuddy: Medical Analysis System"
echo "========================================"
echo ""

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first."
    echo "   Run: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
poetry install --no-root

# Start backend server
echo ""
echo "🚀 Starting Backend API Server..."
echo "   Backend: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""

cd backend
poetry run python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo ""
echo "✅ Backend started (PID: $BACKEND_PID)"
echo ""

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start"
        kill $BACKEND_PID
        exit 1
    fi
    sleep 1
done

echo ""
echo "========================================"
echo "🎉 CareBuddy is Ready!"
echo "========================================"
echo ""
echo "Frontend: http://localhost:8080"
echo "Backend API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "To serve the frontend, run in another terminal:"
echo "  cd frontend"
echo "  python -m http.server 8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Keep the backend running
wait $BACKEND_PID
