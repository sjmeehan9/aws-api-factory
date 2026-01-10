# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Factory synth command for CloudFormation synthesis.

This module implements the 'factory synth' command that generates
CloudFormation templates from factory.yaml configuration.

Example:
    $ factory synth
    $ factory synth --config path/to/factory.yaml
    $ factory synth --output cdk.out
    $ factory synth --show

"""

from __future__ import annotations

from pathlib import Path

import click

from aws_api_factory.cli.utils import (
    CDKError,
    CLIError,
    ConfigNotFoundError,
    ConfigValidationError,
    console,
    find_cdk_executable,
    get_project_root,
    get_verbose_context,
    load_and_validate_config,
    print_config_panel,
    print_error,
    print_info,
    print_step,
    print_success,
    print_warning,
    run_cdk_command,
)


def find_cdk_app_path(config_path: Path) -> Path:
    """Find the CDK app.py file for synthesis.

    Args:
        config_path: Path to the factory.yaml config file.

    Returns:
        Path to the CDK app.py file.

    Raises:
        CLIError: If no CDK app is found.
    """
    # Look in common locations relative to the config file
    config_dir = config_path.parent
    search_paths = [
        config_dir / "infra" / "app.py",
        config_dir / "cdk" / "app.py",
        config_dir / "app.py",
    ]

    for path in search_paths:
        if path.exists():
            return path

    # If no app.py found, we'll need to use a generated one
    raise CLIError(
        "CDK app.py not found",
        suggestion="Create an infra/app.py file that imports FactoryStack, or run "
        "'factory init' to generate the project structure.",
    )


def generate_temp_cdk_app(config_path: Path, output_dir: Path) -> Path:
    """Generate a temporary CDK app for synthesis.

    This is used when no infra/app.py exists - we generate a minimal
    CDK app that imports the factory constructs.

    Args:
        config_path: Path to the factory.yaml file.
        output_dir: Directory to write the temporary app.

    Returns:
        Path to the generated app.py.
    """
    app_content = f"""#!/usr/bin/env python3
# Auto-generated CDK app for AWS API Factory synthesis
# This file is temporary and will be regenerated on each synth

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
# For now, we create a minimal stack for synthesis testing
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

app.synth()
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    app_path = output_dir / "app.py"
    app_path.write_text(app_content)
    return app_path


@click.command("synth")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="factory.yaml",
    help="Path to factory.yaml configuration file.",
)
@click.option(
    "--environment",
    "-e",
    type=str,
    default="dev",
    help="Environment to synthesize for.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="cdk.out",
    help="Output directory for synthesized CloudFormation.",
)
@click.option(
    "--show",
    is_flag=True,
    default=False,
    help="Display the synthesized CloudFormation template.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress progress output.",
)
@click.pass_context
def synth(
    ctx: click.Context,
    config: str,
    environment: str,
    output: str,
    show: bool,
    quiet: bool,
) -> None:
    """Synthesize CloudFormation templates.

    Generates CloudFormation templates from the factory configuration
    without deploying to AWS.

    \b
    Examples:
        factory synth
        factory synth --config path/to/factory.yaml
        factory synth -e prod --output prod-cdk.out
        factory synth --show

    """
    verbose = get_verbose_context(ctx)
    config_path = Path(config)
    output_path = Path(output)

    if not quiet:
        console.print()
        console.print(
            f"[bold]Synthesizing CloudFormation:[/bold] [path]{config}[/path]"
        )
        console.print(f"[bold]Environment:[/bold] [cyan]{environment}[/cyan]")
        console.print()

    total_steps = 4 if show else 3
    current_step = 0

    # Step 1: Validate configuration
    current_step += 1
    if not quiet:
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
        print_warning(
            f"Environment '{environment}' not in configured environments: "
            f"{factory_config.project.envs}"
        )

    if not quiet:
        print_success("Configuration valid")

    # Step 2: Check CDK is available
    current_step += 1
    if not quiet:
        print_step(current_step, total_steps, "Checking CDK CLI...")

    try:
        cdk_path = find_cdk_executable()
        if verbose and not quiet:
            print_info(f"Using CDK: {cdk_path}")
    except CLIError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)

    if not quiet:
        print_success("CDK CLI available")

    # Step 3: Run CDK synth
    current_step += 1
    if not quiet:
        print_step(current_step, total_steps, "Running CDK synthesis...")

    # Find or generate CDK app
    try:
        app_path = find_cdk_app_path(config_path)
        cdk_working_dir = app_path.parent.parent  # infra/app.py -> project root
    except CLIError:
        # Generate a temporary app for synthesis
        temp_dir = config_path.parent / ".factory-temp"
        app_path = generate_temp_cdk_app(config_path, temp_dir)
        cdk_working_dir = config_path.parent
        if verbose and not quiet:
            print_info(f"Generated temporary CDK app: {app_path}")

    # Build CDK synth command
    cdk_args = [
        "synth",
        "--app",
        f"python {app_path}",
        "--output",
        str(output_path.absolute()),
        "--context",
        f"env={environment}",
        "--context",
        f"config_path={config_path.absolute()}",
    ]

    if verbose:
        cdk_args.append("--verbose")

    try:
        result = run_cdk_command(
            cdk_args,
            cwd=cdk_working_dir,
            capture_output=True,
            show_progress=not quiet,
        )

        if verbose and not quiet and result.stdout:
            console.print(result.stdout, style="dim")

    except CDKError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)

    if not quiet:
        print_success(f"CloudFormation synthesized to: {output_path}")

    # Step 4: Show template if requested
    if show:
        current_step += 1
        if not quiet:
            print_step(current_step, total_steps, "Displaying template...")

        stack_name = f"{factory_config.project.name}-{environment}-stack"
        template_path = output_path / f"{stack_name}.template.json"

        if template_path.exists():
            import json

            template_content = json.loads(template_path.read_text())
            from rich.panel import Panel
            from rich.syntax import Syntax

            syntax = Syntax(
                json.dumps(template_content, indent=2),
                "json",
                theme="monokai",
                line_numbers=True,
            )
            console.print(
                Panel(syntax, title=f"Template: {stack_name}", border_style="blue")
            )
        else:
            # Try to find any template file
            template_files = list(output_path.glob("*.template.json"))
            if template_files:
                template_path = template_files[0]
                import json

                template_content = json.loads(template_path.read_text())
                from rich.panel import Panel
                from rich.syntax import Syntax

                syntax = Syntax(
                    json.dumps(template_content, indent=2),
                    "json",
                    theme="monokai",
                    line_numbers=True,
                )
                console.print(
                    Panel(
                        syntax,
                        title=f"Template: {template_path.stem}",
                        border_style="blue",
                    )
                )
            else:
                print_warning(f"Template file not found in {output_path}")

    if not quiet:
        console.print()
        console.print("[bold green]✓ Synthesis complete![/bold green]")
        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print(
            f"  • Run [command]factory deploy {environment}[/command] to deploy"
        )
        console.print(f"  • Review templates in [path]{output_path}[/path]")
        console.print()
