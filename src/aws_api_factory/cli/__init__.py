# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS API Factory CLI.

This module provides the command-line interface for AWS API Factory,
including commands for project initialization, configuration validation,
CDK synthesis, deployment, and teardown.

Commands:
    factory init      - Scaffold a new project
    factory validate  - Validate configuration
    factory synth     - Synthesize CloudFormation
    factory deploy    - Deploy to AWS
    factory destroy   - Tear down stacks

"""

import click

from aws_api_factory import __version__


@click.group()
@click.version_option(version=__version__, prog_name="aws-api-factory")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """AWS API Factory - Config-driven API deployment on AWS.

    Transform your business logic into production-ready REST and GraphQL
    APIs using simple YAML configuration.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("project_name", required=False)
@click.option(
    "--template",
    "-t",
    type=click.Choice(["minimal", "full"]),
    default="minimal",
    help="Starter template to use.",
)
@click.pass_context
def init(ctx: click.Context, project_name: str | None, template: str) -> None:
    """Scaffold a new AWS API Factory project.

    Creates a new project directory with the starter template,
    including factory.yaml configuration and example services.
    """
    click.echo(f"Initializing new project: {project_name or 'current directory'}")
    click.echo(f"Template: {template}")
    # Implementation will be added in Component 1.4
    click.echo("Project initialization will be implemented in Component 1.4")


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="factory.yaml",
    help="Path to factory.yaml configuration file.",
)
@click.option(
    "--show-defaults",
    is_flag=True,
    default=False,
    help="Show resolved defaults for the selected profile.",
)
@click.pass_context
def validate(ctx: click.Context, config: str, show_defaults: bool) -> None:
    """Validate factory.yaml configuration.

    Loads the configuration file, validates against the schema,
    resolves profile defaults, and reports any issues.
    """
    click.echo(f"Validating configuration: {config}")
    if show_defaults:
        click.echo("Showing resolved defaults...")
    # Implementation will be added in Component 1.4
    click.echo("Configuration validation will be implemented in Component 1.4")


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="factory.yaml",
    help="Path to factory.yaml configuration file.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="cdk.out",
    help="Output directory for synthesized CloudFormation.",
)
@click.pass_context
def synth(ctx: click.Context, config: str, output: str) -> None:
    """Synthesize CloudFormation templates.

    Generates CloudFormation templates from the factory configuration
    without deploying to AWS.
    """
    click.echo(f"Synthesizing CloudFormation from: {config}")
    click.echo(f"Output directory: {output}")
    # Implementation will be added in Component 1.4
    click.echo("CDK synthesis will be implemented in Component 1.4")


@main.command()
@click.argument("environment")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
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
@click.pass_context
def deploy(
    ctx: click.Context,
    environment: str,
    config: str,
    require_approval: str,
    dry_run: bool,
) -> None:
    """Deploy the API Factory stack to AWS.

    Deploys the configured stack to the specified environment.
    Requires valid AWS credentials configured.
    """
    click.echo(f"Deploying to environment: {environment}")
    click.echo(f"Configuration: {config}")
    if dry_run:
        click.echo("Dry run mode - no changes will be made")
    # Implementation will be added in Component 1.4
    click.echo("Deployment will be implemented in Component 1.4")


@main.command()
@click.argument("environment")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="factory.yaml",
    help="Path to factory.yaml configuration file.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt.",
)
@click.pass_context
def destroy(
    ctx: click.Context,
    environment: str,
    config: str,
    force: bool,
) -> None:
    """Destroy the API Factory stack.

    Tears down all resources in the specified environment.
    Use with caution - this action cannot be undone.
    """
    if not force:
        click.confirm(
            f"Are you sure you want to destroy environment '{environment}'?",
            abort=True,
        )
    click.echo(f"Destroying environment: {environment}")
    # Implementation will be added in Component 1.4
    click.echo("Stack destruction will be implemented in Component 1.4")


if __name__ == "__main__":
    main()
