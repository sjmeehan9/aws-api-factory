# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Helper functions for authentication module.

This module provides utility functions for:
- Creating auth constructs based on configuration
- Applying authentication to API Gateway methods
- Validating auth configuration
- Determining auth mode for routes

Example:
    >>> from aws_api_factory.constructs.auth import (
    ...     create_auth_constructs,
    ...     apply_auth_to_method,
    ... )
    >>>
    >>> # Create all needed auth constructs based on config
    >>> auth_constructs = create_auth_constructs(
    ...     stack,
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     api=rest_api.api,
    ... )
    >>>
    >>> # Apply auth to a method
    >>> apply_auth_to_method(
    ...     method=api_method,
    ...     auth_mode=AuthModeEnum.COGNITO,
    ...     auth_constructs=auth_constructs,
    ... )

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aws_cdk import aws_apigateway as apigw
from constructs import Construct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import AuthModeEnum, FactoryConfig, RouteConfig
    from aws_api_factory.constructs.auth.api_key import ApiKeyAuthConstruct
    from aws_api_factory.constructs.auth.cognito import CognitoAuthConstruct
    from aws_api_factory.constructs.auth.iam import IamAuthConstruct
    from aws_api_factory.constructs.outputs import OutputManager


@dataclass
class AuthConstructs:
    """Container for all authentication constructs.

    This dataclass holds references to all authentication constructs
    that have been created based on configuration. Only constructs
    that are needed (based on route auth settings) are populated.

    Attributes:
        api_key: API Key authentication construct (if any route uses api_key auth).
        iam: IAM authentication construct (if any route uses iam auth).
        cognito: Cognito authentication construct (if any route uses cognito auth).

    Example:
        >>> auth = create_auth_constructs(...)
        >>> if auth.cognito:
        ...     print(f"Cognito Pool: {auth.cognito.user_pool.user_pool_id}")
    """

    api_key: "ApiKeyAuthConstruct | None" = None  # pragma: allowlist secret
    iam: "IamAuthConstruct | None" = None
    cognito: "CognitoAuthConstruct | None" = None

    def has_any_auth(self) -> bool:
        """Check if any auth construct was created.

        Returns:
            True if at least one auth construct exists.
        """
        return any([self.api_key, self.iam, self.cognito])


def validate_auth_config(config: "FactoryConfig") -> list[str]:
    """Validate authentication configuration.

    Checks that:
    - Routes using cognito auth have cognito config provided
    - Auth modes are valid
    - No conflicting auth settings

    Args:
        config: The factory configuration to validate.

    Returns:
        List of validation error messages (empty if valid).

    Example:
        >>> errors = validate_auth_config(config)
        >>> if errors:
        ...     print("Auth configuration errors:")
        ...     for error in errors:
        ...         print(f"  - {error}")
    """
    errors: list[str] = []

    rest_config = config.apis.rest
    if not rest_config.enabled:
        return errors

    # Collect auth modes used across routes
    from aws_api_factory.config.models import AuthModeEnum

    auth_modes_used = set()
    for route in rest_config.routes:
        auth_modes_used.add(route.auth)

    # Check Cognito configuration
    if AuthModeEnum.COGNITO in auth_modes_used:
        if not rest_config.cognito:
            cognito_routes = [
                r.path for r in rest_config.routes if r.auth == AuthModeEnum.COGNITO
            ]
            errors.append(
                f"Routes {cognito_routes} use 'cognito' auth but no cognito "
                "configuration is provided in 'apis.rest.cognito'"
            )
        elif rest_config.cognito.user_pool_id and rest_config.cognito.create_user_pool:
            errors.append(
                "Cannot specify both 'user_pool_id' and 'create_user_pool: true' "
                "in cognito configuration"
            )

    return errors


def get_auth_mode_for_route(route: "RouteConfig") -> "AuthModeEnum":
    """Get the authentication mode for a route.

    Args:
        route: The route configuration.

    Returns:
        The authentication mode enum.

    Example:
        >>> auth_mode = get_auth_mode_for_route(route)
        >>> if auth_mode == AuthModeEnum.API_KEY:
        ...     print("This route requires an API key")
    """
    return route.auth


def get_required_auth_modes(config: "FactoryConfig") -> set["AuthModeEnum"]:
    """Get all authentication modes required by the configuration.

    Args:
        config: The factory configuration.

    Returns:
        Set of authentication modes used in routes.

    Example:
        >>> modes = get_required_auth_modes(config)
        >>> if AuthModeEnum.COGNITO in modes:
        ...     print("Cognito auth is needed")
    """
    from aws_api_factory.config.models import AuthModeEnum

    modes: set[AuthModeEnum] = set()

    rest_config = config.apis.rest
    if rest_config.enabled:
        for route in rest_config.routes:
            if route.auth != AuthModeEnum.NONE:
                modes.add(route.auth)

    return modes


