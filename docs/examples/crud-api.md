# CRUD API Example

Build a complete CRUD (Create, Read, Update, Delete) API with AWS API Factory.

## What We'll Build

A simple **Orders API** with endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | /orders | List all orders |
| POST | /orders | Create new order |
| GET | /orders/{id} | Get order by ID |
| PUT | /orders/{id} | Update order |
| DELETE | /orders/{id} | Delete order |

## Project Setup

### 1. Initialize Project

```bash
factory init orders-api
cd orders-api
```

### 2. Configure factory.yaml

```yaml
project:
  name: orders-api
  envs:
    - dev
    - prod

profile: minimal

apis:
  rest:
    enabled: true
    cors:
      allow_origins: ["*"]
      allow_methods: [GET, POST, PUT, DELETE, OPTIONS]
      allow_headers: [Content-Type]
    routes:
      # Collection endpoints
      - path: /orders
        methods: [GET, POST]
        service: orders
        auth: none

      # Single resource endpoints
      - path: /orders/{id}
        methods: [GET, PUT, DELETE]
        service: orders
        auth: none

compute:
  lambda:
    enabled: true
    services:
      orders:
        entry: src/services/orders/handler.py:handler
        memory_mb: 512
        timeout_s: 30
        environment:
          TABLE_NAME: orders
```

## Handler Implementation

Create the orders handler at `src/services/orders/handler.py`:

```python
"""Orders CRUD Lambda handler.

Demonstrates a complete REST API with:
- Request routing by HTTP method
- Input validation
- Error handling
- Consistent response format
- Logging
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# In-memory storage (replace with DynamoDB for production)
orders_db: dict[str, dict] = {}


# =============================================================================
# Response Helpers
# =============================================================================

def success_response(data: Any, status_code: int = 200) -> dict:
    """Create success response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data),
    }


def error_response(message: str, status_code: int = 400) -> dict:
    """Create error response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": message}),
    }


# =============================================================================
# Validation
# =============================================================================

VALID_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}


def validate_create_order(body: dict) -> tuple[bool, str]:
    """Validate order creation request."""
    if not body.get("customer_name"):
        return False, "customer_name is required"

    if not body.get("items"):
        return False, "items array is required"

    if not isinstance(body["items"], list):
        return False, "items must be an array"

    for i, item in enumerate(body["items"]):
        if not item.get("name"):
            return False, f"items[{i}].name is required"
        if "quantity" in item and not isinstance(item["quantity"], int):
            return False, f"items[{i}].quantity must be an integer"
        if "quantity" in item and item["quantity"] < 1:
            return False, f"items[{i}].quantity must be positive"

    return True, ""


def validate_update_order(body: dict) -> tuple[bool, str]:
    """Validate order update request."""
    if "status" in body and body["status"] not in VALID_STATUSES:
        return False, f"status must be one of: {', '.join(VALID_STATUSES)}"

    return True, ""


# =============================================================================
# CRUD Operations
# =============================================================================

def list_orders(event: dict) -> dict:
    """GET /orders - List all orders."""
    logger.info("Listing orders")

    # Optional: pagination
    query_params = event.get("queryStringParameters") or {}
    limit = int(query_params.get("limit", 100))

    orders = list(orders_db.values())[:limit]

    return success_response({
        "orders": orders,
        "count": len(orders),
        "total": len(orders_db),
    })


def create_order(event: dict) -> dict:
    """POST /orders - Create new order."""
    logger.info("Creating order")

    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")

    # Validate
    valid, message = validate_create_order(body)
    if not valid:
        return error_response(message)

    # Create order
    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    order = {
        "order_id": order_id,
        "customer_name": body["customer_name"],
        "items": [
            {
                "name": item["name"],
                "quantity": item.get("quantity", 1),
                "price": item.get("price", 0.0),
            }
            for item in body["items"]
        ],
        "status": "pending",
        "total": sum(
            item.get("price", 0) * item.get("quantity", 1)
            for item in body["items"]
        ),
        "created_at": now,
        "updated_at": now,
    }

    orders_db[order_id] = order
    logger.info(f"Created order: {order_id}")

    return success_response(order, status_code=201)


def get_order(event: dict) -> dict:
    """GET /orders/{id} - Get order by ID."""
    order_id = event["pathParameters"]["id"]
    logger.info(f"Getting order: {order_id}")

    order = orders_db.get(order_id)
    if not order:
        return error_response(f"Order not found: {order_id}", status_code=404)

    return success_response(order)


def update_order(event: dict) -> dict:
    """PUT /orders/{id} - Update order."""
    order_id = event["pathParameters"]["id"]
    logger.info(f"Updating order: {order_id}")

    order = orders_db.get(order_id)
    if not order:
        return error_response(f"Order not found: {order_id}", status_code=404)

    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body")

    # Validate
    valid, message = validate_update_order(body)
    if not valid:
        return error_response(message)

    # Update fields
    if "status" in body:
        order["status"] = body["status"]
    if "customer_name" in body:
        order["customer_name"] = body["customer_name"]

    order["updated_at"] = datetime.now(timezone.utc).isoformat()
    orders_db[order_id] = order

    logger.info(f"Updated order: {order_id}")
    return success_response(order)


def delete_order(event: dict) -> dict:
    """DELETE /orders/{id} - Delete order."""
    order_id = event["pathParameters"]["id"]
    logger.info(f"Deleting order: {order_id}")

    if order_id not in orders_db:
        return error_response(f"Order not found: {order_id}", status_code=404)

    del orders_db[order_id]
    logger.info(f"Deleted order: {order_id}")

    return success_response({"message": "Order deleted", "order_id": order_id})


# =============================================================================
# Main Handler
# =============================================================================

def handler(event: dict, context: Any) -> dict:
    """Main Lambda handler - routes requests to CRUD operations."""
    logger.info(f"Request: {event.get('httpMethod')} {event.get('path')}")

    method = event.get("httpMethod", "GET")
    path_params = event.get("pathParameters") or {}
    has_id = "id" in path_params

    try:
        # Route to appropriate handler
        if method == "GET" and not has_id:
            return list_orders(event)
        elif method == "POST" and not has_id:
            return create_order(event)
        elif method == "GET" and has_id:
            return get_order(event)
        elif method == "PUT" and has_id:
            return update_order(event)
        elif method == "DELETE" and has_id:
            return delete_order(event)
        else:
            return error_response(f"Method not allowed: {method}", status_code=405)

    except Exception as e:
        logger.exception("Unexpected error")
        return error_response("Internal server error", status_code=500)
```

