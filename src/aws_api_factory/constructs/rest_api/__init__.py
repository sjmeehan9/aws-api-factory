# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""REST API constructs for AWS API Factory.

This module provides CDK constructs for deploying Amazon API Gateway REST APIs
with Lambda or HTTP backend integrations configured via factory.yaml.

Classes:
    RestApiConstruct: Creates API Gateway REST API with routes and integrations.
    RestLambdaConstruct: Combined construct for REST API with Lambda backend.

Functions:
    create_lambda_integration: Create Lambda proxy integration for a route.
    create_api_resource: Create API Gateway resource for a path.

Example:
    >>> from aws_api_factory.constructs.rest_api import RestApiConstruct
    >>> rest_api = RestApiConstruct(
    ...     stack, "RestApi",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     lambda_functions=lambdas.functions,
    ... )

"""

from aws_api_factory.constructs.rest_api.api import RestApiConstruct
from aws_api_factory.constructs.rest_api.http_integration import (
    attach_http_integration_to_resource,
    attach_http_integration_to_routes,
    create_catch_all_proxy,
    create_http_integration,
    create_http_proxy_integration,
)
from aws_api_factory.constructs.rest_api.lambda_integration import (
    attach_lambda_integration,
    create_lambda_integration,
    grant_api_invoke_permission,
)
from aws_api_factory.constructs.rest_api.rest_lambda import RestLambdaConstruct

__all__ = [
    # Constructs
    "RestApiConstruct",
    "RestLambdaConstruct",
    # Lambda integration
    "attach_lambda_integration",
    "create_lambda_integration",
    "grant_api_invoke_permission",
    # HTTP integration (for App Runner)
    "attach_http_integration_to_resource",
    "attach_http_integration_to_routes",
    "create_catch_all_proxy",
    "create_http_integration",
    "create_http_proxy_integration",
]
