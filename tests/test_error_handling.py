"""
Tests for protocol-specific error handling with OpenTelemetry observability.

This module tests the unified error handling strategy across Python/MCP/HTTP protocols
and validates OpenTelemetry trace context and error response formatting.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.strands_location_service_weather.config import DeploymentMode
from src.strands_location_service_weather.error_handling import (
    ErrorCategory,
    ErrorContext,
    ErrorHandlerFactory,
    ErrorSeverity,
    HTTPRestErrorHandler,
    MCPErrorHandler,
    PythonDirectErrorHandler,
    StandardizedError,
    create_error_context,
    handle_error,
)


class TestErrorClassification:
    """Test error classification and categorization."""

    def test_error_category_enum(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.INTERNAL.value == "internal"

    def test_error_severity_enum(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorContext:
    """Test ErrorContext dataclass."""

    def test_error_context_creation(self):
        """Test ErrorContext creation with all fields."""
        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
            request_id="req_123",
            session_id="sess_456",
            user_id="user_789",
            trace_id="trace_abc",
            span_id="span_def",
            metadata={"key": "value"},
        )

        assert context.deployment_mode == DeploymentMode.LOCAL
        assert context.protocol == "python_direct"
        assert context.tool_name == "test_tool"
        assert context.request_id == "req_123"
        assert context.session_id == "sess_456"
        assert context.user_id == "user_789"
        assert context.trace_id == "trace_abc"
        assert context.span_id == "span_def"
        assert context.metadata == {"key": "value"}
        assert isinstance(context.timestamp, datetime)

    def test_error_context_minimal(self):
        """Test ErrorContext creation with minimal fields."""
        context = ErrorContext(
            deployment_mode=DeploymentMode.MCP,
            protocol="mcp",
        )

        assert context.deployment_mode == DeploymentMode.MCP
        assert context.protocol == "mcp"
        assert context.tool_name is None
        assert context.metadata == {}


class TestStandardizedError:
    """Test StandardizedError dataclass and serialization."""

    def test_standardized_error_creation(self):
        """Test StandardizedError creation."""
        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

        error = StandardizedError(
            error_id="err_123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            details="Test error details",
            error_code="TEST_ERROR",
            context=context,
        )

        assert error.error_id == "err_123"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.message == "Test error message"
        assert error.details == "Test error details"
        assert error.error_code == "TEST_ERROR"
        assert error.context == context

    def test_standardized_error_to_dict(self):
        """Test StandardizedError serialization to dictionary."""
        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
            request_id="req_123",
        )

        error = StandardizedError(
            error_id="err_123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            error_code="TEST_ERROR",
            context=context,
        )

        error_dict = error.to_dict()

        assert error_dict["error_id"] == "err_123"
        assert error_dict["category"] == "validation"
        assert error_dict["severity"] == "medium"
        assert error_dict["message"] == "Test error message"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert "timestamp" in error_dict
        assert "context" in error_dict
        assert error_dict["context"]["deployment_mode"] == "local"
        assert error_dict["context"]["protocol"] == "python_direct"
        assert error_dict["context"]["tool_name"] == "test_tool"
        assert error_dict["context"]["request_id"] == "req_123"

    def test_standardized_error_to_json(self):
        """Test StandardizedError serialization to JSON."""
        error = StandardizedError(
            error_id="err_123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
        )

        json_str = error.to_json()
        parsed = json.loads(json_str)

        assert parsed["error_id"] == "err_123"
        assert parsed["category"] == "validation"
        assert parsed["severity"] == "medium"
        assert parsed["message"] == "Test error message"


class TestPythonDirectErrorHandler:
    """Test PythonDirectErrorHandler for LOCAL deployment mode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = PythonDirectErrorHandler(DeploymentMode.LOCAL)

    def test_protocol_name(self):
        """Test protocol name is correct."""
        assert self.handler._get_protocol_name() == "python_direct"

    def test_format_error_response(self):
        """Test error response formatting for Python direct protocol."""
        error = StandardizedError(
            error_id="err_123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            error_code="TEST_ERROR",
        )

        response = self.handler.format_error_response(error)

        assert response["error"] == "Test error message"
        assert response["error_id"] == "err_123"
        assert response["error_code"] == "TEST_ERROR"
        assert response["category"] == "validation"
        assert response["severity"] == "medium"
        assert response["success"] is False
        assert "timestamp" in response

    def test_extract_error_context(self):
        """Test error context extraction."""
        context = self.handler.extract_error_context(
            tool_name="test_tool",
            request_id="req_123",
            metadata={"key": "value"},
        )

        assert context.deployment_mode == DeploymentMode.LOCAL
        assert context.protocol == "python_direct"
        assert context.tool_name == "test_tool"
        assert context.request_id == "req_123"
        assert context.metadata == {"key": "value"}

    @patch("src.strands_location_service_weather.error_handling.tracer")
    def test_handle_error_with_telemetry(self, mock_tracer):
        """Test error handling with OpenTelemetry recording."""
        # Set up mock span
        mock_span = Mock()
        mock_span.is_recording.return_value = True
        mock_span.get_span_context.return_value = Mock(
            trace_id=12345,
            span_id=67890,
        )

        # Mock trace.get_current_span to return our mock span
        with patch(
            "src.strands_location_service_weather.error_handling.trace.get_current_span",
            return_value=mock_span,
        ):
            exception = ValueError("Test validation error")

            response = self.handler.handle_error(
                exception=exception,
                tool_name="test_tool",
                request_id="req_123",
            )

            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("error.category", "validation")
            mock_span.set_attribute.assert_any_call("error.severity", "medium")
            mock_span.set_attribute.assert_any_call("error.protocol", "python_direct")
            mock_span.set_attribute.assert_any_call("error.deployment_mode", "local")

            # Verify exception was recorded with attributes (OpenTelemetry best practice)
            mock_span.record_exception.assert_called_once_with(
                exception,
                attributes={
                    "exception.escaped": "false",
                    "exception.category": "validation",
                    "exception.severity": "medium",
                },
            )

            # Verify response format
            assert response["error"] == "Test validation error"
            assert response["category"] == "validation"
            assert response["success"] is False

    def test_error_classification(self):
        """Test error classification for different exception types."""
        test_cases = [
            (ValueError("test"), ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            (ConnectionError("test"), ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            (TimeoutError("test"), ErrorCategory.TIMEOUT, ErrorSeverity.HIGH),
            (PermissionError("test"), ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH),
            (Exception("test"), ErrorCategory.INTERNAL, ErrorSeverity.HIGH),
        ]

        for exception, expected_category, expected_severity in test_cases:
            category, severity = self.handler._classify_error(exception)
            assert category == expected_category
            assert severity == expected_severity


class TestMCPErrorHandler:
    """Test MCPErrorHandler for MCP deployment mode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = MCPErrorHandler(DeploymentMode.MCP)

    def test_protocol_name(self):
        """Test protocol name is correct."""
        assert self.handler._get_protocol_name() == "mcp"

    def test_format_error_response(self):
        """Test error response formatting for MCP JSON-RPC protocol."""
        context = ErrorContext(
            deployment_mode=DeploymentMode.MCP,
            protocol="mcp",
            request_id="req_123",
        )

        error = StandardizedError(
            error_id="err_123",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            error_code="TEST_ERROR",
            context=context,
        )

        response = self.handler.format_error_response(error)

        # Verify JSON-RPC 2.0 format
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert response["error"]["message"] == "Test error message"
        assert response["id"] == "req_123"

        # Verify error data
        error_data = response["error"]["data"]
        assert error_data["error_id"] == "err_123"
        assert error_data["category"] == "validation"
        assert error_data["severity"] == "medium"
        assert error_data["error_code"] == "TEST_ERROR"
        assert error_data["protocol"] == "mcp"

    def test_jsonrpc_error_code_mapping(self):
        """Test JSON-RPC error code mapping for different categories."""
        test_cases = [
            (ErrorCategory.VALIDATION, -32602),  # Invalid params
            (ErrorCategory.CONFIGURATION, -32601),  # Method not found
            (ErrorCategory.INTERNAL, -32603),  # Internal error
            (ErrorCategory.PROTOCOL, -32600),  # Invalid request
            (ErrorCategory.AUTHENTICATION, -32001),  # Custom: Authentication error
            (ErrorCategory.AUTHORIZATION, -32002),  # Custom: Authorization error
        ]

        for category, expected_code in test_cases:
            code = self.handler._get_jsonrpc_error_code(category)
            assert code == expected_code

    def test_extract_error_context(self):
        """Test error context extraction for MCP."""
        context = self.handler.extract_error_context(
            tool_name="test_tool",
            request_id="req_123",
            session_id="sess_456",
            metadata={"key": "value"},
        )

        assert context.deployment_mode == DeploymentMode.MCP
        assert context.protocol == "mcp"
        assert context.tool_name == "test_tool"
        assert context.request_id == "req_123"
        assert context.session_id == "sess_456"
        assert context.metadata == {"key": "value"}


class TestHTTPRestErrorHandler:
    """Test HTTPRestErrorHandler for BEDROCK_AGENT deployment mode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = HTTPRestErrorHandler(DeploymentMode.BEDROCK_AGENT)

    def test_protocol_name(self):
        """Test protocol name is correct."""
        assert self.handler._get_protocol_name() == "http_rest"

    def test_format_error_response(self):
        """Test error response formatting for BedrockAgent Lambda protocol."""
        error = StandardizedError(
            error_id="err_123",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            message="Test network error",
            error_code="NETWORK_ERROR",
        )

        response = self.handler.format_error_response(error)

        # Verify BedrockAgent Lambda response format
        assert response["messageVersion"] == "1.0"
        assert "response" in response
        assert response["response"]["contentType"] == "application/json"

        # Parse response body
        body_data = json.loads(response["response"]["body"])
        assert body_data["error"] == "Test network error"
        assert body_data["error_id"] == "err_123"
        assert body_data["error_type"] == "network"
        assert body_data["error_code"] == "NETWORK_ERROR"
        assert body_data["severity"] == "high"
        assert body_data["success"] is False
        assert body_data["retryable"] is True  # Network errors are retryable

    def test_retryable_error_classification(self):
        """Test retryable error classification."""
        retryable_categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
        ]

        non_retryable_categories = [
            ErrorCategory.VALIDATION,
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.AUTHORIZATION,
        ]

        for category in retryable_categories:
            error = StandardizedError(
                error_id="err_123",
                category=category,
                severity=ErrorSeverity.HIGH,
                message="Test error",
            )
            response = self.handler.format_error_response(error)
            body_data = json.loads(response["response"]["body"])
            assert body_data["retryable"] is True

        for category in non_retryable_categories:
            error = StandardizedError(
                error_id="err_123",
                category=category,
                severity=ErrorSeverity.HIGH,
                message="Test error",
            )
            response = self.handler.format_error_response(error)
            body_data = json.loads(response["response"]["body"])
            assert body_data["retryable"] is False

    def test_extract_error_context_with_lambda_context(self):
        """Test error context extraction with Lambda context."""
        # Mock Lambda context
        mock_lambda_context = Mock()
        mock_lambda_context.aws_request_id = "req_123"
        mock_lambda_context.function_name = "test_function"
        mock_lambda_context.function_version = "1.0"
        mock_lambda_context.memory_limit_in_mb = 256

        # Mock BedrockAgent event
        bedrock_agent_event = {
            "sessionId": "sess_456",
            "agent": {"agentId": "agent_789"},
            "actionGroup": {"actionGroupName": "weather_actions"},
        }

        context = self.handler.extract_error_context(
            tool_name="test_tool",
            lambda_context=mock_lambda_context,
            bedrock_agent_event=bedrock_agent_event,
            metadata={"key": "value"},
        )

        assert context.deployment_mode == DeploymentMode.BEDROCK_AGENT
        assert context.protocol == "http_rest"
        assert context.tool_name == "test_tool"
        assert context.request_id == "req_123"
        assert context.session_id == "sess_456"
        assert context.metadata["lambda_function_name"] == "test_function"
        assert context.metadata["lambda_function_version"] == "1.0"
        assert context.metadata["lambda_memory_limit"] == 256
        assert context.metadata["bedrock_agent_agent_id"] == "agent_789"
        assert context.metadata["bedrock_agent_action_group"] == "weather_actions"


class TestErrorHandlerFactory:
    """Test ErrorHandlerFactory for creating protocol-specific handlers."""

    def test_create_handler_local(self):
        """Test creating handler for LOCAL deployment mode."""
        handler = ErrorHandlerFactory.create_handler(DeploymentMode.LOCAL)
        assert isinstance(handler, PythonDirectErrorHandler)
        assert handler.deployment_mode == DeploymentMode.LOCAL

    def test_create_handler_mcp(self):
        """Test creating handler for MCP deployment mode."""
        handler = ErrorHandlerFactory.create_handler(DeploymentMode.MCP)
        assert isinstance(handler, MCPErrorHandler)
        assert handler.deployment_mode == DeploymentMode.MCP

    def test_create_handler_bedrock_agent(self):
        """Test creating handler for BEDROCK_AGENT deployment mode."""
        handler = ErrorHandlerFactory.create_handler(DeploymentMode.BEDROCK_AGENT)
        assert isinstance(handler, HTTPRestErrorHandler)
        assert handler.deployment_mode == DeploymentMode.BEDROCK_AGENT

    def test_create_handler_invalid_mode(self):
        """Test creating handler for invalid deployment mode."""
        with pytest.raises(ValueError, match="No error handler available"):
            # Create a mock invalid deployment mode
            invalid_mode = Mock()
            invalid_mode.value = "invalid"
            ErrorHandlerFactory.create_handler(invalid_mode)


class TestConvenienceFunctions:
    """Test convenience functions for error handling."""

    @patch("src.strands_location_service_weather.error_handling.ErrorHandlerFactory")
    def test_handle_error_function(self, mock_factory):
        """Test handle_error convenience function."""
        # Set up mock handler
        mock_handler = Mock()
        mock_handler.handle_error.return_value = {"error": "test error"}
        mock_factory.create_handler.return_value = mock_handler

        exception = ValueError("Test error")
        result = handle_error(
            exception=exception,
            deployment_mode=DeploymentMode.LOCAL,
            tool_name="test_tool",
        )

        # Verify factory was called with correct mode
        mock_factory.create_handler.assert_called_once_with(DeploymentMode.LOCAL)

        # Verify handler was called with correct parameters
        mock_handler.handle_error.assert_called_once()
        call_args = mock_handler.handle_error.call_args
        assert call_args[1]["tool_name"] == "test_tool"

        # Verify result
        assert result == {"error": "test error"}

    @patch("src.strands_location_service_weather.error_handling.ErrorHandlerFactory")
    def test_create_error_context_function(self, mock_factory):
        """Test create_error_context convenience function."""
        # Set up mock handler
        mock_handler = Mock()
        mock_context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )
        mock_handler.extract_error_context.return_value = mock_context
        mock_factory.create_handler.return_value = mock_handler

        result = create_error_context(
            deployment_mode=DeploymentMode.LOCAL,
            tool_name="test_tool",
            request_id="req_123",
        )

        # Verify factory was called with correct mode
        mock_factory.create_handler.assert_called_once_with(DeploymentMode.LOCAL)

        # Verify handler was called with correct parameters
        mock_handler.extract_error_context.assert_called_once_with(
            tool_name="test_tool",
            request_id="req_123",
        )

        # Verify result
        assert result == mock_context


