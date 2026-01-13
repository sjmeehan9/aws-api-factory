# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Pydantic models for AWS API Factory configuration.

This module defines all configuration models used to validate and parse
factory.yaml files. Models use Pydantic v2 with strict validation and
comprehensive error messages.

Example:
    >>> from aws_api_factory.config.models import FactoryConfig
    >>> config = FactoryConfig.model_validate(yaml_dict)

"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProfileEnum(str, Enum):
    """Deployment profile options.

    Attributes:
        MINIMAL: Lower ops overhead, fewer moving parts, sensible defaults.
        SCALABLE: Higher resilience, stronger security, production observability.
    """

    MINIMAL = "minimal"
    SCALABLE = "scalable"


class AuthModeEnum(str, Enum):
    """Authentication mode options for API routes.

    Attributes:
        NONE: No authentication required.
        API_KEY: API key authentication via usage plans.
        IAM: AWS IAM authentication with SigV4 signing.
        COGNITO: Cognito User Pool JWT authorization.
    """

    NONE = "none"
    API_KEY = "api_key"  # pragma: allowlist secret
    IAM = "iam"
    COGNITO = "cognito"


class SecretsProviderEnum(str, Enum):
    """Secrets provider options.

    Attributes:
        SSM: AWS Systems Manager Parameter Store.
        SECRETS_MANAGER: AWS Secrets Manager.
    """

    SSM = "ssm"
    SECRETS_MANAGER = "secrets_manager"  # pragma: allowlist secret


class ObservabilityLevelEnum(str, Enum):
    """Observability level options.

    Attributes:
        BASIC: CloudWatch logs and basic metrics.
        ENHANCED: Structured logging, tracing, alarms, and dashboards.
    """

    BASIC = "basic"
    ENHANCED = "enhanced"


class HttpMethodEnum(str, Enum):
    """HTTP methods supported for REST API routes."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class GraphQLTypeEnum(str, Enum):
    """GraphQL operation types for resolvers."""

    QUERY = "Query"
    MUTATION = "Mutation"
    SUBSCRIPTION = "Subscription"


class DynamoDBBillingModeEnum(str, Enum):
    """DynamoDB billing mode options."""

    PAY_PER_REQUEST = "PAY_PER_REQUEST"
    PROVISIONED = "PROVISIONED"


class AuroraEngineEnum(str, Enum):
    """Aurora database engine options."""

    POSTGRES = "postgres"
    MYSQL = "mysql"


class AuroraModeEnum(str, Enum):
    """Aurora deployment mode options."""

    SERVERLESS_V2 = "serverless_v2"
    PROVISIONED = "provisioned"


# =============================================================================
# Project Configuration
# =============================================================================


class ProjectConfig(BaseModel):
    """Project metadata configuration.

    Attributes:
        name: Project name used for resource naming and tagging.
        envs: List of environment names (e.g., dev, staging, prod).
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$",
            description="Project name (lowercase, alphanumeric with hyphens)",
            examples=["my-api", "orders-service"],
        ),
    ]
    envs: Annotated[
        list[str],
        Field(
            min_length=1,
            description="List of environment names",
            examples=[["dev", "prod"], ["dev", "staging", "prod"]],
        ),
    ]

    @field_validator("envs")
    @classmethod
    def validate_envs(cls, v: list[str]) -> list[str]:
        """Validate environment names are valid identifiers."""
        for env in v:
            if not env or not env.replace("-", "").replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid environment name '{env}'. "
                    "Must be alphanumeric with hyphens or underscores."
                )
            if len(env) > 32:
                raise ValueError(
                    f"Environment name '{env}' too long. Maximum 32 characters."
                )
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate environment names are not allowed.")
        return v


# =============================================================================
# REST API Configuration
# =============================================================================


