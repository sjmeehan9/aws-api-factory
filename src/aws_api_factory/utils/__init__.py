# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS API Factory Utilities.

This module provides shared utility functions used across the library,
including authentication helpers for Lambda handlers.

Submodules:
    auth: Authentication utilities for Lambda handlers

Example:
    >>> from aws_api_factory.utils.auth import (
    ...     extract_auth_context,
    ...     require_auth,
    ...     AuthContext,
    ...     AuthType,
    ... )
    >>>
    >>> @require_auth()
    ... def handler(event, context):
    ...     auth = event.get("authContext")
    ...     return {"statusCode": 200, "body": f"Hello {auth.get_user_identifier()}"}

"""

from aws_api_factory.utils.auth import (
    AuthContext,
    AuthenticationError,
    AuthType,
    extract_auth_context,
    get_api_key_id,
    get_cognito_claims,
    get_iam_principal,
    require_api_key,
    require_auth,
    require_cognito_auth,
    require_iam_auth,
)

__all__ = [
    # Auth context
    "AuthContext",
    "AuthType",
    "AuthenticationError",
    # Extraction functions
    "extract_auth_context",
    "get_cognito_claims",
    "get_api_key_id",
    "get_iam_principal",
    # Decorators
    "require_auth",
    "require_cognito_auth",
    "require_iam_auth",
    "require_api_key",
]
