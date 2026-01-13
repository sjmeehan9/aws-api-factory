# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Profile defaults resolver for AWS API Factory.

This module provides the DefaultsResolver class that takes user configuration
and resolves all missing or "auto" values using profile defaults.

The resolver ensures that after resolution:
1. All "auto" values are replaced with appropriate profile defaults
2. User-specified values are preserved (user wins)
3. The resolved configuration is complete and valid
4. An explanation of applied defaults is available

Example:
    >>> from aws_api_factory.config import load_config
    >>> from aws_api_factory.config.resolver import DefaultsResolver
    >>> config = load_config("factory.yaml")
    >>> resolver = DefaultsResolver(config)
    >>> resolved = resolver.resolve()
    >>> print(resolver.explain())
    Applied defaults for profile 'minimal':
      - compute.lambda.services.hello.memory_mb: auto → 512
      - compute.lambda.services.hello.timeout_s: auto → 30

"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aws_api_factory.config.defaults import ProfileDefaults, get_defaults

if TYPE_CHECKING:
    from aws_api_factory.config.models import FactoryConfig


@dataclass
class ResolvedValue:
    """Record of a resolved default value.

    Attributes:
        path: Dot-separated path to the field (e.g., "compute.lambda.services.hello.memory_mb").
        original: The original value ("auto" or None).
        resolved: The resolved value from profile defaults.
        rationale: Explanation of why this default was applied.
    """

    path: str
    original: Any
    resolved: Any
    rationale: str = ""


@dataclass
class ResolutionResult:
    """Result of defaults resolution.

    Attributes:
        config: The resolved FactoryConfig with all defaults applied.
        applied_defaults: List of ResolvedValue records for each default applied.
        profile: The profile used for resolution.
        is_complete: Whether all required fields have values.
        warnings: List of warnings (e.g., recommendations for scalable profile).
    """

    config: FactoryConfig
    applied_defaults: list[ResolvedValue] = field(default_factory=list)
    profile: str = ""
    is_complete: bool = True
    warnings: list[str] = field(default_factory=list)


