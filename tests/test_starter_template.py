# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for starter template and documentation (Component 1.9).

These tests verify:
- Starter template completeness and correctness
- Documentation file existence and content
- All code examples are syntactically valid
- Configuration examples validate correctly
- Links between documentation files work
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml


class TestStarterTemplateStructure:
    """Tests for starter template directory structure."""

    def test_starter_directory_exists(self, starter_dir: Path) -> None:
        """Test that starter directory exists."""
        assert starter_dir.exists()
        assert starter_dir.is_dir()

    def test_factory_yaml_exists(self, starter_dir: Path) -> None:
        """Test that factory.yaml exists in starter."""
        factory_yaml = starter_dir / "factory.yaml"
        assert factory_yaml.exists()

    def test_starter_readme_exists(self, starter_dir: Path) -> None:
        """Test that README.md exists in starter."""
        readme = starter_dir / "README.md"
        assert readme.exists()

    def test_hello_service_exists(self, starter_dir: Path) -> None:
        """Test that hello service exists."""
        handler = starter_dir / "src" / "services" / "hello" / "handler.py"
        assert handler.exists()

    def test_orders_service_exists(self, starter_dir: Path) -> None:
        """Test that orders CRUD service exists."""
        handler = starter_dir / "src" / "services" / "orders" / "handler.py"
        assert handler.exists()

    def test_public_api_service_exists(self, starter_dir: Path) -> None:
        """Test that public_api App Runner service exists."""
        app = starter_dir / "src" / "services" / "public_api" / "app.py"
        dockerfile = starter_dir / "src" / "services" / "public_api" / "Dockerfile"
        assert app.exists()
        assert dockerfile.exists()

    def test_infra_directory_exists(self, starter_dir: Path) -> None:
        """Test that infra directory exists with app.py."""
        app_py = starter_dir / "infra" / "app.py"
        assert app_py.exists()


class TestStarterFactoryYaml:
    """Tests for starter factory.yaml configuration."""

    def test_factory_yaml_valid_yaml(self, starter_dir: Path) -> None:
        """Test that factory.yaml is valid YAML."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert isinstance(config, dict)

    def test_factory_yaml_has_required_sections(self, starter_dir: Path) -> None:
        """Test that factory.yaml has all required sections."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)

        assert "project" in config
        assert "profile" in config
        assert "apis" in config
        assert "compute" in config

    def test_factory_yaml_project_config(self, starter_dir: Path) -> None:
        """Test project configuration is valid."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)

        project = config["project"]
        assert "name" in project
        assert "envs" in project
        assert isinstance(project["envs"], list)
        assert len(project["envs"]) >= 1

    def test_factory_yaml_has_hello_route(self, starter_dir: Path) -> None:
        """Test that factory.yaml has hello route configured."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)

        routes = config["apis"]["rest"]["routes"]
        hello_routes = [r for r in routes if r["path"] == "/hello"]
        assert len(hello_routes) == 1
        assert "GET" in hello_routes[0]["methods"]

    def test_factory_yaml_has_orders_routes(self, starter_dir: Path) -> None:
        """Test that factory.yaml has orders CRUD routes."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)

        routes = config["apis"]["rest"]["routes"]
        orders_routes = [r for r in routes if "/orders" in r["path"]]
        assert len(orders_routes) >= 2  # /orders and /orders/{id}

    def test_factory_yaml_has_hello_service(self, starter_dir: Path) -> None:
        """Test that hello Lambda service is configured."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)

        services = config["compute"]["lambda"]["services"]
        assert "hello" in services
        assert "entry" in services["hello"]

    def test_factory_yaml_has_orders_service(self, starter_dir: Path) -> None:
        """Test that orders Lambda service is configured."""
        factory_yaml = starter_dir / "factory.yaml"
        with open(factory_yaml) as f:
            config = yaml.safe_load(f)

        services = config["compute"]["lambda"]["services"]
        assert "orders" in services
        assert "entry" in services["orders"]

    def test_factory_yaml_validates_with_config_loader(self, starter_dir: Path) -> None:
        """Test that factory.yaml validates with the config loader."""
        from aws_api_factory.config import load_config

        factory_yaml = starter_dir / "factory.yaml"
        config = load_config(factory_yaml)
        assert config is not None
        assert config.project.name == "my-api"


