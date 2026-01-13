# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Additional CLI tests to ensure full coverage of implemented features."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import cli, deploy, destroy, init, main, synth, validate


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def valid_config_content() -> str:
    """Return valid factory.yaml content."""
    return """project:
  name: test-project
  envs:
    - dev
    - prod

profile: minimal

apis:
  rest:
    enabled: true
    routes:
      - path: /hello
        methods:
          - GET
        service: hello
        auth: none

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: auto
        timeout_s: auto

data:
  dynamodb:
    enabled: false
  s3:
    enabled: false

secrets:
  provider: ssm

observability:
  level: basic
"""


class TestCLICommands:
    """Extended tests for CLI commands to improve coverage."""

    def test_init_creates_directory(self, cli_runner: CliRunner) -> None:
        """Test init creates project directory."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["init", "my-project", "--no-git", "--no-venv"]
            )
            assert result.exit_code == 0
            assert Path("my-project").exists()

    def test_validate_with_show_defaults(
        self, cli_runner: CliRunner, tmp_path: Path, valid_config_content: str
    ) -> None:
        """Test validate with --show-defaults flag."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text(valid_config_content)

        result = cli_runner.invoke(
            cli, ["validate", "--config", str(config_file), "--show-defaults"]
        )

        assert result.exit_code == 0
        # Should show defaults table
        assert (
            "Applied Defaults" in result.output or "defaults" in result.output.lower()
        )

    def test_validate_with_show_resources(
        self, cli_runner: CliRunner, tmp_path: Path, valid_config_content: str
    ) -> None:
        """Test validate with --show-resources flag."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text(valid_config_content)

        result = cli_runner.invoke(
            cli, ["validate", "--config", str(config_file), "--show-resources"]
        )

        assert result.exit_code == 0

    def test_validate_invalid_config(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test validate with invalid config shows error."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("invalid: yaml: content:")

        result = cli_runner.invoke(cli, ["validate", "--config", str(config_file)])

        assert result.exit_code != 0

    def test_validate_missing_config(self, cli_runner: CliRunner) -> None:
        """Test validate with missing config file."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["validate", "--config", "nonexistent.yaml"]
            )
            assert result.exit_code != 0

    def test_synth_help_options(self, cli_runner: CliRunner) -> None:
        """Test synth command has all expected options."""
        result = cli_runner.invoke(cli, ["synth", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--environment" in result.output
        assert "--output" in result.output
        assert "--quiet" in result.output

    def test_deploy_help_options(self, cli_runner: CliRunner) -> None:
        """Test deploy command has all expected options."""
        result = cli_runner.invoke(cli, ["deploy", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--require-approval" in result.output
        assert "--dry-run" in result.output
        assert "--outputs-file" in result.output
        assert "--no-rollback" in result.output
        assert "--force" in result.output

    def test_destroy_help_options(self, cli_runner: CliRunner) -> None:
        """Test destroy command has all expected options."""
        result = cli_runner.invoke(cli, ["destroy", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--force" in result.output
        assert "--exclusively" in result.output


class TestCLIModuleImports:
    """Tests for CLI module imports."""

    def test_cli_is_click_group(self) -> None:
        """Test cli is a Click group."""
        assert hasattr(cli, "commands")
        assert hasattr(cli, "name")

    def test_main_is_callable(self) -> None:
        """Test main function is callable."""
        assert callable(main)

    def test_commands_registered(self) -> None:
        """Test all commands are registered with cli group."""
        command_names = list(cli.commands.keys())

        assert "init" in command_names
        assert "validate" in command_names
        assert "synth" in command_names
        assert "deploy" in command_names
        assert "destroy" in command_names

    def test_command_functions_imported(self) -> None:
        """Test individual command functions are importable."""
        assert callable(init)
        assert callable(validate)
        assert callable(synth)
        assert callable(deploy)
        assert callable(destroy)


class TestCLIVerboseFlag:
    """Tests for CLI --verbose flag."""

    def test_verbose_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test --verbose flag is accepted."""
        result = cli_runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_no_color_flag_accepted(self, cli_runner: CliRunner) -> None:
        """Test --no-color flag is accepted."""
        result = cli_runner.invoke(cli, ["--no-color", "--help"])
        assert result.exit_code == 0
