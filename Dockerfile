# ==============================================================================
# Multi-stage Dockerfile for Zero Trust Sandalwood Agroforestry Monitoring Backend
# ==============================================================================

# Build Stage
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Production Runtime Stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root system user for security compliance
RUN groupadd -r appgroup && useradd -r -g appgroup -s /bin/false appuser

# Copy installed python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy project files
COPY app/ ./app/
COPY blockchain/ ./blockchain/

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
