# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""FastAPI application for AWS API Factory App Runner example.

This module provides a production-ready FastAPI application demonstrating
best practices for containerized services deployed on AWS App Runner:

- Health check endpoint (/healthz) for App Runner health monitoring
- Structured logging with request correlation IDs
- Environment variable configuration
- CORS middleware for cross-origin requests
- Error handling with proper HTTP responses
- Request/response models with Pydantic validation

Example:
    Run locally with uvicorn:
        uvicorn app:app --host 0.0.0.0 --port 8000

    Or with Docker:
        docker build -t public-api .
        docker run -p 8000:8000 public-api

"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.project_name = os.getenv("PROJECT_NAME", "aws-api-factory")
        self.service_name = os.getenv("SERVICE_NAME", "public-api")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Settings(environment={self.environment}, "
            f"project={self.project_name}, service={self.service_name})"
        )


settings = Settings()


# =============================================================================
# Pydantic Models
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Health status", examples=["healthy"])
    environment: str = Field(description="Deployment environment")
    service: str = Field(description="Service name")
    timestamp: str = Field(description="ISO timestamp")


class WelcomeResponse(BaseModel):
    """Welcome message response model."""

    message: str = Field(description="Welcome message")
    version: str = Field(description="API version")
    project: str = Field(description="Project name")


class EchoRequest(BaseModel):
    """Echo request model for POST endpoint."""

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="Message to echo",
        examples=["Hello!"],
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata"
    )


class EchoResponse(BaseModel):
    """Echo response model."""

    echoed_message: str = Field(description="The echoed message")
    request_id: str = Field(description="Request correlation ID")
    metadata: dict[str, Any] | None = Field(description="Echoed metadata")
    timestamp: str = Field(description="ISO timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error message")
    detail: str | None = Field(default=None, description="Detailed error info")
    request_id: str | None = Field(default=None, description="Request ID")


# =============================================================================
# Application Lifecycle
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application.
    Use this for initializing database connections, loading ML models,
    or other expensive startup operations.
    """
    # Startup
    logger.info(
        "Starting %s service in %s environment",
        settings.service_name,
        settings.environment,
    )
    logger.info("Settings: %s", settings)

    yield

    # Shutdown
    logger.info("Shutting down %s service", settings.service_name)


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="AWS API Factory - Public API",
    description="Example FastAPI application for AWS App Runner deployment",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request ID Middleware
# =============================================================================


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to each request for correlation.

    The request ID is extracted from X-Request-ID header if present,
    otherwise a new UUID is generated.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    # Log the incoming request
    logger.info(
        "Request: %s %s | Request-ID: %s",
        request.method,
        request.url.path,
        request_id,
    )

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    # Log the response
    logger.info(
        "Response: %s %s | Status: %d | Request-ID: %s",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
    )

    return response


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured response."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unexpected error: %s | Request-ID: %s", str(exc), request_id)

    # Don't expose internal errors in production
    detail = str(exc) if settings.debug else None

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=detail,
            request_id=request_id,
        ).model_dump(),
    )


# =============================================================================
# Endpoints
# =============================================================================


@app.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for App Runner.

    This endpoint is called by App Runner to verify the service is healthy.
    It should return quickly and not depend on external services.

    Returns:
        HealthResponse: Health status with service information.
    """
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        service=settings.service_name,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/", response_model=WelcomeResponse, tags=["General"])
async def root():
    """Welcome endpoint.

    Returns a welcome message with API version information.

    Returns:
        WelcomeResponse: Welcome message with version info.
    """
    return WelcomeResponse(
        message="Welcome to AWS API Factory!",
        version="1.0.0",
        project=settings.project_name,
    )


@app.get("/info", tags=["General"])
async def info():
    """Service information endpoint.

    Returns detailed information about the service configuration.

    Returns:
        dict: Service configuration details.
    """
    return {
        "service": settings.service_name,
        "project": settings.project_name,
        "environment": settings.environment,
        "debug": settings.debug,
        "log_level": settings.log_level,
    }


@app.post("/echo", response_model=EchoResponse, tags=["Examples"])
async def echo(request: Request, body: EchoRequest):
    """Echo endpoint to demonstrate POST request handling.

    Echoes back the provided message with metadata.

    Args:
        request: The incoming request.
        body: The echo request body.

    Returns:
        EchoResponse: The echoed message with request metadata.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    return EchoResponse(
        echoed_message=body.message,
        request_id=request_id,
        metadata=body.metadata,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/items/{item_id}", tags=["Examples"])
async def get_item(item_id: int, q: str | None = None):
    """Example endpoint with path parameters.

    Demonstrates path parameter handling and optional query parameters.

    Args:
        item_id: The item ID from the path.
        q: Optional query parameter.

    Returns:
        dict: Item information.

    Raises:
        HTTPException: If item_id is negative.
    """
    if item_id < 0:
        raise HTTPException(status_code=400, detail="Item ID must be non-negative")

    return {
        "item_id": item_id,
        "query": q,
        "description": f"This is item {item_id}",
    }


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    # Binding to 0.0.0.0 is required for containerized deployments (App Runner, Docker)
    # to receive traffic from the container orchestrator's load balancer
    uvicorn.run(
        "app:app",
        host="0.0.0.0",  # nosec B104 - intentional for container deployments
        port=int(os.getenv("PORT", "8000")),
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
