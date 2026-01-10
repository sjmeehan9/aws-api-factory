#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS CDK App entry point for AWS API Factory.

This is the main entry point for CDK synthesis and deployment.
It loads the factory.yaml configuration, resolves defaults, and
creates the FactoryStack for the specified environment.

Usage:
    cdk synth --context env=dev
    cdk deploy --context env=dev
    cdk destroy --context env=dev

The environment is specified via CDK context. Available environments
are defined in factory.yaml under project.envs.

"""

from __future__ import annotations

import sys
from pathlib import Path

from aws_cdk import App, Environment

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aws_api_factory.config import load_config, resolve_config
from aws_api_factory.constructs import FactoryStack


def main() -> None:
    """Main entry point for CDK app."""
    app = App()

    # Get environment from CDK context
    environment = app.node.try_get_context("env")
    if not environment:
        print("Error: Environment not specified.")
        print("Usage: cdk synth --context env=dev")
        print("       cdk deploy --context env=dev")
        sys.exit(1)

    # Find and load configuration
    config_path = project_root / "factory.yaml"
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Load and validate configuration
        config = load_config(config_path)

        # Validate environment is defined
        if environment not in config.project.envs:
            print(f"Error: Environment '{environment}' not found in factory.yaml")
            print(f"Available environments: {', '.join(config.project.envs)}")
            sys.exit(1)

        # Resolve defaults based on profile
        resolved_config = resolve_config(config)

        # Get AWS environment from context (optional)
        account = app.node.try_get_context("account")
        region = app.node.try_get_context("region")

        cdk_env = None
        if account and region:
            cdk_env = Environment(account=account, region=region)

        # Create the stack
        stack_id = f"{resolved_config.project.name.replace('-', '').title()}{environment.capitalize()}Stack"

        FactoryStack(
            app,
            stack_id,
            config=resolved_config,
            environment=environment,
            env=cdk_env,
        )

        # Synthesize the app
        app.synth()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
