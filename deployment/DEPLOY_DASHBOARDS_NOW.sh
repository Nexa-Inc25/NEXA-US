#!/bin/bash

echo "🚀 DEPLOYING ALL DASHBOARDS TO RENDER"
echo "======================================"

# Step 1: Update the web dashboard to use production API
echo "📝 Updating API URL in web dashboard..."

cat > nexa-core/apps/web/.env.production << 'EOF'
REACT_APP_API_URL=https://nexa-doc-analyzer-oct2025.onrender.com
REACT_APP_ENV=production
EOF

# Step 2: Create build script for web dashboard
cat > nexa-core/apps/web/package.json.update << 'EOF'
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "serve": "serve -s build -p $PORT",
    "start:prod": "npm run serve"
  }
}
EOF

# Step 3: Add serve dependency for production
cd nexa-core/apps/web
npm install serve --save

# Step 4: Create Dockerfile for web dashboard
cat > Dockerfile << 'EOF'
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy app files
COPY . .

# Build the React app
RUN npm run build

# Install serve globally
RUN npm install -g serve

# Expose port
EXPOSE 3000

# Start the app
CMD ["serve", "-s", "build", "-l", "3000"]
EOF

# Step 5: Commit and push
echo "📦 Committing changes..."
git add -A
git commit -m "Deploy GF dashboard to production"
git push origin main

echo ""
echo "✅ NOW GO TO RENDER AND:"
echo "========================"
echo ""
echo "1. Click 'New +' > 'Web Service'"
echo "2. Connect your GitHub repo"
echo "3. Settings:"
echo "   - Name: nexa-gf-dashboard"
echo "   - Root Directory: nexa-core/apps/web"
echo "   - Build Command: npm install && npm run build"
echo "   - Start Command: npm run serve"
echo ""
echo "4. Environment Variables:"
echo "   - REACT_APP_API_URL = https://nexa-doc-analyzer-oct2025.onrender.com"
echo "   - PORT = 3000"
echo ""
echo "5. Click 'Create Web Service'"
echo ""
echo "🎉 Your GF Dashboard will be LIVE at:"
echo "   https://nexa-gf-dashboard.onrender.com"
echo ""
echo "TOTAL TIME: 5 minutes"
