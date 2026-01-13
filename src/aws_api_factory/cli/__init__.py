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

Example:
    >>> # From command line:
    >>> factory init my-api
    >>> factory validate
    >>> factory deploy dev

"""

from aws_api_factory.cli.commands.deploy import deploy
from aws_api_factory.cli.commands.destroy import destroy
from aws_api_factory.cli.commands.init import init
from aws_api_factory.cli.commands.synth import synth
from aws_api_factory.cli.commands.validate import validate
from aws_api_factory.cli.main import cli, main
from aws_api_factory.cli.utils import (
    AWSCredentialsError,
    CDKError,
    CLIError,
    ConfigNotFoundError,
    ConfigValidationError,
    confirm_action,
    console,
    error_console,
    load_and_validate_config,
    print_config_panel,
    print_error,
    print_info,
    print_resolved_defaults,
    print_resources_table,
    print_step,
    print_success,
    print_warning,
    run_cdk_command,
)

__all__ = [
    # Main entry points
    "cli",
    "main",
    # Commands
    "init",
    "validate",
    "synth",
    "deploy",
    "destroy",
    # Exceptions
    "CLIError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "CDKError",
    "AWSCredentialsError",
    # Utilities
    "console",
    "error_console",
    "load_and_validate_config",
    "run_cdk_command",
    "confirm_action",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_step",
    "print_config_panel",
    "print_resolved_defaults",
    "print_resources_table",
]
