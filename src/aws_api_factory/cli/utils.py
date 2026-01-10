# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""CLI utility functions for AWS API Factory.

This module provides helper functions for CLI commands including:
- Configuration loading and validation
- CDK subprocess execution
- User prompts and confirmations
- Rich output formatting

"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - intentional use for CDK subprocess execution
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

if TYPE_CHECKING:
    from aws_api_factory.config.models import FactoryConfig
    from aws_api_factory.config.resolver import ResolutionResult

# Custom theme for consistent styling
FACTORY_THEME = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "path": "blue underline",
        "command": "magenta",
        "config": "cyan italic",
    }
)

# Console instances for stdout and stderr
console = Console(theme=FACTORY_THEME)
error_console = Console(theme=FACTORY_THEME, stderr=True)


class CLIError(Exception):
    """Base exception for CLI errors with user-friendly messages."""

    def __init__(
        self, message: str, suggestion: str | None = None, exit_code: int = 1
    ) -> None:
        """Initialize CLI error.

        Args:
            message: The error message to display.
            suggestion: Optional suggestion for fixing the error.
            exit_code: The exit code to use when terminating.
        """
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.exit_code = exit_code


class ConfigNotFoundError(CLIError):
    """Configuration file not found error."""

    def __init__(self, path: str) -> None:
        super().__init__(
            f"Configuration file not found: {path}",
            suggestion="Run 'factory init' to create a new project or specify "
            "the correct path with --config.",
            exit_code=2,
        )


class ConfigValidationError(CLIError):
    """Configuration validation error."""

    def __init__(self, message: str, details: str | None = None) -> None:
        suggestion = "Check your factory.yaml file for errors."
        if details:
            suggestion = f"{suggestion}\n{details}"
        super().__init__(
            f"Configuration validation failed: {message}",
            suggestion=suggestion,
            exit_code=3,
        )


class CDKError(CLIError):
    """CDK command execution error."""

    def __init__(self, command: str, stderr: str) -> None:
        super().__init__(
            f"CDK command failed: {command}",
            suggestion=f"CDK error output:\n{stderr}",
            exit_code=4,
        )


class AWSCredentialsError(CLIError):
    """AWS credentials not configured error."""

    def __init__(self) -> None:
        super().__init__(
            "AWS credentials not configured or expired",
            suggestion="Configure AWS credentials using:\n"
            "  - AWS CLI: 'aws configure'\n"
            "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
            "  - AWS SSO: 'aws sso login'",
            exit_code=5,
        )


def print_success(message: str, details: str | None = None) -> None:
    """Print a success message with optional details.

    Args:
        message: The main success message.
        details: Optional additional details to display.
    """
    console.print(f"[success]✓[/success] {message}")
    if details:
        console.print(f"  {details}", style="dim")


def print_error(message: str, suggestion: str | None = None) -> None:
    """Print an error message with optional suggestion.

    Args:
        message: The error message to display.
        suggestion: Optional suggestion for fixing the error.
    """
    error_console.print(f"[error]✗ Error:[/error] {message}")
    if suggestion:
        error_console.print(f"[info]  Suggestion:[/info] {suggestion}")


def print_warning(message: str) -> None:
    """Print a warning message.

    Args:
        message: The warning message to display.
    """
    console.print(f"[warning]⚠[/warning] {message}")


def print_info(message: str) -> None:
    """Print an info message.

    Args:
        message: The info message to display.
    """
    console.print(f"[info]ℹ[/info] {message}")


def print_step(step: int, total: int, message: str) -> None:
    """Print a step indicator for multi-step operations.

    Args:
        step: Current step number (1-indexed).
        total: Total number of steps.
        message: Description of the current step.
    """
    console.print(f"[info][{step}/{total}][/info] {message}")


