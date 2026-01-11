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

# Import auth constructs
from aws_api_factory.constructs.auth import (
    ApiKeyAuthConstruct,
    CognitoAuthConstruct,
    IamAuthConstruct,
    apply_auth_to_method,
    create_auth_constructs,
    get_auth_mode_for_route,
    validate_auth_config,
)
from aws_api_factory.constructs.auth.helpers import (
    AuthConstructs,
    get_authorization_type,
    get_method_options,
    get_required_auth_modes,
)
from aws_api_factory.constructs.base import (
    BaseConstruct,
    apply_global_tags,
    sanitize_resource_id,
)

# Import feature constructs
from aws_api_factory.constructs.compute_apprunner import (
    AppRunnerConstruct,
    create_apprunner_service,
)
from aws_api_factory.constructs.compute_lambda import (
    LambdaFunctionConstruct,
    create_lambda_function,
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
from aws_api_factory.constructs.rest_api import (
    RestApiConstruct,
    RestLambdaConstruct,
    attach_http_integration_to_resource,
    attach_http_integration_to_routes,
    attach_lambda_integration,
    create_catch_all_proxy,
    create_http_integration,
    create_http_proxy_integration,
    create_lambda_integration,
    grant_api_invoke_permission,
)

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
    # Lambda constructs
    "LambdaFunctionConstruct",
    "create_lambda_function",
    # App Runner constructs
    "AppRunnerConstruct",
    "create_apprunner_service",
    # REST API constructs
    "RestApiConstruct",
    "RestLambdaConstruct",
    "attach_lambda_integration",
    "create_lambda_integration",
    "grant_api_invoke_permission",
    # HTTP integration (for App Runner)
    "attach_http_integration_to_resource",
    "attach_http_integration_to_routes",
    "create_catch_all_proxy",
    "create_http_integration",
    "create_http_proxy_integration",
    # Auth constructs (Component 1.8)
    "ApiKeyAuthConstruct",
    "IamAuthConstruct",
    "CognitoAuthConstruct",
    "AuthConstructs",
    "apply_auth_to_method",
    "create_auth_constructs",
    "get_auth_mode_for_route",
    "get_required_auth_modes",
    "get_authorization_type",
    "get_method_options",
    "validate_auth_config",
]
