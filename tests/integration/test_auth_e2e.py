# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Integration tests for authentication end-to-end.

These tests verify that auth constructs work correctly together with
REST API constructs to create properly authenticated endpoints.
"""

from __future__ import annotations

import pytest
from aws_cdk import App, Stack, assertions
from aws_cdk import aws_apigateway as apigw

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
    create_auth_constructs,
    get_method_options,
)
from aws_api_factory.constructs.outputs import OutputManager


@pytest.fixture
def app():
    """Create a CDK App."""
    return App()


@pytest.fixture
def stack(app):
    """Create a test Stack."""
    return Stack(app, "IntegrationTestStack")


@pytest.fixture
def output_manager(stack):
    """Create an OutputManager."""
    return OutputManager(stack, "test-project", "dev")


@pytest.fixture
def minimal_defaults():
    """Get minimal profile defaults."""
    return get_defaults(ProfileEnum.MINIMAL)


@pytest.fixture
def scalable_defaults():
    """Get scalable profile defaults."""
    return get_defaults(ProfileEnum.SCALABLE)


def create_mock_api(stack: Stack, name: str = "TestApi") -> apigw.RestApi:
    """Create a REST API with a root method for testing."""
    api = apigw.RestApi(stack, name, rest_api_name=name.lower())
    # Add a root method so the API is valid
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
# API Key Auth Integration Tests
# =============================================================================


class TestApiKeyAuthIntegration:
    """Integration tests for API Key authentication."""

    def test_api_key_with_usage_plan_attached_to_api(
        self, stack, output_manager, minimal_defaults
    ):
        """Test API key and usage plan are correctly linked to the API."""
        api = create_mock_api(stack, "ApiKeyTestApi")

        config = FactoryConfig(
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

        # Create API Key auth
        ApiKeyAuthConstruct(
            stack,
            "ApiKeyAuth",
            config=config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=api,
        )

        # Add a protected method with API key requirement
        protected = api.root.add_resource("protected")
        protected.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            api_key_required=True,
        )

        template = assertions.Template.from_stack(stack)

        # Verify resources created
        template.resource_count_is("AWS::ApiGateway::ApiKey", 1)
        template.resource_count_is("AWS::ApiGateway::UsagePlan", 1)
        template.resource_count_is("AWS::ApiGateway::UsagePlanKey", 1)

        # Verify usage plan has quota
        template.has_resource_properties(
            "AWS::ApiGateway::UsagePlan",
            {
                "Quota": {"Limit": 1000, "Period": "DAY"},
            },
        )

    def test_scalable_profile_higher_rate_limits(
        self, stack, output_manager, scalable_defaults
    ):
        """Test scalable profile gets higher rate limits."""
        api = create_mock_api(stack, "ScalableApiKeyApi")

        config = FactoryConfig(
            project=ProjectConfig(name="scalable-api-key", envs=["prod"]),
            profile=ProfileEnum.SCALABLE,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/data",
                            methods=[HttpMethodEnum.GET],
                            service="data",
                            auth=AuthModeEnum.API_KEY,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "data": LambdaServiceConfig(
                            entry="src/services/data/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        ApiKeyAuthConstruct(
            stack,
            "ScalableApiKey",
            config=config,
            profile_defaults=scalable_defaults,
            output_manager=output_manager,
            environment="prod",
            api=api,
        )

        # Add protected method
        data = api.root.add_resource("data")
        data.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            api_key_required=True,
        )

        template = assertions.Template.from_stack(stack)

        # Scalable should have 10x quota
        template.has_resource_properties(
            "AWS::ApiGateway::UsagePlan",
            {
                "Quota": {"Limit": 10000, "Period": "DAY"},
            },
        )


# =============================================================================
# IAM Auth Integration Tests
# =============================================================================


class TestIamAuthIntegration:
    """Integration tests for IAM authentication."""

    def test_iam_policy_grants_invoke(self, stack, output_manager, minimal_defaults):
        """Test IAM auth creates proper invoke policy."""
        api = create_mock_api(stack, "IamTestApi")

        config = FactoryConfig(
            project=ProjectConfig(name="iam-test", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/internal",
                            methods=[HttpMethodEnum.POST],
                            service="internal",
                            auth=AuthModeEnum.IAM,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "internal": LambdaServiceConfig(
                            entry="src/services/internal/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        IamAuthConstruct(
            stack,
            "IamAuth",
            config=config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=api,
        )

        # Add IAM protected method
        internal = api.root.add_resource("internal")
        internal.add_method(
            "POST",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorization_type=apigw.AuthorizationType.IAM,
        )

        template = assertions.Template.from_stack(stack)

        # Verify managed policy exists
        template.resource_count_is("AWS::IAM::ManagedPolicy", 1)

        # Verify policy document
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


# =============================================================================
# Cognito Auth Integration Tests
# =============================================================================


class TestCognitoAuthIntegration:
    """Integration tests for Cognito authentication."""

    def test_cognito_authorizer_attached_to_method(
        self, stack, output_manager, minimal_defaults
    ):
        """Test Cognito authorizer is properly attached to API methods."""
        api = create_mock_api(stack, "CognitoTestApi")

        config = FactoryConfig(
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
                            service="users",
                            auth=AuthModeEnum.COGNITO,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "users": LambdaServiceConfig(
                            entry="src/services/users/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        cognito_auth = CognitoAuthConstruct(
            stack,
            "CognitoAuth",
            config=config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=api,
        )

        # Add Cognito protected method
        users = api.root.add_resource("users")
        users.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=cognito_auth.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        # Verify User Pool created
        template.resource_count_is("AWS::Cognito::UserPool", 1)
        template.resource_count_is("AWS::Cognito::UserPoolClient", 1)
        template.resource_count_is("AWS::ApiGateway::Authorizer", 1)

        # Verify authorizer is Cognito type
        template.has_resource_properties(
            "AWS::ApiGateway::Authorizer",
            {
                "Type": "COGNITO_USER_POOLS",
            },
        )

    def test_scalable_profile_enhanced_security(
        self, stack, output_manager, scalable_defaults
    ):
        """Test scalable profile has enhanced Cognito security."""
        api = create_mock_api(stack, "ScalableCognitoApi")

        config = FactoryConfig(
            project=ProjectConfig(name="secure-app", envs=["prod"]),
            profile=ProfileEnum.SCALABLE,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    cognito=CognitoConfig(create_user_pool=True),
                    routes=[
                        RouteConfig(
                            path="/secure",
                            methods=[HttpMethodEnum.GET],
                            service="secure",
                            auth=AuthModeEnum.COGNITO,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "secure": LambdaServiceConfig(
                            entry="src/services/secure/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        cognito_auth = CognitoAuthConstruct(
            stack,
            "ScalableCognito",
            config=config,
            profile_defaults=scalable_defaults,
            output_manager=output_manager,
            environment="prod",
            api=api,
        )

        # Attach authorizer to method
        secure = api.root.add_resource("secure")
        secure.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=cognito_auth.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        # Scalable: MFA optional, 12 char password
        template.has_resource_properties(
            "AWS::Cognito::UserPool",
            {
                "MfaConfiguration": "OPTIONAL",
                "Policies": {
                    "PasswordPolicy": {
                        "MinimumLength": 12,
                        "RequireSymbols": True,
                    },
                },
            },
        )


# =============================================================================
# Mixed Auth Integration Tests
# =============================================================================


class TestMixedAuthIntegration:
    """Integration tests for mixed authentication modes."""

    def test_multiple_auth_modes_in_single_api(
        self, stack, output_manager, minimal_defaults
    ):
        """Test API with multiple auth modes (API Key, IAM, Cognito)."""
        api = create_mock_api(stack, "MixedAuthApi")

        config = FactoryConfig(
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
                            service="public",
                            auth=AuthModeEnum.NONE,
                        ),
                        RouteConfig(
                            path="/partner",
                            methods=[HttpMethodEnum.GET],
                            service="partner",
                            auth=AuthModeEnum.API_KEY,
                        ),
                        RouteConfig(
                            path="/internal",
                            methods=[HttpMethodEnum.POST],
                            service="internal",
                            auth=AuthModeEnum.IAM,
                        ),
                        RouteConfig(
                            path="/users",
                            methods=[HttpMethodEnum.GET],
                            service="users",
                            auth=AuthModeEnum.COGNITO,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "public": LambdaServiceConfig(
                            entry="src/services/public/handler.py:handler",
                        ),
                        "partner": LambdaServiceConfig(
                            entry="src/services/partner/handler.py:handler",
                        ),
                        "internal": LambdaServiceConfig(
                            entry="src/services/internal/handler.py:handler",
                        ),
                        "users": LambdaServiceConfig(
                            entry="src/services/users/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        # Use helper to create all needed auth constructs
        auth = create_auth_constructs(
            stack,
            config=config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=api,
        )

        # Add methods for each auth type
        # Public route (no auth)
        public = api.root.add_resource("public")
        public.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
        )

        # Partner route (API Key)
        partner = api.root.add_resource("partner")
        partner.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            api_key_required=True,
        )

        # Internal route (IAM)
        internal = api.root.add_resource("internal")
        internal.add_method(
            "POST",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorization_type=apigw.AuthorizationType.IAM,
        )

        # Users route (Cognito)
        users = api.root.add_resource("users")
        users.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            authorizer=auth.cognito.authorizer if auth.cognito else None,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        template = assertions.Template.from_stack(stack)

        # Verify all auth resources created
        template.resource_count_is("AWS::ApiGateway::ApiKey", 1)
        template.resource_count_is("AWS::IAM::ManagedPolicy", 1)
        template.resource_count_is("AWS::Cognito::UserPool", 1)
        template.resource_count_is("AWS::ApiGateway::Authorizer", 1)

    def test_create_auth_constructs_only_creates_needed(
        self, stack, output_manager, minimal_defaults
    ):
        """Test that only required auth constructs are created."""
        api = create_mock_api(stack, "PartialAuthApi")

        # Only API Key auth - no Cognito or IAM
        config = FactoryConfig(
            project=ProjectConfig(name="api-key-only", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/data",
                            methods=[HttpMethodEnum.GET],
                            service="data",
                            auth=AuthModeEnum.API_KEY,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "data": LambdaServiceConfig(
                            entry="src/services/data/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        auth = create_auth_constructs(
            stack,
            config=config,
            profile_defaults=minimal_defaults,
            output_manager=output_manager,
            environment="dev",
            api=api,
        )

        # Only API Key should be created
        assert auth.api_key is not None
        assert auth.iam is None
        assert auth.cognito is None

        # Add method to use API key
        data = api.root.add_resource("data")
        data.add_method(
            "GET",
            apigw.MockIntegration(
                integration_responses=[{"statusCode": "200"}],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={"application/json": '{"statusCode": 200}'},
            ),
            method_responses=[{"statusCode": "200"}],
            api_key_required=True,
        )

        template = assertions.Template.from_stack(stack)

        # Verify only API Key resources
        template.resource_count_is("AWS::ApiGateway::ApiKey", 1)
        template.resource_count_is("AWS::IAM::ManagedPolicy", 0)
        template.resource_count_is("AWS::Cognito::UserPool", 0)


# =============================================================================
# Helper Function Integration Tests
# =============================================================================


class TestAuthHelperIntegration:
    """Integration tests for auth helper functions."""

    def test_get_method_options_returns_correct_options(self, minimal_defaults):
        """Test get_method_options returns correct settings for each auth mode."""
        from aws_api_factory.constructs.auth.helpers import AuthConstructs

        # Create empty auth constructs for testing
        auth_constructs = AuthConstructs(api_key=None, iam=None, cognito=None)

        # None - no auth
        options = get_method_options(AuthModeEnum.NONE, auth_constructs)
        assert options is not None
        assert options.get("api_key_required") is False

        # API Key
        options = get_method_options(AuthModeEnum.API_KEY, auth_constructs)
        assert options is not None
        assert options.get("api_key_required") is True

        # IAM
        options = get_method_options(AuthModeEnum.IAM, auth_constructs)
        assert options is not None
