# REST API Guide

Build and deploy REST APIs with Amazon API Gateway and AWS Lambda.

## Overview

AWS API Factory creates REST APIs using Amazon API Gateway (REST API type), which provides:

- **HTTP endpoints** for your Lambda functions
- **Request/response transformation**
- **Built-in throttling and rate limiting**
- **Multiple authentication options**
- **CORS support**
- **CloudWatch logging and metrics**

## Defining Routes

Routes connect URL paths to Lambda services. Define them in `factory.yaml`:

```yaml
apis:
  rest:
    enabled: true
    routes:
      - path: /users
        methods: [GET, POST]
        service: users
        auth: none
```

### Route Structure

Each route requires:

| Field | Description | Example |
|-------|-------------|---------|
| `path` | URL path (must start with /) | `/users`, `/orders/{id}` |
| `methods` | HTTP methods to enable | `[GET]`, `[GET, POST, PUT]` |
| `service` | Lambda service name | `users`, `orders` |
| `auth` | Authentication mode | `none`, `api_key`, `iam`, `cognito` |

### Path Parameters

Use `{param}` syntax for dynamic path segments:

```yaml
routes:
  # Single parameter
  - path: /users/{id}
    methods: [GET, PUT, DELETE]
    service: users
    auth: none

  # Multiple parameters
  - path: /users/{userId}/orders/{orderId}
    methods: [GET]
    service: orders
    auth: none

  # Proxy path (catch-all)
  - path: /files/{proxy+}
    methods: [GET]
    service: files
    auth: none
```

In your Lambda handler, access path parameters via the event:

```python
def handler(event, context):
    path_params = event.get("pathParameters") or {}
    user_id = path_params.get("id")

    return {
        "statusCode": 200,
        "body": f'{{"user_id": "{user_id}"}}'
    }
```

## HTTP Methods

Supported HTTP methods:

| Method | Typical Use | Example |
|--------|------------|---------|
| `GET` | Retrieve resources | Get user by ID |
| `POST` | Create resources | Create new user |
| `PUT` | Replace/update resources | Update user |
| `PATCH` | Partial update | Update user email only |
| `DELETE` | Remove resources | Delete user |
| `HEAD` | Get headers only | Check if resource exists |
| `OPTIONS` | CORS preflight | Browser preflight check |

### Single Route, Multiple Methods

```yaml
routes:
  # Collection endpoint
  - path: /orders
    methods: [GET, POST]
    service: orders
    auth: none

  # Single resource endpoint
  - path: /orders/{id}
    methods: [GET, PUT, DELETE]
    service: orders
    auth: none
```

Your handler should check `httpMethod` to route internally:

```python
def handler(event, context):
    method = event["httpMethod"]

    if method == "GET":
        return get_orders()
    elif method == "POST":
        return create_order(event)
    elif method == "PUT":
        return update_order(event)
    elif method == "DELETE":
        return delete_order(event)
    else:
        return {"statusCode": 405, "body": "Method not allowed"}
```

## Query Parameters

Access query string parameters in your handler:

```python
def handler(event, context):
    # Single-value parameters
    query_params = event.get("queryStringParameters") or {}
    page = query_params.get("page", "1")
    limit = query_params.get("limit", "10")

    # Multi-value parameters (e.g., ?tags=a&tags=b)
    multi_value_params = event.get("multiValueQueryStringParameters") or {}
    tags = multi_value_params.get("tags", [])

    return {
        "statusCode": 200,
        "body": f'{{"page": {page}, "limit": {limit}, "tags": {tags}}}'
    }
```

Example request:

```bash
curl "https://api.example.com/orders?page=2&limit=20&status=pending"
```

## Request Body

For POST/PUT/PATCH requests, access the body:

```python
import json

def handler(event, context):
    # Body is a JSON string
    body_str = event.get("body") or "{}"

    # Check if base64 encoded (binary content)
    is_base64 = event.get("isBase64Encoded", False)
    if is_base64:
        import base64
        body_str = base64.b64decode(body_str).decode("utf-8")

    # Parse JSON
    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": '{"error": "Invalid JSON"}'
        }

    # Use the data
    name = body.get("name")
    email = body.get("email")

    return {
        "statusCode": 201,
        "body": json.dumps({"id": "123", "name": name, "email": email})
    }
```

## Request Headers

Access request headers:

```python
def handler(event, context):
    headers = event.get("headers") or {}

    # Headers are case-insensitive in HTTP, but API Gateway normalizes to lowercase
    content_type = headers.get("content-type")
    authorization = headers.get("authorization")
    custom_header = headers.get("x-custom-header")

    return {"statusCode": 200, "body": "OK"}
```

## Response Format

Lambda responses must follow the API Gateway proxy format:

```python
def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "X-Custom-Header": "value"
        },
        "body": '{"message": "Success"}'
    }
```

### Response Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `statusCode` | int | Yes | HTTP status code (200, 201, 400, etc.) |
| `headers` | dict | No | Response headers |
| `body` | string | No | Response body (must be string, even for JSON) |
| `isBase64Encoded` | bool | No | Set true if body is base64 encoded |

### Common Status Codes

