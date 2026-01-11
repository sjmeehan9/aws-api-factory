# Lambda Functions Guide

Build efficient, well-structured Lambda functions for AWS API Factory.

## Overview

AWS Lambda runs your code in response to events without provisioning servers. AWS API Factory creates Lambda functions with:

- **Automatic IAM roles** with least-privilege permissions
- **CloudWatch logging** for debugging
- **X-Ray tracing** (scalable profile)
- **Environment variable injection**
- **Profile-based resource sizing**

## Handler Contract

Lambda handlers must follow this signature:

```python
def handler(event: dict, context: Any) -> dict:
    """Handle incoming API Gateway request.

    Args:
        event: API Gateway proxy event containing request details.
        context: Lambda context with runtime information.

    Returns:
        API Gateway response dictionary.
    """
    return {
        "statusCode": 200,
        "body": '{"message": "Hello"}'
    }
```

### Configuration

```yaml
compute:
  lambda:
    enabled: true
    services:
      my_service:
        entry: src/services/my_service/handler.py:handler
        memory_mb: 512
        timeout_s: 30
```

The `entry` format is `path/to/file.py:function_name`.

## Event Structure

API Gateway sends a proxy event to your Lambda:

```python
{
    # Request details
    "httpMethod": "POST",
    "path": "/orders",
    "resource": "/orders",

    # Parameters
    "pathParameters": {"id": "123"},
    "queryStringParameters": {"page": "1"},
    "headers": {"content-type": "application/json"},

    # Body
    "body": '{"name": "Widget"}',
    "isBase64Encoded": False,

    # Context
    "requestContext": {
        "requestId": "abc-123",
        "stage": "dev",
        "identity": {"sourceIp": "1.2.3.4"}
    }
}
```

## Context Object

The `context` object provides runtime information:

```python
def handler(event, context):
    # Useful context properties
    function_name = context.function_name        # "my-api-dev-orders"
    memory_limit = context.memory_limit_in_mb    # 512
    request_id = context.aws_request_id          # "uuid-here"
    log_group = context.log_group_name           # "/aws/lambda/..."
    log_stream = context.log_stream_name         # "2024/01/01/[$LATEST]abc"

    # Check remaining time (milliseconds)
    remaining_ms = context.get_remaining_time_in_millis()

    if remaining_ms < 5000:  # Less than 5 seconds
        # Wrap up quickly
        pass

    return {"statusCode": 200, "body": "OK"}
```

## Response Format

Responses must include at minimum:

```python
{
    "statusCode": 200,  # Required: HTTP status code
    "body": "string"    # Required for non-204: Response body as string
}
```

### Complete Response

```python
def handler(event, context):
    import json

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "max-age=300",
            "X-Request-Id": context.aws_request_id
        },
        "body": json.dumps({"message": "Success", "data": {...}}),
        "isBase64Encoded": False
    }
```

## Common Patterns

### Request Routing

Handle multiple HTTP methods in one handler:

```python
def handler(event, context):
    method = event["httpMethod"]
    path = event["path"]

    routes = {
        ("GET", "/orders"): list_orders,
        ("POST", "/orders"): create_order,
        ("GET", "/orders/{id}"): get_order,
        ("PUT", "/orders/{id}"): update_order,
        ("DELETE", "/orders/{id}"): delete_order,
    }

    # Match route pattern
    handler_func = routes.get((method, event["resource"]))

    if handler_func:
        return handler_func(event)
    else:
        return {"statusCode": 404, "body": "Not found"}
```

### Request Validation

Validate input before processing:

```python
import json

def handler(event, context):
    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response("Invalid JSON", 400)

    # Validate required fields
    required_fields = ["name", "email"]
    missing = [f for f in required_fields if f not in body]

    if missing:
        return error_response(f"Missing fields: {missing}", 400)

    # Validate field types/formats
    if not isinstance(body["name"], str) or len(body["name"]) < 2:
        return error_response("Name must be at least 2 characters", 400)

    if "@" not in body.get("email", ""):
        return error_response("Invalid email format", 400)

    # Process valid request
    return process_request(body)


def error_response(message, status_code):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
```

### Response Helper

Create consistent responses:

