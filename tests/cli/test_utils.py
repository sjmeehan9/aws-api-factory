# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for AWS API Factory CLI utility functions."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aws_api_factory.cli.utils import (
    AWSCredentialsError,
    CDKError,
    CLIError,
    ConfigNotFoundError,
    ConfigValidationError,
    check_aws_credentials,
    confirm_action,
    find_cdk_executable,
    format_yaml_output,
    get_project_root,
    get_stack_name,
    get_verbose_context,
    load_and_validate_config,
)


class TestCLIError:
    """Tests for CLI error classes."""

    def test_cli_error_message(self) -> None:
        """Test CLIError stores message correctly."""
        error = CLIError("Test error")
        assert error.message == "Test error"
        assert error.suggestion is None
        assert error.exit_code == 1

    def test_cli_error_with_suggestion(self) -> None:
        """Test CLIError with suggestion."""
        error = CLIError("Test error", suggestion="Try this", exit_code=42)
        assert error.message == "Test error"
        assert error.suggestion == "Try this"
        assert error.exit_code == 42

    def test_config_not_found_error(self) -> None:
        """Test ConfigNotFoundError message format."""
        error = ConfigNotFoundError("/path/to/config.yaml")
        assert "/path/to/config.yaml" in error.message
        assert "factory init" in str(error.suggestion)
        assert error.exit_code == 2

    def test_config_validation_error(self) -> None:
        """Test ConfigValidationError message format."""
        error = ConfigValidationError("Invalid config", details="Check field X")
        assert "Invalid config" in error.message
        assert error.exit_code == 3

    def test_cdk_error(self) -> None:
        """Test CDKError message format."""
        error = CDKError("deploy", "Error: Stack failed")
        assert "deploy" in error.message
        assert "Stack failed" in str(error.suggestion)
        assert error.exit_code == 4

    def test_aws_credentials_error(self) -> None:
        """Test AWSCredentialsError message format."""
        error = AWSCredentialsError()
        assert "credentials" in error.message.lower()
        assert "aws configure" in str(error.suggestion).lower()
        assert error.exit_code == 5


class TestLoadAndValidateConfig:
    """Tests for config loading and validation."""

    def test_config_not_found(self) -> None:
        """Test error when config file doesn't exist."""
        with pytest.raises(ConfigNotFoundError):
            load_and_validate_config("/nonexistent/factory.yaml")

    def test_valid_config_loads(self, starter_dir: Path) -> None:
        """Test loading valid config from starter template."""
        config, result = load_and_validate_config(starter_dir / "factory.yaml")
        assert config.project.name == "my-api"
        assert result is not None
        assert result.profile == "minimal"

    def test_config_with_defaults_resolved(self, starter_dir: Path) -> None:
        """Test that defaults are resolved."""
        config, result = load_and_validate_config(
            starter_dir / "factory.yaml", resolve_defaults=True
        )
        # The hello service should have resolved memory and timeout
        hello_service = config.compute.lambda_.services.get("hello")
        assert hello_service is not None
        assert hello_service.memory_mb != "auto"
        assert hello_service.timeout_s != "auto"

    def test_config_without_defaults(self, starter_dir: Path) -> None:
        """Test loading config without resolving defaults."""
        config, result = load_and_validate_config(
            starter_dir / "factory.yaml", resolve_defaults=False
        )
        assert config is not None
        assert result is None


