# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for the defaults resolver.

These tests validate the DefaultsResolver class, ensuring it correctly
resolves "auto" values and applies profile defaults while preserving
user-specified values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aws_api_factory.config import load_config
from aws_api_factory.config.models import FactoryConfig, ProfileEnum
from aws_api_factory.config.resolver import (
    DefaultsResolver,
    ResolutionResult,
    ResolvedValue,
    apply_profile_defaults,
    merge_defaults,
    resolve_config,
    resolve_config_with_explanation,
    validate_completeness,
)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_config_dict() -> dict[str, Any]:
    """Return a minimal configuration dictionary with auto values."""
    return {
        "project": {
            "name": "test-api",
            "envs": ["dev"],
        },
        "profile": "minimal",
        "apis": {
            "rest": {
                "enabled": True,
                "routes": [
                    {
                        "path": "/hello",
                        "methods": ["GET"],
                        "service": "hello",
                        "auth": "none",
                    }
                ],
            }
        },
        "compute": {
            "lambda": {
                "enabled": True,
                "services": {
                    "hello": {
                        "entry": "src/services/hello/handler.py:handler",
                        "memory_mb": "auto",
                        "timeout_s": "auto",
                    }
                },
            }
        },
    }


@pytest.fixture
def scalable_config_dict() -> dict[str, Any]:
    """Return a scalable configuration dictionary with auto values."""
    return {
        "project": {
            "name": "prod-api",
            "envs": ["dev", "staging", "prod"],
        },
        "profile": "scalable",
        "apis": {
            "rest": {
                "enabled": True,
                "routes": [
                    {
                        "path": "/orders",
                        "methods": ["GET", "POST"],
                        "service": "orders",
                        "auth": "none",
                    }
                ],
            }
        },
        "compute": {
            "lambda": {
                "enabled": True,
                "services": {
                    "orders": {
                        "entry": "src/services/orders/handler.py:handler",
                        "memory_mb": "auto",
                        "timeout_s": "auto",
                    }
                },
            }
        },
    }


