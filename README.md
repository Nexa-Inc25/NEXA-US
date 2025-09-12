# NEXA Foreman App MVP (Monorepo)

This repository is the single source for the NEXA MVP. All code lives under this folder.

Design reference: see `webpage-app-flow.txt` in this directory.

## Scope (6–8 weeks)

- Offline-first mobile app (Expo) for foremen to run the day end-to-end.
- Secure multi-tenant backend with Auth0, Postgres RLS, presigned uploads, and auditing.
- AI assist for photo QA, timesheet suggestions, and closeout generation.

## Monorepo layout

- `backend/api/` — Node.js Express API (org-scoped JWT, sync, presign, timesheet, closeout, notify)
- `backend/ai/` — Python FastAPI services (photo QA, closeout writer) — planned
- `mobile/` — React Native (Expo) app — planned
- `infra/` — Terraform/IaC for API Gateway authorizer, S3/KMS, etc. — planned
- `docs/` — additional docs and diagrams — planned

## Security alignment

- Auth0 OIDC with PKCE on mobile; API validates org-scoped JWT (`org_id` and `roles` in claims)
- Postgres RLS enforces `current_org_id()` for all queries
- S3/KMS per-tenant encryption; presigned PUT URLs with constraints
- Full audit logging for all actions

## Running the API locally

1. Navigate to `backend/api/`
2. Copy `.env.example` to `.env` and set values; for quick start, set `AUTH_DISABLED=1`
3. Install deps and start:

```bash
npm install
npm start
```

The API will listen on `http://localhost:4000`.

## Running the Expo mobile app

1. Navigate to `mobile/`
2. Install dependencies:

```bash
npm install
npx expo install expo-auth-session expo-secure-store expo-sqlite expo-network expo-constants
```

3. Start Expo (Metro bundler):

```bash
npm start
```

4. In the app:
- Use "Dev Login (Bypass)" to try flows during development without Auth0.
- Press "Sync" on the Today screen to pull data from the API and populate the local SQLite cache.

Configuration comes from `mobile/app.json` under `expo.extra`:
- `API_BASE_URL` should point to the API, defaults to `http://localhost:4000`.
- Auth0 values (`AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_AUDIENCE`) can be set later to enable PKCE login.

## Key Documents

- `webpage-app-flow.txt` — product and build plan (screens, APIs, security, acceptance)

## Local services (Docker Compose)

Bring up Postgres and Redis for local development:

```bash
docker compose up -d
docker compose ps
```

Defaults (from `docker-compose.yml`):

- Postgres on `localhost:5432` with user `nexa`, password `nexa`, db `nexa_mvp`
- Redis on `localhost:6379`

API env variables (already set in `backend/api/.env.example`):

- `DATABASE_URL=postgres://nexa:nexa@localhost:5432/nexa_mvp`
- `REDIS_URL=redis://localhost:6379`

## Next steps

- Flesh out API endpoints and connect Postgres
- Scaffold Expo mobile app (Auth0 PKCE, encrypted SQLite, Today view)
- Implement AI services (FastAPI) for photo QA and closeout writer
- Infra IaC for API Gateway authorizer and presign Lambda
