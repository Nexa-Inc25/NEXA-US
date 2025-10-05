#!/bin/bash
# Startup script for NEXA AI Document Analyzer Pro
# Runs both FastAPI backend and Streamlit UI

echo "🚀 Starting NEXA AI Document Analyzer Pro"
echo "=========================================="

# Set environment variables
export PYTHONUNBUFFERED=1
export USE_POSTGRES=${USE_POSTGRES:-false}
export AUTH_ENABLED=${AUTH_ENABLED:-false}

# Check if running on Render
if [ -n "$RENDER" ]; then
    echo "✅ Running on Render.com"
    export USE_POSTGRES=true
    
    # Use Render's PORT for Streamlit
    PORT=${PORT:-8501}
    
    # Start Streamlit with embedded FastAPI
    echo "Starting Streamlit UI on port $PORT..."
    exec streamlit run app_complete.py \
        --server.port $PORT \
        --server.address 0.0.0.0 \
        --server.headless true \
        --server.enableCORS true
else
    echo "🏠 Running locally"
    
    # Start FastAPI in background
    echo "Starting FastAPI backend on port 8000..."
    uvicorn app_complete:app --host 0.0.0.0 --port 8000 --reload &
    FASTAPI_PID=$!
    
    # Wait for API to start
    sleep 3
    
    # Start Streamlit
    echo "Starting Streamlit UI on port 8501..."
    export API_URL=http://localhost:8000
    streamlit run app_complete.py \
        --server.port 8501 \
        --server.address 0.0.0.0
    
    # Cleanup on exit
    trap "kill $FASTAPI_PID" EXIT
fi
