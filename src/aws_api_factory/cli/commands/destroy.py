# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Factory destroy command for tearing down AWS stacks.

This module implements the 'factory destroy' command that tears down
factory stacks from AWS using CDK.

Example:
    $ factory destroy dev
    $ factory destroy prod --config path/to/factory.yaml
    $ factory destroy dev --force

"""

from __future__ import annotations

from pathlib import Path

import click

from aws_api_factory.cli.utils import (
    AWSCredentialsError,
    CDKError,
    CLIError,
    ConfigNotFoundError,
    ConfigValidationError,
    check_aws_credentials,
    confirm_action,
    console,
    error_console,
    find_cdk_executable,
    get_stack_name,
    get_verbose_context,
    load_and_validate_config,
    print_error,
    print_info,
    print_resources_table,
    print_step,
    print_success,
    print_warning,
    run_cdk_command,
)


def find_cdk_app_path(config_path: Path) -> Path:
    """Find the CDK app.py file for destroy.

    Args:
        config_path: Path to the factory.yaml config file.

    Returns:
        Path to the CDK app.py file.

    Raises:
        CLIError: If no CDK app is found.
    """
    config_dir = config_path.parent
    search_paths = [
        config_dir / "infra" / "app.py",
        config_dir / "cdk" / "app.py",
        config_dir / "app.py",
    ]

    for path in search_paths:
        if path.exists():
            return path

    raise CLIError(
        "CDK app.py not found",
        suggestion="Create an infra/app.py file that imports FactoryStack, or run "
        "'factory init' to generate the project structure.",
    )


def generate_temp_cdk_app(config_path: Path, output_dir: Path) -> Path:
    """Generate a temporary CDK app for destroy.

    Args:
        config_path: Path to the factory.yaml file.
        output_dir: Directory to write the temporary app.

    Returns:
        Path to the generated app.py.
    """
    app_content = f"""#!/usr/bin/env python3
# Auto-generated CDK app for AWS API Factory destroy
# This file is temporary and will be regenerated on each destroy

import os
import sys
from pathlib import Path

# Add the project source to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import aws_cdk as cdk

from aws_api_factory.config import load_config, resolve_config

# Load and resolve configuration
config_path = Path("{config_path.absolute()}")
config = load_config(config_path)
resolved_config, _ = resolve_config(config)

# Get environment from CDK context
app = cdk.App()
env_name = app.node.try_get_context("env") or "dev"

# Create the factory stack reference for destroy
stack = cdk.Stack(
    app,
    f"{{resolved_config.project.name}}-{{env_name}}-stack",
    description=f"AWS API Factory stack for {{resolved_config.project.name}} ({{env_name}})",
)

app.synth()
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    app_path = output_dir / "app.py"
    app_path.write_text(app_content)
    return app_path


