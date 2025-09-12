# Auth0 setup for NEXA MVP (Mobile + API)

This guide wires Auth0 OIDC with PKCE for the Expo app and validates org-scoped JWTs in the API.

The API enforces `org_id` via Postgres RLS. Tokens MUST contain `org_id` and `roles` claims.

## 1) Create an Auth0 Application

- Type: Regular Web Application (works for native PKCE flows too)
- Domain: your-tenant.us.auth0.com
- Client ID: copy for later

## 2) Allowed URLs and origins

Using Expo AuthSession proxy in development:

- Allowed Callback URLs:
  - https://auth.expo.io/@YOUR_EXPO_USERNAME/nexa-mobile
- Allowed Logout URLs:
  - https://auth.expo.io/@YOUR_EXPO_USERNAME/nexa-mobile
- Allowed Web Origins:
  - https://auth.expo.io

For production/native scheme (no proxy):

- Allowed Callback URLs:
  - nexaapp://redirect
- Allowed Logout URLs:
  - nexaapp://

## 3) Add custom claims (org_id and roles)

Create an Auth0 Action (Login / Post-Login) to add namespaced claims to the ID and Access tokens.

- Navigate: Auth0 Dashboard → Actions → Library → Build Custom → Post Login
- Name: Add NEXA Claims
- Code:

```js
/**
 * Post-Login Action: add NEXA namespaced claims
 * Ensure you set org_id and roles based on your user/org model
 */
exports.onExecutePostLogin = async (event, api) => {
  // Example: derive org and roles from metadata or an external source
  const orgId = event.user.user_metadata?.org_id || 'dev-org';
  const roles = event.authorization?.roles || event.user.app_metadata?.roles || [];

  const namespace = 'https://nexa.app/';
  api.idToken.setCustomClaim(namespace + 'org_id', orgId);
  api.idToken.setCustomClaim(namespace + 'roles', roles);
  api.accessToken.setCustomClaim(namespace + 'org_id', orgId);
  api.accessToken.setCustomClaim(namespace + 'roles', roles);
};
```

- Deploy the action and add it to your Login flow.

Note: The API also supports non-namespaced keys via `ORG_ID_CLAIM` and `ROLES_CLAIM`, but namespaced is recommended.

## 4) Configure the Expo app

Edit `mobile/app.json` under `expo.extra`:

```json
{
  "expo": {
    "extra": {
      "AUTH0_DOMAIN": "your-tenant.us.auth0.com",
      "AUTH0_CLIENT_ID": "YOUR_MOBILE_CLIENT_ID",
      "AUTH0_AUDIENCE": "https://api.nexa.local",
      "API_BASE_URL": "http://localhost:4000",
      "REDIRECT_SCHEME": "nexaapp"
    }
  }
}
```

- In development, the app uses the Expo AuthSession proxy.
- For production builds, disable the proxy (code change in `AuthProvider.js`) and make sure the native scheme URLs are configured in Auth0.

## 5) Configure the API

Edit `backend/api/.env` (copy from `.env.example`):

```
AUTH_DISABLED=0
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.nexa.local
AUTH0_ISSUER_URL=https://your-tenant.us.auth0.com/
# Multiple keys supported (comma-separated). Namespaced fallbacks included.
ORG_ID_CLAIM=org_id,https://nexa.app/org_id
ROLES_CLAIM=roles,https://nexa.app/roles
```

Restart the API:

```
cd backend/api
npm start
```

## 6) Test end-to-end

- Start the API (AUTH_DISABLED=0)
- Start Expo (in `mobile/`, run `npm start`)
- Tap "Login with Auth0". Complete login.
- On success, the app stores the token and calls the API with `Authorization: Bearer ...`.
- Verify endpoints in the API log and in Postgres RLS behavior.

If you encounter 401 with "Missing org_id claim":
- Check your token at https://jwt.io and ensure it includes:
  - `https://nexa.app/org_id` and `https://nexa.app/roles`
- Confirm API `.env` has the correct domain/audience and claim keys.

## 7) Notes

- During early development you can keep `AUTH_DISABLED=1` and use the "Dev Login (Bypass)" in the app.
- Switch to `AUTH_DISABLED=0` when you are ready to validate Auth0 end-to-end.
