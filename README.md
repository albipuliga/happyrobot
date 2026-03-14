# HappyRobot Backend

Backend API for the HappyRobot FDE take-home challenge. It verifies inbound carriers against FMCSA, searches a seeded load pool, persists negotiation rounds, records call outcomes, and exposes summary metrics for the demo.

## Stack

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL on Railway
- SQLite for local tests/dev fallback
- httpx
- Docker

## Local Setup

1. Install dependencies:
   ```bash
   uv sync --dev
   ```
2. Copy `.env.example` to `.env` and adjust the values for your environment.
   ```bash
   cp .env.example .env
   ```
3. Run the API:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The database is created automatically on startup and seeded from [`data/loads.json`](/Users/albertopuliga/Desktop/Coding/happyrobot/data/loads.json).
In Railway, the app points at a managed PostgreSQL service. SQLite is used locally for quick development and testing.

## Configuration

All `/api/v1/*` endpoints require an `X-API-Key` header. Generate a strong value for `APP_API_KEY` instead of using a placeholder:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set your `APP_API_KEY` value in local `.env` and in Railway service variables.
The dashboard password reuses that same `APP_API_KEY` value.

Runtime settings are centralized in [`.env.example`](/Users/albertopuliga/Desktop/Coding/happyrobot/.env.example), including the database URL, FMCSA settings, request timeout, and negotiation round limit.

## Docker

Build the image:

```bash
docker build -t happyrobot .
```

Run the container:

```bash
docker run --rm -p 8000:8000 --env-file .env happyrobot
```

This starts the API on `http://localhost:8000`.

## Railway

### My Deployment

- Health endpoint: [https://happyrobot-app-production.up.railway.app/health](https://happyrobot-app-production.up.railway.app/health)
- Dashboard: [https://happyrobot-app-production.up.railway.app/dashboard](https://happyrobot-app-production.up.railway.app/dashboard)

### Reproducing This Deployment

To deploy from scratch, use the Railway dashboard with these manual steps:

1. Create a new Railway project.
2. Add an application service from this repository.
   Railway can deploy the repo directly from GitHub, or you can create an empty service and upload the code with the Railway CLI. Because this repo includes a [`Dockerfile`](/Users/albertopuliga/Desktop/Coding/happyrobot/Dockerfile), Railway will build and run the container from that file.
3. Add a PostgreSQL service to the same project.
4. Open the app service variables and set:
   - `APP_API_KEY`
   - `REQUEST_TIMEOUT_SECONDS`
   - `NEGOTIATION_MAX_COUNTER_ROUNDS`
   - `FMCSA_API_KEY`
   - `FMCSA_BASE_URL`
   - `SESSION_HTTPS_ONLY` — set to `true` so session cookies require HTTPS (Railway handles TLS termination)
   - `DATABASE_URL` - Example: if the database service is named `Postgres`, use `${{Postgres.DATABASE_URL}}`.
6. Generate a public domain for the app service from `Settings > Networking > Public Networking`.
7. Verify the deployment with:
   - `GET /health`
   - `GET /dashboard`

## API Endpoints

- `POST /api/v1/carriers/verify`
- `POST /api/v1/loads/search`
- `POST /api/v1/loads/negotiate`
- `POST /api/v1/calls/complete`
- `GET /api/v1/metrics/summary`
- `GET /health`
- `GET /dashboard`
- `GET /dashboard/data`
- `POST /dashboard/login`

## Dashboard Demo Data

Use [`scripts/populate_dashboard.py`](/Users/albertopuliga/Desktop/Coding/happyrobot/scripts/populate_dashboard.py) to generate realistic demo traffic for the local dashboard (requires the app to be running and an `APP_API_KEY` value in your environment).

## Test

To run the tests:

```bash
uv run pytest
```