class TestStarterHandlers:
    """Tests for starter Lambda handlers."""

    def test_hello_handler_syntax(self, starter_dir: Path) -> None:
        """Test hello handler has valid Python syntax."""
        handler_path = starter_dir / "src" / "services" / "hello" / "handler.py"
        source = handler_path.read_text()
        # This will raise SyntaxError if invalid
        ast.parse(source)

    def test_hello_handler_has_handler_function(self, starter_dir: Path) -> None:
        """Test hello handler defines a handler function."""
        handler_path = starter_dir / "src" / "services" / "hello" / "handler.py"
        source = handler_path.read_text()
        tree = ast.parse(source)

        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "handler" in function_names

    def test_orders_handler_syntax(self, starter_dir: Path) -> None:
        """Test orders handler has valid Python syntax."""
        handler_path = starter_dir / "src" / "services" / "orders" / "handler.py"
        source = handler_path.read_text()
        ast.parse(source)

    def test_orders_handler_has_handler_function(self, starter_dir: Path) -> None:
        """Test orders handler defines a handler function."""
        handler_path = starter_dir / "src" / "services" / "orders" / "handler.py"
        source = handler_path.read_text()
        tree = ast.parse(source)

        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "handler" in function_names

    def test_orders_handler_has_crud_functions(self, starter_dir: Path) -> None:
        """Test orders handler has CRUD operation functions."""
        handler_path = starter_dir / "src" / "services" / "orders" / "handler.py"
        source = handler_path.read_text()
        tree = ast.parse(source)

        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        # Should have CRUD functions
        assert "list_orders" in function_names
        assert "create_order" in function_names
        assert "get_order" in function_names
        assert "update_order" in function_names
        assert "delete_order" in function_names

    def test_public_api_app_syntax(self, starter_dir: Path) -> None:
        """Test public_api app.py has valid Python syntax."""
        app_path = starter_dir / "src" / "services" / "public_api" / "app.py"
        source = app_path.read_text()
        ast.parse(source)


class TestDocumentationStructure:
    """Tests for documentation file structure."""

    def test_getting_started_exists(self, project_root: Path) -> None:
        """Test that getting-started.md exists."""
        doc = project_root / "docs" / "getting-started.md"
        assert doc.exists()

    def test_configuration_reference_exists(self, project_root: Path) -> None:
        """Test that configuration reference exists."""
        doc = project_root / "docs" / "reference" / "configuration.md"
        assert doc.exists()

    def test_defaults_reference_exists(self, project_root: Path) -> None:
        """Test that defaults reference exists."""
        doc = project_root / "docs" / "reference" / "defaults.md"
        assert doc.exists()

    def test_rest_api_guide_exists(self, project_root: Path) -> None:
        """Test that REST API guide exists."""
        doc = project_root / "docs" / "guides" / "rest-api.md"
        assert doc.exists()

    def test_lambda_guide_exists(self, project_root: Path) -> None:
        """Test that Lambda functions guide exists."""
        doc = project_root / "docs" / "guides" / "lambda-functions.md"
        assert doc.exists()

    def test_apprunner_guide_exists(self, project_root: Path) -> None:
        """Test that App Runner guide exists."""
        doc = project_root / "docs" / "guides" / "app-runner-containers.md"
        assert doc.exists()

    def test_authentication_guide_exists(self, project_root: Path) -> None:
        """Test that authentication guide exists."""
        doc = project_root / "docs" / "guides" / "authentication.md"
        assert doc.exists()

    def test_crud_example_exists(self, project_root: Path) -> None:
        """Test that CRUD API example exists."""
        doc = project_root / "docs" / "examples" / "crud-api.md"
        assert doc.exists()

    def test_troubleshooting_exists(self, project_root: Path) -> None:
        """Test that troubleshooting guide exists."""
        doc = project_root / "docs" / "troubleshooting.md"
        assert doc.exists()

    def test_construct_development_guide_exists(self, project_root: Path) -> None:
        """Test that construct development guide exists."""
        doc = project_root / "docs" / "guides" / "construct-development.md"
        assert doc.exists()


class TestDocumentationContent:
    """Tests for documentation content quality."""

    def test_getting_started_has_sections(self, project_root: Path) -> None:
        """Test that getting-started.md has expected sections."""
        doc = project_root / "docs" / "getting-started.md"
        content = doc.read_text()

        # Check for key sections
        assert "Prerequisites" in content
        assert "Install" in content or "Installation" in content
        assert "Deploy" in content
        assert "Test" in content

    def test_configuration_reference_has_sections(self, project_root: Path) -> None:
        """Test that configuration reference has expected sections."""
        doc = project_root / "docs" / "reference" / "configuration.md"
        content = doc.read_text()

        # Check for key config sections
        assert "project" in content.lower()
        assert "profile" in content.lower()
        assert "apis" in content.lower()
        assert "compute" in content.lower()

    def test_authentication_guide_has_auth_modes(self, project_root: Path) -> None:
        """Test that auth guide covers all auth modes."""
        doc = project_root / "docs" / "guides" / "authentication.md"
        content = doc.read_text()

        assert "api_key" in content or "API Key" in content
        assert "iam" in content.lower() or "IAM" in content
        assert "cognito" in content.lower() or "Cognito" in content

    def test_troubleshooting_has_common_issues(self, project_root: Path) -> None:
        """Test that troubleshooting covers common issues."""
        doc = project_root / "docs" / "troubleshooting.md"
        content = doc.read_text()

        # Check for common issue categories
        assert "403" in content or "Forbidden" in content
        assert "timeout" in content.lower()
        assert "CDK" in content or "cdk" in content


