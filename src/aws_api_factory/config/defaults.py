# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Profile defaults for AWS API Factory.

This module defines the default values for Minimal and Scalable profiles.
Each profile provides sensible defaults optimized for different use cases:

- **Minimal**: Lower ops overhead, cost-effective, suitable for development,
  prototyping, and low-traffic applications. Approximately free-tier friendly.

- **Scalable**: Higher resilience, stronger security posture, production-ready
  observability, and better performance defaults for production workloads.

Example:
    >>> from aws_api_factory.config.defaults import get_defaults
    >>> from aws_api_factory.config.models import ProfileEnum
    >>> defaults = get_defaults(ProfileEnum.MINIMAL)
    >>> print(defaults.lambda_memory_mb)
    512

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aws_api_factory.config.models import ProfileEnum


@dataclass(frozen=True)
class LambdaDefaults:
    """Default values for Lambda compute configuration.

    Attributes:
        memory_mb: Memory allocation in MB.
        timeout_s: Function timeout in seconds.
        reserved_concurrency: Reserved concurrent executions (None = unreserved).

    Rationale:
        - Minimal: 512MB/30s balances cost and performance for most workloads.
          No reserved concurrency to allow pay-per-use scaling.
        - Scalable: 1024MB/60s provides headroom for production traffic.
          Reserved concurrency (10) ensures consistent performance.
    """

    memory_mb: int
    timeout_s: int
    reserved_concurrency: int | None


@dataclass(frozen=True)
class ApiGatewayDefaults:
    """Default values for API Gateway REST API configuration.

    Attributes:
        throttle_rate: Requests per second limit (None = AWS default 10,000).
        throttle_burst: Burst limit (None = AWS default 5,000).
        logging_level: CloudWatch logging level.
        metrics_enabled: Enable detailed CloudWatch metrics.
        tracing_enabled: Enable X-Ray tracing.

    Rationale:
        - Minimal: No throttle limits to avoid unexpected 429s during dev.
          Basic logging only for cost savings.
        - Scalable: Throttle limits protect backend services. Full metrics
          and tracing for production observability.
    """

    throttle_rate: int | None
    throttle_burst: int | None
    logging_level: str
    metrics_enabled: bool
    tracing_enabled: bool


@dataclass(frozen=True)
class AppRunnerDefaults:
    """Default values for App Runner compute configuration.

    Attributes:
        cpu: CPU units (vCPUs).
        memory: Memory in GB.
        min_instances: Minimum number of instances.
        max_instances: Maximum number of instances.
        healthcheck_protocol: Health check protocol (TCP or HTTP).
        healthcheck_path: HTTP health check endpoint path.

    Rationale:
        - Minimal: 1 vCPU/2GB is the smallest config. 1 min instance keeps
          costs low. TCP health check is simpler.
        - Scalable: 2 vCPU/4GB handles production load. 2 min instances
          ensures availability. HTTP health check validates app readiness.
    """

    cpu: int
    memory: int
    min_instances: int
    max_instances: int
    healthcheck_protocol: str
    healthcheck_path: str


@dataclass(frozen=True)
class DynamoDBDefaults:
    """Default values for DynamoDB table configuration.

    Attributes:
        billing_mode: DynamoDB billing mode.
        pitr_enabled: Point-in-Time Recovery enabled.
        alarms_enabled: CloudWatch alarms for table metrics.

    Rationale:
        - Minimal: PAY_PER_REQUEST is cost-effective for variable traffic.
          No PITR or alarms to minimize costs during development.
        - Scalable: Same billing mode but with PITR for data protection
          and alarms for operational visibility.
    """

    billing_mode: str
    pitr_enabled: bool
    alarms_enabled: bool


@dataclass(frozen=True)
class AuroraDefaults:
    """Default values for Aurora Serverless v2 configuration.

    Attributes:
        min_acu: Minimum Aurora Capacity Units.
        max_acu: Maximum Aurora Capacity Units.
        backup_retention_days: Automated backup retention period.
        deletion_protection: Enable deletion protection.

    Rationale:
        - Minimal: 0.5 ACU minimum allows scale-to-zero-like behavior.
          Lower max ACU caps costs. Minimal backup retention.
        - Scalable: Same minimum but higher max for production traffic.
          Longer backup retention and deletion protection for safety.
    """

    min_acu: float
    max_acu: float
    backup_retention_days: int
    deletion_protection: bool


