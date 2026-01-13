# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Orders CRUD Lambda handler for AWS API Factory starter template.

This module demonstrates a complete CRUD API implementation with:
- In-memory storage (replace with DynamoDB for production)
- Request validation with Pydantic
- Proper error handling and HTTP status codes
- JSON response formatting
- Logging for debugging

Routes handled:
    GET    /orders           - List all orders
    POST   /orders           - Create a new order
    GET    /orders/{id}      - Get order by ID
    PUT    /orders/{id}      - Update order by ID
    DELETE /orders/{id}      - Delete order by ID

Example requests:
    # List orders
    curl https://api-id.execute-api.region.amazonaws.com/dev/orders

    # Create order
    curl -X POST https://api-id.execute-api.region.amazonaws.com/dev/orders \\
         -H "Content-Type: application/json" \\
         -d '{"customer_name": "John Doe", "items": [{"name": "Widget", "quantity": 2}]}'

    # Get order
    curl https://api-id.execute-api.region.amazonaws.com/dev/orders/ord-123

    # Update order
    curl -X PUT https://api-id.execute-api.region.amazonaws.com/dev/orders/ord-123 \\
         -H "Content-Type: application/json" \\
         -d '{"status": "shipped"}'

    # Delete order
    curl -X DELETE https://api-id.execute-api.region.amazonaws.com/dev/orders/ord-123

"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# =============================================================================
# In-Memory Storage
# =============================================================================
# NOTE: This is for demonstration only. In production, use DynamoDB or Aurora.
# Data is lost when the Lambda container is recycled.

_orders_db: dict[str, dict[str, Any]] = {}


# =============================================================================
# Request/Response Models
# =============================================================================


class OrderItem:
    """Order line item."""

    def __init__(self, name: str, quantity: int, price: float = 0.0) -> None:
        """Initialize order item.

        Args:
            name: Item name.
            quantity: Item quantity (must be positive).
            price: Item unit price.

        Raises:
            ValueError: If quantity is not positive.

        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self.name = name
        self.quantity = quantity
        self.price = price

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price,
        }


class Order:
    """Order model."""

    VALID_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}

    def __init__(
        self,
        order_id: str,
        customer_name: str,
        items: list[OrderItem],
        status: str = "pending",
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        """Initialize order.

        Args:
            order_id: Unique order identifier.
            customer_name: Customer name.
            items: List of order items.
            status: Order status.
            created_at: Creation timestamp.
            updated_at: Last update timestamp.

        Raises:
            ValueError: If status is invalid.

        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {self.VALID_STATUSES}")
        self.order_id = order_id
        self.customer_name = customer_name
        self.items = items
        self.status = status
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order_id": self.order_id,
            "customer_name": self.customer_name,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "total": sum(item.price * item.quantity for item in self.items),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# =============================================================================
# Response Helpers
# =============================================================================