def print_config_panel(
    config: FactoryConfig, title: str = "Configuration Summary"
) -> None:
    """Print a configuration summary panel.

    Args:
        config: The configuration to display.
        title: Title for the panel.
    """
    table = Table(show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Project Name", config.project.name)
    table.add_row("Profile", config.profile.value)
    table.add_row("Environments", ", ".join(config.project.envs))

    if config.apis.rest.enabled:
        routes = len(config.apis.rest.routes)
        table.add_row("REST API", f"Enabled ({routes} routes)")
    else:
        table.add_row("REST API", "Disabled")

    if config.apis.graphql.enabled:
        table.add_row("GraphQL API", "Enabled")
    else:
        table.add_row("GraphQL API", "Disabled")

    if config.compute.lambda_.enabled:
        services = len(config.compute.lambda_.services)
        table.add_row("Lambda Services", str(services))

    if config.compute.apprunner.enabled:
        services = len(config.compute.apprunner.services)
        table.add_row("App Runner Services", str(services))

    table.add_row("Observability", config.observability.level.value)

    console.print(Panel(table, title=title, border_style="blue"))


def print_resolved_defaults(result: ResolutionResult) -> None:
    """Print a table of resolved default values.

    Args:
        result: The resolution result containing applied defaults.
    """
    if not result.applied_defaults:
        console.print("[success]✓[/success] No defaults applied (all values specified)")
        return

    table = Table(
        title=f"Applied Defaults (Profile: {result.profile})",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Path", style="cyan")
    table.add_column("Original", style="yellow")
    table.add_column("Resolved", style="green")
    table.add_column("Rationale", style="dim")

    for default in result.applied_defaults:
        table.add_row(
            default.path,
            str(default.original),
            str(default.resolved),
            (
                default.rationale[:50] + "..."
                if len(default.rationale) > 50
                else default.rationale
            ),
        )

    console.print(table)


def print_resources_table(config: FactoryConfig) -> None:
    """Print a table of resources that will be created.

    Args:
        config: The resolved configuration.
    """
    table = Table(
        title="Resources to Create",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Details", style="dim")

    # API Gateway
    if config.apis.rest.enabled:
        table.add_row(
            "API Gateway REST API",
            f"{config.project.name}-rest-api",
            f"{len(config.apis.rest.routes)} routes",
        )

    # Lambda functions
    if config.compute.lambda_.enabled:
        for name, svc in config.compute.lambda_.services.items():
            memory = svc.memory_mb if svc.memory_mb != "auto" else "profile default"
            table.add_row(
                "Lambda Function",
                f"{config.project.name}-{name}",
                f"Entry: {svc.entry}, Memory: {memory}",
            )

    # App Runner services
    if config.compute.apprunner.enabled:
        for name, svc in config.compute.apprunner.services.items():
            table.add_row(
                "App Runner Service",
                f"{config.project.name}-{name}",
                f"Port: {svc.port}",
            )

    # DynamoDB tables
    if config.data.dynamodb.enabled:
        for tbl in config.data.dynamodb.tables:
            table.add_row(
                "DynamoDB Table",
                f"{config.project.name}-{tbl.name}",
                f"PK: {tbl.pk}, SK: {tbl.sk or 'None'}",
            )

    # S3 buckets
    if config.data.s3.enabled:
        for bucket in config.data.s3.buckets:
            table.add_row(
                "S3 Bucket",
                f"{config.project.name}-{bucket.name}",
                "",
            )

    console.print(table)


def format_yaml_output(data: dict[str, Any]) -> str:
    """Format dictionary as YAML string.

    Args:
        data: Dictionary to format.

    Returns:
        Formatted YAML string.
    """
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def print_yaml(data: dict[str, Any], title: str | None = None) -> None:
    """Print formatted YAML with syntax highlighting.

    Args:
        data: Dictionary to print as YAML.
        title: Optional title for the panel.
    """
    yaml_str = format_yaml_output(data)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def load_and_validate_config(
    path: str | Path,
    environment: str | None = None,
    resolve_defaults: bool = True,
) -> tuple[FactoryConfig, ResolutionResult | None]:
    """Load and validate configuration from a file.

    Args:
        path: Path to the factory.yaml configuration file.
        environment: Optional environment name for environment-specific overrides.
        resolve_defaults: Whether to resolve profile defaults.

    Returns:
        Tuple of (validated config, resolution result if defaults were resolved).

    Raises:
        ConfigNotFoundError: If the configuration file doesn't exist.
        ConfigValidationError: If the configuration is invalid.
    """
    from aws_api_factory.config import ConfigLoadError, load_config
    from aws_api_factory.config.resolver import DefaultsResolver

    path = Path(path)
    if not path.exists():
        raise ConfigNotFoundError(str(path))

    try:
        config = load_config(path, env=environment)
    except ConfigLoadError as e:
        raise ConfigValidationError(str(e)) from e
    except Exception as e:
        raise ConfigValidationError(f"Unexpected error: {e}") from e

    resolution_result = None
    if resolve_defaults:
        resolver = DefaultsResolver(config)
        resolution_result = resolver.resolve_with_result()
        config = resolution_result.config

    return config, resolution_result


def find_cdk_executable() -> str:
    """Find the CDK CLI executable.

    Returns:
        Path to the CDK executable.

    Raises:
        CLIError: If CDK is not installed.
    """
    cdk_path = shutil.which("cdk")
    if cdk_path is None:
        raise CLIError(
            "AWS CDK CLI not found",
            suggestion="Install CDK CLI with: npm install -g aws-cdk\n"
            "See: https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html",
        )
    return cdk_path


def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured.

    Returns:
        True if credentials appear to be configured.
    """
    # Check environment variables
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True

    # Check for AWS SSO session or profile
    if os.environ.get("AWS_PROFILE"):
        return True

    # Check for credential file
    cred_path = Path.home() / ".aws" / "credentials"
    if cred_path.exists():
        return True

    return False


def run_cdk_command(
    args: list[str],
    cwd: Path | str | None = None,
    env: str | None = None,
    capture_output: bool = False,
    show_progress: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a CDK command with error handling.

    Args:
        args: CDK command arguments (without 'cdk' prefix).
        cwd: Working directory for the command.
        env: Environment name to pass as context.
        capture_output: Whether to capture and return output.
        show_progress: Whether to show a progress spinner.

    Returns:
        CompletedProcess result.

    Raises:
        CDKError: If the CDK command fails.
        AWSCredentialsError: If AWS credentials are not configured.
    """
    cdk_path = find_cdk_executable()

    # Build the full command
    cmd = [cdk_path] + args

    # Add environment context if specified
    if env:
        cmd.extend(["--context", f"env={env}"])

    # Set up environment variables
    cmd_env = os.environ.copy()
    cmd_env["CDK_DEFAULT_ACCOUNT"] = os.environ.get("CDK_DEFAULT_ACCOUNT", "")
    cmd_env["CDK_DEFAULT_REGION"] = os.environ.get(
        "CDK_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1")
    )

    cwd_path = Path(cwd) if cwd else Path.cwd()

    if show_progress and not capture_output:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Running: cdk {' '.join(args)}", total=None)
            try:
                result = subprocess.run(  # nosec B603 - trusted CDK command
                    cmd,
                    cwd=cwd_path,
                    env=cmd_env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                progress.update(task, completed=True)
            except FileNotFoundError as e:
                raise CDKError(" ".join(args), str(e)) from e
    else:
        try:
            result = subprocess.run(  # nosec B603 - trusted CDK command
                cmd,
                cwd=cwd_path,
                env=cmd_env,
                capture_output=capture_output,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            raise CDKError(" ".join(args), str(e)) from e

    if result.returncode != 0:
        stderr = result.stderr if result.stderr else "No error output"
        if "ExpiredToken" in stderr or "credentials" in stderr.lower():
            raise AWSCredentialsError()
        raise CDKError(" ".join(args), stderr)

    return result


def confirm_action(
    message: str,
    dangerous: bool = False,
    require_input: str | None = None,
) -> bool:
    """Prompt user for confirmation.

    Args:
        message: The confirmation message to display.
        dangerous: If True, use red styling to indicate danger.
        require_input: If set, require user to type this exact string to confirm.

    Returns:
        True if the user confirmed, False otherwise.
    """
    if dangerous:
        console.print(f"[error]⚠ WARNING:[/error] {message}")
    else:
        console.print(f"[warning]?[/warning] {message}")

    if require_input:
        user_input = click.prompt(
            f"Type '{require_input}' to confirm",
            default="",
            show_default=False,
        )
        return user_input == require_input
    else:
        return click.confirm("Continue?", default=False)


def get_stack_name(project_name: str, environment: str) -> str:
    """Generate the CDK stack name for a project and environment.

    Args:
        project_name: The project name from config.
        environment: The environment name.

    Returns:
        The stack name in format: {project}-{env}-stack.
    """
    # Sanitize project name (replace underscores with hyphens, lowercase)
    sanitized = project_name.lower().replace("_", "-").replace(" ", "-")
    return f"{sanitized}-{environment}-stack"


def save_outputs_to_file(outputs: dict[str, Any], path: Path) -> None:
    """Save stack outputs to a JSON file.

    Args:
        outputs: Dictionary of stack outputs.
        path: Path to write the JSON file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(outputs, f, indent=2)
    print_success(f"Outputs saved to: {path}")


def get_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for factory.yaml.

    Args:
        start_path: Starting directory for the search.

    Returns:
        Path to project root or None if not found.
    """
    current = start_path or Path.cwd()

    while current != current.parent:
        if (current / "factory.yaml").exists():
            return current
        current = current.parent

    return None


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory.

    Returns:
        The path that was created or already existed.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_template_file(
    source: Path,
    dest: Path,
    replacements: dict[str, str] | None = None,
) -> None:
    """Copy a template file, optionally replacing placeholders.

    Args:
        source: Source file path.
        dest: Destination file path.
        replacements: Dictionary of placeholder -> replacement value.
    """
    content = source.read_text()

    if replacements:
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)


def get_verbose_context(ctx: click.Context) -> bool:
    """Get the verbose flag from Click context.

    Args:
        ctx: The Click context object.

    Returns:
        True if verbose mode is enabled.
    """
    return ctx.obj.get("verbose", False) if ctx.obj else False
