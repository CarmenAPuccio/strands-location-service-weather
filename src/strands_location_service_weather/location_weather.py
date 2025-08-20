"""
Location and weather services with Bedrock integration.
This module combines location services, weather data, and Bedrock LLM capabilities.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import boto3
import requests
from mcp import StdioServerParameters, stdio_client
from opentelemetry import trace
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands_tools.current_time import current_time

from .config import DeploymentMode, config

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

# Initialize MCP client and tools - moved to function to avoid module-level execution issues
stdio_mcp_client = None
mcp_tools = []


def _initialize_mcp_client():
    """Initialize MCP client and tools."""
    global stdio_mcp_client, mcp_tools
    if stdio_mcp_client is None:
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
        custom_system_prompt=None,
        model_id: str = None,
        region_name: str = None,
        deployment_mode: DeploymentMode = None,
        config_override: dict = None,
    ):
        """Initialize the client with Bedrock model and tools.

        Args:
            custom_system_prompt: Optional custom system prompt to override the default
            model_id: Bedrock model ID to use (defaults to config value)
            region_name: AWS region for Bedrock (defaults to config value)
            deployment_mode: Deployment mode (defaults to LOCAL)
            config_override: Optional config overrides
        """
        # Handle deployment mode (default to LOCAL for backward compatibility)
        if deployment_mode is None:
            deployment_mode = DeploymentMode.LOCAL

        # Store deployment mode for later use
        self._deployment_mode = deployment_mode

        # Create deployment configuration
        from .model_factory import ModelFactory

        deployment_config = self._create_deployment_config(
            deployment_mode, config_override, model_id, region_name
        )
        # Get the tracer for this module
        tracer = trace.get_tracer(__name__)

        # Create a span for the initialization process
        with tracer.start_as_current_span("agent_initialization") as span:
            try:
                logger.info(f"Initializing model for {deployment_mode.value} mode")
                span.set_attribute("deployment_mode", deployment_mode.value)
                span.set_attribute("model_id", deployment_config.bedrock_model_id)
                span.set_attribute("region_name", deployment_config.aws_region)

                # Create model using factory (handles different deployment modes)
                model = ModelFactory.create_model(deployment_config)

                # Get tools based on deployment mode
                all_tools = self._get_tools_for_mode(deployment_mode)
                tool_count = len(all_tools)
                logger.info(f"Registered {tool_count} tools")
                span.set_attribute("tool_count", tool_count)

                # Use the provided system prompt or the default one
                prompt_to_use = (
                    custom_system_prompt if custom_system_prompt else system_prompt
                )

                # Create the agent with the model, tools, and system prompt
                # For BEDROCK_AGENT mode, we handle invocation differently
                if deployment_mode == DeploymentMode.BEDROCK_AGENT:
                    # Store configuration for Bedrock Agent runtime invocation
                    self._bedrock_agent_id = deployment_config.bedrock_agent_id
                    self._bedrock_agent_region = deployment_config.aws_region
                    self._bedrock_agent_model = model
                    self.agent = None  # No direct agent for BEDROCK_AGENT mode
                    logger.info(
                        f"Configured for Bedrock Agent runtime: {self._bedrock_agent_id}"
                    )
                else:
                    # LOCAL and MCP modes use direct agent
                    self.agent = Agent(
                        model=model,
                        tools=all_tools,
                        system_prompt=prompt_to_use,
                    )
                    logger.info("Agent created successfully")
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
        logger.info(f"Processing prompt: {prompt}")

        # Get the tracer for this module
        tracer = trace.get_tracer(__name__)

        # Create a span for the entire agent interaction
        with tracer.start_as_current_span("agent_interaction") as span:
            try:
                # Add the prompt as an attribute
                span.set_attribute("prompt", prompt)
                span.set_attribute("prompt_length", len(prompt))
                span.set_attribute("deployment_mode", self._deployment_mode.value)

                # Handle different deployment modes
                if self._deployment_mode == DeploymentMode.BEDROCK_AGENT:
                    return self._invoke_bedrock_agent(prompt, span)
                else:
                    return self._invoke_direct_agent(prompt, span)

            except Exception as e:
                logger.error(f"Agent interaction failed: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                # Return a user-friendly error message
                return f"I apologize, but I encountered an error processing your request: {str(e)}"

    def _invoke_direct_agent(self, prompt: str, span) -> str:
        """Invoke agent directly for LOCAL and MCP modes."""
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("bedrock_model_inference") as model_span:
            # Set model ID attribute from config
            model_span.set_attribute("model_id", config.bedrock.model_id)

            try:
                result = self.agent(prompt)

                # Process metrics from the result object while span is still active
                if hasattr(result, "metrics"):
                    try:
                        # Add token usage metrics
                        if hasattr(result.metrics, "accumulated_usage") and isinstance(
                            result.metrics.accumulated_usage, dict
                        ):
                            for key, value in result.metrics.accumulated_usage.items():
                                # Only set attributes for compatible types
                                if isinstance(value, str | bool | int | float):
                                    model_span.set_attribute(f"metrics.{key}", value)

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
                        logger.warning(f"Failed to process metrics: {metrics_error}")
                        model_span.set_attribute("metrics.error", str(metrics_error))

            except Exception as model_error:
                logger.error(f"Model inference failed: {model_error}")
                model_span.record_exception(model_error)
                model_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, str(model_error))
                )
                # Re-raise to be handled by outer try/except
                raise

        # Add response attributes to the span
        response_text = str(result)
        span.set_attribute("response_length", len(response_text))

        logger.info("Direct agent interaction completed successfully")
        return response_text

    def _invoke_bedrock_agent(self, prompt: str, span) -> str:
        """Invoke Bedrock Agent for BEDROCK_AGENT mode."""

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("bedrock_agent_invocation") as agent_span:
            agent_span.set_attribute("agent_id", self._bedrock_agent_id)

            try:
                # Create Bedrock Agent Runtime client
                bedrock_agent_client = boto3.client(
                    "bedrock-agent-runtime",
                    region_name=self._bedrock_agent_region,
                )

                # Generate session ID
                session_id = str(uuid.uuid4())

                # Invoke the agent
                response = bedrock_agent_client.invoke_agent(
                    agentId=self._bedrock_agent_id,
                    agentAliasId="TSTALIASID",  # Default test alias
                    sessionId=session_id,
                    inputText=prompt,
                )

                # Process streaming response
                response_text = ""
                if "completion" in response:
                    for event in response["completion"]:
                        if "chunk" in event:
                            chunk = event["chunk"]
                            if "bytes" in chunk:
                                chunk_text = chunk["bytes"].decode("utf-8")
                                response_text += chunk_text

                agent_span.set_attribute("response_length", len(response_text))
                logger.info("Bedrock Agent invocation completed successfully")
                return (
                    response_text.strip()
                    if response_text
                    else "I apologize, but I didn't receive a response from the agent."
                )

            except Exception as e:
                error_msg = f"Bedrock Agent invocation failed: {str(e)}"
                logger.error(error_msg)
                agent_span.record_exception(e)
                raise

    def get_deployment_info(self) -> DeploymentInfo:
        """Get information about the current deployment configuration.

        Returns:
            DeploymentInfo with current configuration details
        """
        # Use the stored deployment mode
        mode = getattr(self, "_deployment_mode", DeploymentMode.LOCAL)

        # Get model information
        model_type = "BedrockModel"
        model_id = None
        agent_id = None
        region = None

        if mode == DeploymentMode.BEDROCK_AGENT:
            # BEDROCK_AGENT mode: Get info from stored configuration
            agent_id = getattr(self, "_bedrock_agent_id", None)
            if hasattr(self, "_bedrock_agent_model"):
                model = self._bedrock_agent_model
                if hasattr(model, "config") and isinstance(model.config, dict):
                    model_id = model.config.get("model_id")
                if hasattr(model, "client") and hasattr(model.client, "meta"):
                    region = getattr(model.client.meta, "region_name", None)
        else:
            # LOCAL and MCP modes: Get info from agent model
            if hasattr(self, "agent") and self.agent and hasattr(self.agent, "model"):
                model = self.agent.model
                # Get model_id from config
                if hasattr(model, "config") and isinstance(model.config, dict):
                    model_id = model.config.get("model_id")

                # Try to get region from various sources
                region = getattr(model, "region_name", None)
                if (
                    not region
                    and hasattr(model, "client")
                    and hasattr(model.client, "meta")
                ):
                    region = getattr(model.client.meta, "region_name", None)

        # Count tools based on deployment mode
        tools_count = 0
        if mode == DeploymentMode.BEDROCK_AGENT:
            # BEDROCK_AGENT mode: Base tools only (3: current_time, get_weather, get_alerts)
            # Location services are handled by Bedrock Agent action groups
            tools_count = 3
        else:
            # LOCAL and MCP modes: Count tools from agent
            if (
                hasattr(self, "agent")
                and self.agent
                and hasattr(self.agent, "tool_registry")
            ):
                try:
                    tools_config = self.agent.tool_registry.get_all_tools_config()
                    tools_count = len(tools_config) if tools_config else 0
                except Exception:
                    tools_count = 0

        return DeploymentInfo(
            mode=mode,
            model_type=model_type,
            model_id=model_id,
            agent_id=agent_id,
            region=region,
            tools_count=tools_count,
        )

    def health_check(self) -> HealthStatus:
        """Perform a health check on the client and its components.

        Returns:
            HealthStatus with health information
        """
        try:
            # Check if agent is available
            if not hasattr(self, "agent") or self.agent is None:
                return HealthStatus(
                    healthy=False,
                    model_healthy=False,
                    tools_available=False,
                    error_message="Agent not initialized",
                )

            # Check model health
            model_healthy = True
            try:
                # Basic model check - see if it has required attributes
                if not hasattr(self.agent, "model") or self.agent.model is None:
                    model_healthy = False
            except Exception:
                model_healthy = False

            # Check tools availability
            tools_available = True
            try:
                if not hasattr(self.agent, "tools") or not self.agent.tools:
                    tools_available = False
                    error_message = "No tools available"
                elif len(self.agent.tools) == 0:
                    tools_available = False
                    error_message = "tools unavailable or invalid"
                else:
                    error_message = None
            except Exception:
                tools_available = False
                error_message = "Error checking tools availability"

            # Overall health
            healthy = model_healthy and tools_available

            return HealthStatus(
                healthy=healthy,
                model_healthy=model_healthy,
                tools_available=tools_available,
                error_message=error_message if not healthy else None,
            )

        except Exception as e:
            return HealthStatus(
                healthy=False,
                model_healthy=False,
                tools_available=False,
                error_message=f"Health check exception: {str(e)}",
            )

    def _create_deployment_config(
        self,
        deployment_mode: DeploymentMode,
        config_override: dict = None,
        model_id: str = None,
        region_name: str = None,
    ):
        """Create deployment configuration from parameters and overrides."""
        from .config import DeploymentConfig

        # Start with defaults
        bedrock_model_id = model_id or config.bedrock.model_id
        aws_region = region_name or config.bedrock.region_name
        # Check environment variable for bedrock_agent_id
        bedrock_agent_id = os.getenv("BEDROCK_AGENT_ID")

        # Apply config overrides (overrides take precedence)
        if config_override:
            bedrock_model_id = (
                config_override.get("bedrock_model_id")
                or config_override.get("model_id")
                or bedrock_model_id
            )
            aws_region = (
                config_override.get("aws_region")
                or config_override.get("region_name")
                or aws_region
            )
            bedrock_agent_id = (
                config_override.get("bedrock_agent_id") or bedrock_agent_id
            )

        return DeploymentConfig(
            mode=deployment_mode,
            bedrock_model_id=bedrock_model_id,
            bedrock_agent_id=bedrock_agent_id,
            aws_region=aws_region,
            enable_tracing=True,
            timeout=30,
        )

    def _get_tools_for_mode(self, mode: DeploymentMode) -> list:
        """Get appropriate tools based on deployment mode."""
        if mode == DeploymentMode.BEDROCK_AGENT:
            # BEDROCK_AGENT mode: Only base tools (no MCP tools)
            # Location services are handled by Bedrock Agent action groups
            return [current_time, get_weather, get_alerts]
        else:
            # LOCAL and MCP modes: Include MCP tools for location services
            _initialize_mcp_client()
            return [current_time, get_weather, get_alerts] + mcp_tools
