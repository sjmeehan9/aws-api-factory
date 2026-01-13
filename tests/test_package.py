# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for AWS API Factory package initialization."""

import pytest


class TestPackageInit:
    """Tests for package-level attributes and imports."""

    def test_version_defined(self) -> None:
        """Test that __version__ is defined and valid."""
        from aws_api_factory import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        # Version should follow semver format
        parts = __version__.split(".")
        assert len(parts) >= 2
        assert all(part.isdigit() for part in parts[:2])

    def test_author_defined(self) -> None:
        """Test that __author__ is defined."""
        from aws_api_factory import __author__

        assert __author__ is not None
        assert isinstance(__author__, str)
        assert len(__author__) > 0

    def test_license_defined(self) -> None:
        """Test that __license__ is defined."""
        from aws_api_factory import __license__

        assert __license__ == "MIT"

    def test_all_exports(self) -> None:
        """Test that __all__ contains expected exports."""
        from aws_api_factory import __all__

        assert "__version__" in __all__
        assert "__author__" in __all__
        assert "__license__" in __all__
