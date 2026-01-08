# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Hello World Lambda handler for AWS API Factory starter template.

This is a minimal example of a Lambda handler that works with
AWS API Factory's REST API integration.

Example:
    The handler receives API Gateway events and returns responses
    in the expected format::

        GET /hello → {"message": "Hello, World!"}

"""

from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle incoming API Gateway requests.

    Args:
        event: API Gateway event containing request details.
        context: Lambda context object with runtime information.

    Returns:
        API Gateway response with status code, headers, and body.

    """
    # Extract query parameters if present
    query_params = event.get("queryStringParameters") or {}
    name = query_params.get("name", "World")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "X-Powered-By": "AWS API Factory",
        },
        "body": f'{{"message": "Hello, {name}!"}}',
    }
