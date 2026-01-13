# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for the factory validate command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


class TestValidateCommand:
    """Tests for the factory validate command."""

    def test_validate_help(self, cli_runner: CliRunner) -> None:
        """Test validate --help shows usage information."""
        result = cli_runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate factory.yaml configuration" in result.output
        assert "--config" in result.output
        assert "--show-defaults" in result.output
        assert "--show-resources" in result.output
        assert "--output" in result.output

    def test_validate_valid_config(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate succeeds with valid config."""
        result = cli_runner.invoke(
            cli, ["validate", "--config", str(starter_dir / "factory.yaml")]
        )

        assert result.exit_code == 0
        assert "Configuration is valid" in result.output
        assert "my-api" in result.output

    def test_validate_shows_defaults(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate --show-defaults displays resolved defaults."""
        result = cli_runner.invoke(
            cli,
            [
                "validate",
                "--config",
                str(starter_dir / "factory.yaml"),
                "--show-defaults",
            ],
        )

        assert result.exit_code == 0
        assert "Applied Defaults" in result.output
        # Check for resolved values shown in defaults table
        assert "512" in result.output or "auto" in result.output

    def test_validate_shows_resources(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate --show-resources displays resources to create."""
        result = cli_runner.invoke(
            cli,
            [
                "validate",
                "--config",
                str(starter_dir / "factory.yaml"),
                "--show-resources",
            ],
        )

        assert result.exit_code == 0
        assert "Resources to Create" in result.output
        assert "Lambda Function" in result.output

    def test_validate_writes_output_yaml(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate --output writes resolved config to file."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli,
                [
                    "validate",
                    "--config",
                    str(starter_dir / "factory.yaml"),
                    "--output",
                    "resolved.yaml",
                ],
            )

            assert result.exit_code == 0
            assert Path("resolved.yaml").exists()

            content = Path("resolved.yaml").read_text()
            assert "my-api" in content

    def test_validate_writes_output_json(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate --output --format json writes JSON."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli,
                [
                    "validate",
                    "--config",
                    str(starter_dir / "factory.yaml"),
                    "--output",
                    "resolved.json",
                    "--format",
                    "json",
                ],
            )

            assert result.exit_code == 0
            assert Path("resolved.json").exists()

            data = json.loads(Path("resolved.json").read_text())
            assert data["project"]["name"] == "my-api"

    def test_validate_missing_config(self, cli_runner: CliRunner) -> None:
        """Test validate fails when config file doesn't exist."""
        result = cli_runner.invoke(cli, ["validate", "--config", "nonexistent.yaml"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_validate_invalid_config(self, cli_runner: CliRunner) -> None:
        """Test validate fails with invalid config."""
        with cli_runner.isolated_filesystem():
            Path("invalid.yaml").write_text("invalid: yaml: content:")

            result = cli_runner.invoke(cli, ["validate", "--config", "invalid.yaml"])

            assert result.exit_code != 0

    def test_validate_with_environment(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate with --environment option."""
        result = cli_runner.invoke(
            cli,
            [
                "validate",
                "--config",
                str(starter_dir / "factory.yaml"),
                "--environment",
                "prod",
            ],
        )

        assert result.exit_code == 0
        assert "prod" in result.output

    def test_validate_shows_next_steps(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate shows helpful next steps."""
        result = cli_runner.invoke(
            cli, ["validate", "--config", str(starter_dir / "factory.yaml")]
        )

        assert result.exit_code == 0
        assert "Next steps" in result.output
        assert "factory synth" in result.output
        assert "factory deploy" in result.output


class TestValidateCommandConfigSummary:
    """Tests for configuration summary display."""

    def test_shows_project_info(self, cli_runner: CliRunner, starter_dir: Path) -> None:
        """Test validate shows project information."""
        result = cli_runner.invoke(
            cli, ["validate", "--config", str(starter_dir / "factory.yaml")]
        )

        assert result.exit_code == 0
        assert "Project Name" in result.output
        assert "Profile" in result.output
        assert "Environments" in result.output

    def test_shows_api_status(self, cli_runner: CliRunner, starter_dir: Path) -> None:
        """Test validate shows API status."""
        result = cli_runner.invoke(
            cli, ["validate", "--config", str(starter_dir / "factory.yaml")]
        )

        assert result.exit_code == 0
        assert "REST API" in result.output
        assert "GraphQL API" in result.output

    def test_shows_observability_level(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test validate shows observability level."""
        result = cli_runner.invoke(
            cli, ["validate", "--config", str(starter_dir / "factory.yaml")]
        )

        assert result.exit_code == 0
        assert "Observability" in result.output
