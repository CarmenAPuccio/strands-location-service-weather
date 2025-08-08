"""
Unit tests for AgentCore Lambda handlers.

This module tests the Lambda function handlers for weather and alerts tools,
including event parsing, response formatting, error handling, and trace propagation.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the Lambda functions directory to the path
lambda_functions_dir = (
    Path(__file__).parent.parent / "infrastructure" / "lambda_functions" / "shared"
)
sys.path.insert(0, str(lambda_functions_dir))

from lambda_handler import (
    format_agentcore_response,
    lambda_error_handler,
    parse_agentcore_event,
)


class TestAgentCoreEventParsing:
    """Test AgentCore event parsing functionality."""

    def test_parse_valid_event_parameters_format(self):
        """Test parsing a valid AgentCore event with parameters array."""
        event = {
            "messageVersion": "1.0",
            "parameters": [
                {"name": "latitude", "value": "47.6062", "type": "number"},
                {"name": "longitude", "value": "-122.3321", "type": "number"},
            ],
            "agent": {"agentId": "test-agent-id", "agentAliasId": "TSTALIASID"},
            "actionGroup": {
                "actionGroupId": "test-action-group",
                "actionGroupName": "weather-tools",
            },
            "function": {"functionName": "get_weather"},
        }

        result = parse_agentcore_event(event)

        assert result["latitude"] == 47.6062
        assert result["longitude"] == -122.3321
        assert result["_agentcore_metadata"]["agent_id"] == "test-agent-id"
        assert result["_agentcore_metadata"]["function_name"] == "get_weather"

    def test_parse_valid_event_requestbody_format(self):
        """Test parsing a valid AgentCore event with requestBody format."""
        event = {
            "requestBody": {
                "content": [{"text": '{"latitude": 47.6062, "longitude": -122.3321}'}]
            },
            "agent": {"agentId": "test-agent-id", "agentAliasId": "TSTALIASID"},
            "actionGroup": {
                "actionGroupId": "test-action-group",
                "actionGroupName": "weather-tools",
            },
            "function": {"functionName": "get_weather"},
        }

        result = parse_agentcore_event(event)

        assert result["latitude"] == 47.6062
        assert result["longitude"] == -122.3321
        assert result["_agentcore_metadata"]["agent_id"] == "test-agent-id"
        assert result["_agentcore_metadata"]["function_name"] == "get_weather"

    def test_parse_event_missing_parameters(self):
        """Test parsing event with no parameters."""
        event = {"agent": {"agentId": "test"}, "function": {"functionName": "test"}}

        with pytest.raises(ValueError, match="No parameters found in AgentCore event"):
            parse_agentcore_event(event)

    def test_parse_event_invalid_json(self):
        """Test parsing event with invalid JSON parameters."""
        event = {
            "requestBody": {
                "content": [
                    {"text": '{"latitude": 47.6062, "longitude":}'}  # Invalid JSON
                ]
            }
        }

        with pytest.raises(ValueError, match="Invalid JSON in requestBody content"):
            parse_agentcore_event(event)


class TestAgentCoreResponseFormatting:
    """Test AgentCore response formatting functionality."""

    def test_format_success_response(self):
        """Test formatting a successful response."""
        data = {"temperature": {"value": 72, "unit": "F"}, "forecast": "Sunny"}

        result = format_agentcore_response(data, success=True)

        assert "response" in result
        assert "body" in result["response"]
        assert result["messageVersion"] == "1.0"
        assert result["response"]["contentType"] == "application/json"

        body_data = json.loads(result["response"]["body"])
        assert body_data["temperature"]["value"] == 72
        assert body_data["forecast"] == "Sunny"
        assert body_data["success"] is True

    def test_format_error_response(self):
        """Test formatting an error response."""
        error_data = {"error": "Test error", "error_type": "test"}

        result = format_agentcore_response(error_data, success=False)

        assert "response" in result
        assert "body" in result["response"]

        body_data = json.loads(result["response"]["body"])
        assert body_data["error"] == "Test error"
        assert body_data["success"] is False


class TestLambdaErrorHandler:
    """Test Lambda error handler decorator."""

    def test_successful_function_execution(self):
        """Test error handler with successful function execution."""

        @lambda_error_handler
        def test_function(event, context):
            return {"success": True}

        # Mock context
        context = Mock()
        context.function_name = "test-function"
        context.function_version = "1"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000
        context.memory_limit_in_mb = 256

        event = {"test": "data"}

        with patch("lambda_handler._tracer") as mock_tracer:
            mock_span = Mock()
            mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
                mock_span
            )
            mock_tracer.start_as_current_span.return_value.__exit__.return_value = None

            result = test_function(event, context)

            assert "response" in result
            body_data = json.loads(result["response"]["body"])
            assert body_data["success"] is True

    def test_value_error_handling(self):
        """Test error handler with ValueError."""

        @lambda_error_handler
        def test_function(event, context):
            raise ValueError("Invalid parameters")

        context = Mock()
        context.function_name = "test-function"
        context.function_version = "1"
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000
        context.memory_limit_in_mb = 256

        event = {"test": "data"}

        with patch("lambda_handler._tracer") as mock_tracer:
            mock_span = Mock()
            mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
                mock_span
            )
            mock_tracer.start_as_current_span.return_value.__exit__.return_value = None

            result = test_function(event, context)

            # Should return formatted error response
            assert "response" in result
            body_data = json.loads(result["response"]["body"])
            assert "Invalid parameters" in body_data["error"]
            assert body_data["error_type"] == "validation"


class TestWeatherHandler:
    """Test weather Lambda handler."""

    @patch("infrastructure.lambda_functions.shared.lambda_handler._tracer")
    @patch("requests.get")
    def test_successful_weather_request(self, mock_requests_get, mock_lambda_tracer):
        """Test successful weather data retrieval."""
        # Mock the HTTP responses
        mock_points_response = Mock()
        mock_points_response.status_code = 200
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/SEW/124,67/forecast"
            }
        }
        mock_points_response.content = b'{"test": "data"}'

        mock_forecast_response = Mock()
        mock_forecast_response.status_code = 200
        mock_forecast_response.json.return_value = {
            "properties": {
                "periods": [
                    {
                        "temperature": 72,
                        "temperatureUnit": "F",
                        "windSpeed": "10 mph",
                        "windDirection": "NW",
                        "shortForecast": "Sunny",
                        "detailedForecast": "Sunny skies with light winds",
                    }
                ]
            }
        }
        mock_forecast_response.content = b'{"test": "forecast"}'

        mock_requests_get.side_effect = [mock_points_response, mock_forecast_response]

        # Create test event
        event = {
            "parameters": [
                {"name": "latitude", "value": "47.6062", "type": "number"},
                {"name": "longitude", "value": "-122.3321", "type": "number"},
            ],
            "agent": {"agentId": "test-agent"},
            "function": {"functionName": "get_weather"},
        }

        context = Mock()
        context.function_name = "get_weather"
        context.function_version = "1"
        context.aws_request_id = "test-request"
        context.get_remaining_time_in_millis.return_value = 30000
        context.memory_limit_in_mb = 256

        # Set up proper context manager mock for tracer
        mock_span = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_span)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_lambda_tracer.start_as_current_span.return_value = mock_context_manager

        # Import the actual lambda handler
        from infrastructure.lambda_functions.get_weather.lambda_function import (
            lambda_handler,
        )

        result = lambda_handler(event, context)

        # Verify response format
        assert "response" in result
        body_data = json.loads(
            result["response"]["responseBody"]["application/json"]["body"]
        )

        assert body_data["success"] is True
        assert body_data["temperature"]["value"] == 72
        assert body_data["temperature"]["unit"] == "F"
        assert body_data["shortForecast"] == "Sunny"

    @patch("infrastructure.lambda_functions.shared.lambda_handler._tracer")
    def test_missing_coordinates(self, mock_lambda_tracer):
        """Test weather handler with missing coordinates."""
        event = {
            "parameters": [
                {"name": "latitude", "value": "47.6062", "type": "number"}
                # Missing longitude
            ],
            "agent": {"agentId": "test-agent"},
            "function": {"functionName": "get_weather"},
        }

        context = Mock()
        context.function_name = "get_weather"
        context.function_version = "1"
        context.aws_request_id = "test-request"
        context.get_remaining_time_in_millis.return_value = 30000
        context.memory_limit_in_mb = 256

        # Set up proper context manager mock for lambda tracer
        mock_span = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_span)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_lambda_tracer.start_as_current_span.return_value = mock_context_manager

        # Import the actual lambda handler
        from infrastructure.lambda_functions.get_weather.lambda_function import (
            lambda_handler,
        )

        result = lambda_handler(event, context)

        # Should return error response
        assert "response" in result
        body_data = json.loads(
            result["response"]["responseBody"]["application/json"]["body"]
        )
        assert (
            "Both latitude and longitude parameters are required" in body_data["error"]
        )


class TestAlertsHandler:
    """Test alerts Lambda handler."""

    @patch("infrastructure.lambda_functions.shared.lambda_handler._tracer")
    @patch("requests.get")
    def test_successful_alerts_request_no_alerts(
        self, mock_requests_get, mock_lambda_tracer
    ):
        """Test successful alerts retrieval with no active alerts."""
        # Mock the HTTP responses
        mock_points_response = Mock()
        mock_points_response.status_code = 200
        mock_points_response.json.return_value = {
            "properties": {"county": "https://api.weather.gov/zones/county/WAC033"}
        }
        mock_points_response.content = b'{"test": "data"}'

        mock_alerts_response = Mock()
        mock_alerts_response.status_code = 200
        mock_alerts_response.json.return_value = {"features": []}  # No alerts
        mock_alerts_response.content = b'{"features": []}'

        mock_requests_get.side_effect = [mock_points_response, mock_alerts_response]

        event = {
            "parameters": [
                {"name": "latitude", "value": "47.6062", "type": "number"},
                {"name": "longitude", "value": "-122.3321", "type": "number"},
            ]
        }

        context = Mock()
        context.function_name = "get_alerts"
        context.function_version = "1"
        context.aws_request_id = "test-request"
        context.get_remaining_time_in_millis.return_value = 30000
        context.memory_limit_in_mb = 256

        # Set up proper context manager mock for tracer
        mock_span = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_span)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_lambda_tracer.start_as_current_span.return_value = mock_context_manager

        # Import the actual lambda handler
        from infrastructure.lambda_functions.get_alerts.lambda_function import (
            lambda_handler,
        )

        result = lambda_handler(event, context)

        # Verify response format
        assert "response" in result
        body_data = json.loads(
            result["response"]["responseBody"]["application/json"]["body"]
        )

        assert body_data["success"] is True
        assert body_data["alert_count"] == 0
        assert len(body_data["alerts"]) == 0