@dataclass(frozen=True)
class S3Defaults:
    """Default values for S3 bucket configuration.

    Attributes:
        versioning_enabled: Enable object versioning.
        encryption_enabled: Enable server-side encryption.
        lifecycle_enabled: Enable lifecycle rules.

    Rationale:
        - Minimal: Encryption always on for security. Versioning off
          to save storage costs during development.
        - Scalable: Versioning on for data protection in production.
          Same encryption. Lifecycle rules for cost management.
    """

    versioning_enabled: bool
    encryption_enabled: bool
    lifecycle_enabled: bool


@dataclass(frozen=True)
class ObservabilityDefaults:
    """Default values for observability configuration.

    Attributes:
        level: Observability level (basic or enhanced).
        tracing_enabled: Enable X-Ray distributed tracing.
        alarms_enabled: Enable CloudWatch alarms.
        dashboards_enabled: Enable CloudWatch dashboards.
        log_retention_days: CloudWatch log retention in days.

    Rationale:
        - Minimal: Basic level with short log retention minimizes costs.
          No tracing, alarms, or dashboards during development.
        - Scalable: Enhanced level with full observability stack.
          Longer log retention for compliance and debugging.
    """

    level: str
    tracing_enabled: bool
    alarms_enabled: bool
    dashboards_enabled: bool
    log_retention_days: int


@dataclass(frozen=True)
class SecretsDefaults:
    """Default values for secrets management configuration.

    Attributes:
        provider: Secrets provider (ssm or secrets_manager).

    Rationale:
        - Minimal: SSM Parameter Store is simpler and lower cost for
          development environments with fewer secrets.
        - Scalable: Secrets Manager provides rotation, cross-account
          access, and better audit logging for production.
    """

    provider: str


@dataclass(frozen=True)
class ProfileDefaults:
    """Complete set of defaults for a deployment profile.

    This class aggregates all component defaults into a single object
    that can be used by the DefaultsResolver to fill in missing values.

    Attributes:
        profile_name: The profile name (minimal or scalable).
        lambda_: Lambda compute defaults.
        api_gateway: API Gateway defaults.
        apprunner: App Runner defaults.
        dynamodb: DynamoDB defaults.
        aurora: Aurora defaults.
        s3: S3 defaults.
        observability: Observability defaults.
        secrets: Secrets management defaults.
    """

    profile_name: str
    lambda_: LambdaDefaults
    api_gateway: ApiGatewayDefaults
    apprunner: AppRunnerDefaults
    dynamodb: DynamoDBDefaults
    aurora: AuroraDefaults
    s3: S3Defaults
    observability: ObservabilityDefaults
    secrets: SecretsDefaults

    # Cost estimate per month (rough approximation for documentation)
    estimated_monthly_cost_usd: str = field(default="")

    def __post_init__(self) -> None:
        """Validate defaults after initialization."""
        # Validate Lambda memory within AWS limits
        if self.lambda_.memory_mb < 128 or self.lambda_.memory_mb > 10240:
            raise ValueError(
                f"Lambda memory_mb must be 128-10240, got {self.lambda_.memory_mb}"
            )
        # Validate Lambda timeout within AWS limits
        if self.lambda_.timeout_s < 1 or self.lambda_.timeout_s > 900:
            raise ValueError(
                f"Lambda timeout_s must be 1-900, got {self.lambda_.timeout_s}"
            )
        # Validate App Runner CPU values
        if self.apprunner.cpu not in (1, 2, 4):
            raise ValueError(
                f"App Runner CPU must be 1, 2, or 4, got {self.apprunner.cpu}"
            )
        # Validate App Runner memory values
        if self.apprunner.memory not in (2, 3, 4, 6, 8, 10, 12):
            raise ValueError(
                f"App Runner memory must be 2-12 GB, got {self.apprunner.memory}"
            )


# =============================================================================
# Profile Default Instances
# =============================================================================

