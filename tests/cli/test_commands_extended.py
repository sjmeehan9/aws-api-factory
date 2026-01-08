# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Additional CLI tests to ensure full coverage of implemented features."""

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import deploy, destroy, init, main, synth, validate


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


class TestCLICommands:
    """Extended tests for CLI commands to improve coverage."""

    def test_init_default_no_project(self, cli_runner: CliRunner) -> None:
        """Test init without project name uses current directory."""
        result = cli_runner.invoke(main, ["init"])

        assert result.exit_code == 0
        assert "current directory" in result.output

    def test_validate_with_show_defaults(self, cli_runner: CliRunner, tmp_path) -> None:
        """Test validate with --show-defaults flag."""
        # Create a temporary config file
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n")

        result = cli_runner.invoke(
            main, ["validate", "--config", str(config_file), "--show-defaults"]
        )

        assert result.exit_code == 0
        assert "Showing resolved defaults" in result.output

    def test_synth_custom_output(self, cli_runner: CliRunner, tmp_path) -> None:
        """Test synth with custom output directory."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n")
        output_dir = tmp_path / "my-output"

        result = cli_runner.invoke(
            main, ["synth", "--config", str(config_file), "--output", str(output_dir)]
        )

        assert result.exit_code == 0
        assert str(output_dir) in result.output

    def test_deploy_with_dry_run(self, cli_runner: CliRunner, tmp_path) -> None:
        """Test deploy with --dry-run flag."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n")

        result = cli_runner.invoke(
            main, ["deploy", "dev", "--config", str(config_file), "--dry-run"]
        )

        assert result.exit_code == 0
        assert "Dry run mode" in result.output

    def test_deploy_with_approval_option(self, cli_runner: CliRunner, tmp_path) -> None:
        """Test deploy with --require-approval option."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n")

        result = cli_runner.invoke(
            main,
            [
                "deploy",
                "prod",
                "--config",
                str(config_file),
                "--require-approval",
                "any-change",
            ],
        )

        assert result.exit_code == 0
        assert "prod" in result.output

    def test_destroy_with_force(self, cli_runner: CliRunner, tmp_path) -> None:
        """Test destroy with --force skips confirmation."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n")

        result = cli_runner.invoke(
            main, ["destroy", "dev", "--config", str(config_file), "--force"]
        )

        assert result.exit_code == 0
        assert "Destroying environment: dev" in result.output

    def test_destroy_confirmation_abort(self, cli_runner: CliRunner, tmp_path) -> None:
        """Test destroy aborts when confirmation is declined."""
        config_file = tmp_path / "factory.yaml"
        config_file.write_text("project:\n  name: test\n")

        result = cli_runner.invoke(
            main, ["destroy", "prod", "--config", str(config_file)], input="n\n"
        )

        assert result.exit_code == 1
        assert "Aborted" in result.output


class TestCLIModuleImports:
    """Tests for CLI module imports."""

    def test_main_callable(self) -> None:
        """Test main function is callable."""
        assert callable(main)

    def test_commands_registered(self) -> None:
        """Test all commands are registered with main group."""
        command_names = list(main.commands.keys())

        assert "init" in command_names
        assert "validate" in command_names
        assert "synth" in command_names
        assert "deploy" in command_names
        assert "destroy" in command_names
