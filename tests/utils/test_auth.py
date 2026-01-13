# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Unit tests for Lambda authentication utilities."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from aws_api_factory.utils.auth import (
    AuthContext,
    AuthenticationError,
    AuthType,
    extract_auth_context,
    get_api_key_id,
    get_cognito_claims,
    get_iam_principal,
    require_api_key,
    require_auth,
    require_cognito_auth,
    require_iam_auth,
)

# =============================================================================
# Test Fixtures - Sample API Gateway Events
# =============================================================================


@pytest.fixture
def unauthenticated_event() -> dict[str, Any]:
    """Create an unauthenticated API Gateway event."""
    return {
        "requestContext": {
            "requestId": "test-request-123",
            "identity": {
                "sourceIp": "192.168.1.1",
                "userAgent": "TestClient/1.0",
            },
        },
        "httpMethod": "GET",
        "path": "/hello",
    }


@pytest.fixture
def api_key_event() -> dict[str, Any]:
    """Create an API Gateway event with API key auth."""
    return {
        "requestContext": {
            "requestId": "test-request-456",
            "identity": {
                "sourceIp": "10.0.0.1",
                "userAgent": "PartnerAPI/2.0",
                "apiKey": "abc123xyz789secretkey",  # pragma: allowlist secret
                "apiKeyId": "apikey-id-12345",  # pragma: allowlist secret
            },
        },
        "httpMethod": "GET",
        "path": "/partner/data",
    }


@pytest.fixture
def iam_event() -> dict[str, Any]:
    """Create an API Gateway event with IAM auth."""
    return {
        "requestContext": {
            "requestId": "test-request-789",
            "identity": {
                "sourceIp": "172.16.0.1",
                "userAgent": "aws-sdk-python/1.0",
                "userArn": "arn:aws:iam::123456789012:user/john.doe",
                "accountId": "123456789012",
                "accessKey": "AKIAIOSFODNN7EXAMPLE",  # pragma: allowlist secret
            },
        },
        "httpMethod": "POST",
        "path": "/internal/process",
    }


@pytest.fixture
def iam_role_event() -> dict[str, Any]:
    """Create an API Gateway event with IAM role auth (assumed role)."""
    return {
        "requestContext": {
            "requestId": "test-request-role",
            "identity": {
                "sourceIp": "172.16.0.2",
                "userAgent": "aws-sdk-go/1.0",
                "userArn": "arn:aws:sts::123456789012:assumed-role/LambdaRole/lambda-session",
                "accountId": "123456789012",
            },
        },
        "httpMethod": "GET",
        "path": "/internal/status",
    }


@pytest.fixture
def cognito_event() -> dict[str, Any]:
    """Create an API Gateway event with Cognito auth."""
    return {
        "requestContext": {
            "requestId": "test-request-cognito",
            "identity": {
                "sourceIp": "192.168.100.1",
                "userAgent": "Mozilla/5.0",
            },
            "authorizer": {
                "claims": {
                    "sub": "12345678-1234-1234-1234-123456789012",
                    "cognito:username": "john.doe",
                    "email": "john.doe@example.com",
                    "email_verified": "true",
                    "cognito:groups": "users,admin",
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXXX",
                    "token_use": "id",
                    "auth_time": "1234567890",
                }
            },
        },
        "httpMethod": "GET",
        "path": "/users/profile",
    }


@pytest.fixture
def cognito_groups_list_event() -> dict[str, Any]:
    """Create a Cognito event with groups as a list."""
    return {
        "requestContext": {
            "requestId": "test-request-cognito-list",
            "identity": {
                "sourceIp": "192.168.100.2",
            },
            "authorizer": {
                "claims": {
                    "sub": "87654321-4321-4321-4321-210987654321",
                    "cognito:username": "jane.doe",
                    "email": "jane.doe@example.com",
                    "cognito:groups": ["users", "moderators"],
                }
            },
        },
        "httpMethod": "GET",
        "path": "/users/profile",
    }


# =============================================================================
# AuthContext Tests
# =============================================================================


