# Nexa Core Mobile App

React Native + Expo app for crew foremen to submit as-builts from the field with offline support.

## Features

- ✅ **Offline-First**: Queue submissions when no network, auto-sync when online
- ✅ **Photo Capture**: Multiple photos per submission with timestamps
- ✅ **GPS Tracking**: Automatic location capture
- ✅ **QR Code**: Scan job QR codes (future feature)
- ✅ **Secure Storage**: API keys stored securely
- ✅ **Real-time Sync**: Automatic background sync when online

## Setup

### 1. Install Dependencies

```bash
cd nexa-core/apps/mobile
npm install
```

### 2. Configure API URL

Edit `App.js` and update the API URL:

```javascript
const API_URL = 'https://nexa-core-api.onrender.com/api';
```

### 3. Run Development

```bash
# Start Expo development server
npm start

# Scan QR code with Expo Go app on your phone
# Or run on simulator:
npm run ios     # iOS
npm run android # Android
```

## First Time Setup

### Set API Key (Temporary - until login implemented)

```javascript
// In Expo Go, open the app and run in console:
import * as SecureStore from 'expo-secure-store';
await SecureStore.setItemAsync('foreman_api_key', 'foreman_test_key_456');
```

Or add a login screen (future enhancement).

## Usage

### Submit As-Built

1. **Enter Job ID**: From QR code or manual entry
2. **Add Notes**: Describe work completed
3. **Add Measurements**: Spacing, clearance, etc.
4. **Add Equipment**: Type, model, serial number
5. **Capture Photos**: Multiple photos with camera
6. **Submit**: 
   - Online: Sends immediately
   - Offline: Queues for sync when online

### Offline Mode

- App automatically detects network status
- Submissions are queued in local storage
- Auto-syncs when network restored
- Shows pending count badge

## API Integration

### Endpoint

```
POST /api/submissions
```

### Headers

```
Content-Type: application/json
X-API-Key: foreman_test_key_456
```

### Request Body

```json
{
  "job_id": 1,
  "as_built_data": {
    "notes": "Installed capacitor per plan",
    "timestamp": "2025-10-07T15:00:00Z"
  },
  "equipment_installed": {
    "description": "500kVA capacitor, serial ABC123"
  },
  "measurements": {
    "values": "Spacing: 6ft, Clearance: 8ft"
  },
  "weather_conditions": "Clear",
  "crew_notes": "Installation complete, tested OK",
  "gps_coordinates": {
    "lat": 37.7749,
    "lon": -122.4194,
    "accuracy": 10,
    "timestamp": "2025-10-07T15:00:00Z"
  },
  "submitted_offline": false,
  "photos": [
    {
      "base64": "...",
      "timestamp": "2025-10-07T15:00:00Z"
    }
  ]
}
```

## Future Enhancements

- [ ] QR code scanner for job loading
- [ ] Login screen with credentials
- [ ] Signature capture
- [ ] Form templates by work type
- [ ] Pull jobs assigned to foreman
- [ ] Real-time status updates
- [ ] Dark mode
- [ ] Offline map view

## Deployment

### TestFlight (iOS)

```bash
expo build:ios
# Upload to App Store Connect
# Add testers in TestFlight
```

### Google Play Internal Test (Android)

```bash
expo build:android
# Upload to Google Play Console
# Add internal testers
```

### Over-The-Air Updates

```bash
# Publish update without rebuild
expo publish
```

## Troubleshooting

### Photos Not Capturing

- Check camera permissions in Settings
- Ensure `expo-image-picker` is installed
- Test on physical device (simulator camera may not work)

### Offline Queue Not Syncing

- Check network status indicator
- Verify API URL is correct
- Check API key is set in SecureStore
- View console logs for errors

### API Errors

- Verify API is deployed and healthy
- Check API key matches database
- Ensure job_id exists in database
- Check request format matches API schema

## Development Notes

### Local Storage Keys

- `pending_submissions`: Array of queued submissions
- `foreman_api_key` (SecureStore): Authentication key

### Network Detection

Uses `@react-native-community/netinfo`:
- Monitors connection status
- Triggers sync on reconnect
- Shows status indicator

### Photo Storage

- Captured as base64 for offline storage
- Sent to API for S3 upload
- Limited to 10MB per photo
- Compressed to quality 0.7

## Testing

### Test Offline Mode

1. Enable airplane mode on device
2. Submit as-built
3. Verify "Queued offline" message
4. Disable airplane mode
5. Verify auto-sync completes

### Test Photo Capture

1. Click "Capture Photo"
2. Grant camera permission
3. Take photo
4. Verify count increases
5. Submit and check photos in API

## Support

See main README.md for overall platform documentation.
