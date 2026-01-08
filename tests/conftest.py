# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Pytest configuration and shared fixtures for AWS API Factory tests."""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def starter_dir(project_root: Path) -> Path:
    """Return the starter template directory."""
    return project_root / "starter"


@pytest.fixture
def minimal_config_dict() -> dict[str, Any]:
    """Return a minimal valid configuration dictionary."""
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
                    }
                },
            }
        },
    }


@pytest.fixture
def scalable_config_dict(minimal_config_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a scalable profile configuration dictionary."""
    config = minimal_config_dict.copy()
    config["profile"] = "scalable"
    config["project"]["envs"] = ["dev", "staging", "prod"]
    config["observability"] = {"level": "enhanced"}
    return config
