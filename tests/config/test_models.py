# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for configuration models (Pydantic v2).

These tests validate the Pydantic models used to parse and validate
factory.yaml configuration files.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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


class TestEnums:
    """Tests for configuration enums."""

    def test_profile_enum_values(self) -> None:
        """Test ProfileEnum has expected values."""
        assert ProfileEnum.MINIMAL.value == "minimal"
        assert ProfileEnum.SCALABLE.value == "scalable"

    def test_auth_mode_enum_values(self) -> None:
        """Test AuthModeEnum has expected values."""
        assert AuthModeEnum.NONE.value == "none"
        assert AuthModeEnum.API_KEY.value == "api_key"
        assert AuthModeEnum.IAM.value == "iam"
        assert AuthModeEnum.COGNITO.value == "cognito"

    def test_http_method_enum_values(self) -> None:
        """Test HttpMethodEnum has all standard HTTP methods."""
        methods = {m.value for m in HttpMethodEnum}
        assert methods == {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

    def test_graphql_type_enum_values(self) -> None:
        """Test GraphQLTypeEnum has expected values."""
        assert GraphQLTypeEnum.QUERY.value == "Query"
        assert GraphQLTypeEnum.MUTATION.value == "Mutation"
        assert GraphQLTypeEnum.SUBSCRIPTION.value == "Subscription"

    def test_secrets_provider_enum_values(self) -> None:
        """Test SecretsProviderEnum has expected values."""
        assert SecretsProviderEnum.SSM.value == "ssm"
        assert SecretsProviderEnum.SECRETS_MANAGER.value == "secrets_manager"

    def test_observability_level_enum_values(self) -> None:
        """Test ObservabilityLevelEnum has expected values."""
        assert ObservabilityLevelEnum.BASIC.value == "basic"
        assert ObservabilityLevelEnum.ENHANCED.value == "enhanced"


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_valid_project_config(self) -> None:
        """Test valid project configuration."""
        config = ProjectConfig(name="my-api", envs=["dev", "prod"])
        assert config.name == "my-api"
        assert config.envs == ["dev", "prod"]

    def test_project_name_validation(self) -> None:
        """Test project name must match pattern."""
        # Valid names
        ProjectConfig(name="a", envs=["dev"])
        ProjectConfig(name="my-api", envs=["dev"])
        ProjectConfig(name="api123", envs=["dev"])

        # Invalid names
        with pytest.raises(ValidationError, match="String should match pattern"):
            ProjectConfig(name="My-API", envs=["dev"])  # Uppercase

        with pytest.raises(ValidationError, match="String should match pattern"):
            ProjectConfig(name="-api", envs=["dev"])  # Starts with hyphen

        with pytest.raises(ValidationError, match="String should match pattern"):
            ProjectConfig(name="api-", envs=["dev"])  # Ends with hyphen

    def test_envs_validation(self) -> None:
        """Test environment names validation."""
        # Valid envs
        ProjectConfig(name="api", envs=["dev"])
        ProjectConfig(name="api", envs=["dev", "staging", "prod"])

        # Empty envs not allowed
        with pytest.raises(ValidationError, match="at least 1"):
            ProjectConfig(name="api", envs=[])

        # Duplicate envs not allowed
        with pytest.raises(ValidationError, match="Duplicate environment"):
            ProjectConfig(name="api", envs=["dev", "dev"])

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ProjectConfig(name="api", envs=["dev"], unknown="value")


class TestRouteConfig:
    """Tests for RouteConfig model."""

    def test_valid_route_config(self) -> None:
        """Test valid route configuration."""
        route = RouteConfig(
            path="/orders",
            methods=[HttpMethodEnum.GET, HttpMethodEnum.POST],
            service="orders",
            auth=AuthModeEnum.NONE,
        )
        assert route.path == "/orders"
        assert route.methods == [HttpMethodEnum.GET, HttpMethodEnum.POST]
        assert route.service == "orders"
        assert route.auth == AuthModeEnum.NONE

    def test_path_must_start_with_slash(self) -> None:
        """Test path must start with /."""
        with pytest.raises(ValidationError, match="String should match pattern"):
            RouteConfig(
                path="orders",  # Missing leading /
                methods=[HttpMethodEnum.GET],
                service="orders",
            )

    def test_methods_required(self) -> None:
        """Test at least one method is required."""
        with pytest.raises(ValidationError, match="at least 1"):
            RouteConfig(path="/orders", methods=[], service="orders")

    def test_auth_default(self) -> None:
        """Test auth defaults to none."""
        route = RouteConfig(
            path="/orders",
            methods=[HttpMethodEnum.GET],
            service="orders",
        )
        assert route.auth == AuthModeEnum.NONE


class TestLambdaServiceConfig:
    """Tests for LambdaServiceConfig model."""

    def test_valid_lambda_service(self) -> None:
        """Test valid Lambda service configuration."""
        service = LambdaServiceConfig(entry="src/services/orders/handler.py:handler")
        assert service.entry == "src/services/orders/handler.py:handler"
        assert service.memory_mb == "auto"
        assert service.timeout_s == "auto"

    def test_memory_validation(self) -> None:
        """Test memory limits validation."""
        # Valid memory
        LambdaServiceConfig(entry="handler.py:h", memory_mb=512)
        LambdaServiceConfig(entry="handler.py:h", memory_mb=10240)

        # Invalid memory - too low
        with pytest.raises(ValidationError, match="between 128 and 10240"):
            LambdaServiceConfig(entry="handler.py:h", memory_mb=64)

        # Invalid memory - too high
        with pytest.raises(ValidationError, match="between 128 and 10240"):
            LambdaServiceConfig(entry="handler.py:h", memory_mb=20000)

    def test_timeout_validation(self) -> None:
        """Test timeout limits validation."""
        # Valid timeout
        LambdaServiceConfig(entry="handler.py:h", timeout_s=30)
        LambdaServiceConfig(entry="handler.py:h", timeout_s=900)

        # Invalid timeout - too low
        with pytest.raises(ValidationError, match="between 1 and 900"):
            LambdaServiceConfig(entry="handler.py:h", timeout_s=0)

        # Invalid timeout - too high
        with pytest.raises(ValidationError, match="between 1 and 900"):
            LambdaServiceConfig(entry="handler.py:h", timeout_s=1000)

    def test_entry_format_validation(self) -> None:
        """Test entry point format validation."""
        # Valid format
        LambdaServiceConfig(entry="handler.py:handler")
        LambdaServiceConfig(entry="src/services/handler.py:my_handler")

        # Invalid format - missing colon
        with pytest.raises(ValidationError, match="String should match pattern"):
            LambdaServiceConfig(entry="handler.py")


class TestAppRunnerServiceConfig:
    """Tests for AppRunnerServiceConfig model."""

    def test_valid_apprunner_service(self) -> None:
        """Test valid App Runner service configuration."""
        service = AppRunnerServiceConfig(dockerfile="Dockerfile")
        assert service.dockerfile == "Dockerfile"
        assert service.port == 8000
        assert service.healthcheck_path == "/healthz"
        assert service.cpu == 1
        assert service.memory == 2
        assert service.min_instances == 1
        assert service.max_instances == 10

    def test_instance_validation(self) -> None:
        """Test min/max instance validation."""
        # Valid
        AppRunnerServiceConfig(
            dockerfile="Dockerfile", min_instances=2, max_instances=10
        )

        # Invalid - min > max
        with pytest.raises(ValidationError, match="cannot be greater than"):
            AppRunnerServiceConfig(
                dockerfile="Dockerfile", min_instances=10, max_instances=5
            )

    def test_cpu_memory_literals(self) -> None:
        """Test CPU and memory accept only specific values."""
        # Valid CPU values
        AppRunnerServiceConfig(dockerfile="Dockerfile", cpu=1)
        AppRunnerServiceConfig(dockerfile="Dockerfile", cpu=2)
        AppRunnerServiceConfig(dockerfile="Dockerfile", cpu=4)

        # Invalid CPU
        with pytest.raises(ValidationError):
            AppRunnerServiceConfig(dockerfile="Dockerfile", cpu=3)


class TestDynamoDBConfig:
    """Tests for DynamoDB configuration models."""

    def test_valid_table_config(self) -> None:
        """Test valid DynamoDB table configuration."""
        table = DynamoDBTableConfig(name="orders", pk="order_id", sk="created_at")
        assert table.name == "orders"
        assert table.pk == "order_id"
        assert table.sk == "created_at"
        assert table.billing_mode == DynamoDBBillingModeEnum.PAY_PER_REQUEST
        assert table.pitr is False

    def test_enabled_requires_tables(self) -> None:
        """Test enabled DynamoDB requires at least one table."""
        with pytest.raises(ValidationError, match="no tables are configured"):
            DynamoDBConfig(enabled=True, tables=[])

    def test_disabled_allows_empty_tables(self) -> None:
        """Test disabled DynamoDB allows empty tables."""
        config = DynamoDBConfig(enabled=False, tables=[])
        assert config.enabled is False

    def test_duplicate_table_names(self) -> None:
        """Test duplicate table names are not allowed."""
        with pytest.raises(ValidationError, match="Duplicate DynamoDB table names"):
            DynamoDBConfig(
                enabled=True,
                tables=[
                    DynamoDBTableConfig(name="orders", pk="id"),
                    DynamoDBTableConfig(name="orders", pk="id"),
                ],
            )


class TestAuroraConfig:
    """Tests for Aurora configuration model."""

    def test_valid_aurora_config(self) -> None:
        """Test valid Aurora configuration."""
        config = AuroraConfig(
            enabled=True,
            engine=AuroraEngineEnum.POSTGRES,
            min_acu=0.5,
            max_acu=8,
        )
        assert config.enabled is True
        assert config.engine == AuroraEngineEnum.POSTGRES
        assert config.mode == AuroraModeEnum.SERVERLESS_V2

    def test_acu_range_validation(self) -> None:
        """Test ACU range validation."""
        # Valid
        AuroraConfig(min_acu=0.5, max_acu=128)

        # Invalid - min > max
        with pytest.raises(ValidationError, match="cannot be greater than"):
            AuroraConfig(min_acu=16, max_acu=8)


class TestCognitoConfig:
    """Tests for Cognito configuration model."""

    def test_create_new_user_pool(self) -> None:
        """Test configuration for creating new User Pool."""
        config = CognitoConfig(create_user_pool=True)
        assert config.create_user_pool is True
        assert config.user_pool_id is None

    def test_use_existing_user_pool(self) -> None:
        """Test configuration for existing User Pool."""
        config = CognitoConfig(user_pool_id="us-east-1_abc123", create_user_pool=False)
        assert config.user_pool_id == "us-east-1_abc123"
        assert config.create_user_pool is False

    def test_conflicting_config(self) -> None:
        """Test cannot specify both user_pool_id and create_user_pool."""
        with pytest.raises(ValidationError, match="Cannot specify both"):
            CognitoConfig(user_pool_id="us-east-1_abc123", create_user_pool=True)

    def test_must_specify_one(self) -> None:
        """Test must specify either user_pool_id or create_user_pool."""
        with pytest.raises(ValidationError, match="Must either provide"):
            CognitoConfig(create_user_pool=False)


class TestRestApiConfig:
    """Tests for REST API configuration model."""

    def test_cognito_auth_requires_config(self) -> None:
        """Test cognito auth requires cognito configuration."""
        with pytest.raises(ValidationError, match="no 'cognito' configuration"):
            RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/orders",
                        methods=[HttpMethodEnum.GET],
                        service="orders",
                        auth=AuthModeEnum.COGNITO,
                    )
                ],
                # Missing cognito config
            )

    def test_cognito_auth_with_config(self) -> None:
        """Test cognito auth works with cognito configuration."""
        config = RestApiConfig(
            enabled=True,
            routes=[
                RouteConfig(
                    path="/orders",
                    methods=[HttpMethodEnum.GET],
                    service="orders",
                    auth=AuthModeEnum.COGNITO,
                )
            ],
            cognito=CognitoConfig(create_user_pool=True),
        )
        assert config.cognito is not None