MINIMAL_DEFAULTS = ProfileDefaults(
    profile_name="minimal",
    lambda_=LambdaDefaults(
        memory_mb=512,
        timeout_s=30,
        reserved_concurrency=None,
    ),
    api_gateway=ApiGatewayDefaults(
        throttle_rate=None,
        throttle_burst=None,
        logging_level="INFO",
        metrics_enabled=False,
        tracing_enabled=False,
    ),
    apprunner=AppRunnerDefaults(
        cpu=1,
        memory=2,
        min_instances=1,
        max_instances=10,
        healthcheck_protocol="TCP",
        healthcheck_path="/healthz",
    ),
    dynamodb=DynamoDBDefaults(
        billing_mode="PAY_PER_REQUEST",
        pitr_enabled=False,
        alarms_enabled=False,
    ),
    aurora=AuroraDefaults(
        min_acu=0.5,
        max_acu=8,
        backup_retention_days=1,
        deletion_protection=False,
    ),
    s3=S3Defaults(
        versioning_enabled=False,
        encryption_enabled=True,
        lifecycle_enabled=False,
    ),
    observability=ObservabilityDefaults(
        level="basic",
        tracing_enabled=False,
        alarms_enabled=False,
        dashboards_enabled=False,
        log_retention_days=7,
    ),
    secrets=SecretsDefaults(
        provider="ssm",
    ),
    estimated_monthly_cost_usd="~$5-50 (varies with usage)",
)

SCALABLE_DEFAULTS = ProfileDefaults(
    profile_name="scalable",
    lambda_=LambdaDefaults(
        memory_mb=1024,
        timeout_s=60,
        reserved_concurrency=10,
    ),
    api_gateway=ApiGatewayDefaults(
        throttle_rate=1000,
        throttle_burst=2000,
        logging_level="INFO",
        metrics_enabled=True,
        tracing_enabled=True,
    ),
    apprunner=AppRunnerDefaults(
        cpu=2,
        memory=4,
        min_instances=2,
        max_instances=25,
        healthcheck_protocol="HTTP",
        healthcheck_path="/healthz",
    ),
    dynamodb=DynamoDBDefaults(
        billing_mode="PAY_PER_REQUEST",
        pitr_enabled=True,
        alarms_enabled=True,
    ),
    aurora=AuroraDefaults(
        min_acu=0.5,
        max_acu=16,
        backup_retention_days=7,
        deletion_protection=True,
    ),
    s3=S3Defaults(
        versioning_enabled=True,
        encryption_enabled=True,
        lifecycle_enabled=True,
    ),
    observability=ObservabilityDefaults(
        level="enhanced",
        tracing_enabled=True,
        alarms_enabled=True,
        dashboards_enabled=True,
        log_retention_days=30,
    ),
    secrets=SecretsDefaults(
        provider="secrets_manager",
    ),
    estimated_monthly_cost_usd="~$100-500+ (scales with traffic)",
)


def get_defaults(profile: ProfileEnum) -> ProfileDefaults:
    """Get default values for a deployment profile.

    Args:
        profile: The deployment profile (minimal or scalable).

    Returns:
        ProfileDefaults containing all default values for the profile.

    Raises:
        ValueError: If an unknown profile is specified.

    Example:
        >>> from aws_api_factory.config.models import ProfileEnum
        >>> defaults = get_defaults(ProfileEnum.MINIMAL)
        >>> print(defaults.lambda_.memory_mb)
        512
    """
    from aws_api_factory.config.models import ProfileEnum

    if profile == ProfileEnum.MINIMAL:
        return MINIMAL_DEFAULTS
    elif profile == ProfileEnum.SCALABLE:
        return SCALABLE_DEFAULTS
    else:
        raise ValueError(f"Unknown profile: {profile}")


def get_all_profiles() -> dict[str, ProfileDefaults]:
    """Get all available profile defaults.

    Returns:
        Dictionary mapping profile names to their defaults.

    Example:
        >>> profiles = get_all_profiles()
        >>> print(list(profiles.keys()))
        ['minimal', 'scalable']
    """
    return {
        "minimal": MINIMAL_DEFAULTS,
        "scalable": SCALABLE_DEFAULTS,
    }


