# SPDX-License-Identifier: MIT
# AWS API Factory - App Runner Dockerfile Example
#
# This is a production-ready, multi-stage Dockerfile for deploying FastAPI
# applications on AWS App Runner. It follows Docker best practices:
#
# - Multi-stage build for smaller final image
# - Non-root user for security
# - Layer optimization for build caching
# - Health check instruction
# - Minimal base image (slim variant)
#
# Build:
#   docker build -t public-api .
#
# Run:
#   docker run -p 8000:8000 public-api
#
# Test health check:
#   curl http://localhost:8000/healthz

# =============================================================================
# Stage 1: Build dependencies
# =============================================================================
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Production image
# =============================================================================
FROM python:3.11-slim AS production

# Labels for container metadata
LABEL maintainer="AWS API Factory"
LABEL org.opencontainers.image.title="AWS API Factory Public API"
LABEL org.opencontainers.image.description="FastAPI application for AWS App Runner"
LABEL org.opencontainers.image.version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser app.py .

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check instruction for Docker and container orchestrators
# App Runner uses its own health check configuration, but this is useful
# for local development and other container runtimes
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Run the application with uvicorn
# - host 0.0.0.0: Listen on all interfaces (required for containers)
# - port 8000: Default port (matches EXPOSE)
# - workers: Number of worker processes (adjust based on CPU)
# - access-log: Enable access logging
# - proxy-headers: Trust proxy headers (important for App Runner)
CMD ["uvicorn", "app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log", \
     "--proxy-headers"]
