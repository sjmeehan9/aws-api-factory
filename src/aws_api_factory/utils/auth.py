# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Lambda authentication utilities for AWS API Factory.

This module provides helper functions for Lambda handlers to:
- Extract authentication context from API Gateway events
- Validate authentication in handlers
- Get user information from different auth types

These utilities work with all three authentication modes:
- API Key: Extracts the API key from headers
- IAM: Extracts the IAM principal (ARN, account, user)
- Cognito: Extracts JWT claims (username, email, groups)

Example:
    >>> from aws_api_factory.utils.auth import extract_auth_context
    >>>
    >>> def handler(event, context):
    ...     auth = extract_auth_context(event)
    ...     if auth.auth_type == "cognito":
    ...         username = auth.cognito_claims.get("cognito:username")
    ...         print(f"Authenticated user: {username}")
    ...     return {"statusCode": 200, "body": "OK"}

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar

# Type variable for decorator return type
F = TypeVar("F", bound=Callable[..., Any])


class AuthType(str, Enum):
    """Authentication type detected from API Gateway event.

    Attributes:
        NONE: No authentication present.
        API_KEY: API key authentication.
        IAM: IAM (SigV4) authentication.
        COGNITO: Cognito JWT authentication.
    """

    NONE = "none"
    API_KEY = "api_key"  # pragma: allowlist secret
    IAM = "iam"
    COGNITO = "cognito"