class RouteConfig(BaseModel):
    """REST API route configuration.

    Attributes:
        path: URL path for the route (must start with /).
        methods: HTTP methods enabled for this route.
        service: Name of the compute service handling this route.
        auth: Authentication mode for this route.
    """

    model_config = ConfigDict(extra="forbid")

    path: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^/.*",
            description="URL path starting with /",
            examples=["/orders", "/users/{id}"],
        ),
    ]
    methods: Annotated[
        list[HttpMethodEnum],
        Field(
            min_length=1,
            description="HTTP methods for this route",
            examples=[["GET", "POST"]],
        ),
    ]
    service: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            description="Name of the service handling this route",
            examples=["orders", "users"],
        ),
    ]
    auth: Annotated[
        AuthModeEnum,
        Field(
            default=AuthModeEnum.NONE,
            description="Authentication mode for this route",
        ),
    ]


class CognitoConfig(BaseModel):
    """Cognito User Pool configuration for authentication.

    Attributes:
        user_pool_id: Existing Cognito User Pool ID (optional).
        create_user_pool: Whether to create a new User Pool.
    """

    model_config = ConfigDict(extra="forbid")

    user_pool_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Existing Cognito User Pool ID",
        ),
    ]
    create_user_pool: Annotated[
        bool,
        Field(
            default=True,
            description="Create a new Cognito User Pool",
        ),
    ]

    @model_validator(mode="after")
    def validate_cognito_config(self) -> "CognitoConfig":
        """Validate Cognito configuration is consistent."""
        if self.user_pool_id and self.create_user_pool:
            raise ValueError(
                "Cannot specify both 'user_pool_id' and 'create_user_pool: true'. "
                "Either provide an existing User Pool ID or let the factory create one."
            )
        if not self.user_pool_id and not self.create_user_pool:
            raise ValueError(
                "Must either provide 'user_pool_id' or set 'create_user_pool: true'."
            )
        return self


class RestApiConfig(BaseModel):
    """REST API configuration.

    Attributes:
        enabled: Whether REST API is enabled.
        routes: List of route configurations.
        cognito: Cognito configuration (required if any route uses cognito auth).
        throttle_rate: API-level throttle rate limit (requests per second).
        throttle_burst: API-level throttle burst limit.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=True, description="Enable REST API deployment"),
    ]
    routes: Annotated[
        list[RouteConfig],
        Field(
            default_factory=list,
            description="List of API routes",
        ),
    ]
    cognito: Annotated[
        CognitoConfig | None,
        Field(
            default=None,
            description="Cognito configuration for JWT authentication",
        ),
    ]
    throttle_rate: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="API throttle rate (requests per second)",
        ),
    ]
    throttle_burst: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="API throttle burst limit",
        ),
    ]

    @model_validator(mode="after")
    def validate_rest_api_config(self) -> "RestApiConfig":
        """Validate REST API configuration consistency."""
        if not self.enabled:
            return self

        # Check if cognito auth is used but not configured
        cognito_routes = [r for r in self.routes if r.auth == AuthModeEnum.COGNITO]
        if cognito_routes and not self.cognito:
            route_paths = ", ".join(r.path for r in cognito_routes)
            raise ValueError(
                f"Routes [{route_paths}] use 'cognito' auth but no 'cognito' "
                "configuration is provided. Add 'cognito' config under 'apis.rest'."
            )

        return self


# =============================================================================
# GraphQL API Configuration
# =============================================================================


class ResolverConfig(BaseModel):
    """GraphQL resolver configuration.

    Attributes:
        type: GraphQL operation type (Query, Mutation, Subscription).
        field: Field name in the schema.
        service: Name of the compute service handling this resolver.
        resolver: Function/method name within the service.
    """

    model_config = ConfigDict(extra="forbid")

    type: Annotated[
        GraphQLTypeEnum,
        Field(description="GraphQL operation type"),
    ]
    field: Annotated[
        str,
        Field(
            min_length=1,
            max_length=128,
            description="Field name in the GraphQL schema",
            examples=["getOrder", "createUser"],
        ),
    ]
    service: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            description="Name of the service handling this resolver",
        ),
    ]
    resolver: Annotated[
        str,
        Field(
            min_length=1,
            max_length=128,
            description="Function name within the service",
            examples=["get_order", "create_user"],
        ),
    ]


class GraphQLConfig(BaseModel):
    """GraphQL API configuration.

    Attributes:
        enabled: Whether GraphQL API is enabled.
        schema_path: Path to GraphQL schema file.
        auth: Default authentication mode for the API.
        resolvers: List of resolver configurations.
        cognito: Cognito configuration (required if auth is cognito).
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=False, description="Enable GraphQL API deployment"),
    ]
    schema_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Path to GraphQL schema file",
            examples=["src/graphql/schema.graphql"],
        ),
    ]
    auth: Annotated[
        AuthModeEnum,
        Field(
            default=AuthModeEnum.API_KEY,
            description="Default authentication mode",
        ),
    ]
    resolvers: Annotated[
        list[ResolverConfig],
        Field(
            default_factory=list,
            description="List of resolver configurations",
        ),
    ]
    cognito: Annotated[
        CognitoConfig | None,
        Field(
            default=None,
            description="Cognito configuration for JWT authentication",
        ),
    ]

    @model_validator(mode="after")
    def validate_graphql_config(self) -> "GraphQLConfig":
        """Validate GraphQL configuration consistency."""
        if not self.enabled:
            return self

        if not self.schema_path:
            raise ValueError(
                "GraphQL is enabled but 'schema_path' is not specified. "
                "Provide the path to your GraphQL schema file."
            )

        if self.auth == AuthModeEnum.COGNITO and not self.cognito:
            raise ValueError(
                "GraphQL auth is 'cognito' but no 'cognito' configuration provided. "
                "Add 'cognito' config under 'apis.graphql'."
            )

        return self


