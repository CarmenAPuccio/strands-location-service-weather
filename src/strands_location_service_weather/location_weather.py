"""
Location and weather services with Bedrock integration.
This module combines location services, weather data, and Bedrock LLM capabilities.
"""

import json
import logging
from datetime import datetime
from typing import Any

import requests
from mcp import StdioServerParameters, stdio_client
from opentelemetry import trace
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from strands_tools import current_time

from .config import config

# Get logger for this module
logger = logging.getLogger(__name__)

# System prompt for the location and weather assistant
system_prompt = """
# Location Service Weather Assistant

You are an AI assistant that helps users find location information and weather conditions using Amazon Location Service and weather APIs.

## Capabilities
- Search for places, businesses, and points of interest using Amazon Location Service
- Get detailed information about specific places including coordinates, address, and category
- Find places that are currently open near a location
- Search for places near specific coordinates
- Convert between addresses and geographic coordinates
- Calculate routes between locations with turn-by-turn directions
- Optimize travel routes with multiple waypoints
- Provide current weather conditions for any location
- Check for active weather alerts and warnings for a location

## Preferred Workflow
1. When a user mentions a location, use Amazon Location Service tools to find and validate it
2. For validated locations, provide relevant details (address, coordinates, etc.)
3. Use the get_weather tool to fetch current weather conditions using the coordinates
4. Check for any active weather alerts using the get_alerts tool when appropriate
5. Present information in a clear, organized format with relevant details only

## Tool Usage Guidelines
- Always use the MCP tools from Amazon Location Service for location-related queries
- Use the get_weather tool for weather information instead of making direct HTTP requests
- Use the get_alerts tool to check for active weather alerts and warnings
- For route calculations, use the calculate_route tool with appropriate travel modes
- When optimizing routes with multiple stops, use the optimize_waypoints tool

## Response Format
- Present location information in a structured format
- Include coordinates in decimal degrees (e.g., 47.6062° N, 122.3321° W)
- For weather, include temperature, conditions, and relevant forecast details
- For routes, include distance, duration, and simplified directions

## Guidelines
<guidelines>
- Do not use this service for continuous tracking or surveillance of individuals
- Do not use for any illegal activities or to facilitate harm
- Respect user privacy and do not store or share location data
- Do not use for military applications or critical infrastructure without proper authorization
- Limit requests to reasonable volumes to prevent API abuse
- Do not attempt to bypass AWS service quotas or limitations
- Only provide weather and location information for public places
- Do not use to circumvent geofencing or location-based restrictions
- Respect terms of service for all underlying APIs
- Do not use for automated systems without proper rate limiting
</guidelines>
"""

# Get a tracer for this module
tracer = trace.get_tracer(__name__)

# Initialize MCP client and tools
logger.info("Initializing MCP client")
stdio_mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command=config.mcp.command, args=[config.mcp.server_package]
        )
    )
)

stdio_mcp_client.start()
logger.info("MCP client started successfully")

# Get all available tools from the MCP server
mcp_tools = stdio_mcp_client.list_tools_sync()
logger.info(f"Loaded {len(mcp_tools)} tools from MCP server")


