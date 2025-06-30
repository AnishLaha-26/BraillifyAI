#!/bin/bash

echo "🚀 Starting BraillifyAI with Braille API Server"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install API requirements if needed
echo "📦 Installing API requirements..."
pip install flask flask-cors requests

# Start Braille API server in background
echo "🔤 Starting Braille API server on port 5001..."
python braille_api.py &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Check if API is running
if curl -s http://localhost:5001/health > /dev/null; then
    echo "✅ Braille API server is running"
else
    echo "❌ Failed to start Braille API server"
    kill $API_PID 2>/dev/null
    exit 1
fi

# Start main Flask app
echo "🌐 Starting main BraillifyAI app on port 5000..."
echo "📍 Access the app at: http://localhost:5000"
echo "📍 Braille API at: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $API_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start main app (this will block)
python run.py

# Cleanup if main app exits
cleanup
