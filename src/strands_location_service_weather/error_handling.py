"""
Protocol-specific error handling with OpenTelemetry observability.

This module implements unified error handling across Python/MCP/HTTP protocols
for different deployment modes, with comprehensive OpenTelemetry tracing and
standardized error response formatting.

Requirements addressed:
- 8.5: Standardized error handling and timeout behavior
- 9.1: OpenTelemetry error spans and metrics
- 9.3: Request correlation and tool execution tracking
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .config import DeploymentMode

# Get logger for this module
logger = logging.getLogger(__name__)

# Get tracer for OpenTelemetry spans
tracer = trace.get_tracer(__name__)


class ErrorCategory(Enum):
    """Categories of errors for consistent classification."""

    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL = "internal"
    PROTOCOL = "protocol"
    TOOL_EXECUTION = "tool_execution"


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error handling and observability."""

    deployment_mode: DeploymentMode
    protocol: str
    tool_name: str | None = None
    request_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StandardizedError:
    """Standardized error format that works across all protocols."""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: str | None = None
    error_code: str | None = None
    retry_after: int | None = None
    context: ErrorContext | None = None
    original_exception: Exception | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        result = {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.details:
            result["details"] = self.details
        if self.error_code:
            result["error_code"] = self.error_code
        if self.retry_after:
            result["retry_after"] = self.retry_after
        if self.context:
            result["context"] = {
                "deployment_mode": self.context.deployment_mode.value,
                "protocol": self.context.protocol,
                "tool_name": self.context.tool_name,
                "request_id": self.context.request_id,
                "session_id": self.context.session_id,
                "trace_id": self.context.trace_id,
                "span_id": self.context.span_id,
                "metadata": self.context.metadata,
            }

        return result

    def to_json(self) -> str:
        """Convert error to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


class ProtocolErrorHandler(ABC):
    """Abstract base class for protocol-specific error handlers."""

    def __init__(self, deployment_mode: DeploymentMode):
        self.deployment_mode = deployment_mode
        self.protocol_name = self._get_protocol_name()

    @abstractmethod
    def _get_protocol_name(self) -> str:
        """Get the protocol name for this handler."""
        pass

    @abstractmethod
    def format_error_response(self, error: StandardizedError) -> Any:
        """Format error for protocol-specific response."""
        pass

    @abstractmethod
    def extract_error_context(self, **kwargs) -> ErrorContext:
        """Extract error context from protocol-specific parameters."""
        pass

    def handle_error(
        self, exception: Exception, context: ErrorContext | None = None, **kwargs
    ) -> Any:
        """Handle error with OpenTelemetry observability and protocol formatting.

        Args:
            exception: The original exception
            context: Error context information
            **kwargs: Additional protocol-specific parameters

        Returns:
            Protocol-specific error response
        """
        # Generate unique error ID for tracking
        error_id = self._generate_error_id()

        # Extract context if not provided
        if context is None:
            context = self.extract_error_context(**kwargs)

        # Classify the error
        category, severity = self._classify_error(exception)

        # Create standardized error
        standardized_error = StandardizedError(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(exception),
            details=self._extract_error_details(exception),
            error_code=self._get_error_code(exception),
            context=context,
            original_exception=exception,
        )

        # Record error with OpenTelemetry
        self._record_error_telemetry(standardized_error, exception)

        # Log error with structured logging
        self._log_error(standardized_error)

        # Format response for protocol
        return self.format_error_response(standardized_error)

    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid

        return f"err_{int(time.time())}_{str(uuid.uuid4())[:8]}"

    def _classify_error(
        self, exception: Exception
    ) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        # Map exception types to categories and severities
        error_mapping = {
            ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            TypeError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            KeyError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            TimeoutError: (ErrorCategory.TIMEOUT, ErrorSeverity.HIGH),
            PermissionError: (ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH),
            FileNotFoundError: (ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM),
            ImportError: (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH),
            ModuleNotFoundError: (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH),
        }

        # Check for specific error types
        exception_type = type(exception)
        if exception_type in error_mapping:
            return error_mapping[exception_type]

        # Check for requests library errors
        try:
            import requests

            if isinstance(exception, requests.RequestException):
                if isinstance(exception, requests.Timeout):
                    return ErrorCategory.TIMEOUT, ErrorSeverity.HIGH
                elif isinstance(exception, requests.ConnectionError):
                    return ErrorCategory.NETWORK, ErrorSeverity.HIGH
                elif isinstance(exception, requests.HTTPError):
                    # Classify by HTTP status code
                    if hasattr(exception, "response") and exception.response:
                        status_code = exception.response.status_code
                        if 400 <= status_code < 500:
                            return ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM
                        elif status_code >= 500:
                            return ErrorCategory.SERVICE_UNAVAILABLE, ErrorSeverity.HIGH
                    return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
                else:
                    return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        except ImportError:
            pass

        # Check error message for common patterns
        error_message = str(exception).lower()
        if "timeout" in error_message:
            return ErrorCategory.TIMEOUT, ErrorSeverity.HIGH
        elif "connection" in error_message:
            return ErrorCategory.NETWORK, ErrorSeverity.HIGH
        elif "permission" in error_message or "unauthorized" in error_message:
            return ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH
        elif "not found" in error_message:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
        elif "rate limit" in error_message:
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM

        # Default classification
        return ErrorCategory.INTERNAL, ErrorSeverity.HIGH

    def _extract_error_details(self, exception: Exception) -> str | None:
        """Extract detailed error information."""
        details = []

        # Add exception type
        details.append(f"Exception type: {type(exception).__name__}")

        # Add module information
        if hasattr(exception, "__module__"):
            details.append(f"Module: {exception.__module__}")

        # Add traceback information (limited for security)
        try:
            import traceback

            tb_lines = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            # Only include the last few lines to avoid exposing sensitive information
            if len(tb_lines) > 3:
                details.append(f"Traceback (last 2 lines): {' '.join(tb_lines[-2:])}")
            else:
                details.append(f"Traceback: {' '.join(tb_lines)}")
        except Exception:
            details.append("Traceback: Unable to extract traceback information")

        return " | ".join(details) if details else None

    def _get_error_code(self, exception: Exception) -> str | None:
        """Get error code for the exception."""
        # Map common exceptions to error codes
        error_codes = {
            ValueError: "INVALID_INPUT",
            TypeError: "TYPE_ERROR",
            KeyError: "MISSING_KEY",
            ConnectionError: "CONNECTION_FAILED",
            TimeoutError: "TIMEOUT",
            PermissionError: "PERMISSION_DENIED",
            FileNotFoundError: "FILE_NOT_FOUND",
            ImportError: "IMPORT_ERROR",
            ModuleNotFoundError: "MODULE_NOT_FOUND",
        }

        exception_type = type(exception)
        if exception_type in error_codes:
            return error_codes[exception_type]

        # Check for requests library errors
        try:
            import requests

            if isinstance(exception, requests.RequestException):
                if isinstance(exception, requests.Timeout):
                    return "HTTP_TIMEOUT"
                elif isinstance(exception, requests.ConnectionError):
                    return "HTTP_CONNECTION_ERROR"
                elif isinstance(exception, requests.HTTPError):
                    if hasattr(exception, "response") and exception.response:
                        return f"HTTP_{exception.response.status_code}"
                    return "HTTP_ERROR"
                else:
                    return "HTTP_REQUEST_ERROR"
        except ImportError:
            pass

        return "UNKNOWN_ERROR"

    def _record_error_telemetry(self, error: StandardizedError, exception: Exception):
        """Record error information with OpenTelemetry following OTEL best practices.

        Based on OpenTelemetry error handling best practices:
        - Use semantic conventions for error attributes
        - Record exceptions with proper context
        - Set span status appropriately
        - Include relevant error metadata
        """
        # Get current span or create a new one
        current_span = trace.get_current_span()

        if current_span and current_span.is_recording():
            # Follow OpenTelemetry semantic conventions for error attributes
            # https://opentelemetry.io/docs/specs/semconv/exceptions/
            current_span.set_attribute("error.type", type(exception).__name__)
            current_span.set_attribute("error.message", str(exception))

            # Custom attributes for our error handling system
            current_span.set_attribute("error.id", error.error_id)
            current_span.set_attribute("error.category", error.category.value)
            current_span.set_attribute("error.severity", error.severity.value)
            current_span.set_attribute("error.protocol", self.protocol_name)
            current_span.set_attribute(
                "error.deployment_mode", self.deployment_mode.value
            )

            if error.error_code:
                current_span.set_attribute("error.code", error.error_code)

            if error.context and error.context.tool_name:
                current_span.set_attribute("error.tool_name", error.context.tool_name)

            # Add request correlation attributes if available
            if error.context:
                if error.context.request_id:
                    current_span.set_attribute("request.id", error.context.request_id)
                if error.context.session_id:
                    current_span.set_attribute("session.id", error.context.session_id)
                if error.context.user_id:
                    current_span.set_attribute("user.id", error.context.user_id)

            # Record the exception with full context (OTEL best practice)
            current_span.record_exception(
                exception,
                attributes={
                    "exception.escaped": "false",  # Exception was handled
                    "exception.category": error.category.value,
                    "exception.severity": error.severity.value,
                },
            )

            # Set span status to error with descriptive message
            current_span.set_status(
                Status(StatusCode.ERROR, f"{error.category.value}: {error.message}")
            )
        else:
            # Create a new span for error recording following OTEL naming conventions
            with tracer.start_as_current_span(
                f"error_handler.{self.protocol_name}", kind=trace.SpanKind.INTERNAL
            ) as span:
                # Follow same attribute setting pattern as above
                span.set_attribute("error.type", type(exception).__name__)
                span.set_attribute("error.message", str(exception))
                span.set_attribute("error.id", error.error_id)
                span.set_attribute("error.category", error.category.value)
                span.set_attribute("error.severity", error.severity.value)
                span.set_attribute("error.protocol", self.protocol_name)
                span.set_attribute("error.deployment_mode", self.deployment_mode.value)

                if error.error_code:
                    span.set_attribute("error.code", error.error_code)

                if error.context and error.context.tool_name:
                    span.set_attribute("error.tool_name", error.context.tool_name)

                # Add request correlation attributes
                if error.context:
                    if error.context.request_id:
                        span.set_attribute("request.id", error.context.request_id)
                    if error.context.session_id:
                        span.set_attribute("session.id", error.context.session_id)

                span.record_exception(
                    exception,
                    attributes={
                        "exception.escaped": "false",
                        "exception.category": error.category.value,
                        "exception.severity": error.severity.value,
                    },
                )
                span.set_status(
                    Status(StatusCode.ERROR, f"{error.category.value}: {error.message}")
                )

    def _log_error(self, error: StandardizedError):
        """Log error with structured logging."""
        log_data = {
            "error_id": error.error_id,
            "category": error.category.value,
            "severity": error.severity.value,
            "error_message": error.message,  # Changed from 'message' to avoid conflict
            "protocol": self.protocol_name,
            "deployment_mode": self.deployment_mode.value,
            "timestamp": error.timestamp.isoformat(),
        }

        if error.error_code:
            log_data["error_code"] = error.error_code

        if error.context:
            log_data["context"] = {
                "tool_name": error.context.tool_name,
                "request_id": error.context.request_id,
                "session_id": error.context.session_id,
                "trace_id": error.context.trace_id,
            }

        # Log at appropriate level based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error("High severity error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error occurred", extra=log_data)
        else:
            logger.info("Low severity error occurred", extra=log_data)


class PythonDirectErrorHandler(ProtocolErrorHandler):
    """Error handler for Python direct function calls (LOCAL mode)."""

    def _get_protocol_name(self) -> str:
        return "python_direct"

    def format_error_response(self, error: StandardizedError) -> dict[str, Any]:
        """Format error for Python direct response."""
        return {
            "error": error.message,
            "error_id": error.error_id,
            "error_code": error.error_code,
            "category": error.category.value,
            "severity": error.severity.value,
            "timestamp": error.timestamp.isoformat(),
            "success": False,
        }

    def extract_error_context(self, **kwargs) -> ErrorContext:
        """Extract error context from Python direct parameters."""
        return ErrorContext(
            deployment_mode=self.deployment_mode,
            protocol=self.protocol_name,
            tool_name=kwargs.get("tool_name"),
            request_id=kwargs.get("request_id"),
            trace_id=self._get_current_trace_id(),
            span_id=self._get_current_span_id(),
            metadata=kwargs.get("metadata", {}),
        )

    def _get_current_trace_id(self) -> str | None:
        """Get current trace ID from OpenTelemetry context."""
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = current_span.get_span_context().trace_id
                return f"{trace_id:032x}"
        except Exception:
            pass
        return None

    def _get_current_span_id(self) -> str | None:
        """Get current span ID from OpenTelemetry context."""
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                span_id = current_span.get_span_context().span_id
                return f"{span_id:016x}"
        except Exception:
            pass
        return None


class MCPErrorHandler(ProtocolErrorHandler):
    """Error handler for Model Context Protocol (MCP mode)."""

    def _get_protocol_name(self) -> str:
        return "mcp"

    def format_error_response(self, error: StandardizedError) -> dict[str, Any]:
        """Format error for MCP JSON-RPC response following MCP best practices.

        Based on MCP error handling discussion:
        - Use standard JSON-RPC 2.0 error codes where appropriate
        - Include detailed error information in data field
        - Maintain compatibility with MCP clients
        - Support error recovery and retry logic
        """
        # MCP uses JSON-RPC 2.0 error format
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": self._get_jsonrpc_error_code(error.category),
                "message": error.message,
                "data": {
                    "error_id": error.error_id,
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "error_code": error.error_code,
                    "timestamp": error.timestamp.isoformat(),
                    "protocol": "mcp",
                    # Add MCP-specific error metadata
                    "retryable": error.category
                    in [
                        ErrorCategory.NETWORK,
                        ErrorCategory.TIMEOUT,
                        ErrorCategory.RATE_LIMIT,
                        ErrorCategory.SERVICE_UNAVAILABLE,
                    ],
                },
            },
            "id": error.context.request_id if error.context else None,
        }

        # Add retry_after for rate limiting errors
        if error.category == ErrorCategory.RATE_LIMIT and error.retry_after:
            error_response["error"]["data"]["retry_after"] = error.retry_after

        # Add tool-specific context for MCP tool errors
        if error.context and error.context.tool_name:
            error_response["error"]["data"]["tool_name"] = error.context.tool_name

        # Add trace correlation for debugging
        if error.context:
            if error.context.trace_id:
                error_response["error"]["data"]["trace_id"] = error.context.trace_id
            if error.context.session_id:
                error_response["error"]["data"]["session_id"] = error.context.session_id

        return error_response

    def extract_error_context(self, **kwargs) -> ErrorContext:
        """Extract error context from MCP parameters."""
        return ErrorContext(
            deployment_mode=self.deployment_mode,
            protocol=self.protocol_name,
            tool_name=kwargs.get("tool_name"),
            request_id=kwargs.get("request_id"),
            session_id=kwargs.get("session_id"),
            trace_id=self._get_current_trace_id(),
            span_id=self._get_current_span_id(),
            metadata=kwargs.get("metadata", {}),
        )

    def _get_jsonrpc_error_code(self, category: ErrorCategory) -> int:
        """Map error category to JSON-RPC error code."""
        # JSON-RPC 2.0 standard error codes
        error_code_mapping = {
            ErrorCategory.VALIDATION: -32602,  # Invalid params
            ErrorCategory.CONFIGURATION: -32601,  # Method not found
            ErrorCategory.INTERNAL: -32603,  # Internal error
            ErrorCategory.PROTOCOL: -32600,  # Invalid request
            ErrorCategory.NETWORK: -32603,  # Internal error
            ErrorCategory.TIMEOUT: -32603,  # Internal error
            ErrorCategory.SERVICE_UNAVAILABLE: -32603,  # Internal error
            ErrorCategory.AUTHENTICATION: -32001,  # Custom: Authentication error
            ErrorCategory.AUTHORIZATION: -32002,  # Custom: Authorization error
            ErrorCategory.RATE_LIMIT: -32003,  # Custom: Rate limit error
            ErrorCategory.TOOL_EXECUTION: -32004,  # Custom: Tool execution error
        }

        return error_code_mapping.get(category, -32603)  # Default to internal error

    def _get_current_trace_id(self) -> str | None:
        """Get current trace ID from OpenTelemetry context."""
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = current_span.get_span_context().trace_id
                return f"{trace_id:032x}"
        except Exception:
            pass
        return None

    def _get_current_span_id(self) -> str | None:
        """Get current span ID from OpenTelemetry context."""
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                span_id = current_span.get_span_context().span_id
                return f"{span_id:016x}"
        except Exception:
            pass
        return None


class HTTPRestErrorHandler(ProtocolErrorHandler):
    """Error handler for HTTP/REST via Lambda functions (BEDROCK_AGENT mode)."""

    def _get_protocol_name(self) -> str:
        return "http_rest"

    def format_error_response(self, error: StandardizedError) -> dict[str, Any]:
        """Format error for Bedrock Agent Lambda response."""
        # Bedrock Agent expects specific response format
        error_response = {
            "error": error.message,
            "error_id": error.error_id,
            "error_type": error.category.value,
            "error_code": error.error_code,
            "severity": error.severity.value,
            "timestamp": error.timestamp.isoformat(),
            "success": False,
        }

        # Add retry information for recoverable errors
        if error.category in [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
        ]:
            error_response["retryable"] = True
            if error.retry_after:
                error_response["retry_after"] = error.retry_after
        else:
            error_response["retryable"] = False

        # Bedrock Agent Lambda response format
        return {
            "messageVersion": "1.0",
            "response": {
                "body": json.dumps(error_response, default=str, ensure_ascii=False),
                "contentType": "application/json",
            },
        }

    def extract_error_context(self, **kwargs) -> ErrorContext:
        """Extract error context from Bedrock Agent Lambda parameters."""
        # Extract Bedrock Agent-specific context
        lambda_context = kwargs.get("lambda_context")
        bedrock_agent_event = kwargs.get("bedrock_agent_event", {})

        request_id = None
        session_id = None

        if lambda_context:
            request_id = getattr(lambda_context, "aws_request_id", None)

        if isinstance(bedrock_agent_event, dict):
            session_id = bedrock_agent_event.get("sessionId")

        return ErrorContext(
            deployment_mode=self.deployment_mode,
            protocol=self.protocol_name,
            tool_name=kwargs.get("tool_name"),
            request_id=request_id,
            session_id=session_id,
            trace_id=self._get_current_trace_id(),
            span_id=self._get_current_span_id(),
            metadata={
                "lambda_function_name": (
                    getattr(lambda_context, "function_name", None)
                    if lambda_context
                    else None
                ),
                "lambda_function_version": (
                    getattr(lambda_context, "function_version", None)
                    if lambda_context
                    else None
                ),
                "lambda_memory_limit": (
                    getattr(lambda_context, "memory_limit_in_mb", None)
                    if lambda_context
                    else None
                ),
                "bedrock_agent_id": (
                    bedrock_agent_event.get("agent", {}).get("agentId")
                    if isinstance(bedrock_agent_event, dict)
                    else None
                ),
                "bedrock_action_group": (
                    bedrock_agent_event.get("actionGroup", {}).get("actionGroupName")
                    if isinstance(bedrock_agent_event, dict)
                    else None
                ),
                **kwargs.get("metadata", {}),
            },
        )

    def _get_current_trace_id(self) -> str | None:
        """Get current trace ID from OpenTelemetry context."""
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = current_span.get_span_context().trace_id
                return f"{trace_id:032x}"
        except Exception:
            pass
        return None

    def _get_current_span_id(self) -> str | None:
        """Get current span ID from OpenTelemetry context."""
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                span_id = current_span.get_span_context().span_id
                return f"{span_id:016x}"
        except Exception:
            pass
        return None


class ErrorHandlerFactory:
    """Factory for creating protocol-specific error handlers."""

    @staticmethod
    def create_handler(deployment_mode: DeploymentMode) -> ProtocolErrorHandler:
        """Create appropriate error handler for deployment mode.

        Args:
            deployment_mode: Deployment mode

        Returns:
            Protocol-specific error handler

        Raises:
            ValueError: If deployment mode is not supported
        """
        handler_mapping = {
            DeploymentMode.LOCAL: PythonDirectErrorHandler,
            DeploymentMode.MCP: MCPErrorHandler,
            DeploymentMode.BEDROCK_AGENT: HTTPRestErrorHandler,
        }

        handler_class = handler_mapping.get(deployment_mode)
        if not handler_class:
            raise ValueError(
                f"No error handler available for deployment mode: {deployment_mode.value}"
            )

        return handler_class(deployment_mode)


# Convenience functions for error handling
def handle_error(
    exception: Exception,
    deployment_mode: DeploymentMode,
    context: ErrorContext | None = None,
    **kwargs,
) -> Any:
    """Handle error with appropriate protocol handler.

    Args:
        exception: The exception to handle
        deployment_mode: Current deployment mode
        context: Optional error context
        **kwargs: Additional protocol-specific parameters

    Returns:
        Protocol-specific error response
    """
    handler = ErrorHandlerFactory.create_handler(deployment_mode)
    return handler.handle_error(exception, context, **kwargs)


def create_error_context(
    deployment_mode: DeploymentMode, tool_name: str | None = None, **kwargs
) -> ErrorContext:
    """Create error context for the deployment mode.

    Args:
        deployment_mode: Current deployment mode
        tool_name: Name of the tool being executed
        **kwargs: Additional context parameters

    Returns:
        Error context for the deployment mode
    """
    handler = ErrorHandlerFactory.create_handler(deployment_mode)
    return handler.extract_error_context(tool_name=tool_name, **kwargs)