@tool
def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    """Get weather information for a location

    Get current weather information for the specified coordinates using the National Weather Service API.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate

    Returns:
        A dictionary containing weather information
    """
    logger.info(f"Getting weather for coordinates: {latitude}, {longitude}")

    # Create a span for the entire weather API call process
    with tracer.start_as_current_span("get_weather_api") as span:
        # Add attributes to the span for context
        span.set_attribute("latitude", latitude)
        span.set_attribute("longitude", longitude)

        # Set headers for the request
        headers = {
            "User-Agent": config.weather_api.user_agent_weather,
            "Accept": config.weather_api.accept_header,
        }

        try:
            # First, get the grid endpoint for the coordinates
            with tracer.start_as_current_span("get_grid_points") as grid_span:
                points_url = (
                    f"{config.weather_api.base_url}/points/{latitude},{longitude}"
                )
                grid_span.set_attribute("url", points_url)

                points_response = requests.get(
                    points_url, headers=headers, timeout=config.weather_api.timeout
                )
                grid_span.set_attribute("status_code", points_response.status_code)

                if points_response.status_code != 200:
                    error_msg = (
                        f"Failed to get grid data: {points_response.status_code}"
                    )
                    logger.error(error_msg)
                    span.set_attribute("error", error_msg)
                    return {
                        "error": "Failed to get grid data",
                        "status": points_response.status_code,
                    }

            points_data = points_response.json()
            forecast_url = points_data["properties"]["forecast"]

            # Get the forecast data
            with tracer.start_as_current_span("get_forecast") as forecast_span:
                forecast_span.set_attribute("url", forecast_url)

                forecast_response = requests.get(
                    forecast_url, headers=headers, timeout=config.weather_api.timeout
                )
                forecast_span.set_attribute(
                    "status_code", forecast_response.status_code
                )

                if forecast_response.status_code != 200:
                    error_msg = (
                        f"Failed to get forecast data: {forecast_response.status_code}"
                    )
                    logger.error(error_msg)
                    span.set_attribute("error", error_msg)
                    return {
                        "error": "Failed to get forecast data",
                        "status": forecast_response.status_code,
                    }

            forecast_data = forecast_response.json()
            current_period = forecast_data["properties"]["periods"][0]

            # Return formatted weather data
            result = {
                "temperature": {
                    "value": current_period["temperature"],
                    "unit": current_period["temperatureUnit"],
                },
                "windSpeed": {"value": current_period["windSpeed"], "unit": "mph"},
                "windDirection": current_period["windDirection"],
                "shortForecast": current_period["shortForecast"],
                "detailedForecast": current_period["detailedForecast"],
            }

            # Add success attributes to the span
            span.set_attribute("temperature", current_period["temperature"])
            span.set_attribute("forecast", current_period["shortForecast"])

            logger.info(
                f"Weather retrieved: {current_period['temperature']}°{current_period['temperatureUnit']}, {current_period['shortForecast']}"
            )
            return result

        except Exception as e:
            # Record the error in the span
            error_msg = f"Error fetching weather data: {str(e)}"
            logger.error(error_msg)
            span.set_attribute("error", str(e))
            span.record_exception(e)
            return {"error": error_msg}


