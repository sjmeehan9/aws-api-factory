# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for hello service handler."""

from starter.src.services.hello.handler import handler


class TestHelloHandler:
    """Tests for the hello Lambda handler."""

    def test_hello_default_response(self) -> None:
        """Test handler returns default greeting."""
        event: dict = {"queryStringParameters": None}
        context = None

        result = handler(event, context)

        assert result["statusCode"] == 200
        assert '"Hello, World!"' in result["body"]

    def test_hello_with_name(self) -> None:
        """Test handler uses name from query params."""
        event: dict = {"queryStringParameters": {"name": "Alice"}}
        context = None

        result = handler(event, context)

        assert result["statusCode"] == 200
        assert '"Hello, Alice!"' in result["body"]

    def test_hello_headers(self) -> None:
        """Test handler includes expected headers."""
        event: dict = {"queryStringParameters": None}
        context = None

        result = handler(event, context)

        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["X-Powered-By"] == "AWS API Factory"
