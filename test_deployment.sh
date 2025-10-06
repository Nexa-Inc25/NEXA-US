#!/bin/bash

echo "Testing NEXA deployment..."
URL="https://nexa-ui.onrender.com"

# Test if service is responding
echo "Checking service health..."
curl -I $URL 2>/dev/null | head -n 1

# If using FastAPI
echo "Testing API health endpoint..."
curl -s $URL/health | python -m json.tool

# If using Streamlit
echo "Testing Streamlit UI..."
curl -s $URL | grep -q "streamlit" && echo "✅ Streamlit UI detected" || echo "❌ Not Streamlit"

echo "Done!"
