# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""API Key authentication construct for AWS API Factory.

This module implements API Key authentication with usage plans and rate
limiting for API Gateway REST APIs. API keys are suitable for:

- Partner/third-party API access with usage tracking
- Rate limiting and quota enforcement
- Internal service authentication (simple cases)

API keys should NOT be used for end-user authentication. For user-facing
applications, use Cognito authentication instead.

Example:
    >>> api_key_auth = ApiKeyAuthConstruct(
    ...     stack, "ApiKeyAuth",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     api=rest_api.api,
    ... )
    >>> # API key is automatically associated with the API stage

Key Rotation Strategy:
    API keys can be rotated by:
    1. Creating a new API key via AWS Console or CLI
    2. Adding the new key to the usage plan
    3. Distributing the new key to consumers
    4. Removing the old key after migration period

    For automated rotation, consider using AWS Secrets Manager with
    a Lambda rotation function.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_apigateway as apigw
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig
    from aws_api_factory.constructs.outputs import OutputManager


class ApiKeyAuthConstruct(BaseConstruct):
    """CDK construct for API Key authentication with usage plans.

    This construct creates:
    - API key(s) for authentication
    - Usage plan with rate limits based on profile
    - Association between usage plan and API stage

    Profile-based defaults:
    - Minimal: 1,000 requests/day, 100 requests/second burst
    - Scalable: 10,000 requests/day, 1,000 requests/second burst

    Attributes:
        api_key: The created API key.
        usage_plan: The usage plan with rate limits.
        api: Reference to the REST API.

    Example:
        >>> construct = ApiKeyAuthConstruct(
        ...     stack, "ApiKeyAuth",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
        >>> print(construct.api_key.key_id)
    """

    # Profile-based rate limits (requests per day)
    MINIMAL_DAILY_QUOTA = 1000
    SCALABLE_DAILY_QUOTA = 10000

    # Profile-based burst limits (requests per second)
    MINIMAL_BURST_LIMIT = 100
    SCALABLE_BURST_LIMIT = 1000

    # Profile-based rate limits (requests per second)
    MINIMAL_RATE_LIMIT = 10
    SCALABLE_RATE_LIMIT = 100

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: FactoryConfig,
        profile_defaults: ProfileDefaults,
        output_manager: OutputManager,
        environment: str,
        api: apigw.RestApi,
        **kwargs: Any,
    ) -> None:
        """Initialize the API Key authentication construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults for rate limits.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            api: The REST API to apply authentication to.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self.api = api
        self.api_key: apigw.ApiKey | None = None
        self.usage_plan: apigw.UsagePlan | None = None

        super().__init__(
            scope,
            id,
            config=config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment=environment,
            **kwargs,
        )

    def validate_config(self) -> list[str]:
        """Validate API Key authentication configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.api:
            errors.append("REST API is required for API Key authentication")

        return errors

    def _create_resources(self) -> None:
        """Create API key and usage plan resources."""
        if not self.api:
            return

        # Create the API key
        self._create_api_key()

        # Create the usage plan
        self._create_usage_plan()

        # Register outputs
        self._register_outputs()

    def _create_api_key(self) -> None:
        """Create the API key resource."""
        key_name = self.generate_resource_name("apikey", "default")

        self.api_key = apigw.ApiKey(
            self,
            "ApiKey",
            api_key_name=key_name,
            description=f"API key for {self.project_name} ({self.environment})",
            enabled=True,
        )

        self.apply_tags(self.api_key)

    def _create_usage_plan(self) -> None:
        """Create the usage plan with rate limits."""
        if not self.api_key:
            return

        plan_name = self.generate_resource_name("usageplan", "default")

        # Determine rate limits based on profile
        from aws_api_factory.config.models import ProfileEnum

        is_scalable = self.config.profile == ProfileEnum.SCALABLE

        daily_quota = (
            self.SCALABLE_DAILY_QUOTA if is_scalable else self.MINIMAL_DAILY_QUOTA
        )
        burst_limit = (
            self.SCALABLE_BURST_LIMIT if is_scalable else self.MINIMAL_BURST_LIMIT
        )
        rate_limit = (
            self.SCALABLE_RATE_LIMIT if is_scalable else self.MINIMAL_RATE_LIMIT
        )

        self.usage_plan = apigw.UsagePlan(
            self,
            "UsagePlan",
            name=plan_name,
            description=f"Usage plan for {self.project_name} ({self.environment})",
            api_stages=[
                apigw.UsagePlanPerApiStage(
                    api=self.api,
                    stage=self.api.deployment_stage,
                )
            ],
            throttle=apigw.ThrottleSettings(
                burst_limit=burst_limit,
                rate_limit=rate_limit,
            ),
            quota=apigw.QuotaSettings(
                limit=daily_quota,
                period=apigw.Period.DAY,
            ),
        )

        # Associate the API key with the usage plan
        self.usage_plan.add_api_key(self.api_key)

        self.apply_tags(self.usage_plan)

    def _register_outputs(self) -> None:
        """Register API key outputs."""
        if self.api_key:
            self.add_output(
                key="ApiKeyId",
                value=self.api_key.key_id,
                description="API Key ID (use AWS CLI to retrieve the key value)",
            )
            # Note: We don't output the actual API key value for security.
            # Users should retrieve it via: aws apigateway get-api-key --api-key <id> --include-value

        if self.usage_plan:
            self.add_output(
                key="UsagePlanId",
                value=self.usage_plan.usage_plan_id,
                description="Usage Plan ID for API key management",
            )

    def get_api_key(self) -> apigw.ApiKey | None:
        """Get the created API key.

        Returns:
            The API key or None if not created.
        """
        return self.api_key

    def get_usage_plan(self) -> apigw.UsagePlan | None:
        """Get the created usage plan.

        Returns:
            The usage plan or None if not created.
        """
        return self.usage_plan

    def require_api_key(self, method: apigw.Method) -> None:
        """Mark an API Gateway method as requiring an API key.

        Note: This is handled automatically by the RestApiConstruct
        when the route auth is set to 'api_key'. This method is provided
        for programmatic use cases.

        Args:
            method: The API Gateway method to protect.
        """
        # API key requirement is set during method creation
        # This method is for documentation and potential future use
        pass


def create_api_key_auth(
    scope: Construct,
    id: str,
    *,
    config: "FactoryConfig",
    profile_defaults: "ProfileDefaults",
    output_manager: "OutputManager",
    environment: str,
    api: apigw.RestApi,
) -> ApiKeyAuthConstruct:
    """Factory function to create API Key authentication.

    This is a convenience function that creates an ApiKeyAuthConstruct
    with sensible defaults.

    Args:
        scope: The CDK construct scope.
        id: The construct ID.
        config: The factory configuration.
        profile_defaults: Profile defaults for rate limits.
        output_manager: Output manager for registering outputs.
        environment: Deployment environment name.
        api: The REST API to apply authentication to.

    Returns:
        The created ApiKeyAuthConstruct.

    Example:
        >>> auth = create_api_key_auth(
        ...     stack, "Auth",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
    """
    return ApiKeyAuthConstruct(
        scope,
        id,
        config=config,
        profile_defaults=profile_defaults,
        output_manager=output_manager,
        environment=environment,
        api=api,
    )
