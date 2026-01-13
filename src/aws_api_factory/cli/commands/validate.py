# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Factory validate command for configuration validation.

This module implements the 'factory validate' command that validates
factory.yaml configuration files and shows resolved defaults.

Example:
    $ factory validate
    $ factory validate --config path/to/factory.yaml
    $ factory validate --show-defaults
    $ factory validate --output resolved.yaml

"""

from __future__ import annotations

from pathlib import Path

import click

from aws_api_factory.cli.utils import (
    ConfigNotFoundError,
    ConfigValidationError,
    console,
    format_yaml_output,
    get_verbose_context,
    load_and_validate_config,
    print_config_panel,
    print_error,
    print_resolved_defaults,
    print_resources_table,
    print_success,
    print_warning,
    print_yaml,
)


@click.command("validate")
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
    default=None,
    help="Environment for environment-specific config overrides.",
)
@click.option(
    "--show-defaults",
    is_flag=True,
    default=False,
    help="Show resolved defaults for the selected profile.",
)
@click.option(
    "--show-resources",
    is_flag=True,
    default=False,
    help="Show resources that will be created.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write resolved configuration to file.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format for resolved configuration.",
)
@click.pass_context
def validate(
    ctx: click.Context,
    config: str,
    environment: str | None,
    show_defaults: bool,
    show_resources: bool,
    output: str | None,
    output_format: str,
) -> None:
    """Validate factory.yaml configuration.

    Loads the configuration file, validates against the schema,
    resolves profile defaults, and reports any issues.

    \b
    Examples:
        factory validate
        factory validate --config path/to/factory.yaml
        factory validate --show-defaults
        factory validate --show-resources
        factory validate --output resolved.yaml
        factory validate -e prod --show-defaults

    """
    verbose = get_verbose_context(ctx)

    console.print()
    console.print(f"[bold]Validating configuration:[/bold] [path]{config}[/path]")
    if environment:
        console.print(f"[bold]Environment:[/bold] [cyan]{environment}[/cyan]")
    console.print()

    # Load and validate configuration
    try:
        factory_config, resolution_result = load_and_validate_config(
            config,
            environment=environment,
            resolve_defaults=True,
        )
    except ConfigNotFoundError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)
    except ConfigValidationError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise SystemExit(1)

    # Show success message
    print_success("Configuration is valid!")
    console.print()

    # Show configuration summary
    print_config_panel(factory_config)
    console.print()

    # Show resolved defaults if requested
    if show_defaults and resolution_result:
        print_resolved_defaults(resolution_result)
        console.print()

        # Show warnings from resolution
        if resolution_result.warnings:
            for warning in resolution_result.warnings:
                print_warning(warning)
            console.print()

    # Show resources if requested
    if show_resources:
        print_resources_table(factory_config)
        console.print()

    # Write output if requested
    if output:
        output_path = Path(output)

        # Convert config to dictionary for serialization
        config_dict = factory_config.model_dump(mode="json", exclude_none=True)

        if output_format == "yaml":
            output_content = format_yaml_output(config_dict)
        else:
            import json

            output_content = json.dumps(config_dict, indent=2)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_content)
        print_success(f"Resolved configuration written to: {output_path}")

    # Print helpful next steps
    console.print("[bold]Next steps:[/bold]")
    console.print("  • Run [command]factory synth[/command] to generate CloudFormation")
    console.print("  • Run [command]factory deploy <env>[/command] to deploy to AWS")
    console.print()
