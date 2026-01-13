# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS API Factory CLI main entry point.

This module defines the main CLI group and registers all commands.
It handles global options like --verbose, --config-path, and --no-color.

Example:
    $ factory --help
    $ factory --version
    $ factory init my-project
    $ factory validate
    $ factory deploy dev

"""

from __future__ import annotations

import sys

import click
from rich.console import Console

from aws_api_factory import __version__
from aws_api_factory.cli.commands.deploy import deploy
from aws_api_factory.cli.commands.destroy import destroy
from aws_api_factory.cli.commands.init import init
from aws_api_factory.cli.commands.synth import synth
from aws_api_factory.cli.commands.validate import validate


class RichGroup(click.Group):
    """Custom Click Group with enhanced help formatting."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format the help text with Rich styling."""
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)


@click.group(cls=RichGroup)
@click.version_option(version=__version__, prog_name="aws-api-factory")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output for debugging.",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    envvar="NO_COLOR",
    help="Disable colored output.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, no_color: bool) -> None:
    """AWS API Factory - Config-driven API deployment on AWS.

    Transform your business logic into production-ready REST and GraphQL
    APIs using simple YAML configuration.

    \b
    Quick Start:
        factory init my-api      Create a new project
        factory validate         Check configuration
        factory synth            Generate CloudFormation
        factory deploy dev       Deploy to AWS

    \b
    For more information on a specific command:
        factory <command> --help

    \b
    Documentation: https://github.com/seanmeehan/aws-api-factory
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store global options in context
    ctx.obj["verbose"] = verbose
    ctx.obj["no_color"] = no_color

    # Configure Rich console for no-color mode
    if no_color:
        Console(force_terminal=False, no_color=True)


# Register commands
cli.add_command(init)
cli.add_command(validate)
cli.add_command(synth)
cli.add_command(deploy)
cli.add_command(destroy)


def main() -> None:
    """Main entry point for the CLI.

    This function is called when the user runs `factory` from the command line.
    It handles keyboard interrupts gracefully and sets appropriate exit codes.
    """
    try:
        cli(obj={})
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(130)  # Standard exit code for SIGINT
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes
        raise
    except Exception as e:
        # Catch any unexpected exceptions
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
