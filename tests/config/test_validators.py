# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for configuration validators."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from aws_api_factory.config.loader import load_config_from_string
from aws_api_factory.config.models import (
    ApisConfig,
    AppRunnerConfig,
    AppRunnerServiceConfig,
    ComputeConfig,
    FactoryConfig,
    GraphQLConfig,
    GraphQLTypeEnum,
    HttpMethodEnum,
    LambdaConfig,
    LambdaServiceConfig,
    ProfileEnum,
    ProjectConfig,
    ResolverConfig,
    RestApiConfig,
    RouteConfig,
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


def create_minimal_config(**overrides) -> FactoryConfig:
    """Create a minimal valid config for testing."""
    base = {
        "project": ProjectConfig(name="test-api", envs=["dev"]),
        "profile": ProfileEnum.MINIMAL,
    }
    base.update(overrides)
    return FactoryConfig(**base)


class TestValidateEntryPointsExist:
    """Tests for validate_entry_points_exist function."""

    def test_valid_entry_points(self, tmp_path: Path) -> None:
        """Test validation passes for existing entry points."""
        # Create handler file
        handler_dir = tmp_path / "src" / "services" / "hello"
        handler_dir.mkdir(parents=True)
        (handler_dir / "handler.py").write_text("def handler(event, context): pass")

        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler"
                        )
                    },
                )
            )
        )

        errors = validate_entry_points_exist(config, base_path=tmp_path)
        assert errors == []

    def test_missing_entry_points(self, tmp_path: Path) -> None:
        """Test validation fails for missing entry points."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler"
                        )
                    },
                )
            )
        )

        errors = validate_entry_points_exist(config, base_path=tmp_path)
        assert len(errors) == 1
        assert "hello" in errors[0]
        assert "not found" in errors[0]

    def test_disabled_lambda_skips_check(self, tmp_path: Path) -> None:
        """Test validation skips check when Lambda is disabled."""
        # When Lambda is disabled with no services, it should skip validation
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=False,
                    services={},  # No services defined
                )
            )
        )

        errors = validate_entry_points_exist(config, base_path=tmp_path)
        assert errors == []


class TestValidateDockerfilesExist:
    """Tests for validate_dockerfiles_exist function."""

    def test_valid_dockerfile(self, tmp_path: Path) -> None:
        """Test validation passes for existing Dockerfile."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.12")

        config = create_minimal_config(
            compute=ComputeConfig(
                apprunner=AppRunnerConfig(
                    enabled=True,
                    services={"web": AppRunnerServiceConfig(dockerfile="Dockerfile")},
                )
            )
        )

        errors = validate_dockerfiles_exist(config, base_path=tmp_path)
        assert errors == []

    def test_missing_dockerfile(self, tmp_path: Path) -> None:
        """Test validation fails for missing Dockerfile."""
        config = create_minimal_config(
            compute=ComputeConfig(
                apprunner=AppRunnerConfig(
                    enabled=True,
                    services={"web": AppRunnerServiceConfig(dockerfile="Dockerfile")},
                )
            )
        )

        errors = validate_dockerfiles_exist(config, base_path=tmp_path)
        assert len(errors) == 1
        assert "Dockerfile" in errors[0]


class TestValidateGraphqlSchemaExists:
    """Tests for validate_graphql_schema_exists function."""

    def test_valid_schema(self, tmp_path: Path) -> None:
        """Test validation passes for existing schema file."""
        schema_file = tmp_path / "schema.graphql"
        schema_file.write_text("type Query { hello: String }")

        config = create_minimal_config(
            apis=ApisConfig(
                graphql=GraphQLConfig(
                    enabled=True,
                    schema_path="schema.graphql",
                )
            )
        )

        errors = validate_graphql_schema_exists(config, base_path=tmp_path)
        assert errors == []

    def test_missing_schema(self, tmp_path: Path) -> None:
        """Test validation fails for missing schema file."""
        config = create_minimal_config(
            apis=ApisConfig(
                graphql=GraphQLConfig(
                    enabled=True,
                    schema_path="schema.graphql",
                )
            )
        )

        errors = validate_graphql_schema_exists(config, base_path=tmp_path)
        assert len(errors) == 1
        assert "schema.graphql" in errors[0]


