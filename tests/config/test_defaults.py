# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for profile defaults configuration.

These tests validate the MinimalDefaults and ScalableDefaults dataclasses,
ensuring all default values are sensible and properly documented.
"""

from __future__ import annotations

import pytest

from aws_api_factory.config.defaults import (
    MINIMAL_DEFAULTS,
    SCALABLE_DEFAULTS,
    ApiGatewayDefaults,
    AppRunnerDefaults,
    AuroraDefaults,
    DynamoDBDefaults,
    LambdaDefaults,
    ObservabilityDefaults,
    ProfileDefaults,
    S3Defaults,
    SecretsDefaults,
    compare_profiles,
    get_all_profiles,
    get_defaults,
)
from aws_api_factory.config.models import ProfileEnum


class TestLambdaDefaults:
    """Tests for Lambda default values."""

    def test_minimal_lambda_defaults(self) -> None:
        """Test minimal profile Lambda defaults are sensible."""
        defaults = MINIMAL_DEFAULTS.lambda_
        assert defaults.memory_mb == 512
        assert defaults.timeout_s == 30
        assert defaults.reserved_concurrency is None

    def test_scalable_lambda_defaults(self) -> None:
        """Test scalable profile Lambda defaults are higher."""
        defaults = SCALABLE_DEFAULTS.lambda_
        assert defaults.memory_mb == 1024
        assert defaults.timeout_s == 60
        assert defaults.reserved_concurrency == 10

    def test_scalable_has_higher_resources_than_minimal(self) -> None:
        """Test scalable defaults are >= minimal defaults."""
        assert SCALABLE_DEFAULTS.lambda_.memory_mb >= MINIMAL_DEFAULTS.lambda_.memory_mb
        assert SCALABLE_DEFAULTS.lambda_.timeout_s >= MINIMAL_DEFAULTS.lambda_.timeout_s

    def test_lambda_defaults_within_aws_limits(self) -> None:
        """Test Lambda defaults are within AWS Lambda limits."""
        for defaults in [MINIMAL_DEFAULTS.lambda_, SCALABLE_DEFAULTS.lambda_]:
            assert 128 <= defaults.memory_mb <= 10240
            assert 1 <= defaults.timeout_s <= 900

    def test_lambda_defaults_dataclass_frozen(self) -> None:
        """Test LambdaDefaults is immutable."""
        defaults = LambdaDefaults(
            memory_mb=512, timeout_s=30, reserved_concurrency=None
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            defaults.memory_mb = 1024  # type: ignore


class TestApiGatewayDefaults:
    """Tests for API Gateway default values."""

    def test_minimal_api_gateway_defaults(self) -> None:
        """Test minimal profile API Gateway defaults."""
        defaults = MINIMAL_DEFAULTS.api_gateway
        assert defaults.throttle_rate is None
        assert defaults.throttle_burst is None
        assert defaults.logging_level == "INFO"
        assert defaults.metrics_enabled is False
        assert defaults.tracing_enabled is False

    def test_scalable_api_gateway_defaults(self) -> None:
        """Test scalable profile API Gateway defaults."""
        defaults = SCALABLE_DEFAULTS.api_gateway
        assert defaults.throttle_rate == 1000
        assert defaults.throttle_burst == 2000
        assert defaults.logging_level == "INFO"
        assert defaults.metrics_enabled is True
        assert defaults.tracing_enabled is True

    def test_scalable_has_more_observability(self) -> None:
        """Test scalable has metrics and tracing enabled."""
        assert SCALABLE_DEFAULTS.api_gateway.metrics_enabled is True
        assert SCALABLE_DEFAULTS.api_gateway.tracing_enabled is True
        assert MINIMAL_DEFAULTS.api_gateway.metrics_enabled is False
        assert MINIMAL_DEFAULTS.api_gateway.tracing_enabled is False


class TestAppRunnerDefaults:
    """Tests for App Runner default values."""

    def test_minimal_apprunner_defaults(self) -> None:
        """Test minimal profile App Runner defaults."""
        defaults = MINIMAL_DEFAULTS.apprunner
        assert defaults.cpu == 1
        assert defaults.memory == 2
        assert defaults.min_instances == 1
        assert defaults.max_instances == 10
        assert defaults.healthcheck_protocol == "TCP"
        assert defaults.healthcheck_path == "/healthz"

    def test_scalable_apprunner_defaults(self) -> None:
        """Test scalable profile App Runner defaults."""
        defaults = SCALABLE_DEFAULTS.apprunner
        assert defaults.cpu == 2
        assert defaults.memory == 4
        assert defaults.min_instances == 2
        assert defaults.max_instances == 25
        assert defaults.healthcheck_protocol == "HTTP"
        assert defaults.healthcheck_path == "/healthz"

    def test_apprunner_values_within_aws_limits(self) -> None:
        """Test App Runner defaults are within AWS limits."""
        for defaults in [MINIMAL_DEFAULTS.apprunner, SCALABLE_DEFAULTS.apprunner]:
            assert defaults.cpu in (1, 2, 4)
            assert defaults.memory in (2, 3, 4, 6, 8, 10, 12)
            assert 1 <= defaults.min_instances <= 25
            assert 1 <= defaults.max_instances <= 25
            assert defaults.min_instances <= defaults.max_instances

    def test_scalable_has_higher_resources(self) -> None:
        """Test scalable profile has higher App Runner resources."""
        assert SCALABLE_DEFAULTS.apprunner.cpu >= MINIMAL_DEFAULTS.apprunner.cpu
        assert SCALABLE_DEFAULTS.apprunner.memory >= MINIMAL_DEFAULTS.apprunner.memory
        assert (
            SCALABLE_DEFAULTS.apprunner.min_instances
            >= MINIMAL_DEFAULTS.apprunner.min_instances
        )


class TestDynamoDBDefaults:
    """Tests for DynamoDB default values."""

    def test_minimal_dynamodb_defaults(self) -> None:
        """Test minimal profile DynamoDB defaults."""
        defaults = MINIMAL_DEFAULTS.dynamodb
        assert defaults.billing_mode == "PAY_PER_REQUEST"
        assert defaults.pitr_enabled is False
        assert defaults.alarms_enabled is False

    def test_scalable_dynamodb_defaults(self) -> None:
        """Test scalable profile DynamoDB defaults."""
        defaults = SCALABLE_DEFAULTS.dynamodb
        assert defaults.billing_mode == "PAY_PER_REQUEST"
        assert defaults.pitr_enabled is True
        assert defaults.alarms_enabled is True

    def test_scalable_has_data_protection(self) -> None:
        """Test scalable profile has PITR enabled."""
        assert SCALABLE_DEFAULTS.dynamodb.pitr_enabled is True
        assert MINIMAL_DEFAULTS.dynamodb.pitr_enabled is False


class TestAuroraDefaults:
    """Tests for Aurora Serverless v2 default values."""

    def test_minimal_aurora_defaults(self) -> None:
        """Test minimal profile Aurora defaults."""
        defaults = MINIMAL_DEFAULTS.aurora
        assert defaults.min_acu == 0.5
        assert defaults.max_acu == 8
        assert defaults.backup_retention_days == 1
        assert defaults.deletion_protection is False

    def test_scalable_aurora_defaults(self) -> None:
        """Test scalable profile Aurora defaults."""
        defaults = SCALABLE_DEFAULTS.aurora
        assert defaults.min_acu == 0.5
        assert defaults.max_acu == 16
        assert defaults.backup_retention_days == 7
        assert defaults.deletion_protection is True

    def test_aurora_acu_ranges_valid(self) -> None:
        """Test Aurora ACU values are within AWS limits."""
        for defaults in [MINIMAL_DEFAULTS.aurora, SCALABLE_DEFAULTS.aurora]:
            assert 0.5 <= defaults.min_acu <= 128
            assert 0.5 <= defaults.max_acu <= 128
            assert defaults.min_acu <= defaults.max_acu


class TestS3Defaults:
    """Tests for S3 bucket default values."""

    def test_minimal_s3_defaults(self) -> None:
        """Test minimal profile S3 defaults."""
        defaults = MINIMAL_DEFAULTS.s3
        assert defaults.versioning_enabled is False
        assert defaults.encryption_enabled is True
        assert defaults.lifecycle_enabled is False

    def test_scalable_s3_defaults(self) -> None:
        """Test scalable profile S3 defaults."""
        defaults = SCALABLE_DEFAULTS.s3
        assert defaults.versioning_enabled is True
        assert defaults.encryption_enabled is True
        assert defaults.lifecycle_enabled is True

    def test_encryption_always_on(self) -> None:
        """Test S3 encryption is enabled in both profiles."""
        assert MINIMAL_DEFAULTS.s3.encryption_enabled is True
        assert SCALABLE_DEFAULTS.s3.encryption_enabled is True


class TestObservabilityDefaults:
    """Tests for observability default values."""

    def test_minimal_observability_defaults(self) -> None:
        """Test minimal profile observability defaults."""
        defaults = MINIMAL_DEFAULTS.observability
        assert defaults.level == "basic"
        assert defaults.tracing_enabled is False
        assert defaults.alarms_enabled is False
        assert defaults.dashboards_enabled is False
        assert defaults.log_retention_days == 7

    def test_scalable_observability_defaults(self) -> None:
        """Test scalable profile observability defaults."""
        defaults = SCALABLE_DEFAULTS.observability
        assert defaults.level == "enhanced"
        assert defaults.tracing_enabled is True
        assert defaults.alarms_enabled is True
        assert defaults.dashboards_enabled is True
        assert defaults.log_retention_days == 30

    def test_scalable_has_full_observability(self) -> None:
        """Test scalable profile has complete observability stack."""
        assert SCALABLE_DEFAULTS.observability.tracing_enabled is True
        assert SCALABLE_DEFAULTS.observability.alarms_enabled is True
        assert SCALABLE_DEFAULTS.observability.dashboards_enabled is True


class TestSecretsDefaults:
    """Tests for secrets management default values."""

    def test_minimal_secrets_defaults(self) -> None:
        """Test minimal profile uses SSM Parameter Store."""
        assert MINIMAL_DEFAULTS.secrets.provider == "ssm"

    def test_scalable_secrets_defaults(self) -> None:
        """Test scalable profile uses Secrets Manager."""
        assert SCALABLE_DEFAULTS.secrets.provider == "secrets_manager"


class TestProfileDefaults:
    """Tests for ProfileDefaults container class."""

    def test_profile_names_correct(self) -> None:
        """Test profile names are set correctly."""
        assert MINIMAL_DEFAULTS.profile_name == "minimal"
        assert SCALABLE_DEFAULTS.profile_name == "scalable"

    def test_cost_estimates_present(self) -> None:
        """Test cost estimates are provided."""
        assert MINIMAL_DEFAULTS.estimated_monthly_cost_usd != ""
        assert SCALABLE_DEFAULTS.estimated_monthly_cost_usd != ""

    def test_invalid_lambda_memory_raises(self) -> None:
        """Test invalid Lambda memory raises ValueError."""
        with pytest.raises(ValueError, match="Lambda memory_mb must be 128-10240"):
            ProfileDefaults(
                profile_name="test",
                lambda_=LambdaDefaults(
                    memory_mb=64, timeout_s=30, reserved_concurrency=None
                ),
                api_gateway=MINIMAL_DEFAULTS.api_gateway,
                apprunner=MINIMAL_DEFAULTS.apprunner,
                dynamodb=MINIMAL_DEFAULTS.dynamodb,
                aurora=MINIMAL_DEFAULTS.aurora,
                s3=MINIMAL_DEFAULTS.s3,
                observability=MINIMAL_DEFAULTS.observability,
                secrets=MINIMAL_DEFAULTS.secrets,
            )

    def test_invalid_lambda_timeout_raises(self) -> None:
        """Test invalid Lambda timeout raises ValueError."""
        with pytest.raises(ValueError, match="Lambda timeout_s must be 1-900"):
            ProfileDefaults(
                profile_name="test",
                lambda_=LambdaDefaults(
                    memory_mb=512, timeout_s=1000, reserved_concurrency=None
                ),
                api_gateway=MINIMAL_DEFAULTS.api_gateway,
                apprunner=MINIMAL_DEFAULTS.apprunner,
                dynamodb=MINIMAL_DEFAULTS.dynamodb,
                aurora=MINIMAL_DEFAULTS.aurora,
                s3=MINIMAL_DEFAULTS.s3,
                observability=MINIMAL_DEFAULTS.observability,
                secrets=MINIMAL_DEFAULTS.secrets,
            )

    def test_invalid_apprunner_cpu_raises(self) -> None:
        """Test invalid App Runner CPU raises ValueError."""
        with pytest.raises(ValueError, match="App Runner CPU must be 1, 2, or 4"):
            ProfileDefaults(
                profile_name="test",
                lambda_=MINIMAL_DEFAULTS.lambda_,
                api_gateway=MINIMAL_DEFAULTS.api_gateway,
                apprunner=AppRunnerDefaults(
                    cpu=3,
                    memory=2,
                    min_instances=1,
                    max_instances=10,
                    healthcheck_protocol="TCP",
                    healthcheck_path="/healthz",
                ),
                dynamodb=MINIMAL_DEFAULTS.dynamodb,
                aurora=MINIMAL_DEFAULTS.aurora,
                s3=MINIMAL_DEFAULTS.s3,
                observability=MINIMAL_DEFAULTS.observability,
                secrets=MINIMAL_DEFAULTS.secrets,
            )


class TestGetDefaults:
    """Tests for get_defaults function."""

    def test_get_minimal_defaults(self) -> None:
        """Test getting minimal profile defaults."""
        defaults = get_defaults(ProfileEnum.MINIMAL)
        assert defaults is MINIMAL_DEFAULTS
        assert defaults.profile_name == "minimal"

    def test_get_scalable_defaults(self) -> None:
        """Test getting scalable profile defaults."""
        defaults = get_defaults(ProfileEnum.SCALABLE)
        assert defaults is SCALABLE_DEFAULTS
        assert defaults.profile_name == "scalable"


class TestGetAllProfiles:
    """Tests for get_all_profiles function."""

    def test_returns_both_profiles(self) -> None:
        """Test get_all_profiles returns both profiles."""
        profiles = get_all_profiles()
        assert "minimal" in profiles
        assert "scalable" in profiles
        assert len(profiles) == 2

    def test_profiles_are_correct_instances(self) -> None:
        """Test returned profiles are the correct instances."""
        profiles = get_all_profiles()
        assert profiles["minimal"] is MINIMAL_DEFAULTS
        assert profiles["scalable"] is SCALABLE_DEFAULTS


class TestCompareProfiles:
    """Tests for compare_profiles function."""

    def test_compare_profiles_returns_diffs(self) -> None:
        """Test compare_profiles returns differences."""
        diffs = compare_profiles()
        assert "lambda" in diffs
        assert "apprunner" in diffs
        assert "observability" in diffs

    def test_lambda_diffs_correct(self) -> None:
        """Test Lambda differences are captured correctly."""
        diffs = compare_profiles()
        assert diffs["lambda"]["memory_mb"] == (512, 1024)
        assert diffs["lambda"]["timeout_s"] == (30, 60)
        assert diffs["lambda"]["reserved_concurrency"] == (None, 10)

    def test_api_gateway_diffs_correct(self) -> None:
        """Test API Gateway differences are captured correctly."""
        diffs = compare_profiles()
        assert diffs["api_gateway"]["throttle_rate"] == (None, 1000)
        assert diffs["api_gateway"]["metrics_enabled"] == (False, True)
        assert diffs["api_gateway"]["tracing_enabled"] == (False, True)

    def test_observability_diffs_correct(self) -> None:
        """Test observability differences are captured correctly."""
        diffs = compare_profiles()
        assert diffs["observability"]["level"] == ("basic", "enhanced")
        assert diffs["observability"]["tracing_enabled"] == (False, True)
        assert diffs["observability"]["log_retention_days"] == (7, 30)

    def test_no_empty_categories(self) -> None:
        """Test compare_profiles doesn't return empty categories."""
        diffs = compare_profiles()
        for category, values in diffs.items():
            assert len(values) > 0, f"Category {category} is empty"