class ApisConfig(BaseModel):
    """API configuration container.

    Attributes:
        rest: REST API configuration.
        graphql: GraphQL API configuration.
    """

    model_config = ConfigDict(extra="forbid")

    rest: Annotated[
        RestApiConfig,
        Field(
            default_factory=RestApiConfig,
            description="REST API configuration",
        ),
    ]
    graphql: Annotated[
        GraphQLConfig,
        Field(
            default_factory=GraphQLConfig,
            description="GraphQL API configuration",
        ),
    ]


# =============================================================================
# Compute Configuration
# =============================================================================


class LambdaServiceConfig(BaseModel):
    """Lambda service configuration.

    Attributes:
        entry: Entry point in format 'path/to/handler.py:function_name'.
        memory_mb: Memory allocation in MB (or 'auto' for profile default).
        timeout_s: Timeout in seconds (or 'auto' for profile default).
        reserved_concurrency: Reserved concurrent executions (optional).
        environment: Environment variables for the function.
    """

    model_config = ConfigDict(extra="forbid")

    entry: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^.+\.py:.+$",
            description="Entry point (path/to/file.py:handler_function)",
            examples=["src/services/orders/handler.py:handler"],
        ),
    ]
    memory_mb: Annotated[
        int | Literal["auto"],
        Field(
            default="auto",
            description="Memory in MB or 'auto' for profile default",
        ),
    ]
    timeout_s: Annotated[
        int | Literal["auto"],
        Field(
            default="auto",
            description="Timeout in seconds or 'auto' for profile default",
        ),
    ]
    reserved_concurrency: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=1000,
            description="Reserved concurrent executions",
        ),
    ]
    environment: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            description="Environment variables",
        ),
    ]

    @field_validator("memory_mb")
    @classmethod
    def validate_memory(cls, v: int | str) -> int | str:
        """Validate memory is within AWS Lambda limits."""
        if isinstance(v, int):
            if v < 128 or v > 10240:
                raise ValueError(
                    f"Lambda memory must be between 128 and 10240 MB, got {v}."
                )
        return v

    @field_validator("timeout_s")
    @classmethod
    def validate_timeout(cls, v: int | str) -> int | str:
        """Validate timeout is within AWS Lambda limits."""
        if isinstance(v, int):
            if v < 1 or v > 900:
                raise ValueError(
                    f"Lambda timeout must be between 1 and 900 seconds, got {v}."
                )
        return v


