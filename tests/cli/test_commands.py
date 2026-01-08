# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for AWS API Factory CLI commands."""

import pytest
from click.testing import CliRunner

from aws_api_factory import __version__
from aws_api_factory.cli import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


class TestCLIMain:
    """Tests for main CLI group."""

    def test_cli_version(self, cli_runner: CliRunner) -> None:
        """Test --version flag shows correct version."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output

    def test_cli_help(self, cli_runner: CliRunner) -> None:
        """Test --help flag shows usage information."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "AWS API Factory" in result.output
        assert "init" in result.output
        assert "validate" in result.output
        assert "deploy" in result.output

    def test_cli_verbose_flag(self, cli_runner: CliRunner) -> None:
        """Test --verbose flag is accepted."""
        result = cli_runner.invoke(main, ["--verbose", "--help"])

        assert result.exit_code == 0


class TestInitCommand:
    """Tests for factory init command."""

    def test_init_help(self, cli_runner: CliRunner) -> None:
        """Test init --help shows usage."""
        result = cli_runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "Scaffold" in result.output
        assert "--template" in result.output

    def test_init_with_project_name(self, cli_runner: CliRunner) -> None:
        """Test init with project name argument."""
        result = cli_runner.invoke(main, ["init", "my-project"])

        assert result.exit_code == 0
        assert "my-project" in result.output

    def test_init_with_template_option(self, cli_runner: CliRunner) -> None:
        """Test init with --template option."""
        result = cli_runner.invoke(main, ["init", "my-project", "--template", "full"])

        assert result.exit_code == 0
        assert "full" in result.output


class TestValidateCommand:
    """Tests for factory validate command."""

    def test_validate_help(self, cli_runner: CliRunner) -> None:
        """Test validate --help shows usage."""
        result = cli_runner.invoke(main, ["validate", "--help"])

        assert result.exit_code == 0
        assert "Validate" in result.output
        assert "--config" in result.output
        assert "--show-defaults" in result.output


class TestSynthCommand:
    """Tests for factory synth command."""

    def test_synth_help(self, cli_runner: CliRunner) -> None:
        """Test synth --help shows usage."""
        result = cli_runner.invoke(main, ["synth", "--help"])

        assert result.exit_code == 0
        assert "Synthesize" in result.output
        assert "--config" in result.output
        assert "--output" in result.output


class TestDeployCommand:
    """Tests for factory deploy command."""

    def test_deploy_help(self, cli_runner: CliRunner) -> None:
        """Test deploy --help shows usage."""
        result = cli_runner.invoke(main, ["deploy", "--help"])

        assert result.exit_code == 0
        assert "Deploy" in result.output
        assert "--require-approval" in result.output
        assert "--dry-run" in result.output

    def test_deploy_requires_environment(self, cli_runner: CliRunner) -> None:
        """Test deploy requires environment argument."""
        result = cli_runner.invoke(main, ["deploy"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "ENVIRONMENT" in result.output


class TestDestroyCommand:
    """Tests for factory destroy command."""

    def test_destroy_help(self, cli_runner: CliRunner) -> None:
        """Test destroy --help shows usage."""
        result = cli_runner.invoke(main, ["destroy", "--help"])

        assert result.exit_code == 0
        assert "Destroy" in result.output
        assert "--force" in result.output

    def test_destroy_requires_environment(self, cli_runner: CliRunner) -> None:
        """Test destroy requires environment argument."""
        result = cli_runner.invoke(main, ["destroy"])

        assert result.exit_code != 0
