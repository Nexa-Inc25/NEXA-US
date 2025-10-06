# NEXA Foreman App Integration Plan

## Phase 1: Document Analyzer Setup ✅
- [x] Deploy analyzer to Render Pro ($30/month)
- [ ] Upload full PG&E spec book (150-200 pages)
- [ ] Test QA audit analysis locally
- [ ] Verify production endpoints

## Phase 2: Expo Mobile App Integration

### 2.1 Project Setup
```bash
cd c:\Users\mikev\CascadeProjects\nexa-inc-mvp\foreman-app
npm install axios expo-image-picker @react-native-async-storage/async-storage
```

### 2.2 Environment Configuration
Update `app.json`:
```json
{
  "expo": {
    "extra": {
      "AUTH0_DOMAIN": "dev-4klipkgroc7grk1q.us.auth0.com",
      "AUTH0_CLIENT_ID": "YOUR_CLIENT_ID",
      "AUTH0_AUDIENCE": "https://api.nexa.local",
      "API_URL": "https://nexa-api.onrender.com"
    }
  }
}
```

### 2.3 Key Features to Implement
1. **Photos/QA Screen**
   - Camera integration with expo-image-picker
   - Direct analysis via `/analyze-audit` endpoint
   - Results: Repealability, confidence scores, spec references

2. **Closeout Generation**
   - Aggregate job analysis
   - PDF generation via `/closeout/generate`
   - Offline queue for sync

3. **Offline-First Architecture**
   - AsyncStorage for queue management
   - WatermelonDB for local data
   - Sync on connectivity restore

### 2.4 API Endpoints Used
- `POST /learn-spec/` - Upload spec books
- `POST /analyze-audit/` - Analyze QA photos/documents
- `POST /closeout/generate` - Generate closeout PDFs
- `GET /health` - Service status check

### 2.5 Auth0 PKCE Flow
```javascript
const discovery = AuthSession.useAutoDiscovery('https://dev-4klipkgroc7grk1q.us.auth0.com');
// Implement secure token exchange
```

## Phase 3: Testing & Deployment

### Local Testing
1. Run analyzer locally: `python -m uvicorn api:app --port 8000`
2. Run Expo: `npx expo start`
3. Test flows:
   - Photo capture → Analysis
   - Closeout generation
   - Offline queue

### Production Deployment
1. Render API: https://nexa-api.onrender.com
2. Expo Build: `eas build --platform all`
3. App Store/Play Store submission

## Timeline
- **Tonight (7:00-8:00 PM)**: Complete spec upload, test analyzer
- **Tonight (8:00-10:00 PM)**: Expo integration Phase 2.1-2.3
- **Tomorrow AM**: Auth0 setup, offline sync
- **Tomorrow PM**: Testing & refinement

## Success Metrics
- [ ] Spec book processes in <30 seconds
- [ ] QA analysis returns in <5 seconds
- [ ] Offline queue syncs reliably
- [ ] Closeout PDFs generate correctly
- [ ] Auth0 login works on mobile

## Next Steps After Integration
1. Add job detail screens
2. Implement timesheet tracking
3. Add crew management
4. Integrate billing/invoicing
