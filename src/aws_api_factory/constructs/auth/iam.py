# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""IAM authentication construct for AWS API Factory.

This module implements IAM authentication (SigV4 signing) for API Gateway
REST APIs. IAM authentication is best suited for:

- Service-to-service communication within AWS
- Internal microservices that have AWS credentials
- Backend integrations with other AWS services
- Machine-to-machine authentication

Clients must sign requests using AWS Signature Version 4 (SigV4).
This requires AWS credentials on the client side.

Example:
    >>> iam_auth = IamAuthConstruct(
    ...     stack, "IamAuth",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     api=rest_api.api,
    ... )
    >>> # The construct creates an example IAM policy for granting access

SigV4 Signing with Python (boto3):
    ```python
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
    import requests

    # Create and sign the request
    credentials = boto3.Session().get_credentials()
    request = AWSRequest(method='GET', url='https://api.example.com/orders')
    SigV4Auth(credentials, 'execute-api', 'us-east-1').add_auth(request)

    # Execute the signed request
    response = requests.get(
        request.url,
        headers=dict(request.headers)
    )
    ```

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig
    from aws_api_factory.constructs.outputs import OutputManager


class IamAuthConstruct(BaseConstruct):
    """CDK construct for IAM (SigV4) authentication.

    This construct configures IAM authorization for API Gateway methods
    and creates example IAM policies that can be attached to roles/users
    to grant API access.

    IAM authentication provides:
    - AWS-native authentication using existing credentials
    - Fine-grained access control via IAM policies
    - Automatic credential rotation (when using IAM roles)
    - Integration with AWS Organizations and cross-account access

    Attributes:
        api: Reference to the REST API.
        invoke_policy: IAM policy for invoking the API.

    Example:
        >>> construct = IamAuthConstruct(
        ...     stack, "IamAuth",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
        >>> # Grant a role permission to invoke the API
        >>> construct.grant_invoke(some_role)
    """

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
        """Initialize the IAM authentication construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults for configuration.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            api: The REST API to apply authentication to.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self.api = api
        self.invoke_policy: iam.ManagedPolicy | None = None
        self._invoke_policy_document: iam.PolicyDocument | None = None

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
        """Validate IAM authentication configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.api:
            errors.append("REST API is required for IAM authentication")

        return errors

    def _create_resources(self) -> None:
        """Create IAM policy resources for API access."""
        if not self.api:
            return

        # Create the invoke policy document
        self._create_invoke_policy()

        # Register outputs
        self._register_outputs()

    def _create_invoke_policy(self) -> None:
        """Create an IAM managed policy for API invocation."""
        policy_name = self.generate_resource_name("policy", "api-invoke")

        # Create policy document allowing execute-api:Invoke
        self._invoke_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    sid="AllowApiInvoke",
                    effect=iam.Effect.ALLOW,
                    actions=["execute-api:Invoke"],
                    resources=[
                        # Allow all methods and paths on this API
                        self.api.arn_for_execute_api("*", "/*", self.environment),
                    ],
                ),
            ],
        )

        self.invoke_policy = iam.ManagedPolicy(
            self,
            "InvokePolicy",
            managed_policy_name=policy_name,
            description=(
                f"Allows invoking {self.project_name} REST API ({self.environment})"
            ),
            document=self._invoke_policy_document,
        )

        self.apply_tags(self.invoke_policy)

    def _register_outputs(self) -> None:
        """Register IAM authentication outputs."""
        if self.invoke_policy:
            self.add_output(
                key="IamInvokePolicyArn",
                value=self.invoke_policy.managed_policy_arn,
                description="IAM policy ARN for API invocation (attach to roles/users)",
                export=True,
            )

        if self.api:
            self.add_output(
                key="IamApiExecuteArn",
                value=self.api.arn_for_execute_api("*", "/*", self.environment),
                description="API ARN pattern for IAM policies",
            )

    def get_invoke_policy(self) -> iam.ManagedPolicy | None:
        """Get the API invocation policy.

        Returns:
            The managed policy or None if not created.
        """
        return self.invoke_policy

    def get_invoke_policy_document(self) -> iam.PolicyDocument | None:
        """Get the API invocation policy document.

        This can be used to create inline policies or custom managed policies.

        Returns:
            The policy document or None if not created.
        """
        return self._invoke_policy_document

    def grant_invoke(self, grantee: iam.IGrantable) -> iam.Grant:
        """Grant a principal permission to invoke the API.

        This method attaches the invoke policy to the specified principal,
        allowing them to make SigV4-signed requests to the API.

        Args:
            grantee: The IAM principal to grant access to (role, user, etc.).

        Returns:
            The IAM Grant object.

        Example:
            >>> # Grant a Lambda function permission to call this API
            >>> iam_auth.grant_invoke(lambda_function)
            >>>
            >>> # Grant an IAM role permission
            >>> iam_auth.grant_invoke(role)
        """
        return iam.Grant.add_to_principal(
            grantee=grantee,
            actions=["execute-api:Invoke"],
            resource_arns=[
                self.api.arn_for_execute_api("*", "/*", self.environment),
            ],
        )

    def grant_invoke_path(
        self,
        grantee: iam.IGrantable,
        method: str,
        path: str,
    ) -> iam.Grant:
        """Grant a principal permission to invoke a specific API path.

        This method provides fine-grained access control by limiting
        the grant to specific HTTP methods and paths.

        Args:
            grantee: The IAM principal to grant access to.
            method: HTTP method (GET, POST, etc.) or "*" for all.
            path: API path (e.g., "/orders/*") or "*" for all.

        Returns:
            The IAM Grant object.

        Example:
            >>> # Grant read-only access to orders
            >>> iam_auth.grant_invoke_path(role, "GET", "/orders/*")
            >>>
            >>> # Grant full access to a specific resource
            >>> iam_auth.grant_invoke_path(role, "*", "/admin/*")
        """
        return iam.Grant.add_to_principal(
            grantee=grantee,
            actions=["execute-api:Invoke"],
            resource_arns=[
                self.api.arn_for_execute_api(method, path, self.environment),
            ],
        )

    @staticmethod
    def apply_iam_auth_to_method(method: apigw.Method) -> None:
        """Apply IAM authorization to an API Gateway method.

        Note: IAM authorization is typically set during method creation
        by passing authorization_type=AuthorizationType.IAM. This method
        is provided for documentation purposes.

        Args:
            method: The API Gateway method to protect.
        """
        # IAM auth is set at method creation time, not post-creation
        # This method documents the pattern
        pass


def create_iam_auth(
    scope: Construct,
    id: str,
    *,
    config: "FactoryConfig",
    profile_defaults: "ProfileDefaults",
    output_manager: "OutputManager",
    environment: str,
    api: apigw.RestApi,
) -> IamAuthConstruct:
    """Factory function to create IAM authentication.

    This is a convenience function that creates an IamAuthConstruct
    with sensible defaults.

    Args:
        scope: The CDK construct scope.
        id: The construct ID.
        config: The factory configuration.
        profile_defaults: Profile defaults for configuration.
        output_manager: Output manager for registering outputs.
        environment: Deployment environment name.
        api: The REST API to apply authentication to.

    Returns:
        The created IamAuthConstruct.

    Example:
        >>> auth = create_iam_auth(
        ...     stack, "Auth",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
    """
    return IamAuthConstruct(
        scope,
        id,
        config=config,
        profile_defaults=profile_defaults,
        output_manager=output_manager,
        environment=environment,
        api=api,
    )