## Deploy and Test

### 1. Validate Configuration

```bash
factory validate
```

### 2. Deploy

```bash
factory deploy dev
```

Note the API URL from the output.

### 3. Test the API

```bash
# Set your API URL
API_URL="https://abc123.execute-api.us-east-1.amazonaws.com/dev"

# List orders (empty)
curl $API_URL/orders
# {"orders": [], "count": 0, "total": 0}

# Create an order
curl -X POST $API_URL/orders \
     -H "Content-Type: application/json" \
     -d '{
       "customer_name": "John Doe",
       "items": [
         {"name": "Widget", "quantity": 2, "price": 9.99},
         {"name": "Gadget", "quantity": 1, "price": 24.99}
       ]
     }'
# {"order_id": "ord-abc123...", "customer_name": "John Doe", ...}

# Get the order (use the order_id from above)
curl $API_URL/orders/ord-abc123...
# {"order_id": "ord-abc123...", ...}

# Update order status
curl -X PUT $API_URL/orders/ord-abc123... \
     -H "Content-Type: application/json" \
     -d '{"status": "confirmed"}'

# List orders (now has one)
curl $API_URL/orders
# {"orders": [...], "count": 1, "total": 1}

# Delete order
curl -X DELETE $API_URL/orders/ord-abc123...
# {"message": "Order deleted", "order_id": "ord-abc123..."}
```

## Adding Authentication

Secure the API with API keys:

