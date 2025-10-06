#!/bin/bash

# Manual deploy to Render using API
# Get your API key from: https://dashboard.render.com/account/api-keys

echo "Manual Render Deployment Script"
echo "================================"

# Set your Render API key
read -p "Enter your Render API Key: " RENDER_API_KEY

# Your service ID (find in Render dashboard URL)
read -p "Enter your Render Service ID: " SERVICE_ID

echo "Triggering manual deploy..."

curl -X POST "https://api.render.com/v1/services/${SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": false}'

echo "Deploy triggered! Check dashboard for progress."
