# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Lambda compute constructs for AWS API Factory.

This module provides CDK constructs for deploying AWS Lambda functions
configured via factory.yaml. It handles function creation, IAM permissions,
CloudWatch logging, and profile-based defaults.

Classes:
    LambdaFunctionConstruct: Creates and configures Lambda functions.

Example:
    >>> from aws_api_factory.constructs.compute_lambda import LambdaFunctionConstruct
    >>> lambda_construct = LambdaFunctionConstruct(
    ...     stack, "LambdaFunctions",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ... )

"""

from aws_api_factory.constructs.compute_lambda.function import (
    LambdaFunctionConstruct,
    create_lambda_function,
)

__all__ = [
    "LambdaFunctionConstruct",
    "create_lambda_function",
]