class LambdaConfig(BaseModel):
    """Lambda compute configuration.

    Attributes:
        enabled: Whether Lambda compute is enabled.
        services: Dictionary of service name to configuration.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=True, description="Enable Lambda compute"),
    ]
    services: Annotated[
        dict[str, LambdaServiceConfig],
        Field(
            default_factory=dict,
            description="Lambda service configurations",
        ),
    ]


class AppRunnerServiceConfig(BaseModel):
    """App Runner service configuration.

    Attributes:
        dockerfile: Path to Dockerfile.
        port: Container port to expose.
        healthcheck_path: Health check endpoint path.
        cpu: CPU units (1, 2, or 4).
        memory: Memory in GB (2, 3, 4, 6, 8, 10, or 12).
        min_instances: Minimum number of instances.
        max_instances: Maximum number of instances.
        environment: Environment variables.
    """

    model_config = ConfigDict(extra="forbid")

    dockerfile: Annotated[
        str,
        Field(
            min_length=1,
            description="Path to Dockerfile",
            examples=["src/services/api/Dockerfile"],
        ),
    ]
    port: Annotated[
        int,
        Field(
            default=8000,
            ge=1,
            le=65535,
            description="Container port",
        ),
    ]
    healthcheck_path: Annotated[
        str,
        Field(
            default="/healthz",
            pattern=r"^/.*",
            description="Health check endpoint path",
        ),
    ]
    cpu: Annotated[
        Literal[1, 2, 4],
        Field(
            default=1,
            description="CPU units (vCPUs)",
        ),
    ]
    memory: Annotated[
        Literal[2, 3, 4, 6, 8, 10, 12],
        Field(
            default=2,
            description="Memory in GB",
        ),
    ]
    min_instances: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            le=25,
            description="Minimum instances",
        ),
    ]
    max_instances: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=25,
            description="Maximum instances",
        ),
    ]
    environment: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            description="Environment variables",
        ),
    ]

    @model_validator(mode="after")
    def validate_instances(self) -> "AppRunnerServiceConfig":
        """Validate min_instances <= max_instances."""
        if self.min_instances > self.max_instances:
            raise ValueError(
                f"min_instances ({self.min_instances}) cannot be greater than "
                f"max_instances ({self.max_instances})."
            )
        return self


class AppRunnerConfig(BaseModel):
    """App Runner compute configuration.

    Attributes:
        enabled: Whether App Runner compute is enabled.
        services: Dictionary of service name to configuration.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=False, description="Enable App Runner compute"),
    ]
    services: Annotated[
        dict[str, AppRunnerServiceConfig],
        Field(
            default_factory=dict,
            description="App Runner service configurations",
        ),
    ]


class ComputeConfig(BaseModel):
    """Compute configuration container.

    Attributes:
        lambda_: Lambda configuration (aliased as 'lambda' in YAML).
        apprunner: App Runner configuration.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    lambda_: Annotated[
        LambdaConfig,
        Field(
            default_factory=LambdaConfig,
            alias="lambda",
            description="Lambda compute configuration",
        ),
    ]
    apprunner: Annotated[
        AppRunnerConfig,
        Field(
            default_factory=AppRunnerConfig,
            description="App Runner compute configuration",
        ),
    ]


# =============================================================================
# Data Configuration
# =============================================================================


class DynamoDBTableConfig(BaseModel):
    """DynamoDB table configuration.

    Attributes:
        name: Table name.
        pk: Partition key attribute name.
        sk: Sort key attribute name (optional).
        billing_mode: Billing mode (PAY_PER_REQUEST or PROVISIONED).
        pitr: Enable Point-in-Time Recovery.
    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=3,
            max_length=255,
            pattern=r"^[a-zA-Z0-9_.-]+$",
            description="Table name",
        ),
    ]
    pk: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            description="Partition key attribute name",
        ),
    ]
    sk: Annotated[
        str | None,
        Field(
            default=None,
            max_length=255,
            description="Sort key attribute name (optional)",
        ),
    ]
    billing_mode: Annotated[
        DynamoDBBillingModeEnum,
        Field(
            default=DynamoDBBillingModeEnum.PAY_PER_REQUEST,
            description="Billing mode",
        ),
    ]
    pitr: Annotated[
        bool,
        Field(
            default=False,
            description="Enable Point-in-Time Recovery",
        ),
    ]


