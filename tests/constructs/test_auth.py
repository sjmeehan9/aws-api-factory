# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Unit tests for authentication constructs."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from aws_cdk import App, Stack, assertions
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_iam as iam

from aws_api_factory.config.defaults import get_defaults
from aws_api_factory.config.models import (
    ApisConfig,
    AuthModeEnum,
    CognitoConfig,
    ComputeConfig,
    FactoryConfig,
    HttpMethodEnum,
    LambdaConfig,
    LambdaServiceConfig,
    ProfileEnum,
    ProjectConfig,
    RestApiConfig,
    RouteConfig,
)
from aws_api_factory.constructs.auth import (
    ApiKeyAuthConstruct,
    CognitoAuthConstruct,
    IamAuthConstruct,
    apply_auth_to_method,
    create_auth_constructs,
    get_auth_mode_for_route,
    get_required_auth_modes,
    validate_auth_config,
)
from aws_api_factory.constructs.auth.helpers import (
    AuthConstructs,
    get_authorization_type,
    get_method_options,
)
from aws_api_factory.constructs.outputs import OutputManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create a CDK App for testing."""
    return App()


@pytest.fixture
def stack(app):
    """Create a CDK Stack for testing."""
    return Stack(app, "TestStack")


@pytest.fixture
def output_manager(stack):
    """Create an OutputManager for testing."""
    return OutputManager(stack, "test-api", "dev")


@pytest.fixture
def minimal_defaults():
    """Get minimal profile defaults."""
    return get_defaults(ProfileEnum.MINIMAL)


@pytest.fixture
def scalable_defaults():
    """Get scalable profile defaults."""
    return get_defaults(ProfileEnum.SCALABLE)


@pytest.fixture
def minimal_config():
    """Create a minimal factory config."""
    return FactoryConfig(
        project=ProjectConfig(name="test-api", envs=["dev", "prod"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/hello",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.NONE,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def api_key_config():
    """Create a config with API key authentication."""
    return FactoryConfig(
        project=ProjectConfig(name="api-key-test", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/protected",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.API_KEY,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def iam_config():
    """Create a config with IAM authentication."""
    return FactoryConfig(
        project=ProjectConfig(name="iam-test", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/internal",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.IAM,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def cognito_config():
    """Create a config with Cognito authentication."""
    return FactoryConfig(
        project=ProjectConfig(name="cognito-test", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                cognito=CognitoConfig(create_user_pool=True),
                routes=[
                    RouteConfig(
                        path="/users",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.COGNITO,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def scalable_cognito_config():
    """Create a scalable config with Cognito authentication."""
    return FactoryConfig(
        project=ProjectConfig(name="cognito-scalable", envs=["prod"]),
        profile=ProfileEnum.SCALABLE,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                cognito=CognitoConfig(create_user_pool=True),
                routes=[
                    RouteConfig(
                        path="/users",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.COGNITO,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def mixed_auth_config():
    """Create a config with multiple auth modes."""
    return FactoryConfig(
        project=ProjectConfig(name="mixed-auth", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                cognito=CognitoConfig(create_user_pool=True),
                routes=[
                    RouteConfig(
                        path="/public",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.NONE,
                    ),
                    RouteConfig(
                        path="/api-protected",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.API_KEY,
                    ),
                    RouteConfig(
                        path="/internal",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.IAM,
                    ),
                    RouteConfig(
                        path="/users",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.COGNITO,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def mock_rest_api(stack):
    """Create a mock REST API for testing with at least one method."""
    api = apigw.RestApi(stack, "TestApi", rest_api_name="test-api")
    # Add a mock method so template validation passes
    api.root.add_method(
        "GET",
        apigw.MockIntegration(
            integration_responses=[{"statusCode": "200"}],
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_templates={"application/json": '{"statusCode": 200}'},
        ),
        method_responses=[{"statusCode": "200"}],
    )
    return api


# =============================================================================
# API Key Auth Construct Tests
# =============================================================================


class TestApiKeyAuthConstruct:
    """Tests for ApiKeyAuthConstruct."""

    def test_creates_api_key(
        self, stack, api_key_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that API key is created."""
        construct = ApiKeyAuthConstruct(
            stack,
            "ApiKeyAuth",
            config=api_key_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert construct.api_key is not None
        assert construct.usage_plan is not None

    def test_creates_usage_plan(
        self, stack, api_key_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that usage plan is created with correct settings."""
        construct = ApiKeyAuthConstruct(
            stack,
            "ApiKeyAuth",
            config=api_key_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        template = assertions.Template.from_stack(stack)

        # Verify usage plan exists
        template.has_resource_properties(
            "AWS::ApiGateway::UsagePlan",
            {
                "Quota": {
                    "Limit": ApiKeyAuthConstruct.MINIMAL_DAILY_QUOTA,
                    "Period": "DAY",
                },
                "Throttle": {
                    "BurstLimit": ApiKeyAuthConstruct.MINIMAL_BURST_LIMIT,
                    "RateLimit": ApiKeyAuthConstruct.MINIMAL_RATE_LIMIT,
                },
            },
        )

    def test_scalable_profile_higher_limits(
        self, stack, scalable_defaults, output_manager, mock_rest_api
    ):
        """Test that scalable profile has higher rate limits."""
        config = FactoryConfig(
            project=ProjectConfig(name="scalable-test", envs=["prod"]),
            profile=ProfileEnum.SCALABLE,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/protected",
                            methods=[HttpMethodEnum.GET],
                            service="hello",
                            auth=AuthModeEnum.API_KEY,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        construct = ApiKeyAuthConstruct(
            stack,
            "ApiKeyAuth",
            config=config,
            profile_defaults=scalable_defaults,
            output_manager=output_manager,
            environment="prod",
            api=mock_rest_api,
        )

        template = assertions.Template.from_stack(stack)

        # Verify higher limits for scalable
        template.has_resource_properties(
            "AWS::ApiGateway::UsagePlan",
            {
                "Quota": {
                    "Limit": ApiKeyAuthConstruct.SCALABLE_DAILY_QUOTA,
                    "Period": "DAY",
                },
            },
        )

    def test_registers_outputs(
        self, stack, api_key_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that outputs are registered."""
        ApiKeyAuthConstruct(
            stack,
            "ApiKeyAuth",
            config=api_key_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        # Check outputs were registered (get returns None if not found)
        assert output_manager.get("ApiKeyId") is not None
        assert output_manager.get("UsagePlanId") is not None

    def test_validation_fails_without_api(
        self, stack, api_key_config, minimal_defaults, output_manager
    ):
        """Test validation fails without API."""
        with pytest.raises(ValueError, match="REST API is required"):
            ApiKeyAuthConstruct(
                stack,
                "ApiKeyAuth",
                config=api_key_config,
                profile_defaults=minimal_defaults,
                output_manager=output_manager,
                environment="dev",
                api=None,  # type: ignore
            )


# =============================================================================
# IAM Auth Construct Tests
# =============================================================================


class TestIamAuthConstruct:
    """Tests for IamAuthConstruct."""

    def test_creates_invoke_policy(
        self, stack, iam_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that IAM invoke policy is created."""
        construct = IamAuthConstruct(
            stack,
            "IamAuth",
            config=iam_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert construct.invoke_policy is not None

    def test_policy_allows_execute_api(
        self, stack, iam_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that policy allows execute-api:Invoke."""
        IamAuthConstruct(
            stack,
            "IamAuth",
            config=iam_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        template = assertions.Template.from_stack(stack)

        # Verify managed policy exists
        template.has_resource_properties(
            "AWS::IAM::ManagedPolicy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "execute-api:Invoke",
                            "Effect": "Allow",
                        }
                    ],
                },
            },
        )

    def test_grant_invoke(
        self, stack, iam_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test granting invoke permission to a principal."""
        construct = IamAuthConstruct(
            stack,
            "IamAuth",
            config=iam_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        # Create a test role
        role = iam.Role(
            stack,
            "TestRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Grant invoke
        grant = construct.grant_invoke(role)
        assert grant is not None

    def test_grant_invoke_path(
        self, stack, iam_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test granting invoke permission for specific path."""
        construct = IamAuthConstruct(
            stack,
            "IamAuth",
            config=iam_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        role = iam.Role(
            stack,
            "TestRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Grant invoke for specific path
        grant = construct.grant_invoke_path(role, "GET", "/orders/*")
        assert grant is not None

    def test_registers_outputs(
        self, stack, iam_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that outputs are registered."""
        IamAuthConstruct(
            stack,
            "IamAuth",
            config=iam_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert output_manager.get("IamInvokePolicyArn") is not None
        assert output_manager.get("IamApiExecuteArn") is not None


# =============================================================================
# Cognito Auth Construct Tests
# =============================================================================


class TestCognitoAuthConstruct:
    """Tests for CognitoAuthConstruct."""

    def test_creates_user_pool(
        self, stack, cognito_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that Cognito User Pool is created."""
        construct = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=cognito_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert construct.user_pool is not None
        assert construct.user_pool_client is not None
        assert construct.authorizer is not None

    def test_user_pool_email_signin(
        self, stack, cognito_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test User Pool allows email sign-in."""
        construct = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=cognito_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        # Attach authorizer to a method to satisfy CDK validation
        protected = mock_rest_api.root.add_resource("protected")
        protected.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=construct.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        # Verify email is enabled for sign-in
        template.has_resource_properties(
            "AWS::Cognito::UserPool",
            {
                "AutoVerifiedAttributes": ["email"],
            },
        )

    def test_minimal_profile_password_policy(
        self, stack, cognito_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test minimal profile has basic password policy."""
        construct = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=cognito_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        # Attach authorizer to satisfy CDK validation
        protected = mock_rest_api.root.add_resource("protected")
        protected.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=construct.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        # Minimal: 8 chars, no symbols required
        template.has_resource_properties(
            "AWS::Cognito::UserPool",
            {
                "Policies": {
                    "PasswordPolicy": {
                        "MinimumLength": 8,
                        "RequireSymbols": False,
                    },
                },
            },
        )

    def test_scalable_profile_strong_password(
        self,
        stack,
        scalable_cognito_config,
        scalable_defaults,
        output_manager,
        mock_rest_api,
    ):
        """Test scalable profile has strong password policy."""
        construct = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=scalable_cognito_config,
            profile_defaults=scalable_defaults,
            output_manager=output_manager,
            environment="prod",
            api=mock_rest_api,
        )

        # Attach authorizer to satisfy CDK validation
        protected = mock_rest_api.root.add_resource("protected")
        protected.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=construct.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        # Scalable: 12 chars, symbols required
        template.has_resource_properties(
            "AWS::Cognito::UserPool",
            {
                "Policies": {
                    "PasswordPolicy": {
                        "MinimumLength": 12,
                        "RequireSymbols": True,
                    },
                },
            },
        )

    def test_scalable_profile_mfa_optional(
        self,
        stack,
        scalable_cognito_config,
        scalable_defaults,
        output_manager,
        mock_rest_api,
    ):
        """Test scalable profile has MFA optional."""
        construct = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=scalable_cognito_config,
            profile_defaults=scalable_defaults,
            output_manager=output_manager,
            environment="prod",
            api=mock_rest_api,
        )

        # Attach authorizer to satisfy CDK validation
        protected = mock_rest_api.root.add_resource("protected")
        protected.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=construct.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Cognito::UserPool",
            {
                "MfaConfiguration": "OPTIONAL",
            },
        )

    def test_creates_authorizer(
        self, stack, cognito_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test Cognito authorizer is created."""
        construct = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=cognito_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        # Attach authorizer to satisfy CDK validation
        protected = mock_rest_api.root.add_resource("protected")
        protected.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=construct.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::ApiGateway::Authorizer",
            {
                "Type": "COGNITO_USER_POOLS",
            },
        )

    def test_registers_outputs(
        self, stack, cognito_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test that outputs are registered."""
        CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=cognito_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert output_manager.get("CognitoUserPoolId") is not None
        assert output_manager.get("CognitoUserPoolArn") is not None
        assert output_manager.get("CognitoClientId") is not None
        assert output_manager.get("CognitoAuthorizerId") is not None


# =============================================================================
# Helper Functions Tests
# =============================================================================


class TestAuthHelpers:
    """Tests for auth helper functions."""

    def test_validate_auth_config_valid(self, cognito_config):
        """Test validation passes for valid config."""
        errors = validate_auth_config(cognito_config)
        assert errors == []

    def test_validate_auth_config_missing_cognito(self):
        """Test validation fails when cognito auth used without config.

        Note: Pydantic model validation catches this before validate_auth_config
        is called, so we expect a ValueError during model creation.
        """
        with pytest.raises(ValueError, match="cognito"):
            FactoryConfig(
                project=ProjectConfig(name="test", envs=["dev"]),
                profile=ProfileEnum.MINIMAL,
                apis=ApisConfig(
                    rest=RestApiConfig(
                        enabled=True,
                        # Missing cognito config
                        routes=[
                            RouteConfig(
                                path="/users",
                                methods=[HttpMethodEnum.GET],
                                service="hello",
                                auth=AuthModeEnum.COGNITO,
                            ),
                        ],
                    )
                ),
                compute=ComputeConfig(
                    lambda_=LambdaConfig(
                        enabled=True,
                        services={
                            "hello": LambdaServiceConfig(
                                entry="src/services/hello/handler.py:handler",
                            ),
                        },
                    )
                ),
            )

    def test_get_auth_mode_for_route(self, cognito_config):
        """Test getting auth mode for a route."""
        route = cognito_config.apis.rest.routes[0]
        auth_mode = get_auth_mode_for_route(route)
        assert auth_mode == AuthModeEnum.COGNITO

    def test_get_required_auth_modes(self, mixed_auth_config):
        """Test getting all required auth modes."""
        modes = get_required_auth_modes(mixed_auth_config)

        assert AuthModeEnum.API_KEY in modes
        assert AuthModeEnum.IAM in modes
        assert AuthModeEnum.COGNITO in modes
        assert AuthModeEnum.NONE not in modes  # NONE is not a "required" mode

    def test_create_auth_constructs(
        self, stack, mixed_auth_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test creating all auth constructs from config."""
        auth = create_auth_constructs(
            stack,
            config=mixed_auth_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert auth.api_key is not None
        assert auth.iam is not None
        assert auth.cognito is not None
        assert auth.has_any_auth()

    def test_create_auth_constructs_only_needed(
        self, stack, api_key_config, minimal_defaults, output_manager, mock_rest_api
    ):
        """Test only needed auth constructs are created."""
        auth = create_auth_constructs(
            stack,
            config=api_key_config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=mock_rest_api,
        )

        assert auth.api_key is not None
        assert auth.iam is None
        assert auth.cognito is None

    def test_get_authorization_type(self):
        """Test getting API Gateway authorization type."""
        assert get_authorization_type(AuthModeEnum.NONE) == apigw.AuthorizationType.NONE
        assert get_authorization_type(AuthModeEnum.IAM) == apigw.AuthorizationType.IAM
        assert (
            get_authorization_type(AuthModeEnum.COGNITO)
            == apigw.AuthorizationType.COGNITO
        )
        # API key uses NONE with api_key_required flag
        assert (
            get_authorization_type(AuthModeEnum.API_KEY) == apigw.AuthorizationType.NONE
        )

    def test_get_method_options_none(self):
        """Test getting method options for no auth."""
        auth_constructs = AuthConstructs()
        options = get_method_options(AuthModeEnum.NONE, auth_constructs)

        assert options["authorization_type"] == apigw.AuthorizationType.NONE
        assert options["api_key_required"] is False

    def test_get_method_options_api_key(self):
        """Test getting method options for API key auth."""
        auth_constructs = AuthConstructs()
        options = get_method_options(AuthModeEnum.API_KEY, auth_constructs)

        assert options["authorization_type"] == apigw.AuthorizationType.NONE
        assert options["api_key_required"] is True

    def test_get_method_options_iam(self):
        """Test getting method options for IAM auth."""
        auth_constructs = AuthConstructs()
        options = get_method_options(AuthModeEnum.IAM, auth_constructs)

        assert options["authorization_type"] == apigw.AuthorizationType.IAM
        assert options["api_key_required"] is False

    def test_auth_constructs_has_any_auth(self):
        """Test AuthConstructs.has_any_auth()."""
        # Empty
        empty = AuthConstructs()
        assert not empty.has_any_auth()

        # With api_key
        with_api_key = AuthConstructs(api_key=MagicMock())
        assert with_api_key.has_any_auth()

        # With iam
        with_iam = AuthConstructs(iam=MagicMock())
        assert with_iam.has_any_auth()

        # With cognito
        with_cognito = AuthConstructs(cognito=MagicMock())
        assert with_cognito.has_any_auth()