class TestValidateUniqueRoutePaths:
    """Tests for validate_unique_route_paths function."""

    def test_unique_routes(self) -> None:
        """Test validation passes for unique routes."""
        config = create_minimal_config(
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
                            path="/orders",
                            methods=[HttpMethodEnum.POST],
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

        errors = validate_unique_route_paths(config)
        assert errors == []

    def test_duplicate_routes(self) -> None:
        """Test validation fails for duplicate routes."""
        config = create_minimal_config(
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
                            path="/orders",
                            methods=[HttpMethodEnum.GET],
                            service="other",
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(entry="h.py:h"),
                        "other": LambdaServiceConfig(entry="h.py:h"),
                    },
                )
            ),
        )

        errors = validate_unique_route_paths(config)
        assert len(errors) == 1
        assert "Duplicate route" in errors[0]
        assert "GET /orders" in errors[0]


class TestValidateUniqueResolverFields:
    """Tests for validate_unique_resolver_fields function."""

    def test_unique_resolvers(self) -> None:
        """Test validation passes for unique resolvers."""
        config = create_minimal_config(
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

        errors = validate_unique_resolver_fields(config)
        assert errors == []

    def test_duplicate_resolvers(self) -> None:
        """Test validation fails for duplicate resolvers."""
        config = create_minimal_config(
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
                            type=GraphQLTypeEnum.QUERY,
                            field="getOrder",
                            service="other",
                            resolver="get_order",
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(entry="h.py:h"),
                        "other": LambdaServiceConfig(entry="h.py:h"),
                    },
                )
            ),
        )

        errors = validate_unique_resolver_fields(config)
        assert len(errors) == 1
        assert "Duplicate resolver" in errors[0]


class TestValidateEnvironmentVariables:
    """Tests for validate_environment_variables function."""

    def test_valid_env_vars(self) -> None:
        """Test validation passes for valid env var names."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="h.py:h",
                            environment={
                                "LOG_LEVEL": "INFO",
                                "DATABASE_URL": "postgres://...",
                                "_PRIVATE": "value",
                            },
                        )
                    },
                )
            )
        )

        errors = validate_environment_variables(config)
        assert errors == []

    def test_invalid_env_var_names(self) -> None:
        """Test validation fails for invalid env var names."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="h.py:h",
                            environment={
                                "123_INVALID": "value",  # Starts with number
                            },
                        )
                    },
                )
            )
        )

        errors = validate_environment_variables(config)
        assert len(errors) == 1
        assert "123_INVALID" in errors[0]


class TestValidateNoSecretsInConfig:
    """Tests for validate_no_secrets_in_config function."""

    def test_no_secrets(self) -> None:
        """Test no warnings for non-secret values."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="h.py:h",
                            environment={
                                "LOG_LEVEL": "INFO",
                                "TABLE_NAME": "orders",
                            },
                        )
                    },
                )
            )
        )

        warnings = validate_no_secrets_in_config(config)
        assert warnings == []

    def test_potential_secret_detected(self) -> None:
        """Test warning for potential secret in env var."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="h.py:h",
                            environment={
                                "API_KEY": "sk-1234567890abcdef",  # pragma: allowlist secret
                            },
                        )
                    },
                )
            )
        )

        warnings = validate_no_secrets_in_config(config)
        assert len(warnings) == 1
        assert "API_KEY" in warnings[0]
        assert "secret" in warnings[0].lower()

    def test_ssm_reference_not_flagged(self) -> None:
        """Test SSM references are not flagged as secrets."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="h.py:h",
                            environment={
                                "API_KEY": "ssm:/my/api/key",  # pragma: allowlist secret
                            },
                        )
                    },
                )
            )
        )

        warnings = validate_no_secrets_in_config(config)
        assert warnings == []


class TestValidateProfileRecommendations:
    """Tests for validate_profile_recommendations function."""

    def test_scalable_with_basic_observability(self) -> None:
        """Test recommendation when scalable uses basic observability."""
        config = create_minimal_config(profile=ProfileEnum.SCALABLE)

        recommendations = validate_profile_recommendations(config)
        assert any("enhanced" in r.lower() for r in recommendations)

    def test_minimal_profile_no_recommendations(self) -> None:
        """Test no recommendations for typical minimal profile."""
        config = create_minimal_config(profile=ProfileEnum.MINIMAL)

        recommendations = validate_profile_recommendations(config)
        # Should not have aurora warning if aurora not enabled
        assert not any("aurora" in r.lower() for r in recommendations)


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_all_validators_run(self, tmp_path: Path) -> None:
        """Test all validators are executed."""
        # Create a config with multiple potential issues
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="nonexistent/handler.py:handler",
                            environment={
                                "API_KEY": "sk-secret123456789",  # pragma: allowlist secret
                            },
                        )
                    },
                )
            )
        )

        errors, warnings = validate_config(config, base_path=tmp_path)
        assert len(errors) >= 1  # At least entry point error
        assert len(warnings) >= 1  # At least secret warning

    def test_skip_file_checks(self) -> None:
        """Test file checks can be skipped."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="nonexistent/handler.py:handler"
                        )
                    },
                )
            )
        )

        errors, warnings = validate_config(config, check_files=False)
        # Should not have entry point error
        assert not any("not found" in e for e in errors)