class DefaultsResolver:
    """Resolves missing and "auto" configuration values using profile defaults.

    The resolver takes a FactoryConfig and applies profile-appropriate defaults
    for any missing or "auto" values. User-specified values are always preserved.

    Attributes:
        config: The original user configuration.
        profile_defaults: The defaults for the user's chosen profile.
        applied_defaults: List of resolved values for explanation.

    Example:
        >>> config = load_config("factory.yaml")
        >>> resolver = DefaultsResolver(config)
        >>> resolved_config = resolver.resolve()
        >>> print(resolver.explain())
    """

    def __init__(self, config: FactoryConfig) -> None:
        """Initialize the resolver with user configuration.

        Args:
            config: The user's FactoryConfig to resolve.
        """
        self.config = config
        self.profile_defaults = get_defaults(config.profile)
        self.applied_defaults: list[ResolvedValue] = []
        self._warnings: list[str] = []

    def resolve(self) -> FactoryConfig:
        """Resolve all missing and "auto" values using profile defaults.

        Returns:
            A new FactoryConfig with all defaults applied. The original
            config is not modified.

        Note:
            After calling resolve(), use explain() to get a human-readable
            summary of what defaults were applied.
        """
        # Create a deep copy to avoid modifying the original
        config_dict = self.config.model_dump(by_alias=True)

        # Clear previous resolution state
        self.applied_defaults = []
        self._warnings = []

        # Resolve each section
        self._resolve_lambda_services(config_dict)
        self._resolve_apprunner_services(config_dict)
        self._resolve_api_gateway(config_dict)
        self._resolve_dynamodb(config_dict)
        self._resolve_aurora(config_dict)
        self._resolve_s3(config_dict)
        self._resolve_observability(config_dict)
        self._resolve_secrets(config_dict)

        # Generate warnings based on profile recommendations
        self._generate_warnings(config_dict)

        # Reconstruct the config from the resolved dict
        from aws_api_factory.config.models import FactoryConfig

        return FactoryConfig.model_validate(config_dict)

    def resolve_with_result(self) -> ResolutionResult:
        """Resolve defaults and return detailed result.

        Returns:
            ResolutionResult with the resolved config, applied defaults,
            and any warnings.
        """
        resolved_config = self.resolve()
        return ResolutionResult(
            config=resolved_config,
            applied_defaults=list(self.applied_defaults),
            profile=self.profile_defaults.profile_name,
            is_complete=self._validate_completeness(resolved_config),
            warnings=list(self._warnings),
        )

    def explain(self) -> str:
        """Generate human-readable explanation of applied defaults.

        Returns:
            Multi-line string describing what defaults were applied.

        Example:
            >>> resolver = DefaultsResolver(config)
            >>> resolver.resolve()
            >>> print(resolver.explain())
            Applied defaults for profile 'minimal':
              - compute.lambda.services.hello.memory_mb: auto → 512
        """
        if not self.applied_defaults:
            return f"No defaults applied for profile '{self.profile_defaults.profile_name}'."

        lines = [
            f"Applied defaults for profile '{self.profile_defaults.profile_name}':"
        ]
        for resolved in self.applied_defaults:
            original_str = (
                repr(resolved.original) if resolved.original != "auto" else "auto"
            )
            lines.append(f"  - {resolved.path}: {original_str} → {resolved.resolved}")
            if resolved.rationale:
                lines.append(f"    ({resolved.rationale})")

        if self._warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self._warnings:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)

    def explain_as_dict(self) -> dict[str, Any]:
        """Generate machine-readable explanation of applied defaults.

        Returns:
            Dictionary with profile name, applied defaults, and warnings.
        """
        return {
            "profile": self.profile_defaults.profile_name,
            "applied_defaults": [
                {
                    "path": d.path,
                    "original": d.original,
                    "resolved": d.resolved,
                    "rationale": d.rationale,
                }
                for d in self.applied_defaults
            ],
            "warnings": self._warnings,
            "estimated_cost": self.profile_defaults.estimated_monthly_cost_usd,
        }

    def _resolve_lambda_services(self, config_dict: dict[str, Any]) -> None:
        """Resolve Lambda service defaults."""
        lambda_config = config_dict.get("compute", {}).get("lambda", {})
        if not lambda_config.get("enabled", True):
            return

        services = lambda_config.get("services", {})
        for service_name, service_config in services.items():
            base_path = f"compute.lambda.services.{service_name}"

            # Resolve memory_mb
            if service_config.get("memory_mb") == "auto":
                service_config["memory_mb"] = self.profile_defaults.lambda_.memory_mb
                self.applied_defaults.append(
                    ResolvedValue(
                        path=f"{base_path}.memory_mb",
                        original="auto",
                        resolved=self.profile_defaults.lambda_.memory_mb,
                        rationale=f"Profile default for {self.profile_defaults.profile_name}",
                    )
                )

            # Resolve timeout_s
            if service_config.get("timeout_s") == "auto":
                service_config["timeout_s"] = self.profile_defaults.lambda_.timeout_s
                self.applied_defaults.append(
                    ResolvedValue(
                        path=f"{base_path}.timeout_s",
                        original="auto",
                        resolved=self.profile_defaults.lambda_.timeout_s,
                        rationale=f"Profile default for {self.profile_defaults.profile_name}",
                    )
                )

            # Apply reserved_concurrency for scalable profile if not set
            if (
                service_config.get("reserved_concurrency") is None
                and self.profile_defaults.lambda_.reserved_concurrency is not None
            ):
                # Only apply if profile is scalable (minimal has None as default)
                if self.profile_defaults.profile_name == "scalable":
                    service_config["reserved_concurrency"] = (
                        self.profile_defaults.lambda_.reserved_concurrency
                    )
                    self.applied_defaults.append(
                        ResolvedValue(
                            path=f"{base_path}.reserved_concurrency",
                            original=None,
                            resolved=self.profile_defaults.lambda_.reserved_concurrency,
                            rationale="Scalable profile ensures consistent performance",
                        )
                    )

    def _resolve_apprunner_services(self, config_dict: dict[str, Any]) -> None:
        """Resolve App Runner service defaults."""
        apprunner_config = config_dict.get("compute", {}).get("apprunner", {})
        if not apprunner_config.get("enabled", False):
            return

        services = apprunner_config.get("services", {})
        defaults = self.profile_defaults.apprunner

        for service_name, service_config in services.items():
            base_path = f"compute.apprunner.services.{service_name}"

            # Only resolve if user hasn't specified values explicitly
            # App Runner config has explicit defaults in the model, so we check
            # if the profile default differs from model default

            # For scalable profile, upgrade defaults if user hasn't overridden
            if self.profile_defaults.profile_name == "scalable":
                # CPU upgrade: 1 -> 2
                if service_config.get("cpu") == 1:
                    service_config["cpu"] = defaults.cpu
                    self.applied_defaults.append(
                        ResolvedValue(
                            path=f"{base_path}.cpu",
                            original=1,
                            resolved=defaults.cpu,
                            rationale="Scalable profile uses more CPU for production traffic",
                        )
                    )

                # Memory upgrade: 2 -> 4
                if service_config.get("memory") == 2:
                    service_config["memory"] = defaults.memory
                    self.applied_defaults.append(
                        ResolvedValue(
                            path=f"{base_path}.memory",
                            original=2,
                            resolved=defaults.memory,
                            rationale="Scalable profile uses more memory for production traffic",
                        )
                    )

                # Min instances upgrade: 1 -> 2
                if service_config.get("min_instances") == 1:
                    service_config["min_instances"] = defaults.min_instances
                    self.applied_defaults.append(
                        ResolvedValue(
                            path=f"{base_path}.min_instances",
                            original=1,
                            resolved=defaults.min_instances,
                            rationale="Scalable profile maintains 2+ instances for availability",
                        )
                    )

                # Max instances upgrade: 10 -> 25
                if service_config.get("max_instances") == 10:
                    service_config["max_instances"] = defaults.max_instances
                    self.applied_defaults.append(
                        ResolvedValue(
                            path=f"{base_path}.max_instances",
                            original=10,
                            resolved=defaults.max_instances,
                            rationale="Scalable profile allows more instances for peak traffic",
                        )
                    )

    def _resolve_api_gateway(self, config_dict: dict[str, Any]) -> None:
        """Resolve API Gateway defaults."""
        rest_config = config_dict.get("apis", {}).get("rest", {})
        if not rest_config.get("enabled", True):
            return

        defaults = self.profile_defaults.api_gateway

        # Resolve throttle settings for scalable profile
        if self.profile_defaults.profile_name == "scalable":
            if rest_config.get("throttle_rate") is None:
                rest_config["throttle_rate"] = defaults.throttle_rate
                self.applied_defaults.append(
                    ResolvedValue(
                        path="apis.rest.throttle_rate",
                        original=None,
                        resolved=defaults.throttle_rate,
                        rationale="Scalable profile sets throttle limits to protect backends",
                    )
                )

            if rest_config.get("throttle_burst") is None:
                rest_config["throttle_burst"] = defaults.throttle_burst
                self.applied_defaults.append(
                    ResolvedValue(
                        path="apis.rest.throttle_burst",
                        original=None,
                        resolved=defaults.throttle_burst,
                        rationale="Scalable profile sets burst limits to handle traffic spikes",
                    )
                )

    def _resolve_dynamodb(self, config_dict: dict[str, Any]) -> None:
        """Resolve DynamoDB table defaults."""
        dynamodb_config = config_dict.get("data", {}).get("dynamodb", {})
        if not dynamodb_config.get("enabled", False):
            return

        tables = dynamodb_config.get("tables", [])
        defaults = self.profile_defaults.dynamodb

        for i, table in enumerate(tables):
            table_name = table.get("name", f"table_{i}")
            base_path = f"data.dynamodb.tables[{table_name}]"

            # Apply PITR for scalable profile
            if self.profile_defaults.profile_name == "scalable" and not table.get(
                "pitr", False
            ):
                table["pitr"] = defaults.pitr_enabled
                self.applied_defaults.append(
                    ResolvedValue(
                        path=f"{base_path}.pitr",
                        original=False,
                        resolved=defaults.pitr_enabled,
                        rationale="Scalable profile enables Point-in-Time Recovery for data protection",
                    )
                )

    def _resolve_aurora(self, config_dict: dict[str, Any]) -> None:
        """Resolve Aurora Serverless defaults."""
        aurora_config = config_dict.get("data", {}).get("aurora", {})
        if not aurora_config.get("enabled", False):
            return

        defaults = self.profile_defaults.aurora

        # Adjust max_acu for scalable profile
        if (
            self.profile_defaults.profile_name == "scalable"
            and aurora_config.get("max_acu", 8) == 8
        ):
            aurora_config["max_acu"] = defaults.max_acu
            self.applied_defaults.append(
                ResolvedValue(
                    path="data.aurora.max_acu",
                    original=8,
                    resolved=defaults.max_acu,
                    rationale="Scalable profile allows higher ACU for production traffic",
                )
            )

    def _resolve_s3(self, config_dict: dict[str, Any]) -> None:
        """Resolve S3 bucket defaults."""
        s3_config = config_dict.get("data", {}).get("s3", {})
        if not s3_config.get("enabled", False):
            return

        buckets = s3_config.get("buckets", [])
        defaults = self.profile_defaults.s3

        for i, bucket in enumerate(buckets):
            bucket_name = bucket.get("name", f"bucket_{i}")
            base_path = f"data.s3.buckets[{bucket_name}]"

            # Apply versioning for scalable profile
            if self.profile_defaults.profile_name == "scalable" and not bucket.get(
                "versioning", False
            ):
                bucket["versioning"] = defaults.versioning_enabled
                self.applied_defaults.append(
                    ResolvedValue(
                        path=f"{base_path}.versioning",
                        original=False,
                        resolved=defaults.versioning_enabled,
                        rationale="Scalable profile enables versioning for data protection",
                    )
                )

    def _resolve_observability(self, config_dict: dict[str, Any]) -> None:
        """Resolve observability defaults."""
        obs_config = config_dict.get("observability", {})
        defaults = self.profile_defaults.observability

        # Apply observability level based on profile
        if obs_config.get("level") is None:
            obs_config["level"] = defaults.level
            self.applied_defaults.append(
                ResolvedValue(
                    path="observability.level",
                    original=None,
                    resolved=defaults.level,
                    rationale=f"Profile default for {self.profile_defaults.profile_name}",
                )
            )

        # Resolve tracing based on level or profile
        if obs_config.get("tracing") is None:
            obs_config["tracing"] = defaults.tracing_enabled
            self.applied_defaults.append(
                ResolvedValue(
                    path="observability.tracing",
                    original=None,
                    resolved=defaults.tracing_enabled,
                    rationale="Derived from observability level",
                )
            )

        # Resolve alarms based on level or profile
        if obs_config.get("alarms") is None:
            obs_config["alarms"] = defaults.alarms_enabled
            self.applied_defaults.append(
                ResolvedValue(
                    path="observability.alarms",
                    original=None,
                    resolved=defaults.alarms_enabled,
                    rationale="Derived from observability level",
                )
            )

    def _resolve_secrets(self, config_dict: dict[str, Any]) -> None:
        """Resolve secrets management defaults."""
        secrets_config = config_dict.get("secrets", {})
        defaults = self.profile_defaults.secrets

        # Only upgrade to secrets_manager for scalable if not explicitly set
        if (
            self.profile_defaults.profile_name == "scalable"
            and secrets_config.get("provider") == "ssm"
        ):
            secrets_config["provider"] = defaults.provider
            self.applied_defaults.append(
                ResolvedValue(
                    path="secrets.provider",
                    original="ssm",
                    resolved=defaults.provider,
                    rationale="Scalable profile uses Secrets Manager for rotation and audit",
                )
            )

    def _generate_warnings(self, config_dict: dict[str, Any]) -> None:
        """Generate warnings based on configuration and profile."""
        profile = self.profile_defaults.profile_name

        # Warn about production use with minimal profile
        if profile == "minimal":
            envs = config_dict.get("project", {}).get("envs", [])
            if "prod" in envs or "production" in envs:
                self._warnings.append(
                    "Using 'minimal' profile with production environment. "
                    "Consider 'scalable' profile for production workloads."
                )

        # Warn about large Lambda memory with minimal profile
        if profile == "minimal":
            lambda_services = (
                config_dict.get("compute", {}).get("lambda", {}).get("services", {})
            )
            for name, svc in lambda_services.items():
                if isinstance(svc.get("memory_mb"), int) and svc["memory_mb"] > 1024:
                    self._warnings.append(
                        f"Lambda service '{name}' has high memory ({svc['memory_mb']}MB) "
                        "in minimal profile. Consider scalable profile for production."
                    )

        # Warn about no auth on public routes in scalable profile
        if profile == "scalable":
            routes = config_dict.get("apis", {}).get("rest", {}).get("routes", [])
            no_auth_routes = [r["path"] for r in routes if r.get("auth") == "none"]
            if no_auth_routes:
                self._warnings.append(
                    f"Routes {no_auth_routes} have no authentication in scalable profile. "
                    "Consider adding authentication for production APIs."
                )

    def _validate_completeness(self, config: FactoryConfig) -> bool:
        """Validate that the resolved config is complete.

        Args:
            config: The resolved configuration.

        Returns:
            True if all required fields have values, False otherwise.
        """
        # Check Lambda services have resolved memory/timeout
        for name, service in config.compute.lambda_.services.items():
            if service.memory_mb == "auto" or service.timeout_s == "auto":
                return False

        return True


