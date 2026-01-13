# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Output management for AWS API Factory stacks.

This module provides the OutputManager class that collects outputs from
all constructs and exports them as CloudFormation CfnOutputs. It also
supports exporting outputs to JSON files for CLI consumption.

Example:
    >>> from aws_api_factory.constructs.outputs import OutputManager
    >>> manager = OutputManager(stack)
    >>> manager.add("ApiEndpoint", api.url, "REST API endpoint")
    >>> manager.export_to_cfn()  # Creates CfnOutputs

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aws_cdk import CfnOutput

if TYPE_CHECKING:
    from aws_cdk import Stack


@dataclass
class OutputEntry:
    """A single output entry to be exported.

    Attributes:
        key: The unique output key.
        value: The output value (e.g., URL, ARN).
        description: Human-readable description.
        export_name: CloudFormation export name for cross-stack references.
        category: Category for grouping outputs (e.g., "api", "compute").
    """

    key: str
    value: str
    description: str
    export_name: str | None = None
    category: str = "general"


class OutputManager:
    """Manages stack outputs for AWS API Factory.

    The OutputManager collects outputs from all constructs during stack
    synthesis and exports them as CloudFormation CfnOutputs. It also
    provides methods to export outputs to JSON files for CLI consumption
    and to retrieve outputs programmatically.

    Outputs are organized by category (api, compute, data, auth) for
    better organization in the CloudFormation console and CLI output.

    Attributes:
        stack: The CDK stack to add outputs to.
        project_name: The project name for namespacing.
        environment: The deployment environment.

    Example:
        >>> manager = OutputManager(stack, "my-api", "dev")
        >>> manager.add(
        ...     key="OrdersApiEndpoint",
        ...     value="https://xxx.execute-api.us-east-1.amazonaws.com/prod",
        ...     description="REST API endpoint for Orders service",
        ...     category="api",
        ... )
        >>> manager.export_to_cfn()
    """

    def __init__(
        self,
        stack: Stack,
        project_name: str,
        environment: str,
    ) -> None:
        """Initialize the output manager.

        Args:
            stack: The CDK stack to add outputs to.
            project_name: The project name for namespacing.
            environment: The deployment environment.
        """
        self.stack = stack
        self.project_name = project_name
        self.environment = environment
        self._outputs: dict[str, OutputEntry] = {}
        self._exported = False

    def add(
        self,
        key: str,
        value: str,
        description: str,
        *,
        export_name: str | None = None,
        category: str = "general",
    ) -> None:
        """Add an output to be exported.

        Args:
            key: The unique output key (e.g., "ApiEndpoint").
            value: The output value (e.g., the API URL).
            description: A human-readable description of the output.
            export_name: Optional CloudFormation export name for cross-stack refs.
            category: Category for grouping (api, compute, data, auth, general).

        Raises:
            ValueError: If the key already exists or outputs have been exported.

        Example:
            >>> manager.add(
            ...     key="LambdaFunctionArn",
            ...     value=function.function_arn,
            ...     description="Orders Lambda function ARN",
            ...     category="compute",
            ... )
        """
        if self._exported:
            raise ValueError(
                f"Cannot add output '{key}': outputs have already been exported. "
                "Add all outputs before calling export_to_cfn()."
            )

        if key in self._outputs:
            raise ValueError(
                f"Output key '{key}' already exists. "
                "Each output key must be unique within the stack."
            )

        self._outputs[key] = OutputEntry(
            key=key,
            value=value,
            description=description,
            export_name=export_name,
            category=category,
        )

    def get(self, key: str) -> OutputEntry | None:
        """Get an output entry by key.

        Args:
            key: The output key to retrieve.

        Returns:
            The OutputEntry if found, None otherwise.
        """
        return self._outputs.get(key)

    def get_all(self) -> dict[str, OutputEntry]:
        """Get all registered outputs.

        Returns:
            Dictionary of all output entries keyed by their key.
        """
        return dict(self._outputs)

    def get_by_category(self, category: str) -> dict[str, OutputEntry]:
        """Get all outputs for a specific category.

        Args:
            category: The category to filter by.

        Returns:
            Dictionary of output entries in the specified category.
        """
        return {
            key: entry
            for key, entry in self._outputs.items()
            if entry.category == category
        }

    def get_categories(self) -> list[str]:
        """Get all unique categories.

        Returns:
            List of unique category names.
        """
        return sorted(set(entry.category for entry in self._outputs.values()))

    def export_to_cfn(self) -> None:
        """Export all outputs as CloudFormation CfnOutputs.

        This method creates CfnOutput resources for each registered output.
        It should be called once after all outputs have been added.

        The outputs are grouped by category in the CloudFormation template
        for better organization.

        Raises:
            ValueError: If export_to_cfn() has already been called.
        """
        if self._exported:
            raise ValueError(
                "Outputs have already been exported. "
                "export_to_cfn() should only be called once."
            )

        # Sort outputs by category for organized output
        sorted_outputs = sorted(
            self._outputs.values(),
            key=lambda x: (x.category, x.key),
        )

        for entry in sorted_outputs:
            output_id = f"{entry.category.capitalize()}{entry.key}"

            CfnOutput(
                self.stack,
                output_id,
                value=entry.value,
                description=entry.description,
                export_name=entry.export_name,
            )

        self._exported = True

    def export_to_json(self, output_path: Path | str) -> None:
        """Export all outputs to a JSON file.

        This creates a JSON file with all outputs organized by category.
        Useful for CLI tools and scripts that need to consume stack outputs.

        Args:
            output_path: Path to the output JSON file.

        Example:
            >>> manager.export_to_json("outputs.json")
            # Creates: {"api": {"ApiEndpoint": {"value": "...", ...}}, ...}
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Organize outputs by category
        categorized: dict[str, dict[str, Any]] = {}
        for entry in self._outputs.values():
            if entry.category not in categorized:
                categorized[entry.category] = {}
            categorized[entry.category][entry.key] = {
                "value": entry.value,
                "description": entry.description,
                "export_name": entry.export_name,
            }

        # Add metadata
        output_data = {
            "metadata": {
                "project": self.project_name,
                "environment": self.environment,
                "output_count": len(self._outputs),
            },
            "outputs": categorized,
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Convert all outputs to a dictionary.

        Returns:
            Dictionary representation of all outputs organized by category.
        """
        categorized: dict[str, dict[str, Any]] = {}
        for entry in self._outputs.values():
            if entry.category not in categorized:
                categorized[entry.category] = {}
            categorized[entry.category][entry.key] = {
                "value": entry.value,
                "description": entry.description,
                "export_name": entry.export_name,
            }
        return categorized

    def to_flat_dict(self) -> dict[str, str]:
        """Convert outputs to a flat key-value dictionary.

        Returns:
            Dictionary of output key to value (no metadata).
        """
        return {key: entry.value for key, entry in self._outputs.items()}

    def __len__(self) -> int:
        """Return the number of registered outputs."""
        return len(self._outputs)

    def __contains__(self, key: str) -> bool:
        """Check if an output key exists."""
        return key in self._outputs

    def summary(self) -> str:
        """Generate a human-readable summary of outputs.

        Returns:
            Multi-line string summarizing all outputs by category.
        """
        if not self._outputs:
            return "No outputs registered."

        lines = [
            f"Stack Outputs ({len(self._outputs)} total):",
            f"  Project: {self.project_name}",
            f"  Environment: {self.environment}",
            "",
        ]

        for category in self.get_categories():
            lines.append(f"  [{category.upper()}]")
            for entry in self.get_by_category(category).values():
                export_marker = " (exported)" if entry.export_name else ""
                lines.append(f"    {entry.key}: {entry.description}{export_marker}")
            lines.append("")

        return "\n".join(lines)
