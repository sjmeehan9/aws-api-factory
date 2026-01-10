#!/usr/bin/env python3
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
config_path = Path(
    "/Users/seanmeehan/Library/CloudStorage/OneDrive-Personal/Documents/Projects/aws-api-factory/starter/factory.yaml"
)
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
    f"{resolved_config.project.name}-{env_name}-stack",
    description=f"AWS API Factory stack for {resolved_config.project.name} ({env_name})",
    tags={
        "Project": resolved_config.project.name,
        "Environment": env_name,
        "Profile": resolved_config.profile.value,
        "ManagedBy": "aws-api-factory",
    },
)

app.synth()
