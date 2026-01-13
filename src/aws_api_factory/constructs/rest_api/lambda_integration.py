# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Lambda integration helpers for API Gateway REST API.

This module provides helper functions for creating and configuring
Lambda proxy integrations with API Gateway.

Example:
    >>> from aws_cdk import aws_lambda as lambda_
    >>> from aws_api_factory.constructs.rest_api.lambda_integration import (
    ...     create_lambda_integration,
    ...     grant_api_invoke_permission,
    ... )
    >>> integration = create_lambda_integration(lambda_function)
    >>> grant_api_invoke_permission(api, lambda_function)

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam

if TYPE_CHECKING:
    from aws_cdk import aws_lambda as lambda_


def create_lambda_integration(
    lambda_function: lambda_.Function,
    *,
    proxy: bool = True,
    allow_test_invoke: bool = True,
    cache_key_parameters: list[str] | None = None,
    cache_namespace: str | None = None,
    passthrough_behavior: apigw.PassthroughBehavior | None = None,
) -> apigw.LambdaIntegration:
    """Create a Lambda proxy integration for API Gateway.

    Creates an API Gateway integration that forwards requests to a Lambda
    function using proxy integration. With proxy integration, the entire
    request is passed to Lambda and the response is returned directly.

    Args:
        lambda_function: The Lambda function to integrate with.
        proxy: Whether to use Lambda proxy integration (default: True).
        allow_test_invoke: Allow test invocations from AWS console.
        cache_key_parameters: Parameters to use for caching.
        cache_namespace: Namespace for caching.
        passthrough_behavior: How to handle request body passthrough.

    Returns:
        Configured LambdaIntegration for use with API Gateway methods.

    Example:
        >>> integration = create_lambda_integration(my_lambda_fn)
        >>> resource.add_method("GET", integration)
    """
    return apigw.LambdaIntegration(
        lambda_function,
        proxy=proxy,
        allow_test_invoke=allow_test_invoke,
        cache_key_parameters=cache_key_parameters,
        cache_namespace=cache_namespace,
        passthrough_behavior=passthrough_behavior,
    )


def attach_lambda_integration(
    method: apigw.Method,
    lambda_function: lambda_.Function,
    *,
    proxy: bool = True,
) -> apigw.LambdaIntegration:
    """Attach a Lambda integration to an existing API Gateway method.

    Note: This is a convenience function. In most cases, you should use
    create_lambda_integration() when adding a method.

    Args:
        method: The API Gateway method to attach to.
        lambda_function: The Lambda function to integrate with.
        proxy: Whether to use Lambda proxy integration.

    Returns:
        The created LambdaIntegration.
    """
    integration = create_lambda_integration(lambda_function, proxy=proxy)
    return integration


def grant_api_invoke_permission(
    api: apigw.RestApi,
    lambda_function: lambda_.Function,
    *,
    path: str = "*",
    method: str = "*",
    stage: str = "*",
) -> iam.Grant:
    """Grant API Gateway permission to invoke a Lambda function.

    This is typically handled automatically by LambdaIntegration, but
    this function allows explicit control over permissions.

    Args:
        api: The API Gateway REST API.
        lambda_function: The Lambda function to grant access to.
        path: The API path pattern (default: all paths).
        method: The HTTP method pattern (default: all methods).
        stage: The API stage pattern (default: all stages).

    Returns:
        IAM Grant representing the permission.

    Example:
        >>> grant_api_invoke_permission(api, orders_fn, path="/orders/*")
    """
    # Build the source ARN for the API Gateway
    # Format: arn:aws:execute-api:region:account:api-id/stage/method/path
    source_arn = api.arn_for_execute_api(method=method, path=path, stage=stage)

    return lambda_function.grant_invoke(
        iam.ServicePrincipal(
            "apigateway.amazonaws.com",
            conditions={
                "ArnLike": {"aws:SourceArn": source_arn},
            },
        )
    )


def create_method_response() -> list[apigw.MethodResponse]:
    """Create standard method responses for Lambda proxy integration.

    Returns:
        List of MethodResponse configurations for common HTTP status codes.
    """
    return [
        apigw.MethodResponse(
            status_code="200",
            response_models={"application/json": apigw.Model.EMPTY_MODEL},
        ),
        apigw.MethodResponse(
            status_code="400",
            response_models={"application/json": apigw.Model.ERROR_MODEL},
        ),
        apigw.MethodResponse(
            status_code="500",
            response_models={"application/json": apigw.Model.ERROR_MODEL},
        ),
    ]


def create_integration_response() -> list[apigw.IntegrationResponse]:
    """Create standard integration responses for Lambda proxy integration.

    Note: With Lambda proxy integration, these are typically not needed
    as the Lambda function controls the response format directly.

    Returns:
        List of IntegrationResponse configurations.
    """
    return [
        apigw.IntegrationResponse(
            status_code="200",
        ),
    ]