@tool
def get_alerts(latitude: float, longitude: float) -> list[dict[str, Any]]:
    """Get active weather alerts for a location

    Retrieves active weather alerts and warnings for the specified coordinates using the National Weather Service API.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate

    Returns:
        A list of active weather alerts with their details
    """
    logger.info(f"Getting weather alerts for coordinates: {latitude}, {longitude}")

    # Create a span for the alerts API call
    with tracer.start_as_current_span("get_weather_alerts") as span:
        # Add attributes to the span for context
        span.set_attribute("latitude", latitude)
        span.set_attribute("longitude", longitude)

        # Set headers for the request
        headers = {
            "User-Agent": config.weather_api.user_agent_alerts,
            "Accept": config.weather_api.accept_header,
        }

        try:
            # First, get the zone for the coordinates
            with tracer.start_as_current_span("get_zone_info") as zone_span:
                points_url = (
                    f"{config.weather_api.base_url}/points/{latitude},{longitude}"
                )
                zone_span.set_attribute("url", points_url)
                logger.debug(f"Requesting zone data from: {points_url}")
                points_response = requests.get(
                    points_url, headers=headers, timeout=config.weather_api.timeout
                )
                zone_span.set_attribute("status_code", points_response.status_code)

                if points_response.status_code != 200:
                    error_msg = (
                        f"Failed to get zone data: {points_response.status_code}"
                    )
                    logger.error(error_msg)
                    span.set_attribute("error", error_msg)
                    return [
                        {
                            "error": "Failed to get zone data",
                            "status": points_response.status_code,
                        }
                    ]

            points_data = points_response.json()

            # Get the county/zone code
            county_zone = points_data["properties"]["county"].split("/")[-1]
            logger.debug(f"Found county/zone code: {county_zone}")

            # Get active alerts for the zone
            with tracer.start_as_current_span("get_alerts_data") as alerts_span:
                alerts_url = (
                    f"{config.weather_api.base_url}/alerts/active/zone/{county_zone}"
                )
                alerts_span.set_attribute("url", alerts_url)
                logger.debug(f"Requesting alerts data from: {alerts_url}")
                alerts_response = requests.get(
                    alerts_url, headers=headers, timeout=config.weather_api.timeout
                )
                alerts_span.set_attribute("status_code", alerts_response.status_code)

                if alerts_response.status_code != 200:
                    error_msg = (
                        f"Failed to get alerts data: {alerts_response.status_code}"
                    )
                    logger.error(error_msg)
                    span.set_attribute("error", error_msg)
                    return [
                        {
                            "error": "Failed to get alerts data",
                            "status": alerts_response.status_code,
                        }
                    ]

            alerts_data = alerts_response.json()

            # Process and format the alerts
            alerts = []
            for feature in alerts_data.get("features", []):
                properties = feature.get("properties", {})

                # Convert effective and expires times to more readable format
                effective = properties.get("effective")
                expires = properties.get("expires")

                try:
                    if effective:
                        effective_dt = datetime.fromisoformat(
                            effective.replace("Z", "+00:00")
                        )
                        effective = effective_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

                    if expires:
                        expires_dt = datetime.fromisoformat(
                            expires.replace("Z", "+00:00")
                        )
                        expires = expires_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                except Exception as date_error:
                    logger.warning(f"Error parsing date: {date_error}")
                    # Keep original format if parsing fails
                    pass

                alert = {
                    "event": properties.get("event"),
                    "headline": properties.get("headline"),
                    "description": properties.get("description"),
                    "severity": properties.get("severity"),
                    "urgency": properties.get("urgency"),
                    "effective": effective,
                    "expires": expires,
                    "instruction": properties.get("instruction"),
                }
                alerts.append(alert)

            # Add count to span
            alert_count = len(alerts)
            span.set_attribute("alert_count", alert_count)

            # If no alerts, return a clear message
            if not alerts:
                logger.info("No active weather alerts found for this location")
                return [{"message": "No active weather alerts for this location"}]

            logger.info(f"Found {alert_count} active weather alert(s)")
            return alerts

        except Exception as e:
            # Record the error in the span
            error_msg = f"Error fetching weather alerts: {str(e)}"
            logger.error(error_msg)
            span.set_attribute("error", str(e))
            span.record_exception(e)
            return [{"error": error_msg}]