class TestDefaultsDocumentation:
    """Tests to ensure defaults are well-documented."""

    def test_lambda_defaults_has_docstring(self) -> None:
        """Test LambdaDefaults has a docstring."""
        assert LambdaDefaults.__doc__ is not None
        assert "memory" in LambdaDefaults.__doc__.lower()

    def test_api_gateway_defaults_has_docstring(self) -> None:
        """Test ApiGatewayDefaults has a docstring."""
        assert ApiGatewayDefaults.__doc__ is not None
        assert "throttle" in ApiGatewayDefaults.__doc__.lower()

    def test_apprunner_defaults_has_docstring(self) -> None:
        """Test AppRunnerDefaults has a docstring."""
        assert AppRunnerDefaults.__doc__ is not None
        assert "instance" in AppRunnerDefaults.__doc__.lower()

    def test_dynamodb_defaults_has_docstring(self) -> None:
        """Test DynamoDBDefaults has a docstring."""
        assert DynamoDBDefaults.__doc__ is not None
        assert "pitr" in DynamoDBDefaults.__doc__.lower()

    def test_aurora_defaults_has_docstring(self) -> None:
        """Test AuroraDefaults has a docstring."""
        assert AuroraDefaults.__doc__ is not None
        assert "acu" in AuroraDefaults.__doc__.lower()

    def test_s3_defaults_has_docstring(self) -> None:
        """Test S3Defaults has a docstring."""
        assert S3Defaults.__doc__ is not None
        assert "versioning" in S3Defaults.__doc__.lower()

    def test_observability_defaults_has_docstring(self) -> None:
        """Test ObservabilityDefaults has a docstring."""
        assert ObservabilityDefaults.__doc__ is not None
        assert "tracing" in ObservabilityDefaults.__doc__.lower()

    def test_secrets_defaults_has_docstring(self) -> None:
        """Test SecretsDefaults has a docstring."""
        assert SecretsDefaults.__doc__ is not None
        assert "provider" in SecretsDefaults.__doc__.lower()

    def test_profile_defaults_has_docstring(self) -> None:
        """Test ProfileDefaults has a docstring."""
        assert ProfileDefaults.__doc__ is not None
        assert "profile" in ProfileDefaults.__doc__.lower()