@dataclass
class AuthContext:
    """Authentication context extracted from API Gateway event.

    This dataclass contains all authentication information that can be
    extracted from an API Gateway event. Different fields are populated
    depending on the authentication type.

    Attributes:
        auth_type: The type of authentication used.
        api_key: The API key (masked) if API key auth was used.
        api_key_id: The API key ID if API key auth was used.
        iam_principal: The IAM principal ARN if IAM auth was used.
        iam_user: The IAM user/role name if IAM auth was used.
        iam_account: The AWS account ID if IAM auth was used.
        cognito_username: The Cognito username if Cognito auth was used.
        cognito_email: The user's email if Cognito auth was used.
        cognito_sub: The Cognito user subject (unique ID).
        cognito_groups: List of Cognito groups the user belongs to.
        cognito_claims: All JWT claims from the Cognito token.
        source_ip: The client's source IP address.
        user_agent: The client's User-Agent header.
        request_id: The API Gateway request ID (for correlation).

    Example:
        >>> auth = extract_auth_context(event)
        >>> print(f"Auth type: {auth.auth_type}")
        >>> if auth.cognito_username:
        ...     print(f"User: {auth.cognito_username}")
    """

    auth_type: AuthType = AuthType.NONE

    # API Key auth fields
    api_key: str | None = None
    api_key_id: str | None = None

    # IAM auth fields
    iam_principal: str | None = None
    iam_user: str | None = None
    iam_account: str | None = None

    # Cognito auth fields
    cognito_username: str | None = None
    cognito_email: str | None = None
    cognito_sub: str | None = None
    cognito_groups: list[str] = field(default_factory=list)
    cognito_claims: dict[str, Any] = field(default_factory=dict)

    # Common fields
    source_ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None

    def is_authenticated(self) -> bool:
        """Check if the request is authenticated.

        Returns:
            True if any form of authentication was detected.
        """
        return self.auth_type != AuthType.NONE

    def get_user_identifier(self) -> str | None:
        """Get a user identifier regardless of auth type.

        Returns the most appropriate user identifier based on auth type:
        - Cognito: cognito_username or cognito_sub
        - IAM: iam_user
        - API Key: api_key_id
        - None: None

        Returns:
            A user identifier string or None.
        """
        if self.auth_type == AuthType.COGNITO:
            return self.cognito_username or self.cognito_sub
        elif self.auth_type == AuthType.IAM:
            return self.iam_user
        elif self.auth_type == AuthType.API_KEY:
            return self.api_key_id
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the auth context.
        """
        return {
            "auth_type": self.auth_type.value,
            "is_authenticated": self.is_authenticated(),
            "user_identifier": self.get_user_identifier(),
            "api_key_id": self.api_key_id,
            "iam_principal": self.iam_principal,
            "iam_user": self.iam_user,
            "iam_account": self.iam_account,
            "cognito_username": self.cognito_username,
            "cognito_email": self.cognito_email,
            "cognito_sub": self.cognito_sub,
            "cognito_groups": self.cognito_groups,
            "source_ip": self.source_ip,
            "request_id": self.request_id,
        }


def extract_auth_context(event: dict[str, Any]) -> AuthContext:
    """Extract authentication context from an API Gateway event.

    This function examines the API Gateway event to determine what
    authentication was used and extracts relevant information.

    Args:
        event: The API Gateway Lambda event.

    Returns:
        AuthContext with extracted authentication information.

    Example:
        >>> def handler(event, context):
        ...     auth = extract_auth_context(event)
        ...     if auth.auth_type == AuthType.COGNITO:
        ...         return {
        ...             "statusCode": 200,
        ...             "body": json.dumps({"user": auth.cognito_username})
        ...         }
        ...     return {"statusCode": 401, "body": "Unauthorized"}
    """
    context = AuthContext()

    # Extract common fields
    request_context = event.get("requestContext", {})
    context.request_id = request_context.get("requestId")

    identity = request_context.get("identity", {})
    context.source_ip = identity.get("sourceIp")
    context.user_agent = identity.get("userAgent")

    # Check for API Key authentication
    api_key = identity.get("apiKey")
    api_key_id = identity.get("apiKeyId")
    if api_key_id:
        context.auth_type = AuthType.API_KEY
        context.api_key_id = api_key_id
        # Mask the API key for security (show last 4 chars only)
        if api_key:
            context.api_key = f"****{api_key[-4:]}" if len(api_key) > 4 else "****"
        return context

    # Check for IAM authentication
    user_arn = identity.get("userArn")
    if user_arn:
        context.auth_type = AuthType.IAM
        context.iam_principal = user_arn
        context.iam_account = identity.get("accountId")
        # Extract user/role name from ARN
        # ARN format: arn:aws:iam::123456789012:user/username
        # or: arn:aws:sts::123456789012:assumed-role/role-name/session
        if user_arn:
            arn_parts = user_arn.split("/")
            if len(arn_parts) >= 2:
                context.iam_user = arn_parts[-1]
        return context

    # Check for Cognito authentication
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    if claims:
        context.auth_type = AuthType.COGNITO
        context.cognito_claims = claims
        context.cognito_sub = claims.get("sub")
        context.cognito_username = claims.get("cognito:username")
        context.cognito_email = claims.get("email")
        # Parse groups from the token
        groups = claims.get("cognito:groups")
        if groups:
            if isinstance(groups, str):
                # Groups might be a comma-separated string
                context.cognito_groups = [g.strip() for g in groups.split(",")]
            elif isinstance(groups, list):
                context.cognito_groups = groups
        return context

    # No authentication detected
    return context


def get_cognito_claims(event: dict[str, Any]) -> dict[str, Any]:
    """Extract Cognito JWT claims from an API Gateway event.

    This is a convenience function for getting just the Cognito claims.

    Args:
        event: The API Gateway Lambda event.

    Returns:
        Dictionary of JWT claims (empty if not Cognito auth).

    Example:
        >>> claims = get_cognito_claims(event)
        >>> email = claims.get("email")
        >>> username = claims.get("cognito:username")
    """
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    return authorizer.get("claims", {})


def get_api_key_id(event: dict[str, Any]) -> str | None:
    """Extract the API key ID from an API Gateway event.

    Args:
        event: The API Gateway Lambda event.

    Returns:
        The API key ID or None if not present.
    """
    request_context = event.get("requestContext", {})
    identity = request_context.get("identity", {})
    return identity.get("apiKeyId")


def get_iam_principal(event: dict[str, Any]) -> str | None:
    """Extract the IAM principal ARN from an API Gateway event.

    Args:
        event: The API Gateway Lambda event.

    Returns:
        The IAM principal ARN or None if not present.
    """
    request_context = event.get("requestContext", {})
    identity = request_context.get("identity", {})
    return identity.get("userArn")


class AuthenticationError(Exception):
    """Exception raised when authentication fails.

    Attributes:
        message: Error message.
        status_code: HTTP status code (401 or 403).
    """

    def __init__(self, message: str, status_code: int = 401):
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code (default 401 Unauthorized).
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def require_auth(
    allowed_auth_types: list[AuthType] | None = None,
    required_groups: list[str] | None = None,
) -> Callable[[F], F]:
    """Decorator to require authentication for a Lambda handler.

    This decorator validates that the request is authenticated and
    optionally checks for specific auth types or Cognito groups.

    Args:
        allowed_auth_types: List of allowed authentication types.
            If None, any authenticated request is allowed.
        required_groups: List of required Cognito groups.
            User must belong to at least one of these groups.

    Returns:
        Decorated handler function.

    Example:
        >>> @require_auth()
        ... def handler(event, context):
        ...     # Only authenticated requests reach here
        ...     return {"statusCode": 200, "body": "OK"}
        >>>
        >>> @require_auth(required_groups=["admin"])
        ... def admin_handler(event, context):
        ...     # Only users in the "admin" group reach here
        ...     return {"statusCode": 200, "body": "Admin access granted"}
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(event: dict[str, Any], context: Any) -> dict[str, Any]:
            try:
                auth = extract_auth_context(event)

                # Check if authenticated
                if not auth.is_authenticated():
                    raise AuthenticationError("Authentication required", 401)

                # Check allowed auth types
                if allowed_auth_types and auth.auth_type not in allowed_auth_types:
                    raise AuthenticationError(
                        f"Authentication type '{auth.auth_type.value}' not allowed",
                        403,
                    )

                # Check required groups (only applies to Cognito)
                if required_groups and auth.auth_type == AuthType.COGNITO:
                    if not any(g in auth.cognito_groups for g in required_groups):
                        raise AuthenticationError(
                            f"User not in required groups: {required_groups}",
                            403,
                        )

                # Attach auth context to event for handler access
                event["authContext"] = auth

                return func(event, context)

            except AuthenticationError as e:
                return {
                    "statusCode": e.status_code,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": e.message}),
                }

        return wrapper  # type: ignore

    return decorator


