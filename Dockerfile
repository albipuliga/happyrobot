FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

COPY pyproject.toml README.md ./
COPY app ./app
COPY data ./data
COPY scripts ./scripts

RUN pip install --no-cache-dir .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=3)"

CMD ["sh", "-c", "\
  uvicorn app.main:app --host 0.0.0.0 --port ${PORT} & \
  SERVER_PID=$!; \
  if [ \"$SEED\" = '1' ] || [ \"$SEED\" = 'true' ]; then \
    echo 'Waiting for server to start...'; \
    until python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT}/health', timeout=2)\" 2>/dev/null; do sleep 1; done; \
    echo 'Seeding dashboard...'; \
    python -m scripts.populate_dashboard || echo 'Seeding failed (non-fatal)'; \
  fi; \
  wait $SERVER_PID"]
