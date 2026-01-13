# App Runner Containers Guide

Deploy containerized applications with AWS App Runner.

## Overview

AWS App Runner provides a fully managed container service that automatically builds, deploys, and scales your applications. Use App Runner when you need:

- **Long-running processes** (WebSocket connections, background workers)
- **Consistent latency** (no cold starts)
- **Existing web frameworks** (FastAPI, Flask, Express)
- **Multi-language support** (Node.js, Go, Rust, etc.)

## When to Use App Runner vs Lambda

| Factor | Lambda | App Runner |
|--------|--------|------------|
| Cold starts | Yes (ms to seconds) | No |
| Request duration | Max 15 minutes | Unlimited |
| Pricing | Per invocation | Per instance-hour |
| Scaling | 0 to thousands instantly | 1+ instances always |
| WebSocket support | Limited | Full |
| Frameworks | Requires adapters | Native support |

### Use Lambda When:
- Short-lived requests (<30s)
- Highly variable traffic
- Cost optimization for low-traffic APIs
- Event-driven processing

### Use App Runner When:
- Consistent traffic patterns
- Low-latency requirements
- WebSocket connections needed
- Existing Docker applications

## Configuration

Enable App Runner in `factory.yaml`:

```yaml
compute:
  apprunner:
    enabled: true
    services:
      api:
        dockerfile: src/services/api/Dockerfile
        port: 8000
        healthcheck_path: /healthz
        cpu: 1
        memory: 2
        min_instances: 1
        max_instances: 10
        environment:
          ENVIRONMENT: production
          LOG_LEVEL: INFO
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `dockerfile` | string | Required | Path to Dockerfile |
| `port` | int | Required | Container listening port |
| `healthcheck_path` | string | /healthz | Health check endpoint |
| `cpu` | float | 1 | vCPUs (0.25, 0.5, 1, 2, 4) |
| `memory` | float | 2 | Memory GB (0.5-12, depends on CPU) |
| `min_instances` | int | 1 | Minimum running instances |
| `max_instances` | int | 10 | Maximum instances for scaling |
| `environment` | dict | {} | Environment variables |

### CPU and Memory Combinations

| vCPU | Valid Memory (GB) |
|------|-------------------|
| 0.25 | 0.5, 1 |
| 0.5 | 1, 2 |
| 1 | 2, 3, 4 |
| 2 | 4, 6 |
| 4 | 8, 10, 12 |

## Dockerfile Best Practices

### Multi-Stage Build

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Key Principles

1. **Multi-stage builds** — Keep final image small
2. **Non-root user** — Security best practice
3. **Health check** — Enable App Runner monitoring
4. **Minimal base image** — Use slim variants
5. **Layer optimization** — Order commands for cache efficiency

## FastAPI Application

### Basic Application

```python
# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="My API",
    version="1.0.0"
)

# Health check endpoint (required for App Runner)
@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}

# Your API endpoints
class Item(BaseModel):
    name: str
    price: float

@app.get("/items")
async def list_items():
    return {"items": []}

@app.post("/items", status_code=201)
async def create_item(item: Item):
    logger.info(f"Creating item: {item.name}")
    return {"id": "123", **item.dict()}

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    if item_id != "123":
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, "name": "Widget", "price": 9.99}
```

### With Middleware

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Add request ID to headers
    response = await call_next(request)

    duration = (time.time() - start_time) * 1000
    logger.info(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")

    response.headers["X-Request-ID"] = request_id
    return response
```

### With Lifespan Events

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import boto3

# Global clients
dynamodb_client = None
s3_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize clients
    global dynamodb_client, s3_client
    dynamodb_client = boto3.client("dynamodb")
    s3_client = boto3.client("s3")
    logger.info("Initialized AWS clients")

    yield

    # Shutdown: Cleanup
    logger.info("Shutting down")

app = FastAPI(lifespan=lifespan)
```

## Health Checks

App Runner uses health checks to determine instance health. Unhealthy instances are replaced.

### Basic Health Check

```python
@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
```

### Comprehensive Health Check

```python
import os
import asyncio

@app.get("/healthz")
async def health_check():
    checks = {
        "status": "healthy",
        "version": os.environ.get("VERSION", "unknown"),
        "checks": {}
    }

    # Check database connectivity
    try:
        # Add your database check here
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["database"] = str(e)

    # Check external dependencies
    try:
        # Add dependency checks here
        checks["checks"]["dependencies"] = "ok"
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["dependencies"] = str(e)

    status_code = 200 if checks["status"] == "healthy" else 503
    return JSONResponse(content=checks, status_code=status_code)