def compare_profiles() -> dict[str, dict[str, tuple[any, any]]]:
    """Compare values between Minimal and Scalable profiles.

    Returns:
        Dictionary of component -> field -> (minimal_value, scalable_value)
        for all fields where values differ.

    Example:
        >>> diffs = compare_profiles()
        >>> print(diffs["lambda"]["memory_mb"])
        (512, 1024)
    """
    diffs: dict[str, dict[str, tuple[any, any]]] = {}

    # Lambda differences
    diffs["lambda"] = {}
    if MINIMAL_DEFAULTS.lambda_.memory_mb != SCALABLE_DEFAULTS.lambda_.memory_mb:
        diffs["lambda"]["memory_mb"] = (
            MINIMAL_DEFAULTS.lambda_.memory_mb,
            SCALABLE_DEFAULTS.lambda_.memory_mb,
        )
    if MINIMAL_DEFAULTS.lambda_.timeout_s != SCALABLE_DEFAULTS.lambda_.timeout_s:
        diffs["lambda"]["timeout_s"] = (
            MINIMAL_DEFAULTS.lambda_.timeout_s,
            SCALABLE_DEFAULTS.lambda_.timeout_s,
        )
    if (
        MINIMAL_DEFAULTS.lambda_.reserved_concurrency
        != SCALABLE_DEFAULTS.lambda_.reserved_concurrency
    ):
        diffs["lambda"]["reserved_concurrency"] = (
            MINIMAL_DEFAULTS.lambda_.reserved_concurrency,
            SCALABLE_DEFAULTS.lambda_.reserved_concurrency,
        )

    # API Gateway differences
    diffs["api_gateway"] = {}
    if (
        MINIMAL_DEFAULTS.api_gateway.throttle_rate
        != SCALABLE_DEFAULTS.api_gateway.throttle_rate
    ):
        diffs["api_gateway"]["throttle_rate"] = (
            MINIMAL_DEFAULTS.api_gateway.throttle_rate,
            SCALABLE_DEFAULTS.api_gateway.throttle_rate,
        )
    if (
        MINIMAL_DEFAULTS.api_gateway.metrics_enabled
        != SCALABLE_DEFAULTS.api_gateway.metrics_enabled
    ):
        diffs["api_gateway"]["metrics_enabled"] = (
            MINIMAL_DEFAULTS.api_gateway.metrics_enabled,
            SCALABLE_DEFAULTS.api_gateway.metrics_enabled,
        )
    if (
        MINIMAL_DEFAULTS.api_gateway.tracing_enabled
        != SCALABLE_DEFAULTS.api_gateway.tracing_enabled
    ):
        diffs["api_gateway"]["tracing_enabled"] = (
            MINIMAL_DEFAULTS.api_gateway.tracing_enabled,
            SCALABLE_DEFAULTS.api_gateway.tracing_enabled,
        )

    # App Runner differences
    diffs["apprunner"] = {}
    if MINIMAL_DEFAULTS.apprunner.cpu != SCALABLE_DEFAULTS.apprunner.cpu:
        diffs["apprunner"]["cpu"] = (
            MINIMAL_DEFAULTS.apprunner.cpu,
            SCALABLE_DEFAULTS.apprunner.cpu,
        )
    if MINIMAL_DEFAULTS.apprunner.memory != SCALABLE_DEFAULTS.apprunner.memory:
        diffs["apprunner"]["memory"] = (
            MINIMAL_DEFAULTS.apprunner.memory,
            SCALABLE_DEFAULTS.apprunner.memory,
        )
    if (
        MINIMAL_DEFAULTS.apprunner.min_instances
        != SCALABLE_DEFAULTS.apprunner.min_instances
    ):
        diffs["apprunner"]["min_instances"] = (
            MINIMAL_DEFAULTS.apprunner.min_instances,
            SCALABLE_DEFAULTS.apprunner.min_instances,
        )
    if (
        MINIMAL_DEFAULTS.apprunner.max_instances
        != SCALABLE_DEFAULTS.apprunner.max_instances
    ):
        diffs["apprunner"]["max_instances"] = (
            MINIMAL_DEFAULTS.apprunner.max_instances,
            SCALABLE_DEFAULTS.apprunner.max_instances,
        )
    if (
        MINIMAL_DEFAULTS.apprunner.healthcheck_protocol
        != SCALABLE_DEFAULTS.apprunner.healthcheck_protocol
    ):
        diffs["apprunner"]["healthcheck_protocol"] = (
            MINIMAL_DEFAULTS.apprunner.healthcheck_protocol,
            SCALABLE_DEFAULTS.apprunner.healthcheck_protocol,
        )

    # DynamoDB differences
    diffs["dynamodb"] = {}
    if (
        MINIMAL_DEFAULTS.dynamodb.pitr_enabled
        != SCALABLE_DEFAULTS.dynamodb.pitr_enabled
    ):
        diffs["dynamodb"]["pitr_enabled"] = (
            MINIMAL_DEFAULTS.dynamodb.pitr_enabled,
            SCALABLE_DEFAULTS.dynamodb.pitr_enabled,
        )
    if (
        MINIMAL_DEFAULTS.dynamodb.alarms_enabled
        != SCALABLE_DEFAULTS.dynamodb.alarms_enabled
    ):
        diffs["dynamodb"]["alarms_enabled"] = (
            MINIMAL_DEFAULTS.dynamodb.alarms_enabled,
            SCALABLE_DEFAULTS.dynamodb.alarms_enabled,
        )

    # Aurora differences
    diffs["aurora"] = {}
    if MINIMAL_DEFAULTS.aurora.max_acu != SCALABLE_DEFAULTS.aurora.max_acu:
        diffs["aurora"]["max_acu"] = (
            MINIMAL_DEFAULTS.aurora.max_acu,
            SCALABLE_DEFAULTS.aurora.max_acu,
        )
    if (
        MINIMAL_DEFAULTS.aurora.backup_retention_days
        != SCALABLE_DEFAULTS.aurora.backup_retention_days
    ):
        diffs["aurora"]["backup_retention_days"] = (
            MINIMAL_DEFAULTS.aurora.backup_retention_days,
            SCALABLE_DEFAULTS.aurora.backup_retention_days,
        )
    if (
        MINIMAL_DEFAULTS.aurora.deletion_protection
        != SCALABLE_DEFAULTS.aurora.deletion_protection
    ):
        diffs["aurora"]["deletion_protection"] = (
            MINIMAL_DEFAULTS.aurora.deletion_protection,
            SCALABLE_DEFAULTS.aurora.deletion_protection,
        )

    # S3 differences
    diffs["s3"] = {}
    if (
        MINIMAL_DEFAULTS.s3.versioning_enabled
        != SCALABLE_DEFAULTS.s3.versioning_enabled
    ):
        diffs["s3"]["versioning_enabled"] = (
            MINIMAL_DEFAULTS.s3.versioning_enabled,
            SCALABLE_DEFAULTS.s3.versioning_enabled,
        )
    if MINIMAL_DEFAULTS.s3.lifecycle_enabled != SCALABLE_DEFAULTS.s3.lifecycle_enabled:
        diffs["s3"]["lifecycle_enabled"] = (
            MINIMAL_DEFAULTS.s3.lifecycle_enabled,
            SCALABLE_DEFAULTS.s3.lifecycle_enabled,
        )

    # Observability differences
    diffs["observability"] = {}
    if MINIMAL_DEFAULTS.observability.level != SCALABLE_DEFAULTS.observability.level:
        diffs["observability"]["level"] = (
            MINIMAL_DEFAULTS.observability.level,
            SCALABLE_DEFAULTS.observability.level,
        )
    if (
        MINIMAL_DEFAULTS.observability.tracing_enabled
        != SCALABLE_DEFAULTS.observability.tracing_enabled
    ):
        diffs["observability"]["tracing_enabled"] = (
            MINIMAL_DEFAULTS.observability.tracing_enabled,
            SCALABLE_DEFAULTS.observability.tracing_enabled,
        )
    if (
        MINIMAL_DEFAULTS.observability.alarms_enabled
        != SCALABLE_DEFAULTS.observability.alarms_enabled
    ):
        diffs["observability"]["alarms_enabled"] = (
            MINIMAL_DEFAULTS.observability.alarms_enabled,
            SCALABLE_DEFAULTS.observability.alarms_enabled,
        )
    if (
        MINIMAL_DEFAULTS.observability.dashboards_enabled
        != SCALABLE_DEFAULTS.observability.dashboards_enabled
    ):
        diffs["observability"]["dashboards_enabled"] = (
            MINIMAL_DEFAULTS.observability.dashboards_enabled,
            SCALABLE_DEFAULTS.observability.dashboards_enabled,
        )
    if (
        MINIMAL_DEFAULTS.observability.log_retention_days
        != SCALABLE_DEFAULTS.observability.log_retention_days
    ):
        diffs["observability"]["log_retention_days"] = (
            MINIMAL_DEFAULTS.observability.log_retention_days,
            SCALABLE_DEFAULTS.observability.log_retention_days,
        )

    # Secrets differences
    diffs["secrets"] = {}
    if MINIMAL_DEFAULTS.secrets.provider != SCALABLE_DEFAULTS.secrets.provider:
        diffs["secrets"]["provider"] = (
            MINIMAL_DEFAULTS.secrets.provider,
            SCALABLE_DEFAULTS.secrets.provider,
        )

    # Remove empty categories
    return {k: v for k, v in diffs.items() if v}