```python
import json
from typing import Any

def api_response(
    status_code: int,
    body: Any = None,
    headers: dict = None
) -> dict:
    """Create API Gateway response.

    Args:
        status_code: HTTP status code.
        body: Response body (will be JSON serialized).
        headers: Additional headers.

    Returns:
        API Gateway response dictionary.
    """
    response_headers = {"Content-Type": "application/json"}
    if headers:
        response_headers.update(headers)

    response = {
        "statusCode": status_code,
        "headers": response_headers,
    }

    if body is not None:
        response["body"] = json.dumps(body)

    return response


# Usage
def handler(event, context):
    data = {"id": "123", "name": "Widget"}
    return api_response(200, {"data": data})
```

### Error Handling

Catch and handle errors appropriately:

```python
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class NotFoundError(Exception):
    pass

class ValidationError(Exception):
    pass

def handler(event, context):
    try:
        return process_request(event)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return api_response(400, {"error": str(e)})

    except NotFoundError as e:
        return api_response(404, {"error": str(e)})

    except Exception as e:
        # Log full traceback for debugging
        logger.error(f"Unexpected error: {traceback.format_exc()}")

        # Return generic error to client
        return api_response(500, {
            "error": "Internal server error",
            "request_id": context.aws_request_id
        })
```

### Middleware Pattern

Wrap handlers with cross-cutting concerns:

```python
import functools
import json
import logging
import time

logger = logging.getLogger()

def with_logging(func):
    """Log request and response details."""
    @functools.wraps(func)
    def wrapper(event, context):
        request_id = context.aws_request_id
        method = event.get("httpMethod", "UNKNOWN")
        path = event.get("path", "/")

        logger.info(f"[{request_id}] {method} {path}")
        start = time.time()

        try:
            response = func(event, context)
            duration = (time.time() - start) * 1000
            logger.info(f"[{request_id}] {response['statusCode']} - {duration:.2f}ms")
            return response
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"[{request_id}] ERROR - {duration:.2f}ms - {e}")
            raise

    return wrapper


def with_error_handling(func):
    """Handle exceptions and return proper responses."""
    @functools.wraps(func)
    def wrapper(event, context):
        try:
            return func(event, context)
        except Exception as e:
            logger.exception("Unhandled exception")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal error"})
            }
    return wrapper


# Apply decorators
@with_logging
@with_error_handling
def handler(event, context):
    return {"statusCode": 200, "body": '{"status": "ok"}'}
```

## Logging

### Basic Logging

```python
import logging

# Configure at module level
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("Processing request")
    logger.debug(f"Event: {event}")  # Only visible if level is DEBUG

    try:
        result = process()
        logger.info(f"Success: {result}")
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        raise
```

### Structured Logging

For enhanced profile, use structured logs:

```python
import json
import logging

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.context = {}

    def set_context(self, **kwargs):
        self.context.update(kwargs)

    def _log(self, level: str, message: str, **extra):
        log_entry = {
            "level": level,
            "message": message,
            **self.context,
            **extra
        }
        self.logger.info(json.dumps(log_entry))

    def info(self, message: str, **extra):
        self._log("INFO", message, **extra)

    def error(self, message: str, **extra):
        self._log("ERROR", message, **extra)


logger = StructuredLogger(__name__)

def handler(event, context):
    logger.set_context(
        request_id=context.aws_request_id,
        function=context.function_name
    )

    logger.info("Request received",
        method=event["httpMethod"],
        path=event["path"]
    )

    # Process...

    logger.info("Request completed", status=200, duration_ms=45)
```

## Environment Variables

### Configuration

```yaml
compute:
  lambda:
    services:
      orders:
        entry: src/services/orders/handler.py:handler
        environment:
          TABLE_NAME: orders
          LOG_LEVEL: INFO
          FEATURE_FLAG_NEW_UI: "true"
```

### Access in Code

```python
import os

def handler(event, context):
    # Get environment variables
    table_name = os.environ.get("TABLE_NAME", "default-table")
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    new_ui = os.environ.get("FEATURE_FLAG_NEW_UI", "false") == "true"

    # AWS-provided variables
    region = os.environ.get("AWS_REGION")
    function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

    return {"statusCode": 200, "body": "OK"}
```

## Memory and Timeout

### Configuration

```yaml
compute:
  lambda:
    services:
      light:
        entry: src/light/handler.py:handler
        memory_mb: 256    # 256 MB
        timeout_s: 10     # 10 seconds

      heavy:
        entry: src/heavy/handler.py:handler
        memory_mb: 2048   # 2 GB
        timeout_s: 120    # 2 minutes

      auto:
        entry: src/auto/handler.py:handler
        memory_mb: auto   # Profile default (512 or 1024)
        timeout_s: auto   # Profile default (30 or 60)
```