class TestGraphQLConfig:
    """Tests for GraphQL configuration model."""

    def test_enabled_requires_schema(self) -> None:
        """Test enabled GraphQL requires schema_path."""
        with pytest.raises(ValidationError, match="schema_path.*not specified"):
            GraphQLConfig(enabled=True)

    def test_cognito_auth_requires_config(self) -> None:
        """Test cognito auth requires cognito configuration."""
        with pytest.raises(ValidationError, match="no 'cognito' configuration"):
            GraphQLConfig(
                enabled=True,
                schema_path="schema.graphql",
                auth=AuthModeEnum.COGNITO,
            )


class TestFactoryConfig:
    """Tests for the root FactoryConfig model."""

    def test_minimal_valid_config(self) -> None:
        """Test minimal valid configuration."""
        config = FactoryConfig(
            project=ProjectConfig(name="my-api", envs=["dev", "prod"]),
            profile=ProfileEnum.MINIMAL,
        )
        assert config.project.name == "my-api"
        assert config.profile == ProfileEnum.MINIMAL

    def test_service_reference_validation(self) -> None:
        """Test routes must reference existing services."""
        with pytest.raises(ValidationError, match="not defined in compute"):
            FactoryConfig(
                project=ProjectConfig(name="api", envs=["dev"]),
                apis=ApisConfig(
                    rest=RestApiConfig(
                        enabled=True,
                        routes=[
                            RouteConfig(
                                path="/orders",
                                methods=[HttpMethodEnum.GET],
                                service="nonexistent",
                            )
                        ],
                    )
                ),
            )

    def test_valid_service_reference(self) -> None:
        """Test valid service reference passes validation."""
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/orders",
                            methods=[HttpMethodEnum.GET],
                            service="orders",
                        )
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(entry="handler.py:handler")
                    },
                )
            ),
        )
        assert "orders" in config.compute.lambda_.services

    def test_get_all_service_names(self) -> None:
        """Test get_all_service_names helper method."""
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(entry="handler.py:handler"),
                        "users": LambdaServiceConfig(entry="handler.py:handler"),
                    },
                ),
                apprunner=AppRunnerConfig(
                    enabled=True,
                    services={
                        "web": AppRunnerServiceConfig(dockerfile="Dockerfile"),
                    },
                ),
            ),
        )
        services = config.get_all_service_names()
        assert services == {"orders", "users", "web"}

    def test_uses_cognito_auth(self) -> None:
        """Test uses_cognito_auth helper method."""
        # No cognito
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
        )
        assert config.uses_cognito_auth() is False

        # With cognito on REST route
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/orders",
                            methods=[HttpMethodEnum.GET],
                            service="orders",
                            auth=AuthModeEnum.COGNITO,
                        )
                    ],
                    cognito=CognitoConfig(create_user_pool=True),
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={"orders": LambdaServiceConfig(entry="h.py:h")},
                )
            ),
        )
        assert config.uses_cognito_auth() is True

    def test_model_validate_dict(self) -> None:
        """Test model_validate works with dictionary input."""
        data = {
            "project": {"name": "my-api", "envs": ["dev", "prod"]},
            "profile": "minimal",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [
                        {"path": "/hello", "methods": ["GET"], "service": "hello"}
                    ],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {"hello": {"entry": "handler.py:handler"}},
                }
            },
        }
        config = FactoryConfig.model_validate(data)
        assert config.project.name == "my-api"
        assert config.profile == ProfileEnum.MINIMAL
        assert len(config.apis.rest.routes) == 1

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are rejected at all levels."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            FactoryConfig.model_validate(
                {
                    "project": {"name": "api", "envs": ["dev"]},
                    "unknown_field": "value",
                }
            )

    def test_get_routes_by_service(self) -> None:
        """Test get_routes_by_service helper method."""
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/orders",
                            methods=[HttpMethodEnum.GET],
                            service="orders",
                        ),
                        RouteConfig(
                            path="/orders/{id}",
                            methods=[HttpMethodEnum.GET],
                            service="orders",
                        ),
                        RouteConfig(
                            path="/users",
                            methods=[HttpMethodEnum.GET],
                            service="users",
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(entry="h.py:h"),
                        "users": LambdaServiceConfig(entry="h.py:h"),
                    },
                )
            ),
        )

        orders_routes = config.get_routes_by_service("orders")
        assert len(orders_routes) == 2
        assert all(r.service == "orders" for r in orders_routes)

        users_routes = config.get_routes_by_service("users")
        assert len(users_routes) == 1

        empty_routes = config.get_routes_by_service("nonexistent")
        assert len(empty_routes) == 0

    def test_get_resolvers_by_service(self) -> None:
        """Test get_resolvers_by_service helper method."""
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                graphql=GraphQLConfig(
                    enabled=True,
                    schema_path="schema.graphql",
                    resolvers=[
                        ResolverConfig(
                            type=GraphQLTypeEnum.QUERY,
                            field="getOrder",
                            service="orders",
                            resolver="get_order",
                        ),
                        ResolverConfig(
                            type=GraphQLTypeEnum.MUTATION,
                            field="createOrder",
                            service="orders",
                            resolver="create_order",
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(entry="h.py:h"),
                    },
                )
            ),
        )

        orders_resolvers = config.get_resolvers_by_service("orders")
        assert len(orders_resolvers) == 2

        empty_resolvers = config.get_resolvers_by_service("nonexistent")
        assert len(empty_resolvers) == 0

    def test_uses_api_key_auth(self) -> None:
        """Test uses_api_key_auth helper method."""
        # No API key auth - explicitly set GraphQL auth to IAM
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                graphql=GraphQLConfig(
                    enabled=False,  # Disabled GraphQL with non-api_key auth
                    auth=AuthModeEnum.IAM,
                )
            ),
        )
        assert config.uses_api_key_auth() is False

        # With API key on REST route
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/orders",
                            methods=[HttpMethodEnum.GET],
                            service="orders",
                            auth=AuthModeEnum.API_KEY,
                        )
                    ],
                ),
                graphql=GraphQLConfig(
                    enabled=False,
                    auth=AuthModeEnum.IAM,
                ),
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={"orders": LambdaServiceConfig(entry="h.py:h")},
                )
            ),
        )
        assert config.uses_api_key_auth() is True

        # With API key on GraphQL
        config = FactoryConfig(
            project=ProjectConfig(name="api", envs=["dev"]),
            apis=ApisConfig(
                graphql=GraphQLConfig(
                    enabled=True,
                    schema_path="schema.graphql",
                    auth=AuthModeEnum.API_KEY,
                )
            ),
        )
        assert config.uses_api_key_auth() is True


class TestS3Config:
    """Tests for S3 configuration model."""

    def test_enabled_requires_buckets(self) -> None:
        """Test enabled S3 requires at least one bucket."""
        with pytest.raises(ValidationError, match="no buckets are configured"):
            S3Config(enabled=True, buckets=[])

    def test_disabled_allows_empty_buckets(self) -> None:
        """Test disabled S3 allows empty buckets."""
        config = S3Config(enabled=False, buckets=[])
        assert config.enabled is False

    def test_duplicate_bucket_names(self) -> None:
        """Test duplicate bucket names are not allowed."""
        with pytest.raises(ValidationError, match="Duplicate S3 bucket names"):
            S3Config(
                enabled=True,
                buckets=[
                    S3BucketConfig(name="uploads"),
                    S3BucketConfig(name="uploads"),
                ],
            )

    def test_valid_bucket_config(self) -> None:
        """Test valid S3 bucket configuration."""
        config = S3Config(
            enabled=True,
            buckets=[
                S3BucketConfig(name="uploads", versioning=True, encryption=True),
            ],
        )
        assert len(config.buckets) == 1
        assert config.buckets[0].versioning is True
