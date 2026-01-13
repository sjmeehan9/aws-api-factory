# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Cognito authentication construct for AWS API Factory.

This module implements Cognito User Pool authentication with JWT
authorization for API Gateway REST APIs. Cognito is the recommended
authentication method for user-facing applications because it provides:

- User registration and sign-in flows
- Password policies and account recovery
- MFA support (SMS, TOTP)
- Social identity provider integration (Google, Facebook, etc.)
- JWT tokens for stateless authentication
- Built-in user management console

Example:
    >>> cognito_auth = CognitoAuthConstruct(
    ...     stack, "CognitoAuth",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     api=rest_api.api,
    ... )
    >>> # Get the User Pool ID and Client ID for your frontend
    >>> print(cognito_auth.user_pool.user_pool_id)
    >>> print(cognito_auth.user_pool_client.user_pool_client_id)

Frontend Integration:
    After deployment, use the Cognito hosted UI or AWS Amplify to
    implement authentication in your frontend. The JWT token from
    Cognito should be passed in the Authorization header:

    ```javascript
    fetch(apiUrl, {
        headers: {
            'Authorization': `Bearer ${jwtToken}`
        }
    })
    ```

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cognito as cognito
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig
    from aws_api_factory.constructs.outputs import OutputManager


class CognitoAuthConstruct(BaseConstruct):
    """CDK construct for Cognito User Pool authentication.

    This construct creates:
    - Cognito User Pool with email sign-in
    - User Pool Client for application integration
    - Cognito Authorizer for API Gateway
    - Optional: Custom domain for hosted UI (Scalable profile)

    Profile-based settings:
    - Minimal: Basic password policy, no MFA, standard security
    - Scalable: Strong password policy, optional MFA, advanced security

    Attributes:
        user_pool: The Cognito User Pool.
        user_pool_client: The User Pool Client for app integration.
        authorizer: The Cognito Authorizer for API Gateway.
        api: Reference to the REST API.

    Example:
        >>> construct = CognitoAuthConstruct(
        ...     stack, "CognitoAuth",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
        >>> # Apply authorizer to methods
        >>> method.grant_method_response()
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
        existing_user_pool_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Cognito authentication construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults for security settings.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            api: The REST API to apply authentication to.
            existing_user_pool_id: Optional existing User Pool ID to use.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self.api = api
        self._existing_user_pool_id = existing_user_pool_id
        self.user_pool: cognito.UserPool | None = None
        self.user_pool_client: cognito.UserPoolClient | None = None
        self.authorizer: apigw.CognitoUserPoolsAuthorizer | None = None

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
        """Validate Cognito authentication configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.api:
            errors.append("REST API is required for Cognito authentication")

        # Check Cognito config in REST API settings
        rest_config = self.config.apis.rest
        if rest_config.cognito:
            cognito_config = rest_config.cognito
            if cognito_config.user_pool_id and cognito_config.create_user_pool:
                errors.append(
                    "Cannot specify both 'user_pool_id' and 'create_user_pool: true'"
                )

        return errors

    def _create_resources(self) -> None:
        """Create Cognito User Pool and authorizer resources."""
        if not self.api:
            return

        # Check if we should use an existing User Pool
        rest_config = self.config.apis.rest
        cognito_config = rest_config.cognito

        if cognito_config and cognito_config.user_pool_id:
            # Import existing User Pool
            self._import_existing_user_pool(cognito_config.user_pool_id)
        else:
            # Create new User Pool
            self._create_user_pool()
            self._create_user_pool_client()

        # Create the authorizer
        self._create_authorizer()

        # Register outputs
        self._register_outputs()

    def _create_user_pool(self) -> None:
        """Create a new Cognito User Pool."""
        pool_name = self.generate_resource_name("userpool", "users")

        # Determine settings based on profile
        from aws_api_factory.config.models import ProfileEnum

        is_scalable = self.config.profile == ProfileEnum.SCALABLE

        # Password policy - stronger for scalable
        if is_scalable:
            password_policy = cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(3),
            )
        else:
            password_policy = cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
                temp_password_validity=Duration.days(7),
            )

        # MFA configuration - optional for scalable
        mfa_config = cognito.Mfa.OPTIONAL if is_scalable else cognito.Mfa.OFF

        # Advanced security - enabled for scalable
        advanced_security = (
            cognito.AdvancedSecurityMode.ENFORCED
            if is_scalable
            else cognito.AdvancedSecurityMode.OFF
        )

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=pool_name,
            # Sign-in configuration
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False,
            ),
            self_sign_up_enabled=True,
            # Verification
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True,
            ),
            # Password policy
            password_policy=password_policy,
            # MFA
            mfa=mfa_config,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=False,
                otp=True,  # TOTP is more secure and doesn't require phone setup
            ),
            # Security
            advanced_security_mode=advanced_security,
            # Account recovery
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            # Standard attributes
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True,
                ),
            ),
            # Removal policy - RETAIN for production safety
            removal_policy=(
                RemovalPolicy.RETAIN if is_scalable else RemovalPolicy.DESTROY
            ),
        )

        self.apply_tags(self.user_pool)

    def _create_user_pool_client(self) -> None:
        """Create a User Pool Client for application integration."""
        if not self.user_pool:
            return

        client_name = self.generate_resource_name("appclient", "web")

        # Token validity settings
        from aws_api_factory.config.models import ProfileEnum

        is_scalable = self.config.profile == ProfileEnum.SCALABLE

        # Shorter token validity for scalable (security)
        access_token_validity = Duration.hours(1) if is_scalable else Duration.hours(4)
        id_token_validity = Duration.hours(1) if is_scalable else Duration.hours(4)
        refresh_token_validity = Duration.days(7) if is_scalable else Duration.days(30)

        self.user_pool_client = self.user_pool.add_client(
            "UserPoolClient",
            user_pool_client_name=client_name,
            # Auth flows
            auth_flows=cognito.AuthFlow(
                user_password=True,  # Allow username/password auth
                user_srp=True,  # Secure Remote Password (recommended)
            ),
            # Token validity
            access_token_validity=access_token_validity,
            id_token_validity=id_token_validity,
            refresh_token_validity=refresh_token_validity,
            # Prevent client secret for public clients (SPA, mobile)
            generate_secret=False,
            # OAuth configuration (if needed for hosted UI)
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False,  # Less secure, disabled
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
                # Callback URLs should be configured per environment
                # Users can add these via AWS Console
            ),
        )

    def _import_existing_user_pool(self, user_pool_id: str) -> None:
        """Import an existing User Pool by ID.

        Args:
            user_pool_id: The Cognito User Pool ID.
        """
        self.user_pool = cognito.UserPool.from_user_pool_id(
            self,
            "ImportedUserPool",
            user_pool_id=user_pool_id,
        )

        # For imported pools, we still need to create a client
        self._create_user_pool_client()

    def _create_authorizer(self) -> None:
        """Create a Cognito Authorizer for API Gateway."""
        if not self.user_pool:
            return

        authorizer_name = self.generate_resource_name("authorizer", "cognito")

        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            authorizer_name=authorizer_name,
            cognito_user_pools=[self.user_pool],
            # Cache authorization for 5 minutes (balance security/performance)
            results_cache_ttl=Duration.minutes(5),
        )

    def _register_outputs(self) -> None:
        """Register Cognito authentication outputs."""
        if self.user_pool:
            self.add_output(
                key="CognitoUserPoolId",
                value=self.user_pool.user_pool_id,
                description="Cognito User Pool ID",
                export=True,
            )
            self.add_output(
                key="CognitoUserPoolArn",
                value=self.user_pool.user_pool_arn,
                description="Cognito User Pool ARN",
            )

        if self.user_pool_client:
            self.add_output(
                key="CognitoClientId",
                value=self.user_pool_client.user_pool_client_id,
                description="Cognito App Client ID (for frontend integration)",
                export=True,
            )

        if self.authorizer:
            self.add_output(
                key="CognitoAuthorizerId",
                value=self.authorizer.authorizer_id,
                description="Cognito Authorizer ID",
            )

    def get_user_pool(self) -> cognito.UserPool | None:
        """Get the Cognito User Pool.

        Returns:
            The User Pool or None if not created.
        """
        return self.user_pool

    def get_user_pool_client(self) -> cognito.UserPoolClient | None:
        """Get the User Pool Client.

        Returns:
            The User Pool Client or None if not created.
        """
        return self.user_pool_client

    def get_authorizer(self) -> apigw.CognitoUserPoolsAuthorizer | None:
        """Get the Cognito Authorizer.

        Returns:
            The Cognito Authorizer or None if not created.
        """
        return self.authorizer

    def apply_cognito_auth_to_method(
        self,
        method: apigw.Method,
        scopes: list[str] | None = None,
    ) -> None:
        """Apply Cognito authorization to an API Gateway method.

        Note: Cognito authorization should be set during method creation.
        This method is provided for documentation and verification.

        Args:
            method: The API Gateway method.
            scopes: Optional OAuth scopes to require.
        """
        # Authorization is typically set at method creation time
        # This method documents the expected pattern
        pass


def create_cognito_auth(
    scope: Construct,
    id: str,
    *,
    config: "FactoryConfig",
    profile_defaults: "ProfileDefaults",
    output_manager: "OutputManager",
    environment: str,
    api: apigw.RestApi,
    existing_user_pool_id: str | None = None,
) -> CognitoAuthConstruct:
    """Factory function to create Cognito authentication.

    This is a convenience function that creates a CognitoAuthConstruct
    with sensible defaults.

    Args:
        scope: The CDK construct scope.
        id: The construct ID.
        config: The factory configuration.
        profile_defaults: Profile defaults for security settings.
        output_manager: Output manager for registering outputs.
        environment: Deployment environment name.
        api: The REST API to apply authentication to.
        existing_user_pool_id: Optional existing User Pool ID to use.

    Returns:
        The created CognitoAuthConstruct.

    Example:
        >>> auth = create_cognito_auth(
        ...     stack, "Auth",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     api=rest_api.api,
        ... )
    """
    return CognitoAuthConstruct(
        scope,
        id,
        config=config,
        profile_defaults=profile_defaults,
        output_manager=output_manager,
        environment=environment,
        api=api,
        existing_user_pool_id=existing_user_pool_id,
    )
