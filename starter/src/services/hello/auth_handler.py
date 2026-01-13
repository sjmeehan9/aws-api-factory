# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Authenticated Lambda handler example for AWS API Factory.

This example demonstrates how to use the authentication utilities
in Lambda handlers. It shows how to:

- Extract authentication context from API Gateway events
- Use decorators to require authentication
- Access user information from different auth types
- Return appropriate responses for authenticated/unauthenticated requests

Example Responses:

    API Key Authentication:
    ```json
    {
        "message": "Authenticated!",
        "auth_type": "api_key",
        "user": "api_key_id_123"
    }
    ```

    Cognito Authentication:
    ```json
    {
        "message": "Authenticated!",
        "auth_type": "cognito",
        "user": "john.doe@example.com",
        "claims": {
            "email": "john.doe@example.com",
            "cognito:username": "john.doe"
        }
    }
    ```

    IAM Authentication:
    ```json
    {
        "message": "Authenticated!",
        "auth_type": "iam",
        "user": "arn:aws:iam::123456789012:user/john"
    }
    ```

"""

from __future__ import annotations

import json
from typing import Any

# Import auth utilities from aws_api_factory
from aws_api_factory.utils.auth import (
    AuthContext,
    AuthType,
    extract_auth_context,
    require_auth,
    require_cognito_auth,
)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle authenticated API requests.

    This handler demonstrates extracting and using authentication context.
    It works with all authentication types: API Key, IAM, and Cognito.

    Args:
        event: API Gateway event containing request details.
        context: Lambda context object.

    Returns:
        API Gateway response with authentication details.

    Example:
        >>> # With API Key auth  # pragma: allowlist secret
        >>> event = {
        ...     "requestContext": {
        ...         "identity": {"apiKeyId": "abc123"}
        ...     }
        ... }
        >>> response = handler(event, None)
        >>> print(response["statusCode"])
        200
    """
    # Extract authentication context
    auth = extract_auth_context(event)

    # Build response based on auth type
    if auth.is_authenticated():
        response_body = {
            "message": "Authenticated!",
            "auth_type": auth.auth_type.value,
            "user": auth.get_user_identifier(),
        }

        # Add auth-type specific information
        if auth.auth_type == AuthType.API_KEY:
            response_body["api_key_id"] = auth.api_key_id

        elif auth.auth_type == AuthType.IAM:
            response_body["iam_principal"] = auth.iam_principal
            response_body["iam_account"] = auth.iam_account

        elif auth.auth_type == AuthType.COGNITO:
            response_body["cognito_username"] = auth.cognito_username
            response_body["cognito_email"] = auth.cognito_email
            response_body["cognito_groups"] = auth.cognito_groups
            # Include selected claims (be careful with sensitive data)
            safe_claims = {
                k: v
                for k, v in auth.cognito_claims.items()
                if k in ("email", "cognito:username", "sub", "email_verified")
            }
            response_body["claims"] = safe_claims

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Powered-By": "AWS API Factory",
            },
            "body": json.dumps(response_body),
        }

    else:
        # No authentication - return 401
        # Note: API Gateway should return 401/403 before reaching here
        # if auth is configured on the route. This is a fallback.
        return {
            "statusCode": 401,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(
                {
                    "error": "Authentication required",
                    "message": "Please provide valid authentication credentials",
                }
            ),
        }


@require_auth()
def protected_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handler that requires any form of authentication.

    This uses the @require_auth() decorator which automatically:
    - Checks for authentication
    - Returns 401 if not authenticated
    - Attaches auth context to the event

    Args:
        event: API Gateway event (auth context attached by decorator).
        context: Lambda context object.

    Returns:
        API Gateway response.
    """
    # Auth context is attached by the decorator
    auth: AuthContext = event.get("authContext")  # type: ignore

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": f"Hello, {auth.get_user_identifier()}!",
                "auth_type": auth.auth_type.value,
            }
        ),
    }


@require_cognito_auth(required_groups=["admin"])
def admin_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handler that requires Cognito authentication with admin group.

    This demonstrates how to restrict access to specific Cognito groups.
    Only users in the "admin" group can access this handler.

    Args:
        event: API Gateway event.
        context: Lambda context object.

    Returns:
        API Gateway response.
    """
    auth: AuthContext = event.get("authContext")  # type: ignore

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "Admin access granted",
                "username": auth.cognito_username,
                "groups": auth.cognito_groups,
            }
        ),
    }


def whoami_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Debug handler that returns full authentication context.

    This is useful for debugging and testing authentication setup.
    It returns the complete auth context as JSON.

    WARNING: Do not use this in production as it may expose
    sensitive information.

    Args:
        event: API Gateway event.
        context: Lambda context object.

    Returns:
        API Gateway response with full auth context.
    """
    auth = extract_auth_context(event)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(auth.to_dict(), indent=2),
    }
