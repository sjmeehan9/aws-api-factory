# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Infrastructure package for AWS API Factory starter template.

This package contains the CDK app entry point and stack definitions.

Modules:
    app: CDK app entry point
    stacks: Stack definitions (customizable)

"""

from starter.infra.stacks.factory_stack import FactoryStack

__all__ = ["FactoryStack"]
