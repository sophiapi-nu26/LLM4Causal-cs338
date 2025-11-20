# Production Dockerfile for Article Retrieval API - Google Cloud
FROM --platform=linux/amd64 python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create and use a non-root user for building (security best practice)
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy only requirements first (Docker layer caching optimization)
# This layer will be cached unless requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production Runtime
FROM python:3.11-slim

# Install runtime dependencies only
# mupdf-tools: Required by PyMuPDF for PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
# This avoids reinstalling and keeps image smaller
COPY --from=builder /root/.local /home/appuser/.local

# Update PATH to include user-installed Python packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Critical environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=api.app \
    FLASK_ENV=production \
    PORT=8080

# Copy application code
# Copy in specific order for better layer caching
COPY --chown=appuser:appuser ./api /app/api
COPY --chown=appuser:appuser ./document_preparation /app/document_preparation

# Switch to non-root user
# All subsequent commands and runtime execution will be as this user
USER appuser

# Cloud Run expects the app to listen on $PORT (default 8080)
EXPOSE 8080

# Health check (optional but recommended for Cloud Run)
# Cloud Run will use this to determine if container is healthy
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/swagger.json', timeout=2)" || exit 1

# Production command using gunicorn
# Configuration:
# --bind 0.0.0.0:$PORT - Listen on all interfaces, port from env var
# --workers 2 - Number of worker processes (Cloud Run: 2 is good default)
# --threads 4 - Threads per worker (handles concurrent requests)
# --timeout 1800 - 30 minutes (for long-running PDF downloads/parsing)
# --worker-class gthread - Threaded worker (good for I/O bound tasks like API calls)
# --access-logfile - - Log requests to stdout (Cloud Run captures this)
# --error-logfile - - Log errors to stderr
CMD exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 1800 \
    --worker-class gthread \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "api.app:create_app()"
