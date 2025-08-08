"""
AgentCore-compliant Lambda handler template for weather tools.

This module provides Lambda function handlers that follow the AgentCore runtime service contract
and AWS Lambda best practices for weather and alert tools. Each handler processes AgentCore
events and returns properly formatted responses with comprehensive error handling,
OpenTelemetry tracing, and optimized performance.

Based on AWS documentation:
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html
- https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import requests
from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider

# Configure structured logging for Lambda CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove default handler and add structured JSON handler
for handler in logger.handlers:
    logger.removeHandler(handler)

# Create structured logging handler for better CloudWatch integration
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Lambda performance optimization: Initialize once per container
_initialized = False
_http_session = None
_tracer = None

# Weather API configuration from environment
WEATHER_API_BASE_URL = os.getenv("WEATHER_API_BASE_URL", "https://api.weather.gov")
WEATHER_API_TIMEOUT = int(os.getenv("WEATHER_API_TIMEOUT", "10"))
USER_AGENT_WEATHER = os.getenv("USER_AGENT_WEATHER", "LocationWeatherService/1.0")
USER_AGENT_ALERTS = os.getenv("USER_AGENT_ALERTS", "LocationWeatherAlertsService/1.0")
ACCEPT_HEADER = os.getenv("ACCEPT_HEADER", "application/geo+json")


def initialize_lambda_environment():
    """
    Initialize Lambda environment once per container.

    This follows AWS Lambda best practices for container reuse optimization.
    """
    global _initialized, _http_session, _tracer

    if _initialized:
        return

    logger.info("Initializing Lambda environment")

    # Initialize OpenTelemetry tracing (simplified for Lambda)
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider()

    # Note: OTLP GRPC exporter removed due to platform compatibility issues
    # AWS Lambda provides X-Ray tracing integration if needed
    logger.info("OpenTelemetry initialized for Lambda (basic tracing)")

    # Instrument requests library for HTTP tracing
    RequestsInstrumentor().instrument()

    # Initialize persistent HTTP session for performance
    _http_session = requests.Session()
    _http_session.headers.update(
        {
            "Accept": ACCEPT_HEADER,
            "User-Agent": "AgentCoreLambda/1.0",  # Will be overridden per request
        }
    )

    # Get tracer instance
    _tracer = trace.get_tracer(__name__)

    _initialized = True
    logger.info("Lambda environment initialization complete")


def parse_agentcore_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Parse AgentCore Lambda event to extract function parameters.

    Supports multiple AgentCore event formats as per runtime service contract.

    Args:
        event: AgentCore Lambda event following runtime service contract

    Returns:
        Dictionary containing parsed parameters with metadata

    Raises:
        ValueError: If event format is invalid or parameters cannot be parsed
    """
    try:
        # Log sanitized event info for debugging
        function_name = event.get("function", {}).get("functionName", "unknown")
        agent_id = event.get("agent", {}).get("agentId", "unknown")
        logger.info(
            f"Processing AgentCore event - Function: {function_name}, Agent: {agent_id}"
        )

        # Validate message version (AgentCore best practice)
        message_version = event.get("messageVersion", "1.0")
        if message_version != "1.0":
            logger.warning(
                f"Unexpected message version: {message_version}, expected 1.0"
            )

        parameters = {}

        # Method 1: Extract from parameters array (preferred AgentCore format)
        if "parameters" in event and isinstance(event["parameters"], list):
            logger.info("Using parameters array format")
            for param in event["parameters"]:
                if isinstance(param, dict) and "name" in param and "value" in param:
                    param_name = param["name"]
                    param_value = param["value"]
                    param_type = param.get("type", "string")

                    # Type conversion based on parameter type
                    if param_type == "number":
                        try:
                            param_value = float(param_value)
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"Invalid number value for parameter {param_name}: {param_value}"
                            ) from e
                    elif param_type == "integer":
                        try:
                            param_value = int(param_value)
                        except (ValueError, TypeError) as e:
                            raise ValueError(
                                f"Invalid integer value for parameter {param_name}: {param_value}"
                            ) from e
                    elif param_type == "boolean":
                        param_value = str(param_value).lower() in ("true", "1", "yes")

                    parameters[param_name] = param_value

        # Method 2: Extract from requestBody content (fallback for compatibility)
        elif "requestBody" in event:
            logger.info("Using requestBody format (fallback)")
            request_body = event.get("requestBody", {})
            content = request_body.get("content", [])

            if content and isinstance(content, list) and len(content) > 0:
                content_item = content[0]
                if isinstance(content_item, dict) and "text" in content_item:
                    parameters_text = content_item.get("text", "{}")
                    try:
                        parsed_params = json.loads(parameters_text)
                        if isinstance(parsed_params, dict):
                            parameters.update(parsed_params)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"Invalid JSON in requestBody content: {e}"
                        ) from e

        # Validate that we found parameters
        if not parameters:
            raise ValueError(
                "No parameters found in AgentCore event. Expected 'parameters' array or 'requestBody' content."
            )

        # Add AgentCore metadata for tracing and debugging
        parameters["_agentcore_metadata"] = {
            "message_version": message_version,
            "agent_id": event.get("agent", {}).get("agentId"),
            "agent_alias_id": event.get("agent", {}).get("agentAliasId"),
            "session_id": event.get("sessionId"),
            "action_group_id": event.get("actionGroup", {}).get("actionGroupId"),
            "action_group_name": event.get("actionGroup", {}).get("actionGroupName"),
            "function_name": function_name,
            "input_text": event.get("inputText", "")[:100],  # Truncate for logging
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Successfully parsed {len(parameters)-1} function parameters")
        return parameters

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in event parameters: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to parse AgentCore event: {e}") from e


def format_agentcore_response(data: Any, success: bool = True) -> dict[str, Any]:
    """
    Format response for AgentCore Lambda functions.

    AgentCore expects responses in the format:
    {
        "messageVersion": "1.0",
        "response": {
            "body": "<json_string>",
            "contentType": "application/json"
        }
    }

    Args:
        data: Response data to be JSON serialized
        success: Whether the operation was successful

    Returns:
        Properly formatted AgentCore response
    """
    try:
        # Ensure data includes success indicator
        if isinstance(data, dict):
            data["success"] = success
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        else:
            data = {
                "result": data,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # For errors, ensure consistent error format
        if not success:
            if not isinstance(data, dict):
                data = {"error": str(data)}
            data["success"] = False

        response_body = json.dumps(data, default=str, ensure_ascii=False)

        return {
            "messageVersion": "1.0",
            "response": {"body": response_body, "contentType": "application/json"},
        }

    except Exception as e:
        # Fallback error response if JSON serialization fails
        logger.error(f"Failed to format AgentCore response: {e}")
        return {
            "messageVersion": "1.0",
            "response": {
                "body": json.dumps(
                    {
                        "error": f"Response formatting error: {str(e)}",
                        "success": False,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                "contentType": "application/json",
            },
        }


def lambda_error_handler(func):
    """
    Decorator for Lambda functions to handle errors and ensure proper AgentCore response format.

    This decorator implements AWS Lambda and AgentCore best practices with comprehensive
    error handling and OpenTelemetry observability.
    """

    def wrapper(event, context):
        # Initialize Lambda environment if needed
        initialize_lambda_environment()

        function_name = getattr(func, "__name__", "unknown_function")
        start_time = time.time()

        # Import error handling components
        try:
            from src.strands_location_service_weather.config import DeploymentMode
            from src.strands_location_service_weather.error_handling import (
                ErrorHandlerFactory,
                create_error_context,
            )

            # Create error context for Lambda execution
            # Ensure event is a dictionary for error handling
            safe_event = event if isinstance(event, dict) else {}
            error_context = create_error_context(
                deployment_mode=DeploymentMode.AGENTCORE,
                tool_name=function_name,
                lambda_context=context,
                agentcore_event=safe_event,
            )

            # Create error handler for AgentCore protocol
            error_handler = ErrorHandlerFactory.create_handler(DeploymentMode.AGENTCORE)

        except ImportError as import_error:
            logger.warning(
                f"Could not import error handling components: {import_error}"
            )
            error_context = None
            error_handler = None

        # Create a span for the entire Lambda execution
        tracer = _tracer or trace.get_tracer(__name__)
        with tracer.start_as_current_span(f"lambda_{function_name}") as span:
            try:
                # Add Lambda context attributes (AWS best practices)
                span.set_attribute("lambda.function_name", context.function_name)
                span.set_attribute("lambda.function_version", context.function_version)
                span.set_attribute("lambda.request_id", context.aws_request_id)
                span.set_attribute(
                    "lambda.remaining_time_ms", context.get_remaining_time_in_millis()
                )
                span.set_attribute("lambda.memory_limit_mb", context.memory_limit_in_mb)

                # Add AgentCore metadata if available
                if isinstance(event, dict):
                    if "agent" in event:
                        span.set_attribute(
                            "agentcore.agent_id", event.get("agent", {}).get("agentId")
                        )
                    if "function" in event:
                        span.set_attribute(
                            "agentcore.function_name",
                            event.get("function", {}).get("functionName"),
                        )
                    if "sessionId" in event:
                        span.set_attribute(
                            "agentcore.session_id", event.get("sessionId")
                        )

                logger.info(
                    f"Processing {function_name} request - RequestId: {context.aws_request_id}, Event type: {type(event)}"
                )

                # Execute the wrapped function
                result = func(event, context)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Add success attributes
                span.set_attribute("lambda.success", True)
                span.set_attribute("lambda.execution_time_ms", execution_time * 1000)

                logger.info(
                    f"{function_name} completed successfully in {execution_time:.3f}s"
                )

                # Format successful response in AgentCore format
                return {
                    "messageVersion": "1.0",
                    "response": {
                        "body": json.dumps(result, default=str, ensure_ascii=False),
                        "contentType": "application/json",
                    },
                }

            except Exception as e:
                # Calculate execution time
                execution_time = time.time() - start_time

                # Use comprehensive error handler if available
                if error_handler and error_context:
                    try:
                        error_response = error_handler.handle_error(
                            exception=e,
                            context=error_context,
                            tool_name=function_name,
                            lambda_context=context,
                            agentcore_event=event,
                        )

                        logger.info("Error handled by comprehensive error handler")
                        return error_response

                    except Exception as handler_error:
                        logger.error(f"Error handler failed: {handler_error}")
                        # Fall back to basic error handling

                # Fall back to basic error handling
                logger.error(f"Error in {function_name}: {str(e)}", exc_info=True)
                span.set_attribute("lambda.success", False)
                span.set_attribute("lambda.error_type", type(e).__name__)
                span.set_attribute("lambda.execution_time_ms", execution_time * 1000)
                span.record_exception(e)

                # Classify error type for basic handling
                if isinstance(e, ValueError):
                    error_type = "parameter_validation"
                    error_code = "INVALID_PARAMETERS"
                elif isinstance(e, requests.RequestException):
                    error_type = "http_request"
                    error_code = "EXTERNAL_API_ERROR"
                else:
                    error_type = "internal_error"
                    error_code = "INTERNAL_ERROR"

                return format_agentcore_response(
                    {
                        "error": f"Error in {function_name}: {str(e)}",
                        "error_type": error_type,
                        "error_code": error_code,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    success=False,
                )

    return wrapper
