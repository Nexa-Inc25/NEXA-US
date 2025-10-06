# NEXA App - EAS Build & Deployment Guide

## Overview
This guide covers the EAS build profiles configured for the NEXA Field Assistant app with AI document analyzer capabilities, including As-Built PDF generation and PG&E spec compliance checking.

## Build Profiles

### 1. Development Profile
**Purpose**: Internal testing with Expo development client
**Use Case**: Test AI spec learning, document uploads, As-Built generation on simulators/devices

```bash
# Build for iOS simulator (fast testing)
eas build --platform ios --profile development

# Install on simulator
tar -xvf your-build.tar.gz
xcrun simctl install booted YourApp.app
```

**Features**:
- iPad simulator support enabled
- Hot reload for rapid iteration
- Direct connection to local backend (http://192.168.1.176:4000)
- Test heavy features: PDF uploads, spec chunking/indexing, audit analysis

### 2. Preview Profile (TestFlight Beta)
**Purpose**: Beta testing with real foremen on iPads
**Use Case**: Validate repeal logic, confidence scoring, cross-references on actual job sites

```bash
# Build for TestFlight
eas build --platform ios --profile preview

# Submit to TestFlight
eas submit --platform ios --profile preview
```

**Features**:
- Internal distribution via TestFlight
- Remote credentials management
- Real-world testing of:
  - Large spec book uploads (100+ pages)
  - Audit analysis with true/repealable status
  - Confidence percentages and spec reasons
  - As-Built PDF generation per TD-2051P-10

### 3. Production Profile
**Purpose**: App Store release with full monetization
**Use Case**: Live deployment with freemium model for unlimited analyses

```bash
# Build for App Store
eas build --platform ios --profile production

# Submit to App Store
eas submit --platform ios --profile production
```

**Features**:
- Auto-increment build numbers
- iCloud entitlements for persistent AI data
- Optimized for performance (m-large resource class)
- Production backend connection

## Initial Setup

### 1. Install EAS CLI
```bash
npm install -g eas-cli
```

### 2. Initialize Project
```bash
cd mobile
eas init
eas whoami  # Verify logged in
```

### 3. Configure Credentials
```bash
# Set up iOS certificates and provisioning profiles
eas credentials --platform ios

# Select options:
# - Keychain: Let EAS manage
# - Push Key: Skip (unless using notifications)
# - Provisioning Profile: Auto-generate
```

### 4. Update Submit Configuration
Edit `eas.json` and replace placeholders:
```json
"submit": {
  "production": {
    "ios": {
      "appleId": "mike@nexa-usa.io",
      "ascAppId": "1234567890",  // From App Store Connect
      "appleTeamId": "ABCD1234"   // From Apple Developer portal
    }
  }
}
```

## Environment Configuration

### API Endpoints by Profile
Configure in `app.json` extra field:

```javascript
// Development (local testing)
"API_BASE_URL": "http://192.168.1.176:4000"

// Preview (staging on Render)
"API_BASE_URL": "https://nexa-api-staging.onrender.com"  

// Production (live on Render)
"API_BASE_URL": "https://nexa-api.onrender.com"
```

## Build Commands Reference

### Development Builds
```bash
# iOS Simulator
eas build --platform ios --profile development

# Android Emulator
eas build --platform android --profile development

# Both platforms
eas build --profile development
```

### Preview Builds (Beta)
```bash
# Build and auto-submit to TestFlight
eas build --platform ios --profile preview --auto-submit

# Manual submit after build
eas submit --platform ios --profile preview --id <build-id>
```

### Production Builds
```bash
# Build with auto-increment version
eas build --platform ios --profile production

# Submit to App Store Review
eas submit --platform ios --profile production
```

## Testing Workflow

### 1. Local Development
```bash
# Start backend
cd backend/api
npm start

# Start mobile app
cd mobile
npm start
```

### 2. TestFlight Beta
1. Build: `eas build --platform ios --profile preview`
2. Submit: `eas submit --platform ios --profile preview`
3. Add testers in App Store Connect
4. Test features:
   - Upload PG&E spec books
   - Analyze utility audits
   - Generate As-Built PDFs
   - Validate repeal recommendations

### 3. Production Release
1. Build: `eas build --platform ios --profile production`
2. Submit: `eas submit --platform ios --profile production`
3. Monitor App Store Review
4. Release to App Store

## Key Features to Test

### AI Document Analyzer
- **Spec Upload**: Large PDF uploads (100+ pages)
- **Learning**: Chunking and indexing of standards
- **Analysis**: Cross-references with confidence scoring
- **Repeals**: True/repealable status with spec reasons

### As-Built Generator
- **Forms**: All 10 required PG&E documents
- **Compliance**: TD-2051P-10 procedure adherence
- **Output**: Color-coded PDF with red-lines/blue-lines
- **Signatures**: LAN ID and completion date

### Performance Targets
- Spec upload: < 30 seconds for 100 pages
- Audit analysis: < 5 seconds per item
- PDF generation: < 2 seconds
- App size: < 50MB

## Troubleshooting

### Certificate Issues
```bash
# Clear and regenerate
eas credentials --platform ios --clear-credentials
eas credentials --platform ios
```

### Build Failures
```bash
# Check diagnostics
eas diagnostics

# Clear cache
eas build --clear-cache --platform ios --profile development
```

### API Connection Issues
- Verify backend is running: `curl http://localhost:4000/readyz`
- Check network: Phone and computer on same WiFi
- Update API_BASE_URL in app.json

## Monetization Setup (Production)

### Freemium Model
- **Free Tier**: 5 analyses/month
- **Pro Tier**: Unlimited analyses ($9.99/month)
- **Team Tier**: Multi-user support ($49.99/month)

### Implementation
1. Add RevenueCat SDK for subscriptions
2. Configure products in App Store Connect
3. Update backend for subscription validation
4. Add paywall screen in app

## Next Steps

1. **Replace placeholders** in eas.json with your Apple credentials
2. **Run** `eas credentials --platform ios` to set up certificates
3. **Build development** version for testing
4. **Deploy backend** updates to Render
5. **Submit to TestFlight** for beta testing
6. **Gather feedback** from field foremen
7. **Submit to App Store** when ready

## Support

- EAS Documentation: https://docs.expo.dev/eas/
- Apple Developer: https://developer.apple.com/
- Render Dashboard: https://dashboard.render.com/
- NEXA Support: support@nexa-usa.io
