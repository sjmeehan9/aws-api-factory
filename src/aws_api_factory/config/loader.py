# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""YAML configuration loader for AWS API Factory.

This module provides functions to load and validate factory.yaml
configuration files, with support for environment-specific overrides
and clear, actionable error messages.

Example:
    >>> from aws_api_factory.config.loader import load_config
    >>> config = load_config("factory.yaml")

    >>> # With environment override
    >>> config = load_config("factory.yaml", env="prod")

"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from aws_api_factory.config.models import FactoryConfig


class ConfigLoadError(Exception):
    """Exception raised when configuration loading fails.

    Attributes:
        message: Human-readable error message.
        file_path: Path to the configuration file that failed to load.
        line_number: Line number where the error occurred (if known).
        details: Additional error details.
    """

    def __init__(
        self,
        message: str,
        file_path: Path | str | None = None,
        line_number: int | None = None,
        details: list[str] | None = None,
    ) -> None:
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        self.details = details or []

        full_message = message
        if file_path:
            full_message = f"{file_path}: {message}"
        if line_number:
            full_message = f"{full_message} (line {line_number})"
        if details:
            full_message += "\n" + "\n".join(f"  - {d}" for d in details)

        super().__init__(full_message)


def _format_validation_error(
    error: ValidationError, file_path: Path | None = None
) -> ConfigLoadError:
    """Format a Pydantic ValidationError into a user-friendly ConfigLoadError.

    Args:
        error: The Pydantic validation error.
        file_path: Path to the config file for context.

    Returns:
        A ConfigLoadError with formatted error details.
    """
    details: list[str] = []

    for err in error.errors():
        # Build the path to the error location
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        err_type = err["type"]

        # Provide more helpful messages for common errors
        if err_type == "missing":
            detail = f"Missing required field: '{loc}'"
        elif err_type == "extra_forbidden":
            detail = f"Unknown field: '{loc}'. Check spelling or remove this field."
        elif err_type == "enum":
            # Extract allowed values from the error message
            detail = f"Invalid value at '{loc}': {msg}"
        elif err_type == "string_pattern_mismatch":
            detail = f"Invalid format at '{loc}': {msg}"
        elif err_type == "value_error":
            detail = f"Invalid value at '{loc}': {msg}"
        else:
            detail = f"Error at '{loc}': {msg}"

        # Add input context if available
        if "input" in err and err["input"] is not None:
            input_val = err["input"]
            if isinstance(input_val, str) and len(input_val) > 50:
                input_val = input_val[:47] + "..."
            detail += f" (got: {input_val!r})"

        details.append(detail)

    return ConfigLoadError(
        message="Configuration validation failed",
        file_path=file_path,
        details=details,
    )