```yaml
apis:
  rest:
    routes:
      - path: /orders
        methods: [GET, POST]
        service: orders
        auth: api_key

      - path: /orders/{id}
        methods: [GET, PUT, DELETE]
        service: orders
        auth: api_key
```

Redeploy and test with API key:

```bash
factory deploy dev

# Get API key from outputs
API_KEY="your-api-key"  # pragma: allowlist secret

# Requests now require x-api-key header
curl $API_URL/orders \
     -H "x-api-key: $API_KEY"
```

## Adding DynamoDB (Production)

For production, replace in-memory storage with DynamoDB:

### 1. Enable DynamoDB

```yaml
data:
  dynamodb:
    enabled: true
    tables:
      - name: orders
        pk: order_id
        sk: created_at
        pitr: true
```

### 2. Update Handler

```python
import boto3
import os

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def list_orders(event: dict) -> dict:
    """GET /orders - List all orders."""
    response = table.scan(Limit=100)
    orders = response.get("Items", [])

    return success_response({
        "orders": orders,
        "count": len(orders),
    })

def create_order(event: dict) -> dict:
    """POST /orders - Create new order."""
    # ... validation ...

    order = {
        "order_id": order_id,
        "created_at": now,
        # ... other fields ...
    }

    table.put_item(Item=order)
    return success_response(order, status_code=201)

def get_order(event: dict) -> dict:
    """GET /orders/{id} - Get order by ID."""
    order_id = event["pathParameters"]["id"]

    response = table.query(
        KeyConditionExpression="order_id = :pk",
        ExpressionAttributeValues={":pk": order_id}
    )

    items = response.get("Items", [])
    if not items:
        return error_response(f"Order not found: {order_id}", status_code=404)

    return success_response(items[0])

def update_order(event: dict) -> dict:
    """PUT /orders/{id} - Update order."""
    order_id = event["pathParameters"]["id"]
    body = json.loads(event.get("body") or "{}")

    update_expr = "SET updated_at = :now"
    expr_values = {":now": datetime.now(timezone.utc).isoformat()}

    if "status" in body:
        update_expr += ", #status = :status"
        expr_values[":status"] = body["status"]

    table.update_item(
        Key={"order_id": order_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
        ExpressionAttributeNames={"#status": "status"}
    )

    return get_order(event)

def delete_order(event: dict) -> dict:
    """DELETE /orders/{id} - Delete order."""
    order_id = event["pathParameters"]["id"]

    table.delete_item(Key={"order_id": order_id})

    return success_response({"message": "Order deleted", "order_id": order_id})
```

## Local Testing

Create a test file `tests/test_orders.py`:

```python
import pytest
import json
from src.services.orders.handler import handler


class MockContext:
    function_name = "test"
    aws_request_id = "test-123"


@pytest.fixture
def context():
    return MockContext()


def test_list_orders_empty(context):
    event = {"httpMethod": "GET", "path": "/orders"}
    response = handler(event, context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["count"] == 0


def test_create_order(context):
    event = {
        "httpMethod": "POST",
        "path": "/orders",
        "body": json.dumps({
            "customer_name": "Test User",
            "items": [{"name": "Widget", "quantity": 1}]
        })
    }
    response = handler(event, context)

    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert "order_id" in body
    assert body["customer_name"] == "Test User"


def test_create_order_validation(context):
    event = {
        "httpMethod": "POST",
        "path": "/orders",
        "body": json.dumps({"items": []})
    }
    response = handler(event, context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "customer_name" in body["error"]


def test_get_order_not_found(context):
    event = {
        "httpMethod": "GET",
        "path": "/orders/nonexistent",
        "pathParameters": {"id": "nonexistent"}
    }
    response = handler(event, context)

    assert response["statusCode"] == 404
```

Run tests:

```bash
pytest tests/test_orders.py -v
```

## Clean Up

```bash
factory destroy dev
```

## Next Steps

- [Authentication Guide](../guides/authentication.md) — Secure your API
- [Lambda Functions Guide](../guides/lambda-functions.md) — Optimization tips
- [Configuration Reference](../reference/configuration.md) — All options
