# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS API Factory CDK Constructs.

This module provides reusable AWS CDK constructs for building
API infrastructure on AWS.

Core Classes:
    FactoryStack: Main CDK stack that composes all factory constructs.
    BaseConstruct: Abstract base class for all factory constructs.
    OutputManager: Manages stack outputs and CloudFormation exports.
    ConstructRegistry: Manages dynamic construct loading and composition.

Submodules:
    rest_api: API Gateway REST API constructs (Component 1.6)
    compute_lambda: Lambda function constructs (Component 1.6)
    compute_apprunner: App Runner service constructs (Component 1.7)
    auth: Authentication constructs (API Keys, IAM, Cognito) (Component 1.8)
    appsync: AWS AppSync GraphQL constructs (Phase 2)
    data: Data layer constructs (DynamoDB, S3, Aurora) (Phase 2)
    observability: Monitoring and alerting constructs (Phase 2)

Example:
    >>> from aws_cdk import App
    >>> from aws_api_factory.constructs import FactoryStack, create_factory_stack
    >>> from aws_api_factory.config import load_config
    >>>
    >>> app = App()
    >>> config = load_config("factory.yaml")
    >>> stack = create_factory_stack(app, config, "dev")
    >>> app.synth()

"""

from aws_api_factory.constructs.base import (
    BaseConstruct,
    apply_global_tags,
    sanitize_resource_id,
)
from aws_api_factory.constructs.factory_stack import (
    ConstructRegistration,
    ConstructRegistry,
    FactoryStack,
    create_factory_stack,
    get_default_registry,
    register_construct,
)
from aws_api_factory.constructs.outputs import OutputEntry, OutputManager

__all__ = [
    # Base construct
    "BaseConstruct",
    "apply_global_tags",
    "sanitize_resource_id",
    # Factory stack
    "FactoryStack",
    "create_factory_stack",
    "ConstructRegistry",
    "ConstructRegistration",
    "get_default_registry",
    "register_construct",
    # Output management
    "OutputManager",
    "OutputEntry",
]