class TestCheckAWSCredentials:
    """Tests for AWS credential checking."""

    def test_credentials_from_env_vars(self) -> None:
        """Test detection of credentials from environment variables."""
        with patch.dict(
            "os.environ",
            {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"},
        ):
            assert check_aws_credentials() is True

    def test_credentials_from_profile(self) -> None:
        """Test detection of credentials from AWS profile."""
        with patch.dict("os.environ", {"AWS_PROFILE": "default"}, clear=True):
            assert check_aws_credentials() is True

    def test_credentials_from_file(self, tmp_path: Path) -> None:
        """Test detection of credentials from credentials file."""
        with patch.dict("os.environ", {}, clear=True):
            # Mock Path.home() to return temp directory
            creds_path = tmp_path / ".aws" / "credentials"
            creds_path.parent.mkdir(parents=True)
            creds_path.write_text("[default]\naws_access_key_id=test")

            with patch("pathlib.Path.home", return_value=tmp_path):
                assert check_aws_credentials() is True


class TestFindCDKExecutable:
    """Tests for CDK executable detection."""

    def test_cdk_found(self) -> None:
        """Test when CDK is found."""
        with patch("shutil.which", return_value="/usr/local/bin/cdk"):
            path = find_cdk_executable()
            assert path == "/usr/local/bin/cdk"

    def test_cdk_not_found(self) -> None:
        """Test error when CDK is not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(CLIError) as exc_info:
                find_cdk_executable()
            assert "CDK" in exc_info.value.message


class TestGetStackName:
    """Tests for stack name generation."""

    def test_simple_name(self) -> None:
        """Test stack name generation with simple project name."""
        name = get_stack_name("my-api", "dev")
        assert name == "my-api-dev-stack"

    def test_name_with_underscores(self) -> None:
        """Test stack name converts underscores to hyphens."""
        name = get_stack_name("my_api_project", "prod")
        assert name == "my-api-project-prod-stack"

    def test_name_lowercase(self) -> None:
        """Test stack name is lowercase."""
        name = get_stack_name("MyAPI", "Dev")
        assert name == "myapi-Dev-stack"  # Only project name is lowercased


class TestFormatYamlOutput:
    """Tests for YAML formatting."""

    def test_simple_dict(self) -> None:
        """Test formatting a simple dictionary."""
        data = {"key": "value", "number": 42}
        output = format_yaml_output(data)
        assert "key: value" in output
        assert "number: 42" in output

    def test_nested_dict(self) -> None:
        """Test formatting a nested dictionary."""
        data = {"outer": {"inner": "value"}}
        output = format_yaml_output(data)
        assert "outer:" in output
        assert "inner: value" in output


class TestGetProjectRoot:
    """Tests for project root detection."""

    def test_finds_root_with_factory_yaml(self, starter_dir: Path) -> None:
        """Test finding project root with factory.yaml."""
        root = get_project_root(starter_dir)
        assert root == starter_dir
        assert (root / "factory.yaml").exists()

    def test_returns_none_without_factory_yaml(self, tmp_path: Path) -> None:
        """Test returns None when no factory.yaml found."""
        root = get_project_root(tmp_path)
        assert root is None


class TestGetVerboseContext:
    """Tests for verbose context extraction."""

    def test_verbose_true(self) -> None:
        """Test extracting verbose=True from context."""
        ctx = MagicMock()
        ctx.obj = {"verbose": True}
        assert get_verbose_context(ctx) is True

    def test_verbose_false(self) -> None:
        """Test extracting verbose=False from context."""
        ctx = MagicMock()
        ctx.obj = {"verbose": False}
        assert get_verbose_context(ctx) is False

    def test_no_obj(self) -> None:
        """Test handling when context has no obj."""
        ctx = MagicMock()
        ctx.obj = None
        assert get_verbose_context(ctx) is False


class TestConfirmAction:
    """Tests for confirm_action utility."""

    def test_confirm_returns_true_on_yes(self) -> None:
        """Test confirm returns True when user says yes."""
        with patch("aws_api_factory.cli.utils.click.confirm", return_value=True):
            assert confirm_action("Do this?") is True

    def test_confirm_dangerous_shows_warning(self) -> None:
        """Test dangerous actions show warning styling."""
        with patch("aws_api_factory.cli.utils.click.confirm", return_value=True):
            with patch("aws_api_factory.cli.utils.console.print") as mock_print:
                confirm_action("Delete everything?", dangerous=True)
                # Should show warning styling
                call_args = str(mock_print.call_args)
                assert "WARNING" in call_args or "error" in call_args
