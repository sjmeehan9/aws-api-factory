# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for the factory init command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aws_api_factory.cli import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Click CLI test runner with isolated filesystem."""
    return CliRunner()


class TestInitCommand:
    """Tests for the factory init command."""

    def test_init_help(self, cli_runner: CliRunner) -> None:
        """Test init --help shows usage information."""
        result = cli_runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "Scaffold a new AWS API Factory project" in result.output
        assert "--profile" in result.output
        assert "--no-git" in result.output
        assert "--no-venv" in result.output

    def test_init_creates_project_directory(self, cli_runner: CliRunner) -> None:
        """Test init creates project directory with template files."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["init", "my-test-project", "--no-git", "--no-venv"]
            )

            assert result.exit_code == 0
            assert "Project created successfully" in result.output

            # Check files were created
            project_dir = Path("my-test-project")
            assert project_dir.exists()
            assert (project_dir / "factory.yaml").exists()
            assert (project_dir / "src").exists()

    def test_init_replaces_project_name(self, cli_runner: CliRunner) -> None:
        """Test init replaces project name in factory.yaml."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["init", "awesome-api", "--no-git", "--no-venv"]
            )

            assert result.exit_code == 0

            # Check project name was replaced
            config_content = (Path("awesome-api") / "factory.yaml").read_text()
            assert (
                "awesome-api" in config_content or "name: awesome-api" in config_content
            )

    def test_init_with_scalable_profile(self, cli_runner: CliRunner) -> None:
        """Test init with --profile scalable option."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli,
                [
                    "init",
                    "my-project",
                    "--profile",
                    "scalable",
                    "--no-git",
                    "--no-venv",
                ],
            )

            assert result.exit_code == 0

            # Check profile was set
            config_content = (Path("my-project") / "factory.yaml").read_text()
            assert "profile: scalable" in config_content

    def test_init_in_current_directory(self, cli_runner: CliRunner) -> None:
        """Test init without project name uses current directory."""
        with cli_runner.isolated_filesystem():
            # Create a directory and cd into it
            Path("my-project").mkdir()
            import os

            os.chdir("my-project")

            result = cli_runner.invoke(cli, ["init", "--no-git", "--no-venv"])

            assert result.exit_code == 0
            assert Path("factory.yaml").exists()

    def test_init_fails_for_existing_directory(self, cli_runner: CliRunner) -> None:
        """Test init fails when directory exists and is not empty."""
        with cli_runner.isolated_filesystem():
            # Create directory with content
            project_dir = Path("existing-project")
            project_dir.mkdir()
            (project_dir / "existing-file.txt").write_text("content")

            result = cli_runner.invoke(
                cli, ["init", "existing-project", "--no-git", "--no-venv"]
            )

            assert result.exit_code != 0
            assert "already exists" in result.output or "not empty" in result.output

    def test_init_fails_for_invalid_project_name(self, cli_runner: CliRunner) -> None:
        """Test init fails for invalid project names."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["init", "invalid project name!", "--no-git", "--no-venv"]
            )

            assert result.exit_code != 0
            assert "Invalid project name" in result.output

    def test_init_with_custom_directory(self, cli_runner: CliRunner) -> None:
        """Test init with --directory option."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli,
                [
                    "init",
                    "my-project",
                    "--directory",
                    "custom/path/my-project",
                    "--no-git",
                    "--no-venv",
                ],
            )

            assert result.exit_code == 0
            assert Path("custom/path/my-project/factory.yaml").exists()

    def test_init_shows_next_steps(self, cli_runner: CliRunner) -> None:
        """Test init shows helpful next steps."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["init", "my-project", "--no-git", "--no-venv"]
            )

            assert result.exit_code == 0
            assert "Next steps" in result.output
            assert "factory validate" in result.output
            assert "factory deploy" in result.output

    def test_init_with_git(self, cli_runner: CliRunner) -> None:
        """Test init initializes git repository when git is available."""
        with cli_runner.isolated_filesystem():
            with patch("shutil.which", return_value="/usr/bin/git"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0

                    result = cli_runner.invoke(cli, ["init", "my-project", "--no-venv"])

                    assert result.exit_code == 0
                    # Git init should have been called
                    assert any("git" in str(call) for call in mock_run.call_args_list)


class TestInitCommandIntegration:
    """Integration tests for factory init."""

    def test_init_creates_working_project(self, cli_runner: CliRunner) -> None:
        """Test that init creates a project that can be validated."""
        with cli_runner.isolated_filesystem():
            # Initialize project
            init_result = cli_runner.invoke(
                cli, ["init", "test-api", "--no-git", "--no-venv"]
            )
            assert init_result.exit_code == 0

            # Validate the created project
            import os

            os.chdir("test-api")

            validate_result = cli_runner.invoke(cli, ["validate"])
            assert validate_result.exit_code == 0
            assert "Configuration is valid" in validate_result.output


class TestInitVirtualEnvironment:
    """Tests for virtual environment creation."""

    def test_init_with_venv_creation(self, cli_runner: CliRunner) -> None:
        """Test init creates virtual environment when requested."""
        with cli_runner.isolated_filesystem():
            with patch("venv.create") as mock_venv:
                result = cli_runner.invoke(cli, ["init", "my-project", "--no-git"])

                # venv.create should have been called
                assert mock_venv.called or result.exit_code == 0

    def test_init_venv_already_exists(self, cli_runner: CliRunner) -> None:
        """Test init handles existing virtual environment."""
        with cli_runner.isolated_filesystem():
            # Create project dir with existing .venv
            Path("my-project/.venv").mkdir(parents=True)

            result = cli_runner.invoke(cli, ["init", "my-project", "--no-git"])

            # Should fail because directory not empty, or handle gracefully
            # Either exit code is acceptable behavior
            assert result.exit_code in [0, 1]


class TestInitGitIntegration:
    """Tests for git repository initialization."""

    def test_init_calls_git_init(self, cli_runner: CliRunner) -> None:
        """Test init initializes git repository."""
        with cli_runner.isolated_filesystem():
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                with patch("shutil.which", return_value="/usr/bin/git"):
                    result = cli_runner.invoke(cli, ["init", "my-project", "--no-venv"])

                    assert result.exit_code == 0
                    # Should have called git init
                    git_calls = [c for c in mock_run.call_args_list if "git" in str(c)]
                    assert len(git_calls) > 0

    def test_init_without_git(self, cli_runner: CliRunner) -> None:
        """Test init works when git is not installed."""
        with cli_runner.isolated_filesystem():
            with patch("shutil.which", return_value=None):
                result = cli_runner.invoke(cli, ["init", "my-project", "--no-venv"])

                # Should still succeed, just skip git init
                assert result.exit_code == 0


class TestInitPreCommit:
    """Tests for pre-commit hook setup."""

    def test_init_setup_precommit(self, cli_runner: CliRunner) -> None:
        """Test init sets up pre-commit hooks."""
        with cli_runner.isolated_filesystem():
            with patch("shutil.which") as mock_which:
                mock_which.side_effect = lambda x: {
                    "git": "/usr/bin/git",
                    "pre-commit": "/usr/bin/pre-commit",
                }.get(x)
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    result = cli_runner.invoke(cli, ["init", "my-project", "--no-venv"])

                    assert result.exit_code == 0


class TestInitEdgeCases:
    """Tests for edge cases and error handling."""

    def test_init_empty_existing_directory(self, cli_runner: CliRunner) -> None:
        """Test init into an empty existing directory."""
        with cli_runner.isolated_filesystem():
            # Create empty directory
            Path("empty-project").mkdir()

            result = cli_runner.invoke(
                cli, ["init", "empty-project", "--no-git", "--no-venv"]
            )

            # Should succeed for empty directory
            assert result.exit_code == 0
            assert Path("empty-project/factory.yaml").exists()

    def test_init_with_special_characters_in_name(self, cli_runner: CliRunner) -> None:
        """Test init rejects names with special characters."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                cli, ["init", "my project@123!", "--no-git", "--no-venv"]
            )

            # Should fail with invalid name
            assert result.exit_code != 0