def resolve_config(config: FactoryConfig) -> FactoryConfig:
    """Convenience function to resolve a config with its profile defaults.

    Args:
        config: The user's FactoryConfig.

    Returns:
        A new FactoryConfig with all defaults applied.

    Example:
        >>> from aws_api_factory.config import load_config
        >>> from aws_api_factory.config.resolver import resolve_config
        >>> config = load_config("factory.yaml")
        >>> resolved = resolve_config(config)
    """
    resolver = DefaultsResolver(config)
    return resolver.resolve()


def resolve_config_with_explanation(
    config: FactoryConfig,
) -> tuple[FactoryConfig, str]:
    """Resolve config and return human-readable explanation.

    Args:
        config: The user's FactoryConfig.

    Returns:
        Tuple of (resolved_config, explanation_string).

    Example:
        >>> resolved, explanation = resolve_config_with_explanation(config)
        >>> print(explanation)
    """
    resolver = DefaultsResolver(config)
    resolved = resolver.resolve()
    return resolved, resolver.explain()


def merge_defaults(
    user_value: Any,
    default_value: Any,
    allow_auto: bool = True,
) -> Any:
    """Merge a user value with a default, respecting user preferences.

    Args:
        user_value: The value specified by the user (may be None or "auto").
        default_value: The profile default value.
        allow_auto: Whether to treat "auto" as a placeholder for defaults.

    Returns:
        The user value if specified, otherwise the default.
    """
    if user_value is None:
        return default_value
    if allow_auto and user_value == "auto":
        return default_value
    return user_value