class DynamoDBConfig(BaseModel):
    """DynamoDB configuration.

    Attributes:
        enabled: Whether DynamoDB is enabled.
        tables: List of table configurations.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=False, description="Enable DynamoDB"),
    ]
    tables: Annotated[
        list[DynamoDBTableConfig],
        Field(
            default_factory=list,
            description="Table configurations",
        ),
    ]

    @model_validator(mode="after")
    def validate_dynamodb_config(self) -> "DynamoDBConfig":
        """Validate DynamoDB configuration."""
        if self.enabled and not self.tables:
            raise ValueError(
                "DynamoDB is enabled but no tables are configured. "
                "Add at least one table under 'data.dynamodb.tables'."
            )
        # Check for duplicate table names
        if self.tables:
            names = [t.name for t in self.tables]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate DynamoDB table names are not allowed.")
        return self


class AuroraConfig(BaseModel):
    """Aurora Serverless v2 configuration.

    Attributes:
        enabled: Whether Aurora is enabled.
        engine: Database engine (postgres or mysql).
        mode: Deployment mode.
        min_acu: Minimum Aurora Capacity Units.
        max_acu: Maximum Aurora Capacity Units.
        database_name: Default database name.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=False, description="Enable Aurora Serverless v2"),
    ]
    engine: Annotated[
        AuroraEngineEnum,
        Field(
            default=AuroraEngineEnum.POSTGRES,
            description="Database engine",
        ),
    ]
    mode: Annotated[
        AuroraModeEnum,
        Field(
            default=AuroraModeEnum.SERVERLESS_V2,
            description="Deployment mode",
        ),
    ]
    min_acu: Annotated[
        float,
        Field(
            default=0.5,
            ge=0.5,
            le=128,
            description="Minimum Aurora Capacity Units",
        ),
    ]
    max_acu: Annotated[
        float,
        Field(
            default=8,
            ge=0.5,
            le=128,
            description="Maximum Aurora Capacity Units",
        ),
    ]
    database_name: Annotated[
        str,
        Field(
            default="appdb",
            min_length=1,
            max_length=64,
            pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
            description="Default database name",
        ),
    ]

    @model_validator(mode="after")
    def validate_acu_range(self) -> "AuroraConfig":
        """Validate min_acu <= max_acu."""
        if self.min_acu > self.max_acu:
            raise ValueError(
                f"min_acu ({self.min_acu}) cannot be greater than "
                f"max_acu ({self.max_acu})."
            )
        return self


class S3BucketConfig(BaseModel):
    """S3 bucket configuration.

    Attributes:
        name: Bucket name suffix (will be prefixed with project name).
        versioning: Enable versioning.
        encryption: Enable server-side encryption.
    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=63,
            pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$|^[a-z0-9]$",
            description="Bucket name suffix",
        ),
    ]
    versioning: Annotated[
        bool,
        Field(default=False, description="Enable versioning"),
    ]
    encryption: Annotated[
        bool,
        Field(default=True, description="Enable server-side encryption"),
    ]


class S3Config(BaseModel):
    """S3 configuration.

    Attributes:
        enabled: Whether S3 is enabled.
        buckets: List of bucket configurations.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(default=False, description="Enable S3"),
    ]
    buckets: Annotated[
        list[S3BucketConfig],
        Field(
            default_factory=list,
            description="Bucket configurations",
        ),
    ]

    @model_validator(mode="after")
    def validate_s3_config(self) -> "S3Config":
        """Validate S3 configuration."""
        if self.enabled and not self.buckets:
            raise ValueError(
                "S3 is enabled but no buckets are configured. "
                "Add at least one bucket under 'data.s3.buckets'."
            )
        # Check for duplicate bucket names
        if self.buckets:
            names = [b.name for b in self.buckets]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate S3 bucket names are not allowed.")
        return self


