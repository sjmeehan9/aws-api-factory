# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for configuration loader.

These tests validate YAML loading, validation error formatting,
and configuration merging functionality.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from aws_api_factory.config.loader import (
    ConfigLoadError,
    _deep_merge,
    find_config_file,
    get_config_dir,
    load_config,
    load_config_from_string,
    load_yaml_file,
    load_yaml_string,
    validate_and_parse,
)
from aws_api_factory.config.models import ProfileEnum, SecretsProviderEnum

# Get the fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLoadYamlFile:
    """Tests for load_yaml_file function."""

    def test_load_valid_yaml(self) -> None:
        """Test loading a valid YAML file."""
        data = load_yaml_file(FIXTURES_DIR / "minimal_valid.yaml")
        assert data["project"]["name"] == "my-api"
        assert data["profile"] == "minimal"

    def test_load_missing_file(self) -> None:
        """Test loading a non-existent file."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_yaml_file(FIXTURES_DIR / "nonexistent.yaml")

        error = exc_info.value
        assert "not found" in error.message.lower()
        assert "factory init" in str(error).lower()

    def test_load_directory_as_file(self, tmp_path: Path) -> None:
        """Test loading a directory instead of a file."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_yaml_file(tmp_path)

        error = exc_info.value
        assert "not a file" in error.message.lower()


class TestLoadYamlString:
    """Tests for load_yaml_string function."""

    def test_load_valid_yaml_string(self) -> None:
        """Test loading valid YAML from string."""
        content = dedent(
            """
            project:
              name: test-api
              envs:
                - dev
            profile: minimal
        """
        )
        data = load_yaml_string(content)
        assert data["project"]["name"] == "test-api"

    def test_load_empty_yaml(self) -> None:
        """Test loading empty YAML content."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_yaml_string("")

        error = exc_info.value
        assert "empty" in error.message.lower()

    def test_load_invalid_yaml_syntax(self) -> None:
        """Test loading YAML with syntax errors."""
        content = dedent(
            """
            project:
              name: test-api
              envs:
                - dev
            profile: minimal
            invalid yaml:
            - this: is
              bad: [unclosed
        """
        )
        with pytest.raises(ConfigLoadError) as exc_info:
            load_yaml_string(content)

        error = exc_info.value
        assert "syntax" in error.message.lower() or "Invalid YAML" in error.message

    def test_load_non_dict_yaml(self) -> None:
        """Test loading YAML that doesn't produce a dict."""
        content = "- item1\n- item2\n- item3"
        with pytest.raises(ConfigLoadError) as exc_info:
            load_yaml_string(content)

        error = exc_info.value
        assert (
            "mapping" in error.message.lower() or "dictionary" in error.message.lower()
        )


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_minimal_config(self) -> None:
        """Test loading minimal valid configuration."""
        config = load_config(FIXTURES_DIR / "minimal_valid.yaml")
        assert config.project.name == "my-api"
        assert config.profile == ProfileEnum.MINIMAL
        assert len(config.apis.rest.routes) == 1

    def test_load_scalable_config(self) -> None:
        """Test loading scalable valid configuration."""
        config = load_config(FIXTURES_DIR / "scalable_valid.yaml")
        assert config.project.name == "production-api"
        assert config.profile == ProfileEnum.SCALABLE
        assert config.data.dynamodb.enabled is True
        assert len(config.data.dynamodb.tables) == 2

    def test_load_invalid_missing_required(self) -> None:
        """Test loading config with missing required fields."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_missing_required.yaml")

        error = exc_info.value
        assert "project" in str(error).lower()

    def test_load_invalid_bad_enum(self) -> None:
        """Test loading config with invalid enum value."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_bad_enum.yaml")

        error = exc_info.value
        assert "profile" in str(error).lower() or "production" in str(error).lower()

    def test_load_invalid_service_ref(self) -> None:
        """Test loading config with invalid service reference."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_service_ref.yaml")

        error = exc_info.value
        assert "nonexistent-service" in str(error)

    def test_load_invalid_cognito_missing(self) -> None:
        """Test loading config with cognito auth but no cognito config."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_cognito_missing.yaml")

        error = exc_info.value
        assert "cognito" in str(error).lower()

    def test_load_invalid_path_format(self) -> None:
        """Test loading config with invalid path format."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_path_format.yaml")

        error = exc_info.value
        assert "pattern" in str(error).lower() or "path" in str(error).lower()

    def test_load_invalid_lambda_limits(self) -> None:
        """Test loading config with invalid Lambda limits."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_lambda_limits.yaml")

        error = exc_info.value
        # Should mention memory or timeout limit
        assert "memory" in str(error).lower() or "10240" in str(error)

    def test_load_invalid_extra_fields(self) -> None:
        """Test loading config with unknown fields."""
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(FIXTURES_DIR / "invalid_extra_fields.yaml")

        error = exc_info.value
        assert "unknown" in str(error).lower() or "Extra" in str(error)