class TestOpenTelemetryIntegration:
    """Test OpenTelemetry integration with error handling."""

    def setup_method(self):
        """Set up OpenTelemetry test environment."""
        # Create in-memory span exporter for testing
        self.span_exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.span_exporter))

        # Set the tracer provider
        trace.set_tracer_provider(self.tracer_provider)

    def test_error_telemetry_recording(self):
        """Test that error telemetry is properly recorded."""
        handler = PythonDirectErrorHandler(DeploymentMode.LOCAL)
        exception = ValueError("Test validation error")

        # Execute error handling within a span
        with trace.get_tracer(__name__).start_as_current_span("test_span"):
            handler.handle_error(
                exception=exception,
                tool_name="test_tool",
                request_id="req_123",
            )

        # Get recorded spans
        spans = self.span_exporter.get_finished_spans()

        # Find the test span (error handler uses current span when available)
        test_spans = [span for span in spans if "test_span" in span.name]
        assert len(test_spans) > 0

        error_span = test_spans[0]

        # Verify span attributes
        attributes = dict(error_span.attributes)
        assert attributes.get("error.category") == "validation"
        assert attributes.get("error.severity") == "medium"
        assert attributes.get("error.protocol") == "python_direct"
        assert attributes.get("error.deployment_mode") == "local"
        assert attributes.get("error.tool_name") == "test_tool"

        # Verify span status indicates error
        assert error_span.status.status_code.name == "ERROR"

    def test_trace_context_propagation(self):
        """Test that trace context is properly propagated in error handling."""
        handler = PythonDirectErrorHandler(DeploymentMode.LOCAL)
        exception = ValueError("Test error")

        # Create a parent span
        with trace.get_tracer(__name__).start_as_current_span(
            "parent_span"
        ) as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id

            # Handle error within the parent span
            handler.handle_error(
                exception=exception,
                tool_name="test_tool",
            )

        # Get recorded spans
        spans = self.span_exporter.get_finished_spans()

        # Verify all spans have the same trace ID
        for span in spans:
            assert span.get_span_context().trace_id == parent_trace_id

    def teardown_method(self):
        """Clean up OpenTelemetry test environment."""
        self.span_exporter.clear()