class TestAuthContext:
    """Tests for AuthContext dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        context = AuthContext()
        assert context.auth_type == AuthType.NONE
        assert context.api_key is None
        assert context.cognito_username is None
        assert context.cognito_groups == []
        assert context.cognito_claims == {}

    def test_is_authenticated_false_for_none(self):
        """Test is_authenticated returns False for NONE."""
        context = AuthContext(auth_type=AuthType.NONE)
        assert not context.is_authenticated()

    def test_is_authenticated_true_for_api_key(self):
        """Test is_authenticated returns True for API_KEY."""
        context = AuthContext(auth_type=AuthType.API_KEY, api_key_id="test-id")
        assert context.is_authenticated()

    def test_is_authenticated_true_for_iam(self):
        """Test is_authenticated returns True for IAM."""
        context = AuthContext(
            auth_type=AuthType.IAM, iam_principal="arn:aws:iam::123456789012:user/test"
        )
        assert context.is_authenticated()

    def test_is_authenticated_true_for_cognito(self):
        """Test is_authenticated returns True for COGNITO."""
        context = AuthContext(auth_type=AuthType.COGNITO, cognito_username="testuser")
        assert context.is_authenticated()

    def test_get_user_identifier_api_key(self):
        """Test get_user_identifier for API key auth."""
        context = AuthContext(auth_type=AuthType.API_KEY, api_key_id="key-123")
        assert context.get_user_identifier() == "key-123"

    def test_get_user_identifier_iam(self):
        """Test get_user_identifier for IAM auth."""
        context = AuthContext(auth_type=AuthType.IAM, iam_user="john.doe")
        assert context.get_user_identifier() == "john.doe"

    def test_get_user_identifier_cognito(self):
        """Test get_user_identifier for Cognito auth."""
        context = AuthContext(
            auth_type=AuthType.COGNITO,
            cognito_username="john",
            cognito_sub="sub-12345",
        )
        assert context.get_user_identifier() == "john"

    def test_get_user_identifier_cognito_fallback_to_sub(self):
        """Test get_user_identifier falls back to sub if username missing."""
        context = AuthContext(
            auth_type=AuthType.COGNITO,
            cognito_sub="sub-12345",
        )
        assert context.get_user_identifier() == "sub-12345"

    def test_get_user_identifier_none(self):
        """Test get_user_identifier for no auth."""
        context = AuthContext()
        assert context.get_user_identifier() is None

    def test_to_dict(self):
        """Test to_dict serialization."""
        context = AuthContext(
            auth_type=AuthType.COGNITO,
            cognito_username="john",
            cognito_email="john@example.com",
            source_ip="192.168.1.1",
            request_id="req-123",
        )
        result = context.to_dict()

        assert result["auth_type"] == "cognito"
        assert result["is_authenticated"] is True
        assert result["cognito_username"] == "john"
        assert result["cognito_email"] == "john@example.com"
        assert result["source_ip"] == "192.168.1.1"
        assert result["request_id"] == "req-123"


# =============================================================================
# extract_auth_context Tests
# =============================================================================


class TestExtractAuthContext:
    """Tests for extract_auth_context function."""

    def test_unauthenticated_event(self, unauthenticated_event):
        """Test extracting context from unauthenticated event."""
        context = extract_auth_context(unauthenticated_event)

        assert context.auth_type == AuthType.NONE
        assert not context.is_authenticated()
        assert context.source_ip == "192.168.1.1"
        assert context.user_agent == "TestClient/1.0"
        assert context.request_id == "test-request-123"

    def test_api_key_event(self, api_key_event):
        """Test extracting context from API key event."""
        context = extract_auth_context(api_key_event)

        assert context.auth_type == AuthType.API_KEY
        assert context.is_authenticated()
        assert context.api_key_id == "apikey-id-12345"
        # API key should be masked
        assert context.api_key == "****tkey"
        assert context.source_ip == "10.0.0.1"

    def test_iam_user_event(self, iam_event):
        """Test extracting context from IAM user event."""
        context = extract_auth_context(iam_event)

        assert context.auth_type == AuthType.IAM
        assert context.is_authenticated()
        assert context.iam_principal == "arn:aws:iam::123456789012:user/john.doe"
        assert context.iam_account == "123456789012"
        assert context.iam_user == "john.doe"

    def test_iam_role_event(self, iam_role_event):
        """Test extracting context from IAM assumed role event."""
        context = extract_auth_context(iam_role_event)

        assert context.auth_type == AuthType.IAM
        assert context.is_authenticated()
        assert "assumed-role" in context.iam_principal
        assert context.iam_user == "lambda-session"

    def test_cognito_event(self, cognito_event):
        """Test extracting context from Cognito event."""
        context = extract_auth_context(cognito_event)

        assert context.auth_type == AuthType.COGNITO
        assert context.is_authenticated()
        assert context.cognito_username == "john.doe"
        assert context.cognito_email == "john.doe@example.com"
        assert context.cognito_sub == "12345678-1234-1234-1234-123456789012"
        assert "users" in context.cognito_groups
        assert "admin" in context.cognito_groups
        assert context.cognito_claims["email_verified"] == "true"

    def test_cognito_groups_as_list(self, cognito_groups_list_event):
        """Test extracting groups when they're a list."""
        context = extract_auth_context(cognito_groups_list_event)

        assert context.auth_type == AuthType.COGNITO
        assert "users" in context.cognito_groups
        assert "moderators" in context.cognito_groups

    def test_empty_event(self):
        """Test handling of empty event."""
        context = extract_auth_context({})
        assert context.auth_type == AuthType.NONE
        assert not context.is_authenticated()


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_cognito_claims(self, cognito_event):
        """Test get_cognito_claims helper."""
        claims = get_cognito_claims(cognito_event)

        assert claims["cognito:username"] == "john.doe"
        assert claims["email"] == "john.doe@example.com"

    def test_get_cognito_claims_empty(self, unauthenticated_event):
        """Test get_cognito_claims with no claims."""
        claims = get_cognito_claims(unauthenticated_event)
        assert claims == {}

    def test_get_api_key_id(self, api_key_event):
        """Test get_api_key_id helper."""
        key_id = get_api_key_id(api_key_event)
        assert key_id == "apikey-id-12345"

    def test_get_api_key_id_none(self, unauthenticated_event):
        """Test get_api_key_id with no API key."""
        key_id = get_api_key_id(unauthenticated_event)
        assert key_id is None

    def test_get_iam_principal(self, iam_event):
        """Test get_iam_principal helper."""
        principal = get_iam_principal(iam_event)
        assert principal == "arn:aws:iam::123456789012:user/john.doe"

    def test_get_iam_principal_none(self, unauthenticated_event):
        """Test get_iam_principal with no IAM auth."""
        principal = get_iam_principal(unauthenticated_event)
        assert principal is None


