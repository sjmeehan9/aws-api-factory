# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Custom validators for AWS API Factory configuration.

This module provides additional validation functions that operate on
loaded configuration to ensure consistency and correctness before
CDK synthesis begins.

These validators complement Pydantic's built-in validation with
cross-cutting checks that are easier to implement as standalone functions.

Example:
    >>> from aws_api_factory.config.validators import validate_config
    >>> errors = validate_config(config)
    >>> if errors:
    ...     raise ValueError(errors)

"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aws_api_factory.config.models import FactoryConfig


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails.

    Attributes:
        errors: List of validation error messages.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = "Configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        super().__init__(message)


def validate_entry_points_exist(
    config: FactoryConfig,
    base_path: Path | None = None,
) -> list[str]:
    """Validate that Lambda handler entry points exist on disk.

    Args:
        config: The factory configuration to validate.
        base_path: Base path to resolve relative paths from.
            Defaults to current working directory.

    Returns:
        List of error messages for missing entry points.
    """
    errors: list[str] = []
    base = base_path or Path.cwd()

    if not config.compute.lambda_.enabled:
        return errors

    for name, service in config.compute.lambda_.services.items():
        # Parse entry point: "path/to/file.py:handler_function"
        entry = service.entry
        if ":" not in entry:
            errors.append(
                f"Service '{name}' has invalid entry format '{entry}'. "
                "Expected format: 'path/to/file.py:handler_function'"
            )
            continue

        file_path, _ = entry.rsplit(":", 1)
        full_path = base / file_path

        if not full_path.exists():
            errors.append(
                f"Service '{name}' entry point file not found: {file_path}. "
                f"Expected at: {full_path}"
            )
        elif not full_path.is_file():
            errors.append(f"Service '{name}' entry point is not a file: {file_path}")

    return errors


def validate_dockerfiles_exist(
    config: FactoryConfig,
    base_path: Path | None = None,
) -> list[str]:
    """Validate that App Runner Dockerfiles exist on disk.

    Args:
        config: The factory configuration to validate.
        base_path: Base path to resolve relative paths from.
            Defaults to current working directory.

    Returns:
        List of error messages for missing Dockerfiles.
    """
    errors: list[str] = []
    base = base_path or Path.cwd()

    if not config.compute.apprunner.enabled:
        return errors

    for name, service in config.compute.apprunner.services.items():
        dockerfile_path = base / service.dockerfile

        if not dockerfile_path.exists():
            errors.append(
                f"Service '{name}' Dockerfile not found: {service.dockerfile}. "
                f"Expected at: {dockerfile_path}"
            )
        elif not dockerfile_path.is_file():
            errors.append(
                f"Service '{name}' Dockerfile path is not a file: {service.dockerfile}"
            )

    return errors


def validate_graphql_schema_exists(
    config: FactoryConfig,
    base_path: Path | None = None,
) -> list[str]:
    """Validate that GraphQL schema file exists on disk.

    Args:
        config: The factory configuration to validate.
        base_path: Base path to resolve relative paths from.
            Defaults to current working directory.

    Returns:
        List of error messages if schema is missing.
    """
    errors: list[str] = []
    base = base_path or Path.cwd()

    if not config.apis.graphql.enabled:
        return errors

    if config.apis.graphql.schema_path:
        schema_path = base / config.apis.graphql.schema_path

        if not schema_path.exists():
            errors.append(
                f"GraphQL schema file not found: {config.apis.graphql.schema_path}. "
                f"Expected at: {schema_path}"
            )
        elif not schema_path.is_file():
            errors.append(
                f"GraphQL schema path is not a file: {config.apis.graphql.schema_path}"
            )

    return errors


def validate_unique_route_paths(config: FactoryConfig) -> list[str]:
    """Validate that REST API route paths are unique per method.

    Args:
        config: The factory configuration to validate.

    Returns:
        List of error messages for duplicate routes.
    """
    errors: list[str] = []

    if not config.apis.rest.enabled:
        return errors

    # Track path+method combinations
    seen: dict[tuple[str, str], str] = {}  # (path, method) -> service

    for route in config.apis.rest.routes:
        for method in route.methods:
            key = (route.path, method.value)
            if key in seen:
                errors.append(
                    f"Duplicate route: {method.value} {route.path} is defined "
                    f"for both services '{seen[key]}' and '{route.service}'."
                )
            else:
                seen[key] = route.service

    return errors


def validate_unique_resolver_fields(config: FactoryConfig) -> list[str]:
    """Validate that GraphQL resolver fields are unique per type.

    Args:
        config: The factory configuration to validate.

    Returns:
        List of error messages for duplicate resolvers.
    """
    errors: list[str] = []

    if not config.apis.graphql.enabled:
        return errors

    # Track type+field combinations
    seen: dict[tuple[str, str], str] = {}  # (type, field) -> service

    for resolver in config.apis.graphql.resolvers:
        key = (resolver.type.value, resolver.field)
        if key in seen:
            errors.append(
                f"Duplicate resolver: {resolver.type.value}.{resolver.field} "
                f"is defined for both services '{seen[key]}' and '{resolver.service}'."
            )
        else:
            seen[key] = resolver.service

    return errors