def apply_profile_defaults(
    config_dict: dict[str, Any],
    profile_defaults: ProfileDefaults,
) -> dict[str, Any]:
    """Apply profile defaults to a configuration dictionary.

    This is a lower-level function for cases where you need to work
    with dictionaries instead of Pydantic models.

    Args:
        config_dict: The configuration as a dictionary.
        profile_defaults: The defaults to apply.

    Returns:
        A new dictionary with defaults applied.
    """
    from aws_api_factory.config.models import FactoryConfig

    # Parse to validate, then use resolver
    config = FactoryConfig.model_validate(config_dict)
    resolver = DefaultsResolver(config)
    resolved = resolver.resolve()
    return resolved.model_dump(by_alias=True)


def validate_completeness(config: FactoryConfig) -> list[str]:
    """Validate that a configuration has no unresolved values.

    Args:
        config: The configuration to validate.

    Returns:
        List of error messages for incomplete fields.
    """
    errors: list[str] = []

    # Check Lambda services
    for name, service in config.compute.lambda_.services.items():
        if service.memory_mb == "auto":
            errors.append(
                f"compute.lambda.services.{name}.memory_mb is 'auto' - must be resolved"
            )
        if service.timeout_s == "auto":
            errors.append(
                f"compute.lambda.services.{name}.timeout_s is 'auto' - must be resolved"
            )

    return errors