class LocationWeatherClient:
    """Client for interacting with location and weather services using Amazon Bedrock."""

    def __init__(
        self,
        custom_system_prompt=None,
        model_id: str = None,
        region_name: str = None,
    ):
        """Initialize the client with Bedrock model and tools.

        Args:
            custom_system_prompt: Optional custom system prompt to override the default
            model_id: Bedrock model ID to use (defaults to config value)
            region_name: AWS region for Bedrock (defaults to config value)
        """
        # Use config defaults if not provided
        model_id = model_id or config.bedrock.model_id
        region_name = region_name or config.bedrock.region_name
        # Get the tracer for this module
        tracer = trace.get_tracer(__name__)

        # Create a span for the initialization process
        with tracer.start_as_current_span("agent_initialization") as span:
            try:
                logger.info("Initializing BedrockModel")
                span.set_attribute("model_id", model_id)
                span.set_attribute("region_name", region_name)

                # Initialize the Bedrock model
                bedrock_model = BedrockModel(model_id=model_id, region_name=region_name)

                # Combine all tools
                all_tools = [current_time, get_weather, get_alerts] + mcp_tools
                tool_count = len(all_tools)
                logger.info(f"Registered {tool_count} tools")
                span.set_attribute("tool_count", tool_count)

                # Use the provided system prompt or the default one
                prompt_to_use = (
                    custom_system_prompt if custom_system_prompt else system_prompt
                )

                # Create the agent with the model, tools, and system prompt
                self.agent = Agent(
                    model=bedrock_model,
                    tools=all_tools,
                    system_prompt=prompt_to_use,
                )
                logger.info("Agent created successfully")

            except Exception as e:
                logger.error(f"Error initializing LocationWeatherClient: {e}")
                span.record_exception(e)
                raise

    def chat(self, prompt: str) -> str:
        """Process a user prompt through the agent.

        Args:
            prompt: User input text

        Returns:
            Agent response as a string
        """
        # Use the same format as the old version with module name
        logger.info(f"Processing prompt: {prompt}")

        # Get the tracer for this module
        tracer = trace.get_tracer(__name__)

        # Create a span for the entire agent interaction
        with tracer.start_as_current_span("agent_interaction") as span:
            try:
                # Add the prompt as an attribute
                span.set_attribute("prompt", prompt)
                span.set_attribute("prompt_length", len(prompt))

                # Call the agent within the span, with explicit model call instrumentation
                with tracer.start_as_current_span(
                    "bedrock_model_inference"
                ) as model_span:
                    # Set model ID attribute from config
                    model_span.set_attribute("model_id", config.bedrock.model_id)

                    try:
                        result = self.agent(prompt)
                    except Exception as model_error:
                        logger.error(f"Model inference failed: {model_error}")
                        model_span.record_exception(model_error)
                        model_span.set_status(
                            trace.Status(trace.StatusCode.ERROR, str(model_error))
                        )
                        # Re-raise to be handled by outer try/except
                        raise

                    # Capture metrics from the result object
                    if hasattr(result, "metrics"):
                        try:
                            # Add token usage metrics
                            if hasattr(
                                result.metrics, "accumulated_usage"
                            ) and isinstance(result.metrics.accumulated_usage, dict):
                                for (
                                    key,
                                    value,
                                ) in result.metrics.accumulated_usage.items():
                                    # Only set attributes for compatible types
                                    if isinstance(value, str | bool | int | float):
                                        model_span.set_attribute(
                                            f"metrics.{key}", value
                                        )

                            # Add execution time metrics
                            if (
                                hasattr(result.metrics, "cycle_durations")
                                and result.metrics.cycle_durations
                            ):
                                total_duration = sum(result.metrics.cycle_durations)
                                model_span.set_attribute(
                                    "metrics.total_duration", total_duration
                                )
                                model_span.set_attribute(
                                    "metrics.cycle_count",
                                    len(result.metrics.cycle_durations),
                                )

                            # Add tool usage metrics
                            if (
                                hasattr(result.metrics, "tool_metrics")
                                and result.metrics.tool_metrics
                            ):
                                tools_used = list(result.metrics.tool_metrics.keys())
                                model_span.set_attribute(
                                    "metrics.tools_used", ", ".join(tools_used)
                                )
                                model_span.set_attribute(
                                    "metrics.tool_count", len(tools_used)
                                )
                        except Exception as metrics_error:
                            # Don't fail the whole request if metrics processing fails
                            logger.warning(
                                f"Failed to process metrics: {metrics_error}"
                            )
                            model_span.set_attribute(
                                "metrics.error", str(metrics_error)
                            )

                    # Log the raw message returned by the model (like in the old version)
                    logger.info("=== Model Raw Message ===")
                    if hasattr(result, "message"):
                        message_dict = dict(result.message)
                        logger.info(json.dumps(message_dict, indent=2))

                # Add response attributes to the span
                response_str = str(result)
                span.set_attribute("response_length", len(response_str))

                # Log that we received a response (like in the old version)
                logger.info("Received response")

                return response_str

            except Exception as e:
                logger.error(f"Error processing prompt: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                # Return a user-friendly error message instead of raising
                return f"I'm sorry, I encountered an error processing your request. Please try again or rephrase your question. (Error: {str(e)})"