def validate_environment_variables(config: FactoryConfig) -> list[str]:
    """Validate environment variable names are valid.

    Args:
        config: The factory configuration to validate.

    Returns:
        List of error messages for invalid environment variable names.
    """
    errors: list[str] = []
    import re

    env_var_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    # Check Lambda services
    for name, service in config.compute.lambda_.services.items():
        for env_name in service.environment.keys():
            if not env_var_pattern.match(env_name):
                errors.append(
                    f"Lambda service '{name}' has invalid environment variable "
                    f"name '{env_name}'. Must match pattern: [A-Za-z_][A-Za-z0-9_]*"
                )

    # Check App Runner services
    for name, service in config.compute.apprunner.services.items():
        for env_name in service.environment.keys():
            if not env_var_pattern.match(env_name):
                errors.append(
                    f"App Runner service '{name}' has invalid environment variable "
                    f"name '{env_name}'. Must match pattern: [A-Za-z_][A-Za-z0-9_]*"
                )

    return errors


def validate_no_secrets_in_config(config: FactoryConfig) -> list[str]:
    """Check for potential secrets in environment variables.

    This is a heuristic check that warns about environment variable
    values that look like they might contain secrets.

    Args:
        config: The factory configuration to validate.

    Returns:
        List of warning messages for potential secrets.
    """
    warnings: list[str] = []

    # Patterns that might indicate secrets
    secret_patterns = [
        "password",
        "secret",
        "api_key",
        "apikey",
        "token",
        "auth",
        "credential",
        "private_key",
    ]

    def check_env_vars(
        service_name: str, service_type: str, env_vars: dict[str, str]
    ) -> None:
        for name, value in env_vars.items():
            name_lower = name.lower()
            # Check if name suggests it's a secret
            if any(pattern in name_lower for pattern in secret_patterns):
                # Check if value looks like a hardcoded secret (not a reference)
                if not value.startswith("${") and not value.startswith("ssm:"):
                    if len(value) > 8:  # Only warn for non-trivial values
                        warnings.append(
                            f"{service_type} service '{service_name}' has environment "
                            f"variable '{name}' that may contain a secret. Consider "
                            "using SSM Parameter Store or Secrets Manager references."
                        )

    # Check Lambda services
    for name, service in config.compute.lambda_.services.items():
        check_env_vars(name, "Lambda", service.environment)

    # Check App Runner services
    for name, service in config.compute.apprunner.services.items():
        check_env_vars(name, "App Runner", service.environment)

    return warnings


def validate_profile_recommendations(config: FactoryConfig) -> list[str]:
    """Check if configuration aligns with profile recommendations.

    Provides warnings (not errors) when configuration choices don't
    align with the selected profile's typical use case.

    Args:
        config: The factory configuration to validate.

    Returns:
        List of recommendation messages.
    """
    recommendations: list[str] = []

    from aws_api_factory.config.models import (
        AuthModeEnum,
        ObservabilityLevelEnum,
        ProfileEnum,
    )

    if config.profile == ProfileEnum.SCALABLE:
        # Scalable profile recommendations
        if config.observability.level == ObservabilityLevelEnum.BASIC:
            recommendations.append(
                "Scalable profile typically uses 'enhanced' observability. "
                "Consider setting observability.level to 'enhanced' for "
                "production-ready monitoring."
            )

        # Check for routes without auth
        unauthenticated_routes = [
            r.path for r in config.apis.rest.routes if r.auth == AuthModeEnum.NONE
        ]
        if unauthenticated_routes:
            recommendations.append(
                f"Scalable profile: routes {unauthenticated_routes} have no "
                "authentication. Consider adding auth for production security."
            )

    elif config.profile == ProfileEnum.MINIMAL:
        # Minimal profile recommendations
        if config.data.aurora.enabled:
            recommendations.append(
                "Minimal profile with Aurora may incur significant costs. "
                "Consider DynamoDB for a more cost-effective option, or "
                "switch to Scalable profile for production workloads."
            )

    return recommendations


def validate_config(
    config: FactoryConfig,
    base_path: Path | None = None,
    check_files: bool = True,
    strict: bool = False,
) -> tuple[list[str], list[str]]:
    """Run all configuration validators.

    Args:
        config: The factory configuration to validate.
        base_path: Base path for file existence checks.
        check_files: Whether to check for file existence.
        strict: If True, treat warnings as errors.

    Returns:
        Tuple of (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Structural validations (always run)
    errors.extend(validate_unique_route_paths(config))
    errors.extend(validate_unique_resolver_fields(config))
    errors.extend(validate_environment_variables(config))

    # File existence checks (optional)
    if check_files:
        errors.extend(validate_entry_points_exist(config, base_path))
        errors.extend(validate_dockerfiles_exist(config, base_path))
        errors.extend(validate_graphql_schema_exists(config, base_path))

    # Warning-level checks
    warnings.extend(validate_no_secrets_in_config(config))
    warnings.extend(validate_profile_recommendations(config))

    if strict:
        errors.extend(warnings)
        warnings = []

    return errors, warnings


def validate_config_strict(
    config: FactoryConfig,
    base_path: Path | None = None,
) -> None:
    """Validate configuration and raise on any error.

    Args:
        config: The factory configuration to validate.
        base_path: Base path for file existence checks.

    Raises:
        ConfigValidationError: If any validation errors are found.
    """
    errors, warnings = validate_config(config, base_path, check_files=True)

    all_issues = errors + [f"[Warning] {w}" for w in warnings]

    if errors:
        raise ConfigValidationError(errors)