def _format_yaml_error(
    error: yaml.YAMLError, file_path: Path | None = None
) -> ConfigLoadError:
    """Format a YAML parsing error into a user-friendly ConfigLoadError.

    Args:
        error: The YAML parsing error.
        file_path: Path to the config file for context.

    Returns:
        A ConfigLoadError with formatted error details.
    """
    line_number = None
    message = "Invalid YAML syntax"
    details: list[str] = []

    if hasattr(error, "problem_mark") and error.problem_mark:
        line_number = error.problem_mark.line + 1  # YAML uses 0-based lines
        column = error.problem_mark.column + 1
        details.append(f"At line {line_number}, column {column}")

    if hasattr(error, "problem") and error.problem:
        details.append(f"Problem: {error.problem}")

    if hasattr(error, "context") and error.context:
        details.append(f"Context: {error.context}")

    return ConfigLoadError(
        message=message,
        file_path=file_path,
        line_number=line_number,
        details=details,
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary.
        override: Override dictionary (values take precedence).

    Returns:
        Merged dictionary.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_yaml_file(file_path: Path | str) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dictionary.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Dictionary containing the YAML file contents.

    Raises:
        ConfigLoadError: If the file cannot be read or parsed.
    """
    path = Path(file_path)

    if not path.exists():
        raise ConfigLoadError(
            message="Configuration file not found",
            file_path=path,
            details=[
                f"Expected file at: {path.absolute()}",
                "Run 'factory init' to create a new project with a factory.yaml template.",
            ],
        )

    if not path.is_file():
        raise ConfigLoadError(
            message="Path is not a file",
            file_path=path,
        )

    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError:
        raise ConfigLoadError(
            message="Permission denied reading configuration file",
            file_path=path,
        )
    except OSError as e:
        raise ConfigLoadError(
            message=f"Error reading configuration file: {e}",
            file_path=path,
        )

    return load_yaml_string(content, file_path=path)


def load_yaml_string(
    content: str, file_path: Path | str | None = None
) -> dict[str, Any]:
    """Parse YAML content from a string.

    Args:
        content: YAML content string.
        file_path: Optional file path for error messages.

    Returns:
        Dictionary containing the parsed YAML.

    Raises:
        ConfigLoadError: If the YAML cannot be parsed.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise _format_yaml_error(e, Path(file_path) if file_path else None)

    if data is None:
        raise ConfigLoadError(
            message="Configuration file is empty",
            file_path=file_path,
            details=["The factory.yaml file must contain configuration content."],
        )

    if not isinstance(data, dict):
        raise ConfigLoadError(
            message="Configuration must be a YAML mapping (dictionary)",
            file_path=file_path,
            details=[f"Got type: {type(data).__name__}"],
        )

    return data


def load_config(
    config_path: Path | str,
    env: str | None = None,
) -> FactoryConfig:
    """Load and validate a factory.yaml configuration file.

    This function loads the main configuration file and optionally
    merges environment-specific overrides (e.g., factory.dev.yaml).

    Args:
        config_path: Path to the factory.yaml file.
        env: Optional environment name for loading overrides.
            If provided, looks for factory.{env}.yaml in the same directory.

    Returns:
        Validated FactoryConfig object.

    Raises:
        ConfigLoadError: If the file cannot be loaded or validated.

    Example:
        >>> config = load_config("factory.yaml")
        >>> config = load_config("factory.yaml", env="prod")
    """
    path = Path(config_path)
    base_data = load_yaml_file(path)

    # Load environment-specific overrides if specified
    if env:
        env_path = path.parent / f"factory.{env}.yaml"
        if env_path.exists():
            env_data = load_yaml_file(env_path)
            base_data = _deep_merge(base_data, env_data)

    return validate_and_parse(base_data, file_path=path)


def load_config_from_string(
    content: str,
    env_content: str | None = None,
) -> FactoryConfig:
    """Load and validate configuration from YAML strings.

    Useful for testing or programmatic configuration.

    Args:
        content: Main configuration YAML string.
        env_content: Optional environment override YAML string.

    Returns:
        Validated FactoryConfig object.

    Raises:
        ConfigLoadError: If the configuration cannot be validated.
    """
    base_data = load_yaml_string(content)

    if env_content:
        env_data = load_yaml_string(env_content)
        base_data = _deep_merge(base_data, env_data)

    return validate_and_parse(base_data)


def validate_and_parse(
    data: dict[str, Any],
    file_path: Path | str | None = None,
) -> FactoryConfig:
    """Validate and parse a configuration dictionary.

    Args:
        data: Configuration dictionary.
        file_path: Optional file path for error messages.

    Returns:
        Validated FactoryConfig object.

    Raises:
        ConfigLoadError: If validation fails.
    """
    try:
        return FactoryConfig.model_validate(data)
    except ValidationError as e:
        raise _format_validation_error(e, Path(file_path) if file_path else None)


def find_config_file(
    start_path: Path | str | None = None,
    filename: str = "factory.yaml",
) -> Path | None:
    """Search for a configuration file in the current or parent directories.

    Args:
        start_path: Directory to start searching from.
            Defaults to current working directory.
        filename: Name of the configuration file to find.

    Returns:
        Path to the configuration file if found, None otherwise.
    """
    current = Path(start_path) if start_path else Path.cwd()
    current = current.resolve()

    # Limit search depth to prevent infinite loops
    max_depth = 10

    for _ in range(max_depth):
        config_path = current / filename
        if config_path.exists():
            return config_path

        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def get_config_dir(config_path: Path | str) -> Path:
    """Get the directory containing the configuration file.

    This is useful for resolving relative paths in the configuration.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Directory containing the configuration file.
    """
    return Path(config_path).resolve().parent
