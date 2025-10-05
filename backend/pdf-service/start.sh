#!/bin/bash
# Startup script for NEXA PDF Processing & AI Analysis Service

echo "🚀 Starting NEXA PDF Processing & AI Analysis Service"
echo "=================================================="

# Check Python version
python3 --version || python --version

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create data directory if it doesn't exist
mkdir -p ./data

# Set environment variables for local testing
export AUTH_ENABLED=false
export AUTH0_DOMAIN=dev-kbnx7pja3zpg0lud.us.auth0.com
export AUTH0_AUDIENCE=https://api.nexa.local

echo ""
echo "✅ Dependencies installed"
echo ""
echo "🔧 Configuration:"
echo "  - Auth: DISABLED (for local testing)"
echo "  - Port: 8000"
echo "  - Data: ./data/"
echo ""
echo "📊 Starting server..."
echo ""

# Start the service
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