def require_cognito_auth(required_groups: list[str] | None = None) -> Callable[[F], F]:
    """Decorator to require Cognito authentication.

    This is a convenience decorator that requires Cognito auth specifically.

    Args:
        required_groups: Optional list of required Cognito groups.

    Returns:
        Decorated handler function.

    Example:
        >>> @require_cognito_auth()
        ... def handler(event, context):
        ...     auth = event.get("authContext")
        ...     return {
        ...         "statusCode": 200,
        ...         "body": json.dumps({"user": auth.cognito_username})
        ...     }
    """
    return require_auth(
        allowed_auth_types=[AuthType.COGNITO],
        required_groups=required_groups,
    )


def require_iam_auth() -> Callable[[F], F]:
    """Decorator to require IAM authentication.

    This is a convenience decorator that requires IAM auth specifically.

    Returns:
        Decorated handler function.

    Example:
        >>> @require_iam_auth()
        ... def internal_handler(event, context):
        ...     auth = event.get("authContext")
        ...     return {
        ...         "statusCode": 200,
        ...         "body": json.dumps({"caller": auth.iam_principal})
        ...     }
    """
    return require_auth(allowed_auth_types=[AuthType.IAM])


def require_api_key() -> Callable[[F], F]:
    """Decorator to require API key authentication.

    This is a convenience decorator that requires API key auth specifically.

    Returns:
        Decorated handler function.

    Example:
        >>> @require_api_key()
        ... def partner_api_handler(event, context):
        ...     auth = event.get("authContext")
        ...     return {
        ...         "statusCode": 200,
        ...         "body": json.dumps({"api_key_id": auth.api_key_id})
        ...     }
    """
    return require_auth(allowed_auth_types=[AuthType.API_KEY])