```python
# Success
return {"statusCode": 200, "body": json.dumps(data)}      # OK
return {"statusCode": 201, "body": json.dumps(created)}   # Created
return {"statusCode": 204, "body": ""}                    # No Content

# Client errors
return {"statusCode": 400, "body": '{"error": "Bad request"}'}
return {"statusCode": 401, "body": '{"error": "Unauthorized"}'}
return {"statusCode": 403, "body": '{"error": "Forbidden"}'}
return {"statusCode": 404, "body": '{"error": "Not found"}'}
return {"statusCode": 422, "body": '{"error": "Validation failed"}'}

# Server errors
return {"statusCode": 500, "body": '{"error": "Internal error"}'}
return {"statusCode": 503, "body": '{"error": "Service unavailable"}'}
```

## CORS Configuration

Enable Cross-Origin Resource Sharing for browser clients:

```yaml
apis:
  rest:
    enabled: true
    cors:
      allow_origins:
        - "https://app.example.com"
        - "https://admin.example.com"
      allow_methods:
        - GET
        - POST
        - PUT
        - DELETE
      allow_headers:
        - Content-Type
        - Authorization
        - X-Custom-Header
```

### CORS for All Origins (Development)

```yaml
cors:
  allow_origins: ["*"]
  allow_methods: [GET, POST, PUT, DELETE, PATCH, OPTIONS]
  allow_headers: [Content-Type, Authorization]
```

### CORS Headers in Responses

Add CORS headers to your Lambda responses for non-simple requests:

```python
def handler(event, context):
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": '{"data": "value"}'
    }
    return response
```

## Throttling and Rate Limiting

API Gateway provides built-in throttling. Defaults vary by profile:

| Profile | Default Rate Limit | Default Burst |
|---------|-------------------|---------------|
| Minimal | Account default | Account default |
| Scalable | 1000 req/s | 2000 |

Override in your configuration (if supported):

```yaml
apis:
  rest:
    throttling:
      rate_limit: 500  # requests per second
      burst_limit: 1000
```

## API Gateway Event Structure

Complete event structure for reference:

```python
{
    "resource": "/orders/{id}",
    "path": "/orders/ord-123",
    "httpMethod": "GET",
    "headers": {
        "accept": "application/json",
        "host": "api.example.com",
        "user-agent": "curl/7.64.1",
        "x-forwarded-for": "1.2.3.4",
        "x-forwarded-proto": "https"
    },
    "queryStringParameters": {
        "include": "items"
    },
    "multiValueQueryStringParameters": {
        "include": ["items"]
    },
    "pathParameters": {
        "id": "ord-123"
    },
    "stageVariables": null,
    "requestContext": {
        "resourceId": "abc123",
        "resourcePath": "/orders/{id}",
        "httpMethod": "GET",
        "requestId": "req-uuid",
        "requestTime": "01/Jan/2024:12:00:00 +0000",
        "requestTimeEpoch": 1704110400000,
        "identity": {
            "sourceIp": "1.2.3.4",
            "userAgent": "curl/7.64.1"
        },
        "path": "/dev/orders/ord-123",
        "stage": "dev",
        "apiId": "apiid123"
    },
    "body": null,
    "isBase64Encoded": false
}
```

## Best Practices

### 1. Use Consistent Response Format

```python
def success_response(data, status_code=200):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"data": data})
    }

def error_response(message, status_code=400, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
```

### 2. Validate Input Early

```python
def handler(event, context):
    # Validate required parameters
    path_params = event.get("pathParameters") or {}
    order_id = path_params.get("id")

    if not order_id:
        return error_response("Order ID is required", 400)

    if not order_id.startswith("ord-"):
        return error_response("Invalid order ID format", 400)

    # Continue with business logic...
```

### 3. Handle Errors Gracefully

```python
import logging
import traceback

logger = logging.getLogger()

def handler(event, context):
    try:
        # Business logic
        return process_request(event)
    except ValidationError as e:
        return error_response(str(e), 400)
    except NotFoundError as e:
        return error_response(str(e), 404)
    except Exception as e:
        logger.error(f"Unexpected error: {traceback.format_exc()}")
        return error_response("Internal server error", 500)
```

### 4. Use Request IDs for Debugging

```python
def handler(event, context):
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    logger.info(f"[{request_id}] Processing request")

    # Include request ID in error responses
    try:
        return process_request(event)
    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal error",
                "request_id": request_id
            })
        }
```

## Debugging

### View API Gateway Logs

```bash
# Enable logging in factory.yaml (default for scalable profile)
observability:
  level: enhanced

# View logs
aws logs tail /aws/apigateway/my-api-dev --follow
```

### Test Locally

```python
# test_handler.py
from src.services.orders.handler import handler

# Simulate GET /orders
event = {
    "httpMethod": "GET",
    "path": "/orders",
    "queryStringParameters": {"page": "1"},
    "pathParameters": None,
    "body": None
}
response = handler(event, None)
print(response)

# Simulate POST /orders
event = {
    "httpMethod": "POST",
    "path": "/orders",
    "body": '{"customer_name": "John", "items": [{"name": "Widget"}]}'
}
response = handler(event, None)
print(response)
```

## Next Steps

- [Lambda Functions Guide](lambda-functions.md) — Handler patterns and optimization
- [Authentication Guide](authentication.md) — Secure your endpoints
- [CRUD API Example](../examples/crud-api.md) — Complete working example
