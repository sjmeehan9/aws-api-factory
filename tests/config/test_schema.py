# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for JSON Schema export functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aws_api_factory.config.schema import (
    export_json_schema,
    export_json_schema_string,
    generate_yaml_schema_header,
    get_config_template,
    get_schema_for_section,
    write_json_schema,
)


class TestExportJsonSchema:
    """Tests for export_json_schema function."""

    def test_schema_has_metadata(self) -> None:
        """Test schema includes required metadata."""
        schema = export_json_schema()
        assert "$schema" in schema
        assert "json-schema.org" in schema["$schema"]
        assert schema["$id"].endswith("factory.schema.json")
        assert "AWS API Factory" in schema["title"]

    def test_schema_has_properties(self) -> None:
        """Test schema has expected top-level properties."""
        schema = export_json_schema()
        assert "properties" in schema

        properties = schema["properties"]
        expected_props = [
            "project",
            "profile",
            "apis",
            "compute",
            "data",
            "secrets",
            "observability",
        ]
        for prop in expected_props:
            assert prop in properties, f"Missing property: {prop}"

    def test_schema_has_definitions(self) -> None:
        """Test schema has definitions for nested models."""
        schema = export_json_schema()
        assert "$defs" in schema

        # Check for some expected definitions
        defs = schema["$defs"]
        assert len(defs) > 0

    def test_schema_has_file_match(self) -> None:
        """Test schema includes file match pattern for IDE support."""
        schema = export_json_schema()
        assert "fileMatch" in schema
        assert "factory.yaml" in schema["fileMatch"]

    def test_schema_is_valid_json(self) -> None:
        """Test schema serializes to valid JSON."""
        schema = export_json_schema()
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)
        assert parsed == schema

    def test_schema_without_descriptions(self) -> None:
        """Test schema can be exported without descriptions."""
        schema = export_json_schema(include_descriptions=False)
        # Top-level description might still be added, but nested ones should be gone
        assert "properties" in schema

    def test_schema_without_examples(self) -> None:
        """Test schema can be exported without examples."""
        schema = export_json_schema(include_examples=False)
        assert "properties" in schema


class TestExportJsonSchemaString:
    """Tests for export_json_schema_string function."""

    def test_returns_formatted_json(self) -> None:
        """Test returns formatted JSON string."""
        schema_str = export_json_schema_string(indent=2)
        assert isinstance(schema_str, str)
        assert schema_str.startswith("{")
        assert "  " in schema_str  # Check indentation

    def test_json_is_parseable(self) -> None:
        """Test returned string is valid JSON."""
        schema_str = export_json_schema_string()
        parsed = json.loads(schema_str)
        assert "properties" in parsed


class TestWriteJsonSchema:
    """Tests for write_json_schema function."""

    def test_writes_file(self, tmp_path: Path) -> None:
        """Test schema is written to file."""
        output_path = tmp_path / "schema.json"
        result = write_json_schema(output_path)

        assert result == output_path
        assert output_path.exists()

        content = output_path.read_text()
        schema = json.loads(content)
        assert "properties" in schema

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test creates parent directories if needed."""
        output_path = tmp_path / "nested" / "dir" / "schema.json"
        write_json_schema(output_path)

        assert output_path.exists()


class TestGetSchemaForSection:
    """Tests for get_schema_for_section function."""

    def test_get_project_section(self) -> None:
        """Test getting schema for project section."""
        schema = get_schema_for_section("project")
        assert schema is not None
        # Should have properties for name and envs
        if "properties" in schema:
            assert "name" in schema["properties"] or "$ref" in schema

    def test_get_apis_section(self) -> None:
        """Test getting schema for apis section."""
        schema = get_schema_for_section("apis")
        assert schema is not None

    def test_get_nonexistent_section(self) -> None:
        """Test getting schema for non-existent section."""
        schema = get_schema_for_section("nonexistent")
        assert schema is None


class TestGenerateYamlSchemaHeader:
    """Tests for generate_yaml_schema_header function."""

    def test_header_includes_schema_reference(self) -> None:
        """Test header includes yaml-language-server schema reference."""
        header = generate_yaml_schema_header()
        assert "yaml-language-server" in header
        assert "$schema=" in header

    def test_header_is_yaml_comment(self) -> None:
        """Test header is valid YAML comment."""
        header = generate_yaml_schema_header()
        for line in header.strip().split("\n"):
            assert line.startswith("#") or line == ""


class TestGetConfigTemplate:
    """Tests for get_config_template function."""

    def test_minimal_template(self) -> None:
        """Test minimal profile template."""
        template = get_config_template("minimal")
        assert "profile: minimal" in template
        assert "project:" in template
        assert "apis:" in template

    def test_scalable_template(self) -> None:
        """Test scalable profile template."""
        template = get_config_template("scalable")
        assert "profile: scalable" in template
        assert "throttle_rate" in template

    def test_template_includes_header(self) -> None:
        """Test template includes schema header."""
        template = get_config_template()
        assert "yaml-language-server" in template

    def test_template_is_valid_yaml(self) -> None:
        """Test generated template is valid YAML."""
        import yaml

        template = get_config_template("minimal")
        # Should parse without error
        data = yaml.safe_load(template)
        assert data["project"]["name"] == "my-api"