class DataConfig(BaseModel):
    """Data layer configuration container.

    Attributes:
        dynamodb: DynamoDB configuration.
        aurora: Aurora Serverless v2 configuration.
        s3: S3 configuration.
    """

    model_config = ConfigDict(extra="forbid")

    dynamodb: Annotated[
        DynamoDBConfig,
        Field(
            default_factory=DynamoDBConfig,
            description="DynamoDB configuration",
        ),
    ]
    aurora: Annotated[
        AuroraConfig,
        Field(
            default_factory=AuroraConfig,
            description="Aurora configuration",
        ),
    ]
    s3: Annotated[
        S3Config,
        Field(
            default_factory=S3Config,
            description="S3 configuration",
        ),
    ]


# =============================================================================
# Secrets & Observability Configuration
# =============================================================================


class SecretsConfig(BaseModel):
    """Secrets management configuration.

    Attributes:
        provider: Secrets provider (SSM or Secrets Manager).
    """

    model_config = ConfigDict(extra="forbid")

    provider: Annotated[
        SecretsProviderEnum,
        Field(
            default=SecretsProviderEnum.SSM,
            description="Secrets provider",
        ),
    ]


class ObservabilityConfig(BaseModel):
    """Observability configuration.

    Attributes:
        level: Observability level (basic or enhanced).
        tracing: Enable X-Ray tracing (auto-enabled for enhanced).
        alarms: Enable CloudWatch alarms (auto-enabled for enhanced).
    """

    model_config = ConfigDict(extra="forbid")

    level: Annotated[
        ObservabilityLevelEnum,
        Field(
            default=ObservabilityLevelEnum.BASIC,
            description="Observability level",
        ),
    ]
    tracing: Annotated[
        bool | None,
        Field(
            default=None,
            description="Enable X-Ray tracing (defaults based on level)",
        ),
    ]
    alarms: Annotated[
        bool | None,
        Field(
            default=None,
            description="Enable CloudWatch alarms (defaults based on level)",
        ),
    ]


# =============================================================================
# Root Configuration Model
# =============================================================================