# =============================================================================
# Decorator Tests
# =============================================================================


class TestRequireAuthDecorator:
    """Tests for require_auth decorator."""

    def test_allows_authenticated_request(self, api_key_event):
        """Test decorator allows authenticated requests."""

        @require_auth()
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        response = handler(api_key_event, None)
        assert response["statusCode"] == 200

    def test_rejects_unauthenticated_request(self, unauthenticated_event):
        """Test decorator rejects unauthenticated requests."""

        @require_auth()
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        response = handler(unauthenticated_event, None)
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert "Authentication required" in body["error"]

    def test_attaches_auth_context(self, cognito_event):
        """Test decorator attaches auth context to event."""

        @require_auth()
        def handler(event, context):
            auth = event.get("authContext")
            return {
                "statusCode": 200,
                "body": json.dumps({"username": auth.cognito_username}),
            }

        response = handler(cognito_event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["username"] == "john.doe"

    def test_filters_by_auth_type(self, api_key_event, iam_event):
        """Test decorator can filter by auth type."""

        @require_auth(allowed_auth_types=[AuthType.IAM])
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        # IAM should pass
        response = handler(iam_event, None)
        assert response["statusCode"] == 200

        # API key should fail
        response = handler(api_key_event, None)
        assert response["statusCode"] == 403

    def test_filters_by_cognito_groups(self, cognito_event):
        """Test decorator can filter by Cognito groups."""

        @require_auth(required_groups=["admin"])
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        # User is in admin group
        response = handler(cognito_event, None)
        assert response["statusCode"] == 200

    def test_rejects_missing_group(self, cognito_event):
        """Test decorator rejects user not in required group."""

        @require_auth(required_groups=["superadmin"])
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        response = handler(cognito_event, None)
        assert response["statusCode"] == 403


class TestConvenienceDecorators:
    """Tests for convenience decorators."""

    def test_require_cognito_auth(self, cognito_event, api_key_event):
        """Test require_cognito_auth decorator."""

        @require_cognito_auth()
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        # Cognito should pass
        response = handler(cognito_event, None)
        assert response["statusCode"] == 200

        # API key should fail
        response = handler(api_key_event, None)
        assert response["statusCode"] == 403

    def test_require_cognito_auth_with_groups(self, cognito_event):
        """Test require_cognito_auth with group requirement."""

        @require_cognito_auth(required_groups=["admin"])
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        response = handler(cognito_event, None)
        assert response["statusCode"] == 200

    def test_require_iam_auth(self, iam_event, cognito_event):
        """Test require_iam_auth decorator."""

        @require_iam_auth()
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        # IAM should pass
        response = handler(iam_event, None)
        assert response["statusCode"] == 200

        # Cognito should fail
        response = handler(cognito_event, None)
        assert response["statusCode"] == 403

    def test_require_api_key(self, api_key_event, iam_event):
        """Test require_api_key decorator."""

        @require_api_key()
        def handler(event, context):
            return {"statusCode": 200, "body": "OK"}

        # API key should pass
        response = handler(api_key_event, None)
        assert response["statusCode"] == 200

        # IAM should fail
        response = handler(iam_event, None)
        assert response["statusCode"] == 403


# =============================================================================
# AuthenticationError Tests
# =============================================================================


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_default_status_code(self):
        """Test default status code is 401."""
        error = AuthenticationError("Test error")
        assert error.status_code == 401
        assert error.message == "Test error"

    def test_custom_status_code(self):
        """Test custom status code."""
        error = AuthenticationError("Forbidden", status_code=403)
        assert error.status_code == 403

    def test_str_representation(self):
        """Test string representation."""
        error = AuthenticationError("Access denied")
        assert str(error) == "Access denied"
