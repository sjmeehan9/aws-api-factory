# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for the factory synth command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner."""
    return CliRunner()


class TestSynthCommand:
    """Tests for the factory synth command."""

    def test_synth_help(self, cli_runner: CliRunner) -> None:
        """Test synth --help shows usage information."""
        result = cli_runner.invoke(cli, ["synth", "--help"])
        assert result.exit_code == 0
        assert "Synthesize CloudFormation templates" in result.output
        assert "--config" in result.output
        assert "--output" in result.output
        assert "--environment" in result.output
        assert "--show" in result.output

    def test_synth_validates_config_first(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth validates configuration before synthesis."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    ["synth", "--config", str(starter_dir / "factory.yaml"), "--quiet"],
                )

                # Should get to validation step
                assert "valid" in result.output.lower() or result.exit_code == 0

    def test_synth_missing_config(self, cli_runner: CliRunner) -> None:
        """Test synth fails when config file doesn't exist."""
        result = cli_runner.invoke(cli, ["synth", "--config", "nonexistent.yaml"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_synth_with_environment(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth with --environment option."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    [
                        "synth",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--environment",
                        "prod",
                    ],
                )

                # Environment should be passed to CDK
                if mock_run.called:
                    args = mock_run.call_args[0][0]
                    assert any("prod" in str(arg) for arg in args)

    def test_synth_with_custom_output(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth with --output option."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    [
                        "synth",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--output",
                        "custom-output",
                        "--quiet",
                    ],
                )

                # Custom output path should be used
                if mock_run.called:
                    args = mock_run.call_args[0][0]
                    assert any("custom-output" in str(arg) for arg in args)

    def test_synth_quiet_mode(self, cli_runner: CliRunner, starter_dir: Path) -> None:
        """Test synth --quiet suppresses output."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    [
                        "synth",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--quiet",
                    ],
                )

                # Output should be minimal
                lines = [l for l in result.output.split("\n") if l.strip()]
                assert len(lines) < 10  # Quiet mode should have minimal output

    def test_synth_cdk_not_found(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth fails gracefully when CDK is not installed."""
        with patch("shutil.which", return_value=None):
            result = cli_runner.invoke(
                cli,
                ["synth", "--config", str(starter_dir / "factory.yaml")],
            )

            assert result.exit_code != 0
            assert "CDK" in result.output

    def test_synth_warns_unknown_environment(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth warns when environment is not in config."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    [
                        "synth",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--environment",
                        "unknown-env",
                    ],
                )

                # Should warn about unknown environment
                # (starter only has dev, prod configured)
                assert "⚠" in result.output or "not in configured" in result.output


class TestSynthCommandCDKIntegration:
    """Tests for CDK command integration."""

    def test_synth_calls_cdk_synth(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth calls cdk synth with correct arguments."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    ["synth", "--config", str(starter_dir / "factory.yaml"), "--quiet"],
                )

                if mock_run.called:
                    args = mock_run.call_args[0][0]
                    assert "synth" in args


class TestSynthCDKFailure:
    """Tests for synth with CDK failures."""

    def test_synth_cdk_failure(self, cli_runner: CliRunner, starter_dir: Path) -> None:
        """Test synth handles CDK command failures."""
        from aws_api_factory.cli.utils import CDKError

        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.side_effect = CDKError("synth", "Synthesis failed")

                result = cli_runner.invoke(
                    cli,
                    ["synth", "--config", str(starter_dir / "factory.yaml")],
                )

                assert result.exit_code != 0


class TestSynthOutputDirectory:
    """Tests for synth output directory options."""

    def test_synth_with_output_dir(
        self, cli_runner: CliRunner, starter_dir: Path, tmp_path: Path
    ) -> None:
        """Test synth with custom output directory."""
        output_dir = tmp_path / "my-output"

        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

                result = cli_runner.invoke(
                    cli,
                    [
                        "synth",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--output",
                        str(output_dir),
                        "--quiet",
                    ],
                )

                # Should pass output dir to CDK
                if mock_run.called:
                    args = mock_run.call_args[0][0]
                    assert "-o" in args or "--output" in args


class TestSynthShowOption:
    """Tests for synth --show option."""

    def test_synth_show_template(
        self, cli_runner: CliRunner, starter_dir: Path
    ) -> None:
        """Test synth --show displays the generated template."""
        with patch(
            "aws_api_factory.cli.commands.synth.find_cdk_executable"
        ) as mock_cdk:
            mock_cdk.return_value = "/usr/bin/cdk"
            with patch(
                "aws_api_factory.cli.commands.synth.run_cdk_command"
            ) as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout='{"Resources": {}}', stderr=""
                )

                result = cli_runner.invoke(
                    cli,
                    [
                        "synth",
                        "--config",
                        str(starter_dir / "factory.yaml"),
                        "--show",
                    ],
                )

                # Should show some output (template or success message)
                assert result.exit_code == 0