class TestLoadConfigFromString:
    """Tests for load_config_from_string function."""

    def test_load_from_string(self) -> None:
        """Test loading configuration from YAML string."""
        content = dedent(
            """
            project:
              name: test-api
              envs:
                - dev
            profile: minimal
        """
        )
        config = load_config_from_string(content)
        assert config.project.name == "test-api"
        assert config.profile == ProfileEnum.MINIMAL

    def test_load_with_env_override(self) -> None:
        """Test loading configuration with environment override."""
        base_content = dedent(
            """
            project:
              name: test-api
              envs:
                - dev
                - prod
            profile: minimal
            secrets:
              provider: ssm
        """
        )
        env_content = dedent(
            """
            profile: scalable
            secrets:
              provider: secrets_manager
        """
        )
        config = load_config_from_string(base_content, env_content)
        assert config.project.name == "test-api"
        assert config.profile == ProfileEnum.SCALABLE
        assert config.secrets.provider == SecretsProviderEnum.SECRETS_MANAGER


class TestDeepMerge:
    """Tests for _deep_merge function."""

    def test_simple_merge(self) -> None:
        """Test simple dictionary merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        """Test nested dictionary merge."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)
        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_override_non_dict_with_dict(self) -> None:
        """Test overriding non-dict value with dict."""
        base = {"a": "string"}
        override = {"a": {"nested": "value"}}
        result = _deep_merge(base, override)
        assert result == {"a": {"nested": "value"}}

    def test_original_unchanged(self) -> None:
        """Test that original dictionaries are not modified."""
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}}
        _deep_merge(base, override)
        assert base == {"a": 1, "b": {"c": 2}}


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_find_in_current_dir(self, tmp_path: Path) -> None:
        """Test finding config file in current directory."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n  envs: [dev]")

        found = find_config_file(tmp_path)
        assert found == config_file

    def test_find_in_parent_dir(self, tmp_path: Path) -> None:
        """Test finding config file in parent directory."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n  envs: [dev]")

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        found = find_config_file(subdir)
        assert found == config_file

    def test_not_found(self, tmp_path: Path) -> None:
        """Test when config file is not found."""
        found = find_config_file(tmp_path)
        assert found is None

    def test_custom_filename(self, tmp_path: Path) -> None:
        """Test finding config with custom filename."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("project:\n  name: test\n  envs: [dev]")

        found = find_config_file(tmp_path, filename="custom.yaml")
        assert found == config_file


class TestGetConfigDir:
    """Tests for get_config_dir function."""

    def test_get_config_dir(self, tmp_path: Path) -> None:
        """Test getting config directory."""
        config_file = tmp_path / "subdir" / "factory.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("")

        result = get_config_dir(config_file)
        assert result == config_file.parent.resolve()


class TestValidateAndParse:
    """Tests for validate_and_parse function."""

    def test_valid_data(self) -> None:
        """Test parsing valid data."""
        data = {
            "project": {"name": "api", "envs": ["dev"]},
            "profile": "minimal",
        }
        config = validate_and_parse(data)
        assert config.project.name == "api"

    def test_invalid_data(self) -> None:
        """Test parsing invalid data."""
        data = {
            "profile": "minimal",  # Missing project
        }
        with pytest.raises(ConfigLoadError) as exc_info:
            validate_and_parse(data)

        error = exc_info.value
        assert "project" in str(error).lower()


class TestErrorMessages:
    """Tests for error message quality."""

    def test_error_includes_file_path(self, tmp_path: Path) -> None:
        """Test error messages include file path."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("profile: invalid")

        with pytest.raises(ConfigLoadError) as exc_info:
            load_config(config_file)

        error = exc_info.value
        assert str(config_file) in str(error) or "bad.yaml" in str(error)

    def test_error_details_helpful(self) -> None:
        """Test error details are actionable."""
        content = dedent(
            """
            project:
              name: test
              envs: []
            profile: minimal
        """
        )
        with pytest.raises(ConfigLoadError) as exc_info:
            load_config_from_string(content)

        error = exc_info.value
        # Should mention the specific field with the issue
        assert "envs" in str(error).lower() or "at least" in str(error).lower()
