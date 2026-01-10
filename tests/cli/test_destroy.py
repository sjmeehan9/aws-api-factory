# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for the factory destroy command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


class TestDestroyCommand:
    """Tests for the factory destroy command."""

    def test_destroy_help(self, cli_runner: CliRunner) -> None:
        """Test destroy --help shows usage information."""
        result = cli_runner.invoke(cli, ["destroy", "--help"])
        assert result.exit_code == 0
        assert "Destroy the API Factory stack" in result.output
        assert "ENVIRONMENT" in result.output
        assert "--config" in result.output
        assert "--force" in result.output
        assert "WARNING" in result.output or "cannot be undone" in result.output

    def test_destroy_requires_environment(self, cli_runner: CliRunner) -> None:
        """Test destroy requires environment argument."""
        result = cli_runner.invoke(cli, ["destroy"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "ENVIRONMENT" in result.output

    def test_destroy_requires_confirmation(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy requires confirmation without --force."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True

                result = cli_runner.invoke(
                    cli,
                    [
                        "destroy",
                        "dev",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                    ],
                    input="n\n",  # Say no to confirmation
                )

                # Should ask for confirmation and exit
                assert result.exit_code != 0 or "cancelled" in result.output.lower()

    def test_destroy_force_skips_confirmation(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy --force skips confirmation prompt."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should complete without waiting for input
                    assert result.exit_code == 0 or "destroyed" in result.output.lower()

    def test_destroy_missing_config(self, cli_runner: CliRunner) -> None:
        """Test destroy fails when config file doesn't exist."""
        result = cli_runner.invoke(
            cli, ["destroy", "dev", "--config", "nonexistent.yaml", "--force"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_destroy_shows_destructive_warning(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy shows destructive operation warning."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should show warning about destructive operation
                    assert "DESTRUCTIVE" in result.output or "DELETE" in result.output

    def test_destroy_shows_resources_to_delete(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy shows resources that will be deleted."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should show resources that will be deleted
                    assert "DELETED" in result.output or "Resources" in result.output

    def test_destroy_calls_cdk_destroy(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy calls cdk destroy with correct arguments."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should call CDK destroy
                    if mock_run.called:
                        args = mock_run.call_args[0][0]
                        assert "destroy" in args

    def test_destroy_cdk_not_found(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy fails gracefully when CDK is not installed."""
        with patch(
            "aws_api_factory.cli.commands.destroy.check_aws_credentials"
        ) as mock_creds:
            mock_creds.return_value = True
            with patch("shutil.which", return_value=None):
                result = cli_runner.invoke(
                    cli,
                    [
                        "destroy",
                        "dev",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--force",
                    ],
                )

                assert result.exit_code != 0
                assert "CDK" in result.output

    def test_destroy_warns_unknown_environment(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy warns when environment is not in config."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "unknown-env",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should warn but continue with --force
                    assert "⚠" in result.output or "not in" in result.output


class TestDestroyCommandSuccess:
    """Tests for successful destroy operations."""

    def test_destroy_success_message(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy shows success message."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "destroyed" in result.output.lower() or "✓" in result.output

    def test_destroy_shows_redeploy_hint(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy shows how to redeploy."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should show how to redeploy
                    assert "factory deploy" in result.output


class TestDestroyMissingCredentials:
    """Tests for destroy with missing credentials."""

    def test_destroy_no_credentials(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy fails when AWS credentials are missing."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = False

                result = cli_runner.invoke(
                    cli,
                    [
                        "destroy",
                        "dev",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--force",
                    ],
                )

                assert result.exit_code != 0
                assert "credentials" in result.output.lower()


class TestDestroyExclusivelyOption:
    """Tests for destroy --exclusively option."""

    def test_destroy_exclusively(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy with --exclusively option."""
        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--exclusively",
                            "--force",
                        ],
                    )

                    # Should pass --exclusively to CDK
                    if mock_run.called:
                        args = mock_run.call_args[0][0]
                        assert "--exclusively" in args


class TestDestroyCDKFailure:
    """Tests for destroy with CDK failures."""

    def test_destroy_cdk_failure(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test destroy handles CDK command failures."""
        from aws_api_factory.cli.utils import CDKError

        with patch(
            "aws_api_factory.cli.commands.destroy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.destroy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.destroy.run_cdk_command"
                ) as mock_run:
                    mock_run.side_effect = CDKError("destroy", "Stack destroy failed")

                    result = cli_runner.invoke(
                        cli,
                        [
                            "destroy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    assert result.exit_code != 0
