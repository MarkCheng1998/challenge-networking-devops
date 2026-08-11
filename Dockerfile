# ─────────────────────────────────────────────────────────────────
# Dockerfile for Challenge Networking - DevOps
# Multi-stage build for CI/CD pipeline
# ─────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS builder

# Build arguments (injected by CI/CD)
ARG APP_VERSION=1.0.0
ENV APP_VERSION=${APP_VERSION}

WORKDIR /build

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ─── Final Stage ──────────────────────────────────────────────────
FROM python:3.11-slim

ARG APP_VERSION=1.0.0
ENV APP_VERSION=${APP_VERSION}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /usr/local/lib/python3.11/site-packages

# Copy application code
COPY app.py .
COPY backend/ ./backend/
COPY templates/ ./templates/
COPY static/ ./static/
COPY config/ ./config/

# Create backup directory
RUN mkdir -p /app/backups

# Health check (CI/CD probe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()" || exit 1

EXPOSE 5000

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]