class TestValidateConfigStrict:
    """Tests for validate_config_strict function."""

    def test_raises_on_error(self, tmp_path: Path) -> None:
        """Test raises ConfigValidationError on errors."""
        config = create_minimal_config(
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="nonexistent/handler.py:handler"
                        )
                    },
                )
            )
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_strict(config, base_path=tmp_path)

        error = exc_info.value
        assert len(error.errors) >= 1
        assert "not found" in str(error)


class TestValidateAppRunnerEnvVars:
    """Tests for App Runner environment variable validation."""

    def test_apprunner_invalid_env_var(self) -> None:
        """Test validation catches invalid App Runner env var names."""
        config = create_minimal_config(
            compute=ComputeConfig(
                apprunner=AppRunnerConfig(
                    enabled=True,
                    services={
                        "web": AppRunnerServiceConfig(
                            dockerfile="Dockerfile",
                            environment={
                                "1BAD_NAME": "value",
                            },
                        )
                    },
                )
            )
        )

        errors = validate_environment_variables(config)
        assert len(errors) == 1
        assert "1BAD_NAME" in errors[0]


class TestValidateAppRunnerSecrets:
    """Tests for App Runner secrets detection."""

    def test_apprunner_secret_detected(self) -> None:
        """Test warning for potential secret in App Runner env var."""
        config = create_minimal_config(
            compute=ComputeConfig(
                apprunner=AppRunnerConfig(
                    enabled=True,
                    services={
                        "web": AppRunnerServiceConfig(
                            dockerfile="Dockerfile",
                            environment={
                                "DATABASE_PASSWORD": "supersecretpassword123",  # pragma: allowlist secret
                            },
                        )
                    },
                )
            )
        )

        warnings = validate_no_secrets_in_config(config)
        assert len(warnings) == 1
        assert "PASSWORD" in warnings[0] or "password" in warnings[0].lower()


class TestValidateScalableProfileRecommendations:
    """Tests for scalable profile recommendations."""

    def test_unauthenticated_routes_warning(self) -> None:
        """Test warning for unauthenticated routes in scalable profile."""
        config = create_minimal_config(
            profile=ProfileEnum.SCALABLE,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/public",
                            methods=[HttpMethodEnum.GET],
                            service="public",
                        )
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "public": LambdaServiceConfig(entry="h.py:h"),
                    },
                )
            ),
        )

        recommendations = validate_profile_recommendations(config)
        assert any("auth" in r.lower() for r in recommendations)


class TestValidateMinimalProfileWithAurora:
    """Tests for minimal profile with Aurora recommendations."""

    def test_aurora_cost_warning(self) -> None:
        """Test warning for Aurora in minimal profile."""
        from aws_api_factory.config.models import AuroraConfig, DataConfig

        config = create_minimal_config(
            profile=ProfileEnum.MINIMAL,
            data=DataConfig(
                aurora=AuroraConfig(enabled=True),
            ),
        )

        recommendations = validate_profile_recommendations(config)
        assert any(
            "aurora" in r.lower() or "cost" in r.lower() for r in recommendations
        )