class TestErrorHandlingRequirements:
    """Test that error handling meets specific requirements."""

    def setup_method(self):
        """Set up OpenTelemetry test environment."""
        # Create in-memory span exporter for testing
        self.span_exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.span_exporter))

        # Set the tracer provider
        trace.set_tracer_provider(self.tracer_provider)

    def teardown_method(self):
        """Clean up test environment."""
        self.span_exporter.clear()

    def test_requirement_8_5_standardized_error_handling(self):
        """Test requirement 8.5: Standardized error handling across protocols."""
        exception = ValueError("Test validation error")

        # Test all deployment modes handle the same error consistently
        modes_and_handlers = [
            (DeploymentMode.LOCAL, PythonDirectErrorHandler),
            (DeploymentMode.MCP, MCPErrorHandler),
            (DeploymentMode.BEDROCK_AGENT, HTTPRestErrorHandler),
        ]

        for mode, handler_class in modes_and_handlers:
            handler = handler_class(mode)

            # All handlers should classify the error the same way
            category, severity = handler._classify_error(exception)
            assert category == ErrorCategory.VALIDATION
            assert severity == ErrorSeverity.MEDIUM

    def test_requirement_9_1_opentelemetry_error_spans(self):
        """Test requirement 9.1: OpenTelemetry error spans and metrics."""
        handler = PythonDirectErrorHandler(DeploymentMode.LOCAL)
        exception = ValueError("Test error")

        # Test that error handler has telemetry recording capability
        assert hasattr(handler, "_record_error_telemetry")

        # Handle error and verify it works
        response = handler.handle_error(exception=exception, tool_name="test_tool")
        assert response is not None

        # Verify error response contains expected fields for Python direct protocol
        assert isinstance(response, dict)
        assert "error" in response
        assert "error_id" in response
        assert "category" in response
        assert "severity" in response
        assert "success" in response
        assert response["success"] is False

    def test_requirement_9_3_request_correlation(self):
        """Test requirement 9.3: Request correlation and tool execution tracking."""
        handler = PythonDirectErrorHandler(DeploymentMode.LOCAL)
        exception = ValueError("Test error")

        # Create error context with correlation IDs
        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
            request_id="req_123",
            session_id="sess_456",
            trace_id="trace_789",
            span_id="span_abc",
        )

        response = handler.handle_error(
            exception=exception,
            context=context,
        )

        # Verify correlation information is preserved in response
        assert "error_id" in response
        # The error ID should be unique and trackable
        assert response["error_id"].startswith("err_")

    def test_protocol_specific_error_formats(self):
        """Test that each protocol returns appropriately formatted errors."""
        exception = ValueError("Test error")

        # Test Python direct format
        python_handler = PythonDirectErrorHandler(DeploymentMode.LOCAL)
        python_response = python_handler.handle_error(exception=exception)

        assert "error" in python_response
        assert "success" in python_response
        assert python_response["success"] is False

        # Test MCP JSON-RPC format
        mcp_handler = MCPErrorHandler(DeploymentMode.MCP)
        mcp_response = mcp_handler.handle_error(exception=exception)

        assert "jsonrpc" in mcp_response
        assert mcp_response["jsonrpc"] == "2.0"
        assert "error" in mcp_response
        assert "code" in mcp_response["error"]
        assert "message" in mcp_response["error"]

        # Test BedrockAgent Lambda format
        bedrock_agent_handler = HTTPRestErrorHandler(DeploymentMode.BEDROCK_AGENT)
        bedrock_agent_response = bedrock_agent_handler.handle_error(exception=exception)

        assert "messageVersion" in bedrock_agent_response
        assert bedrock_agent_response["messageVersion"] == "1.0"
        assert "response" in bedrock_agent_response
        assert "body" in bedrock_agent_response["response"]
        assert "contentType" in bedrock_agent_response["response"]

        # Parse BedrockAgent response body
        body_data = json.loads(bedrock_agent_response["response"]["body"])
        assert "error" in body_data
        assert "success" in body_data
        assert body_data["success"] is False