class TestDefaultsResolver:
    """Tests for DefaultsResolver class."""

    def test_resolver_initialization(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test resolver initializes correctly."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        assert resolver.config is config
        assert resolver.profile_defaults.profile_name == "minimal"

    def test_resolve_returns_new_config(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test resolve() returns a new config instance."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved is not config

    def test_resolve_minimal_lambda_memory(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test auto memory_mb resolves to minimal default (512)."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["hello"].memory_mb == 512

    def test_resolve_minimal_lambda_timeout(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test auto timeout_s resolves to minimal default (30)."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["hello"].timeout_s == 30

    def test_resolve_scalable_lambda_memory(
        self, scalable_config_dict: dict[str, Any]
    ) -> None:
        """Test auto memory_mb resolves to scalable default (1024)."""
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["orders"].memory_mb == 1024

    def test_resolve_scalable_lambda_timeout(
        self, scalable_config_dict: dict[str, Any]
    ) -> None:
        """Test auto timeout_s resolves to scalable default (60)."""
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["orders"].timeout_s == 60

    def test_resolve_scalable_reserved_concurrency(
        self, scalable_config_dict: dict[str, Any]
    ) -> None:
        """Test scalable profile applies reserved_concurrency."""
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["orders"].reserved_concurrency == 10

    def test_user_values_preserved(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test user-specified values are not overwritten."""
        minimal_config_dict["compute"]["lambda"]["services"]["hello"][
            "memory_mb"
        ] = 2048
        minimal_config_dict["compute"]["lambda"]["services"]["hello"]["timeout_s"] = 120
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["hello"].memory_mb == 2048
        assert resolved.compute.lambda_.services["hello"].timeout_s == 120

    def test_partial_auto_values(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test only auto values are resolved, explicit values preserved."""
        minimal_config_dict["compute"]["lambda"]["services"]["hello"]["memory_mb"] = 256
        # timeout_s remains "auto"
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["hello"].memory_mb == 256
        assert resolved.compute.lambda_.services["hello"].timeout_s == 30

    def test_multiple_services_resolved(self) -> None:
        """Test multiple services are all resolved."""
        config_dict = {
            "project": {"name": "multi", "envs": ["dev"]},
            "profile": "minimal",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [
                        {"path": "/a", "methods": ["GET"], "service": "svc_a"},
                        {"path": "/b", "methods": ["GET"], "service": "svc_b"},
                    ],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {
                        "svc_a": {
                            "entry": "src/a/handler.py:handler",
                            "memory_mb": "auto",
                            "timeout_s": "auto",
                        },
                        "svc_b": {
                            "entry": "src/b/handler.py:handler",
                            "memory_mb": 1024,
                            "timeout_s": "auto",
                        },
                    },
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.compute.lambda_.services["svc_a"].memory_mb == 512
        assert resolved.compute.lambda_.services["svc_a"].timeout_s == 30
        assert resolved.compute.lambda_.services["svc_b"].memory_mb == 1024
        assert resolved.compute.lambda_.services["svc_b"].timeout_s == 30


class TestResolverApiGateway:
    """Tests for API Gateway defaults resolution."""

    def test_minimal_no_throttle(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test minimal profile doesn't add throttle limits."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.apis.rest.throttle_rate is None
        assert resolved.apis.rest.throttle_burst is None

    def test_scalable_adds_throttle(self, scalable_config_dict: dict[str, Any]) -> None:
        """Test scalable profile adds throttle limits."""
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.apis.rest.throttle_rate == 1000
        assert resolved.apis.rest.throttle_burst == 2000

    def test_user_throttle_preserved(
        self, scalable_config_dict: dict[str, Any]
    ) -> None:
        """Test user-specified throttle values are preserved."""
        scalable_config_dict["apis"]["rest"]["throttle_rate"] = 500
        scalable_config_dict["apis"]["rest"]["throttle_burst"] = 1000
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.apis.rest.throttle_rate == 500
        assert resolved.apis.rest.throttle_burst == 1000


class TestResolverAppRunner:
    """Tests for App Runner defaults resolution."""

    def test_scalable_upgrades_apprunner_defaults(self) -> None:
        """Test scalable profile upgrades App Runner defaults."""
        config_dict = {
            "project": {"name": "web", "envs": ["prod"]},
            "profile": "scalable",
            "compute": {
                "apprunner": {
                    "enabled": True,
                    "services": {
                        "web": {
                            "dockerfile": "Dockerfile",
                            # Using model defaults (cpu=1, memory=2, etc.)
                        }
                    },
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        svc = resolved.compute.apprunner.services["web"]
        assert svc.cpu == 2
        assert svc.memory == 4
        assert svc.min_instances == 2
        assert svc.max_instances == 25

    def test_minimal_keeps_apprunner_defaults(self) -> None:
        """Test minimal profile keeps App Runner model defaults."""
        config_dict = {
            "project": {"name": "web", "envs": ["dev"]},
            "profile": "minimal",
            "compute": {
                "apprunner": {
                    "enabled": True,
                    "services": {
                        "web": {
                            "dockerfile": "Dockerfile",
                        }
                    },
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        svc = resolved.compute.apprunner.services["web"]
        # Model defaults should be unchanged
        assert svc.cpu == 1
        assert svc.memory == 2
        assert svc.min_instances == 1
        assert svc.max_instances == 10


class TestResolverObservability:
    """Tests for observability defaults resolution."""

    def test_minimal_observability_defaults(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test minimal profile observability defaults."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.observability.tracing is False
        assert resolved.observability.alarms is False

    def test_scalable_observability_defaults(
        self, scalable_config_dict: dict[str, Any]
    ) -> None:
        """Test scalable profile enables observability."""
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.observability.tracing is True
        assert resolved.observability.alarms is True


class TestResolverSecrets:
    """Tests for secrets management defaults resolution."""

    def test_scalable_upgrades_to_secrets_manager(
        self, scalable_config_dict: dict[str, Any]
    ) -> None:
        """Test scalable profile upgrades to Secrets Manager."""
        config = FactoryConfig.model_validate(scalable_config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert resolved.secrets.provider.value == "secrets_manager"


class TestResolverExplanation:
    """Tests for resolver explanation output."""

    def test_explain_returns_string(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test explain() returns a string."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolver.resolve()
        explanation = resolver.explain()
        assert isinstance(explanation, str)
        assert "minimal" in explanation

    def test_explain_contains_resolved_values(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test explanation contains resolved values."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolver.resolve()
        explanation = resolver.explain()
        assert "memory_mb" in explanation
        assert "512" in explanation
        assert "timeout_s" in explanation
        assert "30" in explanation

    def test_explain_no_defaults_message(self) -> None:
        """Test explanation when minimal Lambda defaults are applied."""
        # Note: Observability tracing/alarms are always resolved from None,
        # so we just test that Lambda defaults with explicit values don't add to list
        config_dict = {
            "project": {"name": "explicit", "envs": ["dev"]},
            "profile": "minimal",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [{"path": "/a", "methods": ["GET"], "service": "svc"}],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {
                        "svc": {
                            "entry": "src/handler.py:handler",
                            "memory_mb": 512,  # Explicit, not auto
                            "timeout_s": 30,  # Explicit, not auto
                        }
                    },
                }
            },
            "observability": {
                "level": "basic",
                "tracing": False,  # Explicit
                "alarms": False,  # Explicit
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolver.resolve()
        explanation = resolver.explain()
        assert "No defaults applied" in explanation

    def test_explain_as_dict(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test explain_as_dict() returns dictionary."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        resolver.resolve()
        result = resolver.explain_as_dict()
        assert isinstance(result, dict)
        assert result["profile"] == "minimal"
        assert "applied_defaults" in result
        assert isinstance(result["applied_defaults"], list)


class TestResolverWarnings:
    """Tests for resolver warnings."""

    def test_minimal_with_prod_warning(self) -> None:
        """Test warning when using minimal profile with production env."""
        config_dict = {
            "project": {"name": "api", "envs": ["dev", "prod"]},
            "profile": "minimal",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [{"path": "/a", "methods": ["GET"], "service": "svc"}],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {"svc": {"entry": "src/handler.py:handler"}},
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        result = resolver.resolve_with_result()
        assert len(result.warnings) > 0
        assert any(
            "minimal" in w.lower() and "prod" in w.lower() for w in result.warnings
        )

    def test_scalable_no_auth_warning(self) -> None:
        """Test warning when scalable profile has routes without auth."""
        config_dict = {
            "project": {"name": "api", "envs": ["prod"]},
            "profile": "scalable",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [
                        {
                            "path": "/public",
                            "methods": ["GET"],
                            "service": "svc",
                            "auth": "none",
                        }
                    ],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {"svc": {"entry": "src/handler.py:handler"}},
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        result = resolver.resolve_with_result()
        assert any("auth" in w.lower() for w in result.warnings)


class TestResolutionResult:
    """Tests for ResolutionResult dataclass."""

    def test_resolve_with_result(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test resolve_with_result returns ResolutionResult."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolver = DefaultsResolver(config)
        result = resolver.resolve_with_result()
        assert isinstance(result, ResolutionResult)
        assert result.profile == "minimal"
        assert result.is_complete is True
        assert len(result.applied_defaults) > 0


class TestResolvedValue:
    """Tests for ResolvedValue dataclass."""

    def test_resolved_value_creation(self) -> None:
        """Test ResolvedValue can be created."""
        rv = ResolvedValue(
            path="compute.lambda.services.hello.memory_mb",
            original="auto",
            resolved=512,
            rationale="Profile default",
        )
        assert rv.path == "compute.lambda.services.hello.memory_mb"
        assert rv.original == "auto"
        assert rv.resolved == 512


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_resolve_config(self, minimal_config_dict: dict[str, Any]) -> None:
        """Test resolve_config convenience function."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolved = resolve_config(config)
        assert isinstance(resolved, FactoryConfig)
        assert resolved.compute.lambda_.services["hello"].memory_mb == 512

    def test_resolve_config_with_explanation(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test resolve_config_with_explanation convenience function."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolved, explanation = resolve_config_with_explanation(config)
        assert isinstance(resolved, FactoryConfig)
        assert isinstance(explanation, str)
        assert "memory_mb" in explanation

    def test_merge_defaults_with_auto(self) -> None:
        """Test merge_defaults with auto value."""
        assert merge_defaults("auto", 512) == 512
        assert merge_defaults("auto", 1024) == 1024

    def test_merge_defaults_with_none(self) -> None:
        """Test merge_defaults with None value."""
        assert merge_defaults(None, 512) == 512
        assert merge_defaults(None, "default") == "default"

    def test_merge_defaults_user_wins(self) -> None:
        """Test merge_defaults user value wins."""
        assert merge_defaults(256, 512) == 256
        assert merge_defaults(60, 30) == 60
        assert merge_defaults("custom", "default") == "custom"

    def test_apply_profile_defaults(self) -> None:
        """Test apply_profile_defaults function."""
        from aws_api_factory.config.defaults import MINIMAL_DEFAULTS

        config_dict = {
            "project": {"name": "test", "envs": ["dev"]},
            "profile": "minimal",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [{"path": "/a", "methods": ["GET"], "service": "svc"}],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {"svc": {"entry": "src/h.py:h", "memory_mb": "auto"}},
                }
            },
        }
        result = apply_profile_defaults(config_dict, MINIMAL_DEFAULTS)
        assert isinstance(result, dict)
        assert result["compute"]["lambda"]["services"]["svc"]["memory_mb"] == 512

    def test_validate_completeness_complete(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test validate_completeness with complete config."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        resolved = resolve_config(config)
        errors = validate_completeness(resolved)
        assert len(errors) == 0

    def test_validate_completeness_incomplete(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test validate_completeness with unresolved auto values."""
        config = FactoryConfig.model_validate(minimal_config_dict)
        # Don't resolve - check for auto values
        errors = validate_completeness(config)
        assert len(errors) > 0
        assert any("memory_mb" in e for e in errors)


class TestIntegrationWithFixtures:
    """Integration tests using YAML fixtures."""

    def test_minimal_fixture_resolves(self, fixtures_dir: Path) -> None:
        """Test minimal_valid.yaml resolves correctly."""
        config = load_config(fixtures_dir / "minimal_valid.yaml")
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()

        # Check Lambda service resolved
        svc = resolved.compute.lambda_.services["hello"]
        assert svc.memory_mb == 512
        assert svc.timeout_s == 30
        assert svc.reserved_concurrency is None

        # Check observability
        assert resolved.observability.tracing is False
        assert resolved.observability.alarms is False

    def test_scalable_fixture_resolves(self, fixtures_dir: Path) -> None:
        """Test scalable_valid.yaml resolves correctly."""
        config = load_config(fixtures_dir / "scalable_valid.yaml")
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()

        # Check profile is scalable
        assert resolved.profile == ProfileEnum.SCALABLE

        # Check observability
        assert resolved.observability.tracing is True
        assert resolved.observability.alarms is True

        # Check secrets upgraded
        assert resolved.secrets.provider.value == "secrets_manager"

    def test_resolved_config_still_valid(self, fixtures_dir: Path) -> None:
        """Test resolved config passes Pydantic validation."""
        config = load_config(fixtures_dir / "minimal_valid.yaml")
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()

        # Should be able to dump and re-parse without errors
        resolved_dict = resolved.model_dump(by_alias=True)
        reparsed = FactoryConfig.model_validate(resolved_dict)
        assert reparsed.project.name == resolved.project.name


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_services_dict(self) -> None:
        """Test resolver handles empty services dictionary."""
        config_dict = {
            "project": {"name": "empty", "envs": ["dev"]},
            "profile": "minimal",
            "compute": {"lambda": {"enabled": True, "services": {}}},
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        assert len(resolved.compute.lambda_.services) == 0

    def test_disabled_lambda_not_resolved(self) -> None:
        """Test disabled Lambda compute is skipped during resolution.

        Note: Pydantic validation prevents disabled compute with defined services,
        so we test that when Lambda is disabled (no services), resolution skips it.
        """
        config_dict = {
            "project": {"name": "disabled", "envs": ["dev"]},
            "profile": "minimal",
            "compute": {
                "lambda": {
                    "enabled": False,
                    "services": {},  # No services when disabled
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        # No Lambda services to resolve
        assert len(resolved.compute.lambda_.services) == 0

    def test_disabled_apprunner_not_resolved(self) -> None:
        """Test disabled App Runner compute is skipped."""
        config_dict = {
            "project": {"name": "disabled", "envs": ["dev"]},
            "profile": "scalable",
            "compute": {
                "apprunner": {
                    "enabled": False,
                    "services": {"web": {"dockerfile": "Dockerfile"}},
                }
            },
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        # Defaults should not be upgraded for disabled compute
        svc = resolved.compute.apprunner.services["web"]
        assert svc.cpu == 1  # Model default, not scalable default

    def test_disabled_rest_api_not_resolved(self) -> None:
        """Test disabled REST API is skipped."""
        config_dict = {
            "project": {"name": "disabled", "envs": ["dev"]},
            "profile": "scalable",
            "apis": {"rest": {"enabled": False}},
        }
        config = FactoryConfig.model_validate(config_dict)
        resolver = DefaultsResolver(config)
        resolved = resolver.resolve()
        # Throttle should not be set
        assert resolved.apis.rest.throttle_rate is None