class FactoryConfig(BaseModel):
    """Root configuration model for factory.yaml.

    This is the top-level model that validates the entire factory.yaml
    configuration file. It contains all nested configuration sections
    and performs cross-section validation.

    Attributes:
        project: Project metadata (name, environments).
        profile: Deployment profile (minimal or scalable).
        apis: API configuration (REST, GraphQL).
        compute: Compute configuration (Lambda, App Runner).
        data: Data layer configuration (DynamoDB, Aurora, S3).
        secrets: Secrets management configuration.
        observability: Observability configuration.

    Example:
        >>> config = FactoryConfig.model_validate({
        ...     "project": {"name": "my-api", "envs": ["dev", "prod"]},
        ...     "profile": "minimal",
        ... })
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )

    project: Annotated[
        ProjectConfig,
        Field(description="Project metadata"),
    ]
    profile: Annotated[
        ProfileEnum,
        Field(
            default=ProfileEnum.MINIMAL,
            description="Deployment profile",
        ),
    ]
    apis: Annotated[
        ApisConfig,
        Field(
            default_factory=ApisConfig,
            description="API configuration",
        ),
    ]
    compute: Annotated[
        ComputeConfig,
        Field(
            default_factory=ComputeConfig,
            description="Compute configuration",
        ),
    ]
    data: Annotated[
        DataConfig,
        Field(
            default_factory=DataConfig,
            description="Data layer configuration",
        ),
    ]
    secrets: Annotated[
        SecretsConfig,
        Field(
            default_factory=SecretsConfig,
            description="Secrets management configuration",
        ),
    ]
    observability: Annotated[
        ObservabilityConfig,
        Field(
            default_factory=ObservabilityConfig,
            description="Observability configuration",
        ),
    ]

    @model_validator(mode="after")
    def validate_cross_section_references(self) -> "FactoryConfig":
        """Validate references between configuration sections.

        Ensures that services referenced in routes/resolvers exist in compute,
        and that at least one API and compute option is enabled.
        """
        errors: list[str] = []

        # Collect all defined Lambda service names
        lambda_services = set(self.compute.lambda_.services.keys())
        apprunner_services = set(self.compute.apprunner.services.keys())
        all_services = lambda_services | apprunner_services

        # Validate REST API route service references
        if self.apis.rest.enabled:
            for route in self.apis.rest.routes:
                if route.service not in all_services:
                    errors.append(
                        f"Route '{route.path}' references service '{route.service}' "
                        f"which is not defined in compute.lambda.services or "
                        f"compute.apprunner.services."
                    )

        # Validate GraphQL resolver service references
        if self.apis.graphql.enabled:
            for resolver in self.apis.graphql.resolvers:
                if resolver.service not in all_services:
                    errors.append(
                        f"Resolver '{resolver.type.value}.{resolver.field}' "
                        f"references service '{resolver.service}' which is not "
                        f"defined in compute.lambda.services or "
                        f"compute.apprunner.services."
                    )

        # Validate at least one API is enabled if routes/resolvers defined
        if not self.apis.rest.enabled and not self.apis.graphql.enabled:
            if self.apis.rest.routes or self.apis.graphql.resolvers:
                errors.append(
                    "Routes or resolvers are defined but no API (rest/graphql) "
                    "is enabled. Enable at least one API type."
                )

        # Validate at least one compute option is enabled if services defined
        if not self.compute.lambda_.enabled and not self.compute.apprunner.enabled:
            if lambda_services or apprunner_services:
                errors.append(
                    "Services are defined but no compute option (lambda/apprunner) "
                    "is enabled. Enable at least one compute type."
                )

        if errors:
            raise ValueError(
                "Configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        return self

    def get_all_service_names(self) -> set[str]:
        """Get all defined service names across compute options.

        Returns:
            Set of all service names defined in Lambda and App Runner.
        """
        lambda_services = set(self.compute.lambda_.services.keys())
        apprunner_services = set(self.compute.apprunner.services.keys())
        return lambda_services | apprunner_services

    def get_routes_by_service(self, service_name: str) -> list[RouteConfig]:
        """Get all REST API routes for a specific service.

        Args:
            service_name: Name of the service.

        Returns:
            List of route configurations for the service.
        """
        return [r for r in self.apis.rest.routes if r.service == service_name]

    def get_resolvers_by_service(self, service_name: str) -> list[ResolverConfig]:
        """Get all GraphQL resolvers for a specific service.

        Args:
            service_name: Name of the service.

        Returns:
            List of resolver configurations for the service.
        """
        return [r for r in self.apis.graphql.resolvers if r.service == service_name]

    def uses_cognito_auth(self) -> bool:
        """Check if any API uses Cognito authentication.

        Returns:
            True if Cognito auth is used anywhere.
        """
        rest_uses_cognito = any(
            r.auth == AuthModeEnum.COGNITO for r in self.apis.rest.routes
        )
        graphql_uses_cognito = self.apis.graphql.auth == AuthModeEnum.COGNITO
        return rest_uses_cognito or graphql_uses_cognito

    def uses_api_key_auth(self) -> bool:
        """Check if any API uses API key authentication.

        Returns:
            True if API key auth is used anywhere.
        """
        rest_uses_api_key = any(
            r.auth == AuthModeEnum.API_KEY for r in self.apis.rest.routes
        )
        graphql_uses_api_key = self.apis.graphql.auth == AuthModeEnum.API_KEY
        return rest_uses_api_key or graphql_uses_api_key
