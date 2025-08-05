"""
Location and weather services with Bedrock integration.
This module combines location services, weather data, and Bedrock LLM capabilities.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from mcp import StdioServerParameters, stdio_client
from opentelemetry import trace
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands_tools import current_time

from .config import DeploymentConfig, DeploymentMode, config
from .model_factory import ModelFactory

# Get logger for this module
logger = logging.getLogger(__name__)

# Create a persistent HTTP session for better performance
_http_session = requests.Session()

# Optimized system prompt - essential guidelines with clear response instructions
system_prompt = """You are a location and weather assistant. Use available tools to find locations and provide weather information.

For weather queries, always use get_weather tool first to get temperature, conditions, and wind, then use get_alerts tool to check for warnings.

For route queries, always check weather alerts at both the origin and destination locations for travel safety.

Tools: Use Amazon Location Service MCP tools for locations/routes, get_weather for conditions, get_alerts for warnings.

Guidelines: Only provide information for public places. Respect privacy and prevent API abuse.

Be concise and helpful."""

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

                points_response = _http_session.get(
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

                forecast_response = _http_session.get(
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
                points_response = _http_session.get(
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
                alerts_response = _http_session.get(
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


@dataclass
class DeploymentInfo:
    """Information about the current deployment configuration."""

    mode: DeploymentMode
    model_type: str
    model_id: str | None
    agent_id: str | None
    region: str
    tools_count: int


@dataclass
class HealthStatus:
    """Health status information for the client."""

    healthy: bool
    model_healthy: bool
    tools_available: bool
    error_message: str | None = None


class LocationWeatherClient:
    """Client for interacting with location and weather services using Amazon Bedrock."""

    def __init__(
        self,
        deployment_mode: DeploymentMode | None = None,
        custom_system_prompt: str | None = None,
        config_override: dict | None = None,
        # Backward compatibility parameters
        model_id: str | None = None,
        region_name: str | None = None,
    ):
        """Initialize the client with multi-mode support.

        Args:
            deployment_mode: Deployment mode (LOCAL, MCP, AGENTCORE). If None, uses config default
            custom_system_prompt: Optional custom system prompt to override the default
            config_override: Optional dictionary to override specific config values
            model_id: Bedrock model ID (backward compatibility, overrides config)
            region_name: AWS region (backward compatibility, overrides config)
        """
        # Get the tracer for this module
        tracer = trace.get_tracer(__name__)

        # Create a span for the initialization process
        with tracer.start_as_current_span("agent_initialization") as span:
            try:
                # Resolve configuration with backward compatibility
                self._deployment_config = self._resolve_config(
                    deployment_mode, config_override, model_id, region_name
                )

                logger.info(
                    f"Initializing LocationWeatherClient in {self._deployment_config.mode.value} mode"
                )
                span.set_attribute(
                    "deployment_mode", self._deployment_config.mode.value
                )
                span.set_attribute("model_id", self._deployment_config.bedrock_model_id)
                span.set_attribute("region_name", self._deployment_config.aws_region)

                # Create model using factory
                self._model = ModelFactory.create_model(self._deployment_config)

                # Get tools for the deployment mode
                all_tools = self._get_tools_for_mode(self._deployment_config.mode)
                tool_count = len(all_tools)
                logger.info(
                    f"Registered {tool_count} tools for {self._deployment_config.mode.value} mode"
                )
                span.set_attribute("tool_count", tool_count)

                # Use the provided system prompt or the default one
                prompt_to_use = (
                    custom_system_prompt if custom_system_prompt else system_prompt
                )

                # Create the agent with the model, tools, and system prompt
                self.agent = Agent(
                    model=self._model,
                    tools=all_tools,
                    system_prompt=prompt_to_use,
                )

                logger.info("Agent created successfully")

            except Exception as e:
                logger.error(f"Error initializing LocationWeatherClient: {e}")
                span.record_exception(e)
                raise

    def _resolve_config(
        self,
        deployment_mode: DeploymentMode | None,
        config_override: dict | None,
        model_id: str | None,
        region_name: str | None,
    ) -> DeploymentConfig:
        """Resolve deployment configuration from various sources.

        Args:
            deployment_mode: Explicit deployment mode
            config_override: Configuration overrides
            model_id: Backward compatibility model ID
            region_name: Backward compatibility region name

        Returns:
            Resolved DeploymentConfig
        """
        # Create a new config based on the global config deployment settings
        deployment_config = DeploymentConfig(
            mode=config.deployment.mode,
            bedrock_model_id=config.deployment.bedrock_model_id,
            agentcore_agent_id=config.deployment.agentcore_agent_id,
            aws_region=config.deployment.aws_region,
            enable_tracing=config.deployment.enable_tracing,
            timeout=config.deployment.timeout,
        )

        # Override with explicit deployment mode if provided
        if deployment_mode is not None:
            deployment_config.mode = deployment_mode

        # Apply config overrides if provided
        if config_override:
            for key, value in config_override.items():
                if hasattr(deployment_config, key):
                    setattr(deployment_config, key, value)

        # Apply backward compatibility overrides
        if model_id is not None:
            deployment_config.bedrock_model_id = model_id
        if region_name is not None:
            deployment_config.aws_region = region_name

        # Validate the final configuration
        ModelFactory.validate_model_config(deployment_config)

        return deployment_config

    def _get_tools_for_mode(self, mode: DeploymentMode) -> list:
        """Get appropriate tools based on deployment mode.

        Args:
            mode: Deployment mode

        Returns:
            List of tools for the specified mode
        """
        # Base tools available in all modes
        base_tools = [current_time, get_weather, get_alerts]

        if mode == DeploymentMode.AGENTCORE:
            # For AgentCore mode, external tools (like location services) are typically
            # configured as Action Groups within the AgentCore agent definition
            # The agent handles tool orchestration internally via the AgentCore runtime
            # We still provide base weather tools as they're custom to this application
            logger.info(
                "Using base tools for AgentCore mode (location services handled by AgentCore action groups)"
            )
            return base_tools
        else:
            # For LOCAL and MCP modes, include all MCP tools for location services
            logger.info("Including MCP tools for local/MCP mode")
            return base_tools + mcp_tools

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

                    # Log the raw message returned by the model in development mode only
                    if config.opentelemetry.development_mode:
                        logger.debug("=== Model Raw Message ===")
                        if hasattr(result, "message"):
                            message_dict = dict(result.message)
                            logger.debug(json.dumps(message_dict, indent=2))

                # Add response attributes to the span
                response_str = str(result)
                span.set_attribute("response_length", len(response_str))

                return response_str

            except Exception as e:
                logger.error(f"Error processing prompt: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                # Return a user-friendly error message instead of raising
                return f"I'm sorry, I encountered an error processing your request. Please try again or rephrase your question. (Error: {str(e)})"

    def get_deployment_info(self) -> DeploymentInfo:
        """Get information about the current deployment configuration.

        Returns:
            DeploymentInfo with current configuration details
        """
        model_type = type(self._model).__name__

        # Get agent_id for AgentCore models
        agent_id = getattr(self._model, "agent_id", None)

        # Get model_id from different possible attributes
        # AgentCore models use agent_id instead of model_id
        model_id = None
        if agent_id is not None:
            # This is an AgentCore model, don't set model_id
            model_id = None
        elif hasattr(self._model, "model_id"):
            model_id = self._model.model_id
        elif hasattr(self._model, "_model_id"):
            model_id = self._model._model_id
        else:
            # Fallback to config value for Bedrock models
            model_id = self._deployment_config.bedrock_model_id

        # Count tools (base tools + MCP tools if applicable)
        tools_count = len(self._get_tools_for_mode(self._deployment_config.mode))

        return DeploymentInfo(
            mode=self._deployment_config.mode,
            model_type=model_type,
            model_id=model_id,
            agent_id=agent_id,
            region=self._deployment_config.aws_region,
            tools_count=tools_count,
        )

    def health_check(self) -> HealthStatus:
        """Perform health check on the client and its components.

        Returns:
            HealthStatus with health information
        """
        logger.info("Performing LocationWeatherClient health check")

        try:
            # Check model health
            model_healthy = ModelFactory.health_check(self._model)

            # Check tools availability
            tools_available = True
            try:
                tools = self._get_tools_for_mode(self._deployment_config.mode)
                tools_available = len(tools) > 0
            except Exception as e:
                logger.warning(f"Tools availability check failed: {e}")
                tools_available = False

            # Overall health status
            healthy = model_healthy and tools_available

            error_message = None
            if not healthy:
                error_details = []
                if not model_healthy:
                    error_details.append("model unhealthy")
                if not tools_available:
                    error_details.append("tools unavailable")
                error_message = f"Health check failed: {', '.join(error_details)}"

            return HealthStatus(
                healthy=healthy,
                model_healthy=model_healthy,
                tools_available=tools_available,
                error_message=error_message,
            )

        except Exception as e:
            logger.error(f"Health check failed with exception: {e}")
            return HealthStatus(
                healthy=False,
                model_healthy=False,
                tools_available=False,
                error_message=f"Health check exception: {str(e)}",
            )
