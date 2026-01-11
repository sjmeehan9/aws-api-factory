# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""HTTP integration for API Gateway to App Runner.

This module provides functions for creating API Gateway HTTP integrations
to proxy requests to App Runner services.

Example:
    >>> from aws_api_factory.constructs.rest_api.http_integration import (
    ...     create_http_integration,
    ...     attach_http_integration_to_routes,
    ... )
    >>> integration = create_http_integration(app_runner_url)
    >>> attach_http_integration_to_routes(api, routes, integration)

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aws_cdk import Duration
from aws_cdk import aws_apigateway as apigw

if TYPE_CHECKING:
    from aws_api_factory.config.models import RouteConfig


def create_http_integration(
    backend_url: str,
    *,
    timeout: Duration | None = None,
    connection_type: apigw.ConnectionType = apigw.ConnectionType.INTERNET,
) -> apigw.HttpIntegration:
    """Create an HTTP integration for proxying to a backend service.

    Creates an HTTP_PROXY integration that forwards requests to the
    specified backend URL, preserving headers and request body.

    Args:
        backend_url: The backend service URL (e.g., App Runner service URL).
        timeout: Integration timeout. Defaults to 29 seconds (API Gateway max).
        connection_type: Connection type. Defaults to INTERNET.

    Returns:
        An HttpIntegration configured for proxying.

    Example:
        >>> integration = create_http_integration(
        ...     "https://abc123.us-east-1.awsapprunner.com"
        ... )
    """
    return apigw.HttpIntegration(
        url=backend_url,
        http_method="ANY",
        proxy=True,
        options=apigw.IntegrationOptions(
            timeout=timeout or Duration.seconds(29),
            connection_type=connection_type,
            passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
        ),
    )


def create_http_proxy_integration(
    backend_url: str,
    path: str = "",
    *,
    timeout: Duration | None = None,
) -> apigw.HttpIntegration:
    """Create an HTTP proxy integration with path forwarding.

    Creates an HTTP_PROXY integration that forwards requests to the
    backend URL with the specified path appended.

    Args:
        backend_url: The backend service URL (without trailing slash).
        path: Path to append to the backend URL (e.g., "/api/v1").
        timeout: Integration timeout. Defaults to 29 seconds.

    Returns:
        An HttpIntegration configured for proxying with path forwarding.

    Example:
        >>> integration = create_http_proxy_integration(
        ...     "https://abc123.us-east-1.awsapprunner.com",
        ...     path="/api"
        ... )
    """
    # Ensure path doesn't have trailing slash
    clean_path = path.rstrip("/") if path else ""
    full_url = f"{backend_url.rstrip('/')}{clean_path}"

    return apigw.HttpIntegration(
        url=full_url,
        http_method="ANY",
        proxy=True,
        options=apigw.IntegrationOptions(
            timeout=timeout or Duration.seconds(29),
            passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
        ),
    )


def attach_http_integration_to_resource(
    resource: apigw.IResource,
    http_method: str,
    integration: apigw.HttpIntegration,
    *,
    authorization_type: apigw.AuthorizationType = apigw.AuthorizationType.NONE,
    api_key_required: bool = False,
) -> apigw.Method:
    """Attach an HTTP integration to an API Gateway resource.

    Args:
        resource: The API Gateway resource to add the method to.
        http_method: The HTTP method (GET, POST, etc.) or "ANY".
        integration: The HTTP integration to attach.
        authorization_type: Authorization type for the method.
        api_key_required: Whether an API key is required.

    Returns:
        The created Method.

    Example:
        >>> method = attach_http_integration_to_resource(
        ...     resource=api.root.add_resource("orders"),
        ...     http_method="GET",
        ...     integration=integration,
        ... )
    """
    return resource.add_method(
        http_method,
        integration,
        authorization_type=authorization_type,
        api_key_required=api_key_required,
    )


