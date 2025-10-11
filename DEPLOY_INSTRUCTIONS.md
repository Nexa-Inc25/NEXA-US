# NEXA Dashboard Deployment Instructions

## Web Dashboard Components Ready

The web dashboard for deployment to Render (https://nexa-dashboard.onrender.com) has been fully built with all necessary components:

### Components Created:

1. **General Foreman Dashboard** (`nexa-core/apps/web/src/pages/GeneralForemanDashboard.tsx`)
   - Overview with metrics and charts
   - Crews management with real-time status
   - Jobs queue with assignment functionality
   - Analytics with performance tracking

2. **Foreman Field View** (`nexa-core/apps/web/src/pages/ForemanFieldView.tsx`)
   - Job details with PM/notification numbers
   - Time tracking with modal forms
   - Safety compliance checklists
   - Photo documentation interface

3. **Authentication System**
   - Login page with role selection
   - Auth context for session management
   - Private routes for access control

4. **Styling**
   - Professional CSS with NEXA branding
   - Responsive layouts
   - Modal overlays
   - Clean card-based design

## Files Structure:
```
nexa-core/apps/web/
├── src/
│   ├── App.tsx                    # Main app with routing
│   ├── index.tsx                  # React entry point
│   ├── pages/
│   │   ├── GeneralForemanDashboard.tsx
│   │   ├── ForemanFieldView.tsx
│   │   └── Login.tsx
│   ├── contexts/
│   │   └── AuthContext.tsx
│   ├── components/
│   │   └── PrivateRoute.tsx
│   └── styles/
│       ├── global.css
│       ├── dashboard.css
│       ├── foreman.css
│       └── login.css
├── public/
│   └── index.html
├── package.json
├── tsconfig.json
└── build.sh
```

## Deployment Steps:

### Option 1: Deploy via Render Dashboard

1. **Login to Render**: https://dashboard.render.com
2. **Navigate to**: nexa-dashboard service
3. **Manual Deploy**: Click "Manual Deploy" → "Deploy latest commit"

### Option 2: Deploy via Git Push

```bash
# In the nexa-inc-mvp directory
git add .
git commit -m "Update web dashboard with GF and Foreman views"
git push origin main
```

Render will automatically detect the push and redeploy.

### Option 3: Deploy via Render CLI

```bash
# Install Render CLI if needed
npm install -g @render/cli

# Deploy
render deploy --service-id nexa-dashboard
```

## Environment Variables (Already Configured on Render):

- `REACT_APP_API_URL`: https://nexa-doc-analyzer-oct2025.onrender.com
- `REACT_APP_AUTH0_DOMAIN`: dev-kbnx7pja3zpg0lud.us.auth0.com
- `REACT_APP_AUTH0_CLIENT_ID`: glA8cdWZIAKvNUUjxd2XQRcwLI4HM2f1
- `REACT_APP_ENV`: production

## Build Configuration:

The `build.sh` script in `nexa-core/apps/web/` handles:
1. Installing dependencies
2. Building the React app
3. Creating production bundle

## Features Implemented:

### General Foreman Dashboard:
- **Live Metrics**: 6 KPI cards (Active Crews, Jobs Today, Infractions, On Time %, Budget Used, Safety Score)
- **Crew Management**: Real-time crew status, progress tracking, job assignments
- **Job Queue**: Priority-based sorting, PM/Notification numbers, cost estimates
- **Analytics**: Charts using Recharts library (crew performance, job distribution, weekly trends)

### Foreman Field View:
- **Current Job Display**: Full details with crew list, location, priority
- **Time Entry**: Modal form for logging hours with notes
- **Safety Checklist**: 4-point daily safety verification
- **Photo Upload**: Document capture interface
- **Status Updates**: Real-time job status changes

### Authentication:
- Role-based access (General Foreman, Foreman, Crew Member)
- Session management
- Protected routes

## Testing Locally Before Deploy:

```bash
cd nexa-core/apps/web
npm install
npm run build
npm run start
```

Visit http://localhost:3000 to test:
1. Login page with role selection
2. General Foreman Dashboard (all tabs)
3. Foreman Field View (all tabs)

## API Integration:

The dashboard connects to:
- **Backend API**: https://nexa-doc-analyzer-oct2025.onrender.com
- Currently using mock data for testing
- Real API calls ready to be activated by removing mock data

## Production URL:

Once deployed, the dashboard will be available at:
https://nexa-dashboard.onrender.com

## Troubleshooting:

If deployment fails:
1. Check Render logs: https://dashboard.render.com → nexa-dashboard → Logs
2. Verify all environment variables are set
3. Ensure build.sh has execute permissions: `chmod +x build.sh`
4. Check that package.json dependencies are correct

## Summary:

The web dashboard is fully built with:
- ✅ General Foreman Dashboard with 4 tabs
- ✅ Foreman Field View with 4 tabs  
- ✅ Authentication system
- ✅ Professional styling
- ✅ Mock data for testing
- ✅ API connection ready
- ✅ Deployment configuration

Ready for deployment to Render!