class TestDocumentationCodeExamples:
    """Tests that code examples in documentation are syntactically valid."""

    def _extract_python_code_blocks(self, content: str) -> list[str]:
        """Extract Python code blocks from Markdown content."""
        # Match ```python ... ``` blocks
        pattern = r"```python\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        return matches

    def _extract_yaml_code_blocks(self, content: str) -> list[str]:
        """Extract YAML code blocks from Markdown content."""
        pattern = r"```ya?ml\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        return matches

    def test_getting_started_python_examples(self, project_root: Path) -> None:
        """Test Python examples in getting-started.md are valid."""
        doc = project_root / "docs" / "getting-started.md"
        content = doc.read_text()
        code_blocks = self._extract_python_code_blocks(content)

        for i, code in enumerate(code_blocks):
            # Skip incomplete snippets (those with ... or ellipsis)
            if "..." in code or "# ..." in code:
                continue
            try:
                ast.parse(code)
            except SyntaxError as e:
                pytest.fail(
                    f"Python block {i+1} in getting-started.md has syntax error: {e}"
                )

    def test_getting_started_yaml_examples(self, project_root: Path) -> None:
        """Test YAML examples in getting-started.md are valid."""
        doc = project_root / "docs" / "getting-started.md"
        content = doc.read_text()
        code_blocks = self._extract_yaml_code_blocks(content)

        for i, code in enumerate(code_blocks):
            try:
                yaml.safe_load(code)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML block {i+1} in getting-started.md has error: {e}")

    def test_configuration_yaml_examples(self, project_root: Path) -> None:
        """Test YAML examples in configuration.md are valid."""
        doc = project_root / "docs" / "reference" / "configuration.md"
        content = doc.read_text()
        code_blocks = self._extract_yaml_code_blocks(content)

        for i, code in enumerate(code_blocks):
            # Skip partial examples with comments indicating continuation
            if code.strip().startswith("#") and "..." in code:
                continue
            try:
                yaml.safe_load(code)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML block {i+1} in configuration.md has error: {e}")

    def test_lambda_guide_python_examples(self, project_root: Path) -> None:
        """Test Python examples in lambda-functions.md are valid."""
        doc = project_root / "docs" / "guides" / "lambda-functions.md"
        content = doc.read_text()
        code_blocks = self._extract_python_code_blocks(content)

        for i, code in enumerate(code_blocks):
            if "..." in code or "# ..." in code:
                continue
            try:
                ast.parse(code)
            except SyntaxError as e:
                pytest.fail(
                    f"Python block {i+1} in lambda-functions.md has syntax error: {e}"
                )


class TestDocumentationLinks:
    """Tests for internal documentation links."""

    def _extract_markdown_links(self, content: str) -> list[tuple[str, str]]:
        """Extract Markdown links as (text, path) tuples."""
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        return re.findall(pattern, content)

    def test_readme_links_valid(self, project_root: Path) -> None:
        """Test that links in README.md point to existing files."""
        readme = project_root / "README.md"
        content = readme.read_text()
        links = self._extract_markdown_links(content)

        for text, path in links:
            # Skip external links
            if path.startswith("http"):
                continue
            # Skip anchor links
            if path.startswith("#"):
                continue

            # Resolve relative path
            target = project_root / path.split("#")[0]  # Remove anchor
            assert (
                target.exists()
            ), f"README link '{text}' points to missing file: {path}"

    def test_getting_started_links_valid(self, project_root: Path) -> None:
        """Test that links in getting-started.md are valid."""
        doc = project_root / "docs" / "getting-started.md"
        content = doc.read_text()
        links = self._extract_markdown_links(content)

        for text, path in links:
            if path.startswith("http") or path.startswith("#"):
                continue

            # Resolve relative to docs directory
            target = doc.parent / path.split("#")[0]
            assert target.exists(), f"Link '{text}' points to missing file: {path}"


class TestStarterReadme:
    """Tests for starter template README."""

    def test_starter_readme_has_quick_start(self, starter_dir: Path) -> None:
        """Test starter README has quick start section."""
        readme = starter_dir / "README.md"
        content = readme.read_text()

        assert "Quick Start" in content or "quick start" in content.lower()

    def test_starter_readme_has_structure(self, starter_dir: Path) -> None:
        """Test starter README describes project structure."""
        readme = starter_dir / "README.md"
        content = readme.read_text()

        assert "Structure" in content or "structure" in content.lower()
        assert "factory.yaml" in content
        assert "src/" in content or "services" in content

    def test_starter_readme_has_deploy_instructions(self, starter_dir: Path) -> None:
        """Test starter README has deployment instructions."""
        readme = starter_dir / "README.md"
        content = readme.read_text()

        assert "deploy" in content.lower()
        assert "factory" in content
