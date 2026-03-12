# HappyRobot Backend

Backend API for the HappyRobot FDE take-home challenge. It verifies inbound carriers against FMCSA, searches a seeded load pool, persists negotiation rounds, records call outcomes, and exposes summary metrics for the demo.

## Stack

- FastAPI
- SQLAlchemy 2.0
- SQLite
- httpx
- Docker

## Local Setup

1. Install dependencies:
   ```bash
   uv sync --dev
   ```
2. Copy `.env.example` to `.env` and set `APP_API_KEY` and `FMCSA_API_KEY`.
3. Run the API:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The database is created automatically on startup and seeded from [`data/loads.json`](/Users/albertopuliga/Desktop/Coding/happyrobot/data/loads.json).

## Configuration

All `/api/v1/*` endpoints require an `X-API-Key` header. Generate a strong value for `APP_API_KEY` instead of using a placeholder:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set that value in your local `.env` file and in Railway service variables.

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

Set these variables in Railway before deploying:

- `APP_API_KEY`: generated secret used for the `X-API-Key` header
- `FMCSA_API_KEY`: FMCSA API key
- `FMCSA_BASE_URL`: `https://mobile.fmcsa.dot.gov/qc/services`
- `DATABASE_URL`: `sqlite:///./happyrobot.db` for the challenge unless you switch databases

## API Endpoints

- `POST /api/v1/carriers/verify`
- `POST /api/v1/loads/search`
- `POST /api/v1/loads/negotiate`
- `POST /api/v1/calls/complete`
- `GET /api/v1/metrics/summary`
- `GET /healthz`

## Test

To run the tests:

```bash
uv run pytest
```