```

### Health Check Configuration

App Runner health check settings:

| Setting | Default | Description |
|---------|---------|-------------|
| Protocol | TCP | TCP or HTTP |
| Path | / | HTTP path for health check |
| Interval | 5s | Time between checks |
| Timeout | 2s | Time to wait for response |
| Healthy threshold | 1 | Consecutive successes for healthy |
| Unhealthy threshold | 5 | Consecutive failures for unhealthy |

## Environment Variables

### Configuration

```yaml
compute:
  apprunner:
    services:
      api:
        environment:
          ENVIRONMENT: production
          DATABASE_URL: "{{resolve:secretsmanager:my-db-url}}"
          LOG_LEVEL: INFO
```

### Access in Code

```python
import os

class Settings:
    def __init__(self):
        self.environment = os.environ.get("ENVIRONMENT", "development")
        self.database_url = os.environ.get("DATABASE_URL")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.debug = self.environment == "development"

settings = Settings()
```

### Secrets Integration

For sensitive values, use AWS Secrets Manager:

```yaml
compute:
  apprunner:
    services:
      api:
        secrets:
          DATABASE_URL: arn:aws:secretsmanager:us-east-1:123456789:secret:my-db-url
          API_KEY: arn:aws:secretsmanager:us-east-1:123456789:secret:my-api-key
```

## Auto-Scaling

App Runner automatically scales based on concurrent requests.

### Profile Defaults

| Profile | Min Instances | Max Instances |
|---------|---------------|---------------|
| Minimal | 1 | 10 |
| Scalable | 2 | 25 |

### Custom Configuration

```yaml
compute:
  apprunner:
    services:
      api:
        min_instances: 2      # Always keep 2 warm
        max_instances: 50     # Scale up to 50
        # Scaling happens at ~80 concurrent requests per instance
```

### Scaling Considerations

- Each instance handles ~80-100 concurrent requests
- Scale-up takes ~30 seconds
- Scale-down is gradual (avoids thrashing)
- You pay for running instances

## Local Development

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Build and Test Docker

```bash
# Build image
docker build -t my-api .

# Run container
docker run -p 8000:8000 \
    -e ENVIRONMENT=development \
    -e LOG_LEVEL=DEBUG \
    my-api

# Test health check
curl http://localhost:8000/healthz

# Test endpoints
curl http://localhost:8000/items
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
    volumes:
      - .:/app  # Mount for hot reload
    command: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Debugging

### View Logs

App Runner logs go to CloudWatch:

```bash
# View logs
aws logs tail /aws/apprunner/my-api-dev-api/application --follow
```

### Common Issues

#### 1. Container Fails to Start

**Symptoms**: Deployment fails, no health checks pass

**Solutions**:
- Check Dockerfile CMD is correct
- Verify port matches configuration
- Check logs for startup errors

```bash
# Test locally first
docker run -p 8000:8000 my-api
curl http://localhost:8000/healthz
```

#### 2. Health Checks Failing

**Symptoms**: Instances marked unhealthy, rolling restarts

**Solutions**:
- Ensure `/healthz` returns 200
- Check health check timeout is sufficient
- Verify app starts within 60 seconds

#### 3. Memory Issues

**Symptoms**: OOM errors, container restarts

**Solutions**:
- Increase memory allocation
- Optimize application memory usage
- Check for memory leaks

```yaml
compute:
  apprunner:
    services:
      api:
        memory: 4  # Increase to 4GB
```

## Cost Optimization

### Pricing Model

- **Compute**: Per vCPU-hour and GB-hour
- **Provisioned instances**: Pay for minimum instances 24/7
- **Automatic scaling**: Pay for additional instances when scaled

### Cost Reduction Strategies

1. **Right-size resources** — Don't over-provision CPU/memory
2. **Minimize instances** — Use `min_instances: 1` for dev
3. **Use Lambda for variable traffic** — Pay per request instead
4. **Optimize container size** — Faster startup = better scaling

### Example Costs (us-east-1)

| Configuration | Monthly Cost (approx) |
|--------------|----------------------|
| 1 vCPU, 2GB, 1 instance | ~$30 |
| 1 vCPU, 2GB, 2 instances | ~$60 |
| 2 vCPU, 4GB, 2 instances | ~$120 |

## Best Practices

1. **Implement proper health checks** — Return actual health status
2. **Use multi-stage Docker builds** — Smaller images = faster deploys
3. **Run as non-root** — Security best practice
4. **Configure graceful shutdown** — Handle SIGTERM properly
5. **Set appropriate timeouts** — Client and server timeouts
6. **Use connection pooling** — Reuse database connections
7. **Log with structure** — JSON logs for CloudWatch Insights
8. **Monitor latency** — Set up alarms for p99 latency

## Next Steps

- [Lambda Functions Guide](lambda-functions.md) — Alternative compute option
- [Authentication Guide](authentication.md) — Secure your containers
- [REST API Guide](rest-api.md) — API Gateway integration
