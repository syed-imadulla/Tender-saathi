# Tender Saathi — Production Backend Container
# Multi-arch Linux container for dedicated backend hosting (Render, Railway, Fly.io, Cloud VPS)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=5000 \
    FLASK_DEBUG=false

# Install required system packages for document ingestion & OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (including gunicorn for production WSGI serving)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy verified backend code and authoritative standards datasets
COPY src/ /app/src/
COPY api/ /app/api/
COPY data/ /app/data/

# Create writable directory for generated audit reports
RUN mkdir -p /app/reports/generated

# Expose backend port
EXPOSE 5000

# Health check to ensure API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch production WSGI server: single process with multi-threading to preserve
# warm in-memory report cache and optimize PyTorch/transformer memory usage
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 180 api.server:app"]