def create_auth_constructs(
    scope: Construct,
    *,
    config: "FactoryConfig",
    profile_defaults: "ProfileDefaults",
    output_manager: "OutputManager",
    environment: str,
    api: apigw.RestApi,
) -> AuthConstructs:
    """Create authentication constructs based on configuration.

    This function inspects the routes in the configuration and creates
    only the auth constructs that are needed. For example, if no routes
    use cognito auth, no Cognito User Pool will be created.

    Args:
        scope: The CDK construct scope.
        config: The factory configuration.
        profile_defaults: Profile defaults for auth settings.
        output_manager: Output manager for registering outputs.
        environment: Deployment environment name.
        api: The REST API to apply authentication to.

    Returns:
        AuthConstructs containing the created auth constructs.

    Example:
        >>> auth = create_auth_constructs(
        ...     stack,
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
        >>> if auth.api_key:
        ...     print("API Key auth created")
    """
    from aws_api_factory.config.models import AuthModeEnum
    from aws_api_factory.constructs.auth.api_key import ApiKeyAuthConstruct
    from aws_api_factory.constructs.auth.cognito import CognitoAuthConstruct
    from aws_api_factory.constructs.auth.iam import IamAuthConstruct

    result = AuthConstructs()
    required_modes = get_required_auth_modes(config)

    # Create API Key auth if needed
    if AuthModeEnum.API_KEY in required_modes:
        result.api_key = ApiKeyAuthConstruct(
            scope,
            "ApiKeyAuth",
            config=config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment=environment,
            api=api,
        )

    # Create IAM auth if needed
    if AuthModeEnum.IAM in required_modes:
        result.iam = IamAuthConstruct(
            scope,
            "IamAuth",
            config=config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment=environment,
            api=api,
        )

    # Create Cognito auth if needed
    if AuthModeEnum.COGNITO in required_modes:
        # Get existing user pool ID from config if specified
        existing_pool_id = None
        rest_config = config.apis.rest
        if rest_config.cognito and rest_config.cognito.user_pool_id:
            existing_pool_id = rest_config.cognito.user_pool_id

        result.cognito = CognitoAuthConstruct(
            scope,
            "CognitoAuth",
            config=config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment=environment,
            api=api,
            existing_user_pool_id=existing_pool_id,
        )

    return result


def apply_auth_to_method(
    method: apigw.Method,
    auth_mode: "AuthModeEnum",
    auth_constructs: AuthConstructs,
) -> None:
    """Apply authentication to an API Gateway method.

    This function configures the method's authorization based on the
    specified auth mode. The auth construct must already be created
    and available in auth_constructs.

    Note: For API Gateway, most auth configuration must be done at
    method creation time. This function is primarily for documentation
    and verification purposes. The actual auth is applied in the
    RestApiConstruct during method creation.

    Args:
        method: The API Gateway method to protect.
        auth_mode: The authentication mode to apply.
        auth_constructs: Container with created auth constructs.

    Example:
        >>> apply_auth_to_method(
        ...     method=get_orders_method,
        ...     auth_mode=AuthModeEnum.COGNITO,
        ...     auth_constructs=auth_constructs,
        ... )
    """
    from aws_api_factory.config.models import AuthModeEnum

    if auth_mode == AuthModeEnum.NONE:
        # No authentication required
        return

    if auth_mode == AuthModeEnum.API_KEY:
        if not auth_constructs.api_key:
            raise ValueError(
                "API Key auth requested but ApiKeyAuthConstruct not created"
            )
        # API key requirement is set at method creation
        auth_constructs.api_key.require_api_key(method)

    elif auth_mode == AuthModeEnum.IAM:
        if not auth_constructs.iam:
            raise ValueError("IAM auth requested but IamAuthConstruct not created")
        # IAM auth is set at method creation
        pass

    elif auth_mode == AuthModeEnum.COGNITO:
        if not auth_constructs.cognito:
            raise ValueError(
                "Cognito auth requested but CognitoAuthConstruct not created"
            )
        # Cognito auth is set at method creation
        auth_constructs.cognito.apply_cognito_auth_to_method(method)


def get_authorization_type(auth_mode: "AuthModeEnum") -> apigw.AuthorizationType:
    """Get the API Gateway AuthorizationType for an auth mode.

    Args:
        auth_mode: The authentication mode.

    Returns:
        The corresponding API Gateway AuthorizationType.

    Example:
        >>> auth_type = get_authorization_type(AuthModeEnum.IAM)
        >>> # Returns AuthorizationType.IAM
    """
    from aws_api_factory.config.models import AuthModeEnum

    mapping = {
        AuthModeEnum.NONE: apigw.AuthorizationType.NONE,
        AuthModeEnum.API_KEY: apigw.AuthorizationType.NONE,  # API key uses separate flag
        AuthModeEnum.IAM: apigw.AuthorizationType.IAM,
        AuthModeEnum.COGNITO: apigw.AuthorizationType.COGNITO,
    }

    return mapping.get(auth_mode, apigw.AuthorizationType.NONE)


def get_method_options(
    auth_mode: "AuthModeEnum",
    auth_constructs: AuthConstructs,
) -> dict[str, Any]:
    """Get API Gateway method options for an auth mode.

    This function returns the options that should be passed to
    `resource.add_method()` to configure authentication properly.

    Args:
        auth_mode: The authentication mode.
        auth_constructs: Container with created auth constructs.

    Returns:
        Dictionary of method options.

    Example:
        >>> options = get_method_options(AuthModeEnum.COGNITO, auth_constructs)
        >>> method = resource.add_method("GET", integration, **options)
    """
    from aws_api_factory.config.models import AuthModeEnum

    options: dict[str, Any] = {}

    if auth_mode == AuthModeEnum.NONE:
        options["authorization_type"] = apigw.AuthorizationType.NONE
        options["api_key_required"] = False

    elif auth_mode == AuthModeEnum.API_KEY:
        options["authorization_type"] = apigw.AuthorizationType.NONE
        options["api_key_required"] = True

    elif auth_mode == AuthModeEnum.IAM:
        options["authorization_type"] = apigw.AuthorizationType.IAM
        options["api_key_required"] = False

    elif auth_mode == AuthModeEnum.COGNITO:
        options["authorization_type"] = apigw.AuthorizationType.COGNITO
        options["api_key_required"] = False
        if auth_constructs.cognito and auth_constructs.cognito.authorizer:
            options["authorizer"] = auth_constructs.cognito.authorizer

    return options
