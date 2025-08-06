#!/usr/bin/env python3
"""
FastMCP Server for location weather service.
This creates a FastMCP server that wraps the existing LocationWeatherClient
with comprehensive error handling and OpenTelemetry observability.
"""

import os
import sys

from fastmcp import FastMCP
from opentelemetry import trace

from .config import DeploymentMode
from .error_handling import ErrorHandlerFactory, create_error_context
from .location_weather import LocationWeatherClient

# Get tracer for OpenTelemetry spans
tracer = trace.get_tracer(__name__)

# Initialize FastMCP server with performance optimizations
mcp = FastMCP(
    "Location Weather Service",
    # Note: log_level and debug moved to run() call per FastMCP 2.x
    mask_error_details=False,  # Keep detailed errors for debugging
)

# Global client instance - pre-initialize at startup
_debug = os.getenv("DEVELOPMENT", "false").lower() == "true"

if _debug:
    print(
        "DEBUG: Pre-initializing LocationWeatherClient at startup",
        file=sys.stderr,
        flush=True,
    )

try:
    _client = LocationWeatherClient()
    if _debug:
        print(
            "DEBUG: LocationWeatherClient initialized successfully",
            file=sys.stderr,
            flush=True,
        )
except Exception as e:
    if _debug:
        print(
            f"DEBUG: Failed to initialize LocationWeatherClient: {e}",
            file=sys.stderr,
            flush=True,
        )
    _client = None


def get_client():
    """Get the pre-initialized LocationWeatherClient."""
    global _client, _debug
    if _client is None:
        if _debug:
            print(
                "DEBUG: Client was None, attempting to re-initialize",
                file=sys.stderr,
                flush=True,
            )
        _client = LocationWeatherClient()
    return _client


@mcp.tool()
def ask_location_weather(query: str) -> str:
    """Ask questions about locations, weather, routes, and places.

    Supports natural language queries like:
    - 'Weather in Seattle'
    - 'Find coffee shops in Boston'
    - 'Route from NYC to Philadelphia'
    - 'Places near 47.6062,-122.3321'

    Args:
        query: Natural language query about location, weather, or places

    Returns:
        Response with location and weather information
    """
    if not query:
        # Create error context for validation error
        error_context = create_error_context(
            deployment_mode=DeploymentMode.MCP,
            tool_name="ask_location_weather",
            metadata={"query": query},
        )

        # Handle validation error with MCP error handler
        error_handler = ErrorHandlerFactory.create_handler(DeploymentMode.MCP)
        error_handler.handle_error(
            exception=ValueError("Query parameter is required"),
            context=error_context,
            tool_name="ask_location_weather",
        )

        # Return user-friendly error message for MCP
        return "Error: Query parameter is required"

    try:
        with tracer.start_as_current_span(
            "mcp.tool.ask_location_weather",
            kind=trace.SpanKind.SERVER,
            attributes={
                "mcp.tool_name": "ask_location_weather",
                "mcp.query_length": len(query),
            },
        ) as span:
            span.set_attribute("mcp.tool_name", "ask_location_weather")
            span.set_attribute("mcp.query_length", len(query))
            span.set_attribute("deployment_mode", DeploymentMode.MCP.value)

            if _debug:
                print(f"DEBUG: Processing query: {query}", file=sys.stderr, flush=True)
                span.set_attribute("mcp.debug_mode", True)

            client = get_client()
            if _debug:
                print("DEBUG: Got client, calling chat", file=sys.stderr, flush=True)

            # Add timeout for complex queries to prevent Q CLI timeouts
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Query processing timed out after 90 seconds")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(90)  # 90 second timeout (under Q CLI's 120s limit)

            try:
                with tracer.start_as_current_span(
                    "client.chat",
                    kind=trace.SpanKind.CLIENT,
                    attributes={
                        "client.operation": "chat",
                    },
                ) as chat_span:
                    chat_span.set_attribute(
                        "query", query[:100]
                    )  # Truncate for privacy
                    response = client.chat(query)
                    chat_span.set_attribute("response_length", len(response))
            finally:
                signal.alarm(0)  # Cancel the alarm

            # Add success attributes to span
            span.set_attribute("mcp.success", True)
            span.set_attribute("mcp.response_length", len(response))

            if _debug:
                print(
                    f"DEBUG: Got response: {response[:100]}...",
                    file=sys.stderr,
                    flush=True,
                )
            return response

    except TimeoutError as e:
        # Create error context for timeout
        error_context = create_error_context(
            deployment_mode=DeploymentMode.MCP,
            tool_name="ask_location_weather",
            metadata={"query": query, "timeout": 90},
        )

        # Handle timeout error with MCP error handler
        error_handler = ErrorHandlerFactory.create_handler(DeploymentMode.MCP)
        error_handler.handle_error(
            exception=e,
            context=error_context,
            tool_name="ask_location_weather",
        )

        # Return user-friendly timeout message
        return "Query timed out. Please try asking about individual cities instead of complex routes."

    except Exception as e:
        # Create error context for general error
        error_context = create_error_context(
            deployment_mode=DeploymentMode.MCP,
            tool_name="ask_location_weather",
            metadata={"query": query},
        )

        # Handle general error with MCP error handler
        error_handler = ErrorHandlerFactory.create_handler(DeploymentMode.MCP)
        error_handler.handle_error(
            exception=e,
            context=error_context,
            tool_name="ask_location_weather",
        )

        if _debug:
            print(
                f"DEBUG: Error in ask_location_weather: {e}",
                file=sys.stderr,
                flush=True,
            )
            import traceback

            traceback.print_exc(file=sys.stderr)

        # Return user-friendly error message
        return f"Error processing query: {str(e)}"


def run_mcp_server():
    """Run the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    run_mcp_server()