@click.command("destroy")
@click.argument("environment")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="factory.yaml",
    help="Path to factory.yaml configuration file.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt (dangerous!).",
)
@click.option(
    "--exclusively",
    is_flag=True,
    default=False,
    help="Only destroy resources in the stack, not dependencies.",
)
@click.option(
    "--profile",
    "-p",
    type=str,
    default=None,
    help="AWS profile to use for destroy (from ~/.aws/credentials).",
)
@click.pass_context
def destroy(
    ctx: click.Context,
    environment: str,
    config: str,
    force: bool,
    exclusively: bool,
    profile: str | None,
) -> None:
    """Destroy the API Factory stack.

    Tears down all resources in the specified ENVIRONMENT.
    Use with caution - this action cannot be undone.

    \b
    Examples:
        factory destroy dev
        factory destroy prod --config path/to/factory.yaml
        factory destroy dev --force

    \b
    WARNING: This will permanently delete all resources including:
    - API Gateway APIs
    - Lambda functions
    - DynamoDB tables (and all data!)
    - S3 buckets (and all files!)
    - App Runner services

    """
    verbose = get_verbose_context(ctx)
    config_path = Path(config)

    console.print()
    error_console.print("[error]⚠ DESTRUCTIVE OPERATION[/error]")
    console.print(f"[bold]Destroying environment:[/bold] [error]{environment}[/error]")
    console.print(f"[bold]Configuration:[/bold] [path]{config}[/path]")
    if profile:
        console.print(f"[bold]AWS Profile:[/bold] [cyan]{profile}[/cyan]")
    console.print()

    total_steps = 4
    current_step = 0

    # Step 1: Validate configuration
    current_step += 1
    print_step(current_step, total_steps, "Loading configuration...")

    try:
        factory_config, resolution_result = load_and_validate_config(
            config_path,
            environment=environment,
            resolve_defaults=True,
        )
    except ConfigNotFoundError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)
    except ConfigValidationError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)

    # Validate environment is configured
    if environment not in factory_config.project.envs:
        print_warning(
            f"Environment '{environment}' is not in configured environments: "
            f"{factory_config.project.envs}"
        )
        if not force:
            if not confirm_action(
                "This environment is not in your config. Continue anyway?"
            ):
                raise SystemExit(1)

    print_success("Configuration loaded")

    # Step 2: Check AWS credentials
    current_step += 1
    print_step(current_step, total_steps, "Checking AWS credentials...")

    if not check_aws_credentials():
        print_error(
            "AWS credentials not configured",
            "Configure AWS credentials using 'aws configure' or set "
            "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
        )
        raise SystemExit(5)
    else:
        print_success("AWS credentials available")

    # Step 3: Check CDK
    current_step += 1
    print_step(current_step, total_steps, "Checking CDK CLI...")

    try:
        cdk_path = find_cdk_executable()
        if verbose:
            print_info(f"Using CDK: {cdk_path}")
    except CLIError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)

    print_success("CDK CLI available")

    # Show what will be destroyed
    console.print()
    console.print(
        "[bold red]The following resources will be PERMANENTLY DELETED:[/bold red]"
    )
    console.print()
    print_resources_table(factory_config)
    console.print()

    # Require confirmation
    stack_name = get_stack_name(factory_config.project.name, environment)

    if not force:
        console.print("[bold yellow]This action cannot be undone![/bold yellow]")
        console.print()

        # Require typing the environment name to confirm
        if not confirm_action(
            f"Permanently destroy all resources in '{environment}'?",
            dangerous=True,
            require_input=environment,
        ):
            print_info("Destroy cancelled")
            raise SystemExit(0)

    console.print()

    # Step 4: Run CDK destroy
    current_step += 1
    print_step(current_step, total_steps, "Destroying resources...")

    # Find or generate CDK app
    try:
        app_path = find_cdk_app_path(config_path)
        cdk_working_dir = app_path.parent.parent
    except CLIError:
        temp_dir = config_path.parent / ".factory-temp"
        app_path = generate_temp_cdk_app(config_path, temp_dir)
        cdk_working_dir = config_path.parent
        if verbose:
            print_info(f"Generated temporary CDK app: {app_path}")

    # Build CDK destroy command
    cdk_args = [
        "destroy",
        stack_name,
        "--app",
        f"python {app_path}",
        "--context",
        f"env={environment}",
        "--context",
        f"config_path={config_path.absolute()}",
        "--force",  # CDK's --force skips the confirmation prompt
    ]

    if exclusively:
        cdk_args.append("--exclusively")

    if verbose:
        cdk_args.append("--verbose")

    try:
        result = run_cdk_command(
            cdk_args,
            cwd=cdk_working_dir,
            capture_output=True,
            show_progress=True,
            profile=profile,
        )

        if result.stdout:
            console.print(result.stdout)

    except AWSCredentialsError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)
    except CDKError as e:
        # Check if the stack doesn't exist (which is fine for destroy)
        if "does not exist" in str(e.suggestion).lower():
            print_warning(
                f"Stack '{stack_name}' does not exist or was already destroyed"
            )
        else:
            print_error(e.message, e.suggestion)
            raise SystemExit(e.exit_code)

    console.print()
    console.print("[bold green]✓ Stack destroyed successfully![/bold green]")
    console.print()
    console.print(f"All resources in environment '{environment}' have been deleted.")
    console.print()
    console.print("[bold]To redeploy:[/bold]")
    console.print(f"  [command]factory deploy {environment}[/command]")
    console.print()