def attach_http_integration_to_routes(
    api: apigw.RestApi,
    routes: list[RouteConfig],
    backend_url: str,
    *,
    timeout: Duration | None = None,
) -> dict[str, apigw.Method]:
    """Attach HTTP integrations to multiple API Gateway routes.

    Creates resources and methods for each route, all proxying to
    the same backend URL with path forwarding.

    Args:
        api: The API Gateway RestApi.
        routes: List of route configurations.
        backend_url: The backend service URL to proxy to.
        timeout: Integration timeout for all routes.

    Returns:
        Dictionary mapping "path:METHOD" to created Method.

    Example:
        >>> methods = attach_http_integration_to_routes(
        ...     api=rest_api,
        ...     routes=config.apis.rest.routes,
        ...     backend_url="https://abc123.us-east-1.awsapprunner.com",
        ... )
    """
    methods: dict[str, apigw.Method] = {}
    resources: dict[str, apigw.IResource] = {}

    for route in routes:
        # Get or create the resource for this path
        resource = _get_or_create_resource(api, route.path, resources)

        # Create integration with path forwarding
        integration = create_http_proxy_integration(
            backend_url, route.path, timeout=timeout
        )

        # Determine authorization type
        auth_type = apigw.AuthorizationType.NONE
        if route.auth.value == "iam":
            auth_type = apigw.AuthorizationType.IAM
        api_key_required = route.auth.value == "api_key"

        # Create methods for each HTTP method
        for method in route.methods:
            method_key = f"{route.path}:{method.value}"

            api_method = resource.add_method(
                method.value,
                integration,
                authorization_type=auth_type,
                api_key_required=api_key_required,
            )
            methods[method_key] = api_method

    return methods


def _get_or_create_resource(
    api: apigw.RestApi,
    path: str,
    cache: dict[str, apigw.IResource],
) -> apigw.IResource:
    """Get or create an API Gateway resource for a path.

    Args:
        api: The API Gateway RestApi.
        path: The API path (e.g., "/orders/{orderId}").
        cache: Cache of already created resources.

    Returns:
        The API Gateway Resource for the path.
    """
    if path in cache:
        return cache[path]

    # Start from root
    current_resource: apigw.IResource = api.root

    # Split path and create/get each segment
    clean_path = path.strip("/")
    if not clean_path:
        return current_resource

    segments = clean_path.split("/")
    current_path = ""

    for segment in segments:
        current_path = f"{current_path}/{segment}"

        if current_path in cache:
            current_resource = cache[current_path]
        else:
            current_resource = current_resource.add_resource(segment)
            cache[current_path] = current_resource

    return current_resource


def create_catch_all_proxy(
    api: apigw.RestApi,
    backend_url: str,
    *,
    timeout: Duration | None = None,
    authorization_type: apigw.AuthorizationType = apigw.AuthorizationType.NONE,
    api_key_required: bool = False,
) -> dict[str, apigw.Method]:
    """Create a catch-all proxy that forwards all requests to a backend.

    This creates a {proxy+} resource that captures all paths and forwards
    them to the backend service, maintaining the original path.

    Args:
        api: The API Gateway RestApi.
        backend_url: The backend service URL.
        timeout: Integration timeout.
        authorization_type: Authorization type for all methods.
        api_key_required: Whether API key is required.

    Returns:
        Dictionary with "proxy" method.

    Example:
        >>> methods = create_catch_all_proxy(
        ...     api=rest_api,
        ...     backend_url="https://abc123.us-east-1.awsapprunner.com",
        ... )
    """
    # Create the proxy resource
    proxy_resource = api.root.add_resource("{proxy+}")

    # Create HTTP integration with path forwarding
    integration = apigw.HttpIntegration(
        url=f"{backend_url.rstrip('/')}/{{proxy}}",
        http_method="ANY",
        proxy=True,
        options=apigw.IntegrationOptions(
            timeout=timeout or Duration.seconds(29),
            passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
            request_parameters={
                "integration.request.path.proxy": "method.request.path.proxy",
            },
        ),
    )

    # Add ANY method to handle all HTTP methods
    method = proxy_resource.add_method(
        "ANY",
        integration,
        authorization_type=authorization_type,
        api_key_required=api_key_required,
        request_parameters={
            "method.request.path.proxy": True,
        },
    )

    # Also add a root handler
    root_integration = create_http_integration(backend_url, timeout=timeout)
    root_method = api.root.add_method(
        "ANY",
        root_integration,
        authorization_type=authorization_type,
        api_key_required=api_key_required,
    )

    return {
        "proxy": method,
        "root": root_method,
    }
