# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS API Factory Configuration Module.

This module provides Pydantic models for validating and loading
factory.yaml configuration files.

Classes:
    FactoryConfig: Root configuration model
    ProjectConfig: Project metadata configuration
    ApisConfig: API configuration (REST, GraphQL)
    ComputeConfig: Compute configuration (Lambda, App Runner)
    DataConfig: Data layer configuration (DynamoDB, Aurora, S3)

Functions:
    load_config: Load and validate a factory.yaml file
    export_json_schema: Export configuration schema as JSON Schema

Example:
    >>> from aws_api_factory.config import load_config, FactoryConfig
    >>> config = load_config("factory.yaml")
    >>> print(config.project.name)
    'my-api'

"""

from aws_api_factory.config.loader import (
    ConfigLoadError,
    find_config_file,
    get_config_dir,
    load_config,
    load_config_from_string,
    load_yaml_file,
    load_yaml_string,
    validate_and_parse,
)
from aws_api_factory.config.models import (
    ApisConfig,
    AppRunnerConfig,
    AppRunnerServiceConfig,
    AuroraConfig,
    AuroraEngineEnum,
    AuroraModeEnum,
    AuthModeEnum,
    CognitoConfig,
    ComputeConfig,
    DataConfig,
    DynamoDBBillingModeEnum,
    DynamoDBConfig,
    DynamoDBTableConfig,
    FactoryConfig,
    GraphQLConfig,
    GraphQLTypeEnum,
    HttpMethodEnum,
    LambdaConfig,
    LambdaServiceConfig,
    ObservabilityConfig,
    ObservabilityLevelEnum,
    ProfileEnum,
    ProjectConfig,
    ResolverConfig,
    RestApiConfig,
    RouteConfig,
    S3BucketConfig,
    S3Config,
    SecretsConfig,
    SecretsProviderEnum,
)
from aws_api_factory.config.schema import (
    export_json_schema,
    export_json_schema_string,
    generate_yaml_schema_header,
    get_config_template,
    get_schema_for_section,
    write_json_schema,
)
from aws_api_factory.config.validators import (
    ConfigValidationError,
    validate_config,
    validate_config_strict,
    validate_dockerfiles_exist,
    validate_entry_points_exist,
    validate_environment_variables,
    validate_graphql_schema_exists,
    validate_no_secrets_in_config,
    validate_profile_recommendations,
    validate_unique_resolver_fields,
    validate_unique_route_paths,
)

__all__ = [
    # Loader
    "ConfigLoadError",
    "find_config_file",
    "get_config_dir",
    "load_config",
    "load_config_from_string",
    "load_yaml_file",
    "load_yaml_string",
    "validate_and_parse",
    # Models - Enums
    "AuthModeEnum",
    "AuroraEngineEnum",
    "AuroraModeEnum",
    "DynamoDBBillingModeEnum",
    "GraphQLTypeEnum",
    "HttpMethodEnum",
    "ObservabilityLevelEnum",
    "ProfileEnum",
    "SecretsProviderEnum",
    # Models - Config classes
    "ApisConfig",
    "AppRunnerConfig",
    "AppRunnerServiceConfig",
    "AuroraConfig",
    "CognitoConfig",
    "ComputeConfig",
    "DataConfig",
    "DynamoDBConfig",
    "DynamoDBTableConfig",
    "FactoryConfig",
    "GraphQLConfig",
    "LambdaConfig",
    "LambdaServiceConfig",
    "ObservabilityConfig",
    "ProjectConfig",
    "ResolverConfig",
    "RestApiConfig",
    "RouteConfig",
    "S3BucketConfig",
    "S3Config",
    "SecretsConfig",
    # Schema
    "export_json_schema",
    "export_json_schema_string",
    "generate_yaml_schema_header",
    "get_config_template",
    "get_schema_for_section",
    "write_json_schema",
    # Validators
    "ConfigValidationError",
    "validate_config",
    "validate_config_strict",
    "validate_dockerfiles_exist",
    "validate_entry_points_exist",
    "validate_environment_variables",
    "validate_graphql_schema_exists",
    "validate_no_secrets_in_config",
    "validate_profile_recommendations",
    "validate_unique_resolver_fields",
    "validate_unique_route_paths",
]
