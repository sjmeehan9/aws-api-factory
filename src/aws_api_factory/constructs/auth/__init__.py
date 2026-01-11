# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Authentication module for AWS API Factory.

This module provides CDK constructs for implementing authentication on
API Gateway REST APIs. Three authentication modes are supported:

- **API Key**: Usage plans with rate limiting for partner/internal APIs
- **IAM**: AWS IAM authentication with SigV4 signing for service-to-service
- **Cognito**: JWT authorization with Cognito User Pools for user-facing APIs

Each construct integrates with the RestApiConstruct to apply authentication
at the route level based on factory.yaml configuration.

Example:
    >>> from aws_api_factory.constructs.auth import (
    ...     ApiKeyAuthConstruct,
    ...     CognitoAuthConstruct,
    ...     apply_auth_to_method,
    ... )
    >>>
    >>> # Create API key auth
    >>> api_key_auth = ApiKeyAuthConstruct(
    ...     stack, "ApiKeyAuth",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     api=rest_api.api,
    ... )
    >>>
    >>> # Apply to methods
    >>> for method in api_key_methods:
    ...     api_key_auth.require_api_key(method)

Auth Mode Selection Guide:
    - **API Key**: Best for partner integrations, rate limiting, usage tracking.
      NOT suitable for end-user authentication.
    - **IAM**: Best for AWS service-to-service calls, internal microservices.
      Requires AWS credentials on the client side.
    - **Cognito**: Best for user-facing applications with user registration,
      login flows, and JWT-based authentication.

"""

from aws_api_factory.constructs.auth.api_key import ApiKeyAuthConstruct
from aws_api_factory.constructs.auth.cognito import CognitoAuthConstruct
from aws_api_factory.constructs.auth.helpers import (
    AuthConstructs,
    apply_auth_to_method,
    create_auth_constructs,
    get_auth_mode_for_route,
    get_authorization_type,
    get_method_options,
    get_required_auth_modes,
    validate_auth_config,
)
from aws_api_factory.constructs.auth.iam import IamAuthConstruct

__all__ = [
    # Auth constructs
    "ApiKeyAuthConstruct",
    "IamAuthConstruct",
    "CognitoAuthConstruct",
    # Helper classes
    "AuthConstructs",
    # Helper functions
    "apply_auth_to_method",
    "create_auth_constructs",
    "get_auth_mode_for_route",
    "get_authorization_type",
    "get_method_options",
    "get_required_auth_modes",
    "validate_auth_config",
]
