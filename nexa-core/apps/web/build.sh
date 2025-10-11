#!/bin/bash
# Build script for NEXA Dashboard

echo "Building NEXA Dashboard..."

# Clean install dependencies
rm -rf node_modules package-lock.json
npm install --production=false

# Build the React app
npm run build

echo "Build complete!"
echo "Output in ./build directory"
echo "✅ Build complete!"
