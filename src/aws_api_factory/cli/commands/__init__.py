# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""AWS API Factory CLI commands.

This package contains the individual command implementations:
- init: Scaffold new projects
- validate: Validate configuration
- synth: Synthesize CloudFormation
- deploy: Deploy to AWS
- destroy: Tear down stacks

"""

from aws_api_factory.cli.commands.deploy import deploy
from aws_api_factory.cli.commands.destroy import destroy
from aws_api_factory.cli.commands.init import init
from aws_api_factory.cli.commands.synth import synth
from aws_api_factory.cli.commands.validate import validate

__all__ = [
    "init",
    "validate",
    "synth",
    "deploy",
    "destroy",
]
