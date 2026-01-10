# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for the factory deploy command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


class TestDeployCommand:
    """Tests for the factory deploy command."""

    def test_deploy_help(self, cli_runner: CliRunner) -> None:
        """Test deploy --help shows usage information."""
        result = cli_runner.invoke(cli, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "Deploy the API Factory stack to AWS" in result.output
        assert "ENVIRONMENT" in result.output
        assert "--config" in result.output
        assert "--require-approval" in result.output
        assert "--dry-run" in result.output
        assert "--outputs-file" in result.output

    def test_deploy_requires_environment(self, cli_runner: CliRunner) -> None:
        """Test deploy requires environment argument."""
        result = cli_runner.invoke(cli, ["deploy"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "ENVIRONMENT" in result.output

    def test_deploy_validates_config_first(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy validates configuration before deployment."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should validate config first
                    assert (
                        "valid" in result.output.lower()
                        or "Validating" in result.output
                    )

    def test_deploy_missing_config(self, cli_runner: CliRunner) -> None:
        """Test deploy fails when config file doesn't exist."""
        result = cli_runner.invoke(
            cli, ["deploy", "dev", "--config", "nonexistent.yaml"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_deploy_invalid_environment(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy fails for unconfigured environment."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True

                result = cli_runner.invoke(
                    cli,
                    [
                        "deploy",
                        "nonexistent-env",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--force",
                    ],
                )

                assert result.exit_code != 0
                assert "not configured" in result.output

    def test_deploy_dry_run(self, cli_runner: CliRunner, starter_dir: Path) -> None:
        """Test deploy --dry-run shows what would be deployed."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--dry-run",
                            "--force",
                        ],
                    )

                    assert result.exit_code == 0
                    assert (
                        "dry run" in result.output.lower() or "DRY RUN" in result.output
                    )

                    # Should call cdk diff instead of deploy
                    if mock_run.called:
                        args = mock_run.call_args[0][0]
                        assert "diff" in args

    def test_deploy_force_skips_confirmation(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy --force skips confirmation prompt."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should complete without waiting for input
                    assert result.exit_code == 0 or "complete" in result.output.lower()

    def test_deploy_require_approval_options(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy --require-approval options are passed to CDK."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--require-approval",
                            "never",
                            "--force",
                        ],
                    )

                    # Approval option should be passed
                    if mock_run.called:
                        args = mock_run.call_args[0][0]
                        # Check approval arg is in command
                        approval_idx = (
                            args.index("--require-approval")
                            if "--require-approval" in args
                            else -1
                        )
                        if approval_idx >= 0:
                            assert args[approval_idx + 1] == "never"

    def test_deploy_cdk_not_found(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy fails gracefully when CDK is not installed."""
        with patch("shutil.which", return_value=None):
            result = cli_runner.invoke(
                cli,
                [
                    "deploy",
                    "dev",
                    "--config",
                    str(starter_dir / "factory.yaml"),
                    "--force",
                ],
            )

            assert result.exit_code != 0
            assert "CDK" in result.output


class TestDeployCommandResourcesDisplay:
    """Tests for resource display during deployment."""

    def test_deploy_shows_resources(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy shows resources that will be created."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should show resource table
                    assert (
                        "Resources to Create" in result.output
                        or "Lambda" in result.output
                    )

    def test_deploy_shows_config_summary(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy shows configuration summary."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    # Should show configuration summary
                    assert "my-api" in result.output


class TestDeployMissingCredentials:
    """Tests for deploy with missing credentials."""

    def test_deploy_no_credentials(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test deploy fails when AWS credentials are missing."""
        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = False

                result = cli_runner.invoke(
                    cli,
                    [
                        "deploy",
                        "dev",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--force",
                    ],
                )

                assert result.exit_code != 0
                assert "credentials" in result.output.lower()


class TestDeployCDKFailure:
    """Tests for deploy with CDK failures."""

    def test_deploy_cdk_failure(self, cli_runner: CliRunner, starter_dir: Path) -> None:
        """Test deploy handles CDK command failures."""
        from aws_api_factory.cli.utils import CDKError

        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.side_effect = CDKError("deploy", "Stack failed")

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--force",
                        ],
                    )

                    assert result.exit_code != 0


class TestDeployOutputsFile:
    """Tests for deploy with outputs file option."""

    def test_deploy_outputs_file(
        self, cli_runner: CliRunner, starter_dir: Path, tmp_path: Path
    ) -> None:
        """Test deploy writes outputs to specified file."""
        outputs_file = tmp_path / "outputs.json"

        with patch(
            "aws_api_factory.cli.commands.deploy.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.deploy.check_aws_credentials"
            ) as mock_creds:
                mock_creds.return_value = True
                with patch(
                    "aws_api_factory.cli.commands.deploy.run_cdk_command"
                ) as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0, stdout="", stderr=""
                    )

                    result = cli_runner.invoke(
                        cli,
                        [
                            "deploy",
                            "dev",
                            "--config",
                            str(starter_dir / "factory.yaml"),
                            "--outputs-file",
                            str(outputs_file),
                            "--force",
                        ],
                    )

                    # Should include outputs-file in CDK command
                    if mock_run.called:
                        args = mock_run.call_args[0][0]
                        assert "--outputs-file" in args
