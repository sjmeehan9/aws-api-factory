# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""App Runner compute constructs for AWS API Factory.

This module provides constructs for deploying containerized services
using AWS App Runner, with support for Docker-based deployments.

Classes:
    AppRunnerConstruct: Creates App Runner services from Dockerfile configurations.

Functions:
    create_apprunner_service: Convenience function for creating App Runner services.

Example:
    >>> from aws_api_factory.constructs.compute_apprunner import AppRunnerConstruct
    >>> construct = AppRunnerConstruct(
    ...     stack, "AppRunner",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ... )
    >>> service_url = construct.get_service_url("public_api")

"""

from aws_api_factory.constructs.compute_apprunner.service import (
    AppRunnerConstruct,
    create_apprunner_service,
)

__all__ = [
    "AppRunnerConstruct",
    "create_apprunner_service",
]
