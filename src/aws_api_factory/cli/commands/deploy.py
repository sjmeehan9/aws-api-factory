# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Factory deploy command for deploying to AWS.

This module implements the 'factory deploy' command that deploys
factory stacks to AWS using CDK.

Example:
    $ factory deploy dev
    $ factory deploy prod --config path/to/factory.yaml
    $ factory deploy prod --require-approval never
    $ factory deploy dev --outputs-file outputs.json

"""

from __future__ import annotations

import json
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
    find_cdk_executable,
    get_stack_name,
    get_verbose_context,
    load_and_validate_config,
    print_config_panel,
    print_error,
    print_info,
    print_resources_table,
    print_step,
    print_success,
    print_warning,
    run_cdk_command,
    save_outputs_to_file,
)


def find_cdk_app_path(config_path: Path) -> Path:
    """Find the CDK app.py file for deployment.

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
    """Generate a temporary CDK app for deployment.

    Args:
        config_path: Path to the factory.yaml file.
        output_dir: Directory to write the temporary app.

    Returns:
        Path to the generated app.py.
    """
    app_content = f"""#!/usr/bin/env python3
# Auto-generated CDK app for AWS API Factory deployment
# This file is temporary and will be regenerated on each deploy

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

# Create the factory stack
# Note: FactoryStack will be implemented in Component 1.5
# For now, we create a minimal stack for deployment testing
stack = cdk.Stack(
    app,
    f"{{resolved_config.project.name}}-{{env_name}}-stack",
    description=f"AWS API Factory stack for {{resolved_config.project.name}} ({{env_name}})",
    tags={{
        "Project": resolved_config.project.name,
        "Environment": env_name,
        "Profile": resolved_config.profile.value,
        "ManagedBy": "aws-api-factory",
    }},
)

# Add outputs
cdk.CfnOutput(
    stack,
    "ProjectName",
    value=resolved_config.project.name,
    description="Project name",
)

cdk.CfnOutput(
    stack,
    "Environment",
    value=env_name,
    description="Deployment environment",
)

cdk.CfnOutput(
    stack,
    "Profile",
    value=resolved_config.profile.value,
    description="Factory profile",
)

app.synth()
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    app_path = output_dir / "app.py"
    app_path.write_text(app_content)
    return app_path


def parse_cdk_outputs(output: str) -> dict[str, str]:
    """Parse CDK deploy outputs from stdout.

    Args:
        output: CDK deploy stdout.

    Returns:
        Dictionary of output key -> value.
    """
    outputs: dict[str, str] = {}

    # Look for "Outputs:" section
    in_outputs = False
    for line in output.split("\n"):
        if "Outputs:" in line:
            in_outputs = True
            continue

        if in_outputs:
            # Output format: "StackName.OutputKey = value"
            if " = " in line and "." in line:
                try:
                    key_part, value = line.split(" = ", 1)
                    _, key = key_part.rsplit(".", 1)
                    outputs[key.strip()] = value.strip()
                except ValueError:
                    continue
            elif line.strip() == "" or not line.startswith(" "):
                in_outputs = False

    return outputs


@click.command("deploy")
@click.argument("environment")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="factory.yaml",
    help="Path to factory.yaml configuration file.",
)
@click.option(
    "--require-approval",
    type=click.Choice(["never", "any-change", "broadening"]),
    default="broadening",
    help="When to require approval for changes.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be deployed without deploying.",
)
@click.option(
    "--outputs-file",
    type=click.Path(),
    default=None,
    help="Save stack outputs to JSON file.",
)
@click.option(
    "--no-rollback",
    is_flag=True,
    default=False,
    help="Disable automatic rollback on failure.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Skip confirmation prompts.",
)
@click.pass_context
def deploy(
    ctx: click.Context,
    environment: str,
    config: str,
    require_approval: str,
    dry_run: bool,
    outputs_file: str | None,
    no_rollback: bool,
    force: bool,
) -> None:
    """Deploy the API Factory stack to AWS.

    Deploys the configured stack to the specified ENVIRONMENT.
    Requires valid AWS credentials configured.

    \b
    Examples:
        factory deploy dev
        factory deploy prod --config path/to/factory.yaml
        factory deploy prod --require-approval never
        factory deploy dev --outputs-file outputs.json
        factory deploy staging --dry-run

    """
    verbose = get_verbose_context(ctx)
    config_path = Path(config)

    console.print()
    console.print(f"[bold]Deploying to AWS:[/bold] [cyan]{environment}[/cyan]")
    console.print(f"[bold]Configuration:[/bold] [path]{config}[/path]")
    if dry_run:
        console.print("[warning]DRY RUN MODE - no changes will be made[/warning]")
    console.print()

    total_steps = 5 if not dry_run else 4
    current_step = 0

    # Step 1: Validate configuration
    current_step += 1
    print_step(current_step, total_steps, "Validating configuration...")

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
        print_error(
            f"Environment '{environment}' is not configured",
            suggestion=f"Configure environment in factory.yaml under project.envs. "
            f"Available: {factory_config.project.envs}",
        )
        raise SystemExit(1)

    print_success("Configuration valid")

    # Step 2: Check AWS credentials
    current_step += 1
    print_step(current_step, total_steps, "Checking AWS credentials...")

    if not check_aws_credentials():
        print_warning("AWS credentials may not be configured")
        if not force:
            if not confirm_action(
                "AWS credentials appear to be missing. Continue anyway?"
            ):
                raise SystemExit(1)
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

    # Show what will be deployed
    console.print()
    print_config_panel(factory_config, title=f"Deploying to {environment}")
    print_resources_table(factory_config)
    console.print()

    # Confirm deployment
    if not force and not dry_run:
        stack_name = get_stack_name(factory_config.project.name, environment)
        if not confirm_action(
            f"Deploy stack '{stack_name}' to environment '{environment}'?"
        ):
            print_info("Deployment cancelled")
            raise SystemExit(0)

    # Step 4: Run CDK deploy
    current_step += 1
    action = "Preparing deployment" if dry_run else "Deploying to AWS"
    print_step(current_step, total_steps, f"{action}...")

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

    # Build CDK deploy command
    stack_name = get_stack_name(factory_config.project.name, environment)
    cdk_args = [
        "deploy" if not dry_run else "diff",
        stack_name,
        "--app",
        f"python {app_path}",
        "--context",
        f"env={environment}",
        "--context",
        f"config_path={config_path.absolute()}",
        "--require-approval",
        require_approval,
    ]

    if not dry_run:
        cdk_args.append("--outputs-file")
        cdk_args.append(str((cdk_working_dir / "cdk-outputs.json").absolute()))

        if no_rollback:
            cdk_args.append("--no-rollback")

        # Auto-approve for CI environments or when force is set
        if force:
            cdk_args.append("--require-approval")
            cdk_args.append("never")

    if verbose:
        cdk_args.append("--verbose")

    try:
        result = run_cdk_command(
            cdk_args,
            cwd=cdk_working_dir,
            capture_output=True,
            show_progress=True,
        )

        if result.stdout:
            console.print(result.stdout)

    except AWSCredentialsError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)
    except CDKError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)

    if dry_run:
        print_success("Dry run complete - no changes made")
        console.print()
        console.print("[bold]To deploy for real, run without --dry-run:[/bold]")
        console.print(f"  [command]factory deploy {environment}[/command]")
        console.print()
        return

    # Step 5: Collect and display outputs
    current_step += 1
    print_step(current_step, total_steps, "Collecting deployment outputs...")

    outputs: dict[str, str] = {}

    # Try to read outputs from CDK outputs file
    cdk_outputs_file = cdk_working_dir / "cdk-outputs.json"
    if cdk_outputs_file.exists():
        try:
            all_outputs = json.loads(cdk_outputs_file.read_text())
            # CDK outputs format: {"StackName": {"OutputKey": "OutputValue"}}
            if stack_name in all_outputs:
                outputs = all_outputs[stack_name]
        except Exception as e:
            if verbose:
                print_warning(f"Could not read CDK outputs: {e}")

    # Also try to parse from stdout
    if not outputs and result.stdout:
        outputs = parse_cdk_outputs(result.stdout)

    if outputs:
        from rich.table import Table

        table = Table(title="Stack Outputs", show_header=True, header_style="bold")
        table.add_column("Output", style="cyan")
        table.add_column("Value", style="green")

        for key, value in outputs.items():
            table.add_row(key, value)

        console.print(table)
        console.print()

    # Save outputs if requested
    if outputs_file and outputs:
        save_outputs_to_file(outputs, Path(outputs_file))

    console.print()
    console.print("[bold green]✓ Deployment complete![/bold green]")
    console.print()

    # Print helpful info
    if "RestApiUrl" in outputs:
        console.print(f"[bold]REST API URL:[/bold] {outputs['RestApiUrl']}")
    if "GraphQLUrl" in outputs:
        console.print(f"[bold]GraphQL URL:[/bold] {outputs['GraphQLUrl']}")

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  • Test your API endpoints")
    console.print(
        f"  • Run [command]factory destroy {environment}[/command] to tear down"
    )
    console.print()