def json_response(
    status_code: int,
    body: dict[str, Any] | list[Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a properly formatted API Gateway response.

    Args:
        status_code: HTTP status code.
        body: Response body (will be JSON serialized).
        headers: Additional headers.

    Returns:
        API Gateway response dictionary.

    """
    response_headers = {
        "Content-Type": "application/json",
        "X-Powered-By": "AWS API Factory",
    }
    if headers:
        response_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": json.dumps(body),
    }


def error_response(
    status_code: int, message: str, details: str | None = None
) -> dict[str, Any]:
    """Create an error response.

    Args:
        status_code: HTTP status code.
        message: Error message.
        details: Optional error details.

    Returns:
        API Gateway error response.

    """
    body: dict[str, Any] = {"error": message}
    if details:
        body["details"] = details
    return json_response(status_code, body)


# =============================================================================
# CRUD Operations
# =============================================================================


def list_orders() -> dict[str, Any]:
    """List all orders.

    Returns:
        API Gateway response with list of orders.

    """
    logger.info("Listing all orders")
    orders = [order for order in _orders_db.values()]
    return json_response(200, {"orders": orders, "count": len(orders)})


def get_order(order_id: str) -> dict[str, Any]:
    """Get order by ID.

    Args:
        order_id: Order identifier.

    Returns:
        API Gateway response with order or 404 error.

    """
    logger.info(f"Getting order: {order_id}")
    order = _orders_db.get(order_id)
    if not order:
        return error_response(404, "Order not found", f"No order with ID: {order_id}")
    return json_response(200, order)


def create_order(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new order.

    Args:
        body: Request body with order data.

    Returns:
        API Gateway response with created order or validation error.

    """
    logger.info("Creating new order")

    # Validate required fields
    if "customer_name" not in body:
        return error_response(400, "Missing required field: customer_name")

    if (
        "items" not in body
        or not isinstance(body["items"], list)
        or len(body["items"]) == 0
    ):
        return error_response(
            400, "Missing or invalid field: items (must be non-empty array)"
        )

    # Parse items
    try:
        items = []
        for item_data in body["items"]:
            if "name" not in item_data:
                return error_response(400, "Each item must have a 'name' field")
            items.append(
                OrderItem(
                    name=item_data["name"],
                    quantity=item_data.get("quantity", 1),
                    price=item_data.get("price", 0.0),
                )
            )
    except ValueError as e:
        return error_response(400, "Invalid item data", str(e))

    # Create order
    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    try:
        order = Order(
            order_id=order_id,
            customer_name=body["customer_name"],
            items=items,
            status=body.get("status", "pending"),
        )
    except ValueError as e:
        return error_response(400, "Invalid order data", str(e))

    # Store order
    order_dict = order.to_dict()
    _orders_db[order_id] = order_dict
    logger.info(f"Created order: {order_id}")

    return json_response(201, order_dict, {"Location": f"/orders/{order_id}"})


def update_order(order_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Update an existing order.

    Args:
        order_id: Order identifier.
        body: Request body with fields to update.

    Returns:
        API Gateway response with updated order or error.

    """
    logger.info(f"Updating order: {order_id}")

    order = _orders_db.get(order_id)
    if not order:
        return error_response(404, "Order not found", f"No order with ID: {order_id}")

    # Update allowed fields
    if "status" in body:
        if body["status"] not in Order.VALID_STATUSES:
            return error_response(
                400,
                "Invalid status",
                f"Must be one of: {', '.join(Order.VALID_STATUSES)}",
            )
        order["status"] = body["status"]

    if "customer_name" in body:
        order["customer_name"] = body["customer_name"]

    # Update timestamp
    order["updated_at"] = datetime.now(timezone.utc).isoformat()

    _orders_db[order_id] = order
    logger.info(f"Updated order: {order_id}")

    return json_response(200, order)


def delete_order(order_id: str) -> dict[str, Any]:
    """Delete an order.

    Args:
        order_id: Order identifier.

    Returns:
        API Gateway response confirming deletion or 404 error.

    """
    logger.info(f"Deleting order: {order_id}")

    if order_id not in _orders_db:
        return error_response(404, "Order not found", f"No order with ID: {order_id}")

    del _orders_db[order_id]
    logger.info(f"Deleted order: {order_id}")

    return json_response(200, {"message": "Order deleted", "order_id": order_id})


# =============================================================================
# Main Handler
# =============================================================================


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Main Lambda handler for orders CRUD operations.

    Routes requests to appropriate CRUD functions based on HTTP method
    and path.

    Args:
        event: API Gateway proxy event.
        context: Lambda context object.

    Returns:
        API Gateway response dictionary.

    """
    # Log request for debugging
    logger.info(f"Received event: {json.dumps(event)}")

    # Extract request details
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/orders")
    path_parameters = event.get("pathParameters") or {}
    body_str = event.get("body") or "{}"

    # Parse request body for POST/PUT
    body: dict[str, Any] = {}
    if http_method in ("POST", "PUT") and body_str:
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            return error_response(400, "Invalid JSON in request body")

    # Extract order ID from path if present
    order_id = path_parameters.get("id")

    # Route to appropriate handler
    try:
        if order_id:
            # Single order operations: /orders/{id}
            if http_method == "GET":
                return get_order(order_id)
            elif http_method == "PUT":
                return update_order(order_id, body)
            elif http_method == "DELETE":
                return delete_order(order_id)
            else:
                return error_response(
                    405, f"Method {http_method} not allowed on /orders/{{id}}"
                )
        else:
            # Collection operations: /orders
            if http_method == "GET":
                return list_orders()
            elif http_method == "POST":
                return create_order(body)
            else:
                return error_response(
                    405, f"Method {http_method} not allowed on /orders"
                )

    except Exception as e:
        logger.exception("Unexpected error processing request")
        return error_response(500, "Internal server error", str(e))
