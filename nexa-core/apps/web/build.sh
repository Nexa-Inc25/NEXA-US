#!/bin/bash
# Build script for Render deployment

echo "🚀 Starting dashboard build..."

# Install dependencies (without running parent postinstall)
echo "📦 Installing dependencies..."
npm ci --only=production 2>/dev/null || npm install

# Build the React app
echo "🔨 Building React app..."
npm run build

echo "✅ Build complete!"