### Choosing Memory Size

| Use Case | Recommended Memory |
|----------|-------------------|
| Simple API handlers | 256-512 MB |
| JSON processing | 512-1024 MB |
| Data transformation | 1024-2048 MB |
| ML inference | 2048-10240 MB |

> **Note**: More memory = more CPU. If your function is CPU-bound, increase memory.

### Timeout Strategy

```python
def handler(event, context):
    # Check remaining time periodically for long operations
    items = get_items_to_process()

    for item in items:
        # Check if we have enough time left (5 second buffer)
        if context.get_remaining_time_in_millis() < 5000:
            # Save state and exit gracefully
            save_checkpoint(item)
            return {
                "statusCode": 202,
                "body": '{"status": "partial", "message": "Timeout approaching"}'
            }

        process_item(item)

    return {"statusCode": 200, "body": '{"status": "complete"}'}
```

## Cold Starts

Cold starts occur when Lambda creates a new execution environment. Minimize impact:

### 1. Keep Package Size Small

```python
# Bad: Import everything
import boto3
import pandas
import numpy

# Good: Import only what you need
from boto3 import client
```

### 2. Initialize Outside Handler

```python
import boto3

# Initialize outside handler (reused across invocations)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def handler(event, context):
    # Use pre-initialized resources
    response = table.get_item(Key={"id": "123"})
    return {"statusCode": 200, "body": str(response)}
```

### 3. Use Provisioned Concurrency (Scalable Profile)

```yaml
compute:
  lambda:
    services:
      critical:
        entry: src/critical/handler.py:handler
        reserved_concurrency: 10  # Always keep 10 warm instances
```

## Testing Locally

### Unit Testing

```python
# test_handler.py
import pytest
from src.services.orders.handler import handler

class MockContext:
    function_name = "test-function"
    aws_request_id = "test-request-id"
    memory_limit_in_mb = 512

    def get_remaining_time_in_millis(self):
        return 30000

def test_get_orders():
    event = {
        "httpMethod": "GET",
        "path": "/orders",
        "pathParameters": None,
        "queryStringParameters": None,
        "body": None
    }

    response = handler(event, MockContext())

    assert response["statusCode"] == 200
    assert "orders" in response["body"]

def test_create_order():
    event = {
        "httpMethod": "POST",
        "path": "/orders",
        "body": '{"customer_name": "Test", "items": [{"name": "Widget"}]}'
    }

    response = handler(event, MockContext())

    assert response["statusCode"] == 201
    assert "order_id" in response["body"]

def test_invalid_json():
    event = {
        "httpMethod": "POST",
        "path": "/orders",
        "body": "not valid json"
    }

    response = handler(event, MockContext())

    assert response["statusCode"] == 400
```

### Integration Testing

```python
# test_integration.py
import requests

API_URL = "https://abc123.execute-api.us-east-1.amazonaws.com/dev"

def test_health_check():
    response = requests.get(f"{API_URL}/hello")
    assert response.status_code == 200

def test_crud_flow():
    # Create
    response = requests.post(f"{API_URL}/orders", json={
        "customer_name": "Test User",
        "items": [{"name": "Widget", "quantity": 1}]
    })
    assert response.status_code == 201
    order_id = response.json()["order_id"]

    # Read
    response = requests.get(f"{API_URL}/orders/{order_id}")
    assert response.status_code == 200

    # Update
    response = requests.put(f"{API_URL}/orders/{order_id}", json={
        "status": "confirmed"
    })
    assert response.status_code == 200

    # Delete
    response = requests.delete(f"{API_URL}/orders/{order_id}")
    assert response.status_code == 200
```

## Best Practices

1. **Keep handlers thin** — Business logic in separate modules
2. **Initialize outside handler** — Reuse connections across invocations
3. **Handle errors explicitly** — Don't let exceptions bubble up
4. **Log with context** — Include request ID in all logs
5. **Validate input early** — Fail fast with clear error messages
6. **Use environment variables** — Never hardcode secrets or config
7. **Set appropriate timeouts** — Shorter is better for APIs
8. **Monitor cold starts** — Use CloudWatch Insights

## Next Steps

- [REST API Guide](rest-api.md) — API Gateway integration
- [Authentication Guide](authentication.md) — Secure your functions
- [App Runner Guide](app-runner-containers.md) — When to use containers instead
