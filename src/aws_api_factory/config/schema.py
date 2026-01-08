# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""JSON Schema export for AWS API Factory configuration.

This module provides functions to export the configuration schema
as JSON Schema for IDE autocomplete, documentation, and external
validation tools.

Example:
    >>> from aws_api_factory.config.schema import export_json_schema
    >>> schema = export_json_schema()
    >>> # Write to file for VS Code YAML extension
    >>> with open("factory.schema.json", "w") as f:
    ...     json.dump(schema, f, indent=2)

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aws_api_factory.config.models import FactoryConfig


def export_json_schema(
    indent: int | None = 2,
    include_descriptions: bool = True,
    include_examples: bool = True,
) -> dict[str, Any]:
    """Export the FactoryConfig JSON Schema.

    Generates a JSON Schema from the Pydantic models that can be used
    for IDE autocomplete (VS Code YAML extension), documentation, and
    external validation tools.

    Args:
        indent: Indentation for nested structures (for readability).
        include_descriptions: Include field descriptions in schema.
        include_examples: Include field examples in schema.

    Returns:
        JSON Schema as a dictionary.

    Example:
        >>> schema = export_json_schema()
        >>> schema["$schema"]
        'https://json-schema.org/draft/2020-12/schema'
    """
    # Generate schema from Pydantic model
    schema = FactoryConfig.model_json_schema(
        mode="serialization",
        ref_template="#/$defs/{model}",
    )

    # Add JSON Schema metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://github.com/seanmeehan/aws-api-factory/factory.schema.json"
    schema["title"] = "AWS API Factory Configuration"
    schema["description"] = (
        "Configuration schema for AWS API Factory. "
        "This file configures REST APIs, GraphQL APIs, Lambda functions, "
        "App Runner services, data stores, and observability settings."
    )

    # Add file match pattern for VS Code YAML extension
    schema["fileMatch"] = ["factory.yaml", "factory.*.yaml"]

    # Post-process schema if needed
    if not include_descriptions:
        _remove_field(schema, "description")
    if not include_examples:
        _remove_field(schema, "examples")

    return schema


def _remove_field(obj: Any, field: str) -> None:
    """Recursively remove a field from a JSON Schema.

    Args:
        obj: JSON Schema object or sub-object.
        field: Field name to remove.
    """
    if isinstance(obj, dict):
        obj.pop(field, None)
        for value in obj.values():
            _remove_field(value, field)
    elif isinstance(obj, list):
        for item in obj:
            _remove_field(item, field)


def export_json_schema_string(
    indent: int = 2,
    include_descriptions: bool = True,
    include_examples: bool = True,
) -> str:
    """Export the FactoryConfig JSON Schema as a formatted string.

    Args:
        indent: Indentation for nested structures.
        include_descriptions: Include field descriptions in schema.
        include_examples: Include field examples in schema.

    Returns:
        JSON Schema as a formatted JSON string.
    """
    schema = export_json_schema(
        indent=indent,
        include_descriptions=include_descriptions,
        include_examples=include_examples,
    )
    return json.dumps(schema, indent=indent, sort_keys=False)


def write_json_schema(
    output_path: Path | str,
    indent: int = 2,
    include_descriptions: bool = True,
    include_examples: bool = True,
) -> Path:
    """Write the JSON Schema to a file.

    Args:
        output_path: Path to write the schema file.
        indent: Indentation for nested structures.
        include_descriptions: Include field descriptions in schema.
        include_examples: Include field examples in schema.

    Returns:
        Path to the written schema file.

    Example:
        >>> write_json_schema("docs/factory.schema.json")
        PosixPath('docs/factory.schema.json')
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    schema_str = export_json_schema_string(
        indent=indent,
        include_descriptions=include_descriptions,
        include_examples=include_examples,
    )

    path.write_text(schema_str, encoding="utf-8")
    return path


def get_schema_for_section(section: str) -> dict[str, Any] | None:
    """Get the JSON Schema for a specific configuration section.

    Useful for generating documentation or validation for individual
    configuration sections.

    Args:
        section: Section name (e.g., "project", "apis", "compute").

    Returns:
        JSON Schema for the section, or None if not found.

    Example:
        >>> schema = get_schema_for_section("project")
        >>> schema["properties"]["name"]["type"]
        'string'
    """
    full_schema = export_json_schema()

    # Check if section is in properties
    if "properties" in full_schema and section in full_schema["properties"]:
        section_ref = full_schema["properties"][section]

        # Resolve $ref if present
        if "$ref" in section_ref:
            ref_name = section_ref["$ref"].split("/")[-1]
            if "$defs" in full_schema and ref_name in full_schema["$defs"]:
                return full_schema["$defs"][ref_name]

        return section_ref

    return None


def generate_yaml_schema_header() -> str:
    """Generate YAML header comment for factory.yaml files.

    Includes schema reference for IDE autocomplete support.

    Returns:
        YAML comment block with schema reference.

    Example:
        >>> header = generate_yaml_schema_header()
        >>> print(header)
        # yaml-language-server: $schema=...
    """
    schema_url = (
        "https://raw.githubusercontent.com/seanmeehan/aws-api-factory/"
        "main/docs/factory.schema.json"
    )

    return f"""\
# yaml-language-server: $schema={schema_url}
# AWS API Factory Configuration
# Documentation: https://github.com/seanmeehan/aws-api-factory#readme
#
# This file configures your API deployment. Edit the sections below
# to customize your REST APIs, GraphQL APIs, compute, and data stores.
#
"""


def get_config_template(profile: str = "minimal") -> str:
    """Generate a template factory.yaml with comments.

    Args:
        profile: Profile to use for defaults ("minimal" or "scalable").

    Returns:
        Template YAML content with helpful comments.

    Example:
        >>> template = get_config_template("minimal")
        >>> print(template)
        # yaml-language-server: $schema=...
        project:
          name: my-api
          ...
    """
    header = generate_yaml_schema_header()

    minimal_template = """\
project:
  name: my-api
  envs:
    - dev
    - prod

profile: minimal  # Options: minimal, scalable

apis:
  rest:
    enabled: true
    routes:
      - path: /hello
        methods:
          - GET
        service: hello
        auth: none  # Options: none, api_key, iam, cognito

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: auto  # 'auto' uses profile defaults
        timeout_s: auto

data:
  dynamodb:
    enabled: false
  s3:
    enabled: false

secrets:
  provider: ssm  # Options: ssm, secrets_manager

observability:
  level: basic  # Options: basic, enhanced
"""

    scalable_template = """\
project:
  name: my-api
  envs:
    - dev
    - staging
    - prod

profile: scalable  # Production-ready defaults

apis:
  rest:
    enabled: true
    throttle_rate: 1000
    throttle_burst: 2000
    routes:
      - path: /hello
        methods:
          - GET
        service: hello
        auth: api_key  # Require API key for production
    # Uncomment for Cognito authentication:
    # cognito:
    #   create_user_pool: true

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: 1024
        timeout_s: 30
        reserved_concurrency: 10

data:
  dynamodb:
    enabled: false
    # Uncomment to add a DynamoDB table:
    # tables:
    #   - name: items
    #     pk: id
    #     pitr: true  # Point-in-Time Recovery for production
  s3:
    enabled: false

secrets:
  provider: secrets_manager  # Use Secrets Manager for production

observability:
  level: enhanced  # Enable alarms and tracing
  tracing: true
  alarms: true
"""

    template = scalable_template if profile == "scalable" else minimal_template
    return header + template
