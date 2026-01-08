# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for project structure and packaging configuration."""

from pathlib import Path

import pytest


class TestProjectStructure:
    """Tests for project directory structure."""

    def test_src_directory_exists(self, project_root: Path) -> None:
        """Test that src directory exists."""
        src_dir = project_root / "src"
        assert src_dir.exists()
        assert src_dir.is_dir()

    def test_library_package_exists(self, project_root: Path) -> None:
        """Test that aws_api_factory package exists."""
        lib_dir = project_root / "src" / "aws_api_factory"
        assert lib_dir.exists()
        assert (lib_dir / "__init__.py").exists()

    def test_cli_module_exists(self, project_root: Path) -> None:
        """Test that CLI module exists."""
        cli_dir = project_root / "src" / "aws_api_factory" / "cli"
        assert cli_dir.exists()
        assert (cli_dir / "__init__.py").exists()

    def test_config_module_exists(self, project_root: Path) -> None:
        """Test that config module exists."""
        config_dir = project_root / "src" / "aws_api_factory" / "config"
        assert config_dir.exists()
        assert (config_dir / "__init__.py").exists()

    def test_constructs_module_exists(self, project_root: Path) -> None:
        """Test that constructs module exists."""
        constructs_dir = project_root / "src" / "aws_api_factory" / "constructs"
        assert constructs_dir.exists()
        assert (constructs_dir / "__init__.py").exists()

    def test_templates_module_exists(self, project_root: Path) -> None:
        """Test that templates module exists."""
        templates_dir = project_root / "src" / "aws_api_factory" / "templates"
        assert templates_dir.exists()
        assert (templates_dir / "__init__.py").exists()

    def test_utils_module_exists(self, project_root: Path) -> None:
        """Test that utils module exists."""
        utils_dir = project_root / "src" / "aws_api_factory" / "utils"
        assert utils_dir.exists()
        assert (utils_dir / "__init__.py").exists()

    def test_starter_template_exists(self, starter_dir: Path) -> None:
        """Test that starter template exists."""
        assert starter_dir.exists()
        assert (starter_dir / "factory.yaml").exists()

    def test_starter_has_hello_service(self, starter_dir: Path) -> None:
        """Test that starter template has hello service."""
        handler = starter_dir / "src" / "services" / "hello" / "handler.py"
        assert handler.exists()


class TestPackagingConfiguration:
    """Tests for packaging configuration files."""

    def test_pyproject_toml_exists(self, project_root: Path) -> None:
        """Test that pyproject.toml exists."""
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists()

    def test_pyproject_has_required_sections(self, project_root: Path) -> None:
        """Test that pyproject.toml has required sections."""
        import tomllib

        pyproject = project_root / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)

        assert "project" in config
        assert "build-system" in config
        assert "tool" in config

    def test_pyproject_project_metadata(self, project_root: Path) -> None:
        """Test that pyproject.toml has correct project metadata."""
        import tomllib

        pyproject = project_root / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)

        project = config["project"]
        assert project["name"] == "aws-api-factory"
        assert "version" in project
        assert project["requires-python"] == ">=3.9"

    def test_pyproject_dependencies(self, project_root: Path) -> None:
        """Test that pyproject.toml has required dependencies."""
        import tomllib

        pyproject = project_root / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)

        deps = config["project"]["dependencies"]
        dep_names = [d.split(">=")[0].split("[")[0] for d in deps]

        assert "aws-cdk-lib" in dep_names
        assert "pydantic" in dep_names
        assert "pyyaml" in dep_names
        assert "click" in dep_names

    def test_pyproject_dev_dependencies(self, project_root: Path) -> None:
        """Test that pyproject.toml has dev dependencies."""
        import tomllib

        pyproject = project_root / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)

        dev_deps = config["project"]["optional-dependencies"]["dev"]
        dep_names = [d.split(">=")[0].split("[")[0] for d in dev_deps]

        assert "pytest" in dep_names
        assert "black" in dep_names
        assert "pre-commit" in dep_names
        assert "bandit" in dep_names

    def test_pyproject_cli_entry_point(self, project_root: Path) -> None:
        """Test that CLI entry point is configured."""
        import tomllib

        pyproject = project_root / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)

        scripts = config["project"]["scripts"]
        assert "factory" in scripts
        assert scripts["factory"] == "aws_api_factory.cli:main"

    def test_precommit_config_exists(self, project_root: Path) -> None:
        """Test that pre-commit config exists."""
        precommit = project_root / ".pre-commit-config.yaml"
        assert precommit.exists()

    def test_github_workflow_exists(self, project_root: Path) -> None:
        """Test that GitHub Actions workflow exists."""
        workflow = project_root / ".github" / "workflows" / "ci.yml"
        assert workflow.exists()

    def test_readme_exists(self, project_root: Path) -> None:
        """Test that README.md exists."""
        readme = project_root / "README.md"
        assert readme.exists()

    def test_contributing_exists(self, project_root: Path) -> None:
        """Test that CONTRIBUTING.md exists."""
        contributing = project_root / "CONTRIBUTING.md"
        assert contributing.exists()

    def test_license_exists(self, project_root: Path) -> None:
        """Test that LICENSE file exists."""
        license_file = project_root / "LICENSE"
        assert license_file.exists()
