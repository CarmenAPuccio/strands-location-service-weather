"""Configuration management for the location weather service."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11


@dataclass
class OpenTelemetryConfig:
    """OpenTelemetry configuration."""

    service_name: str = "strands-location-service-weather"
    development_mode: bool = False


@dataclass
class BedrockConfig:
    """Amazon Bedrock configuration."""

    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region_name: str = "us-east-1"


@dataclass
class WeatherAPIConfig:
    """National Weather Service API configuration."""

    base_url: str = "https://api.weather.gov"
    user_agent_weather: str = "LocationWeatherService/1.0"
    user_agent_alerts: str = "LocationWeatherAlertsService/1.0"
    accept_header: str = "application/geo+json"
    timeout: int = 30


@dataclass
class MCPConfig:
    """Model Context Protocol configuration."""

    command: str = "uvx"
    server_package: str = "awslabs.aws-location-mcp-server@latest"


@dataclass
class UIConfig:
    """User interface configuration."""

    app_title: str = "PlaceFinder & Weather"
    welcome_message: str = (
        "Ask about locations, routes, nearby places, or weather conditions."
    )
    prompt_text: str = "How can I help you? "
    exit_commands: list[str] = None

    def __post_init__(self):
        if self.exit_commands is None:
            self.exit_commands = ["exit", "quit"]


@dataclass
class AppConfig:
    """Main application configuration."""

    opentelemetry: OpenTelemetryConfig
    bedrock: BedrockConfig
    weather_api: WeatherAPIConfig
    mcp: MCPConfig
    ui: UIConfig

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "AppConfig":
        """Load configuration from environment variables and optional config file.

        Args:
            config_file: Optional path to TOML config file

        Returns:
            AppConfig instance with loaded configuration
        """
        # Start with defaults
        config_data = {}

        # Load from config file if provided
        if config_file and config_file.exists():
            with open(config_file, "rb") as f:
                config_data = tomllib.load(f)

        # Override with environment variables
        otel_config = OpenTelemetryConfig(
            service_name=os.getenv(
                "OTEL_SERVICE_NAME",
                config_data.get("opentelemetry", {}).get(
                    "service_name", "strands-location-service-weather"
                ),
            ),
            development_mode=os.getenv("DEVELOPMENT", "false").lower() == "true",
        )

        bedrock_config = BedrockConfig(
            model_id=os.getenv(
                "BEDROCK_MODEL_ID",
                config_data.get("bedrock", {}).get(
                    "model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
                ),
            ),
            region_name=os.getenv(
                "AWS_REGION",
                config_data.get("bedrock", {}).get("region_name", "us-east-1"),
            ),
        )

        weather_config = WeatherAPIConfig(
            base_url=os.getenv(
                "WEATHER_API_BASE_URL",
                config_data.get("weather_api", {}).get(
                    "base_url", "https://api.weather.gov"
                ),
            ),
            user_agent_weather=os.getenv(
                "WEATHER_USER_AGENT",
                config_data.get("weather_api", {}).get(
                    "user_agent_weather", "LocationWeatherService/1.0"
                ),
            ),
            user_agent_alerts=os.getenv(
                "WEATHER_ALERTS_USER_AGENT",
                config_data.get("weather_api", {}).get(
                    "user_agent_alerts", "LocationWeatherAlertsService/1.0"
                ),
            ),
            timeout=int(
                os.getenv(
                    "WEATHER_API_TIMEOUT",
                    config_data.get("weather_api", {}).get("timeout", 30),
                )
            ),
        )

        mcp_config = MCPConfig(
            command=os.getenv(
                "MCP_COMMAND", config_data.get("mcp", {}).get("command", "uvx")
            ),
            server_package=os.getenv(
                "MCP_SERVER_PACKAGE",
                config_data.get("mcp", {}).get(
                    "server_package", "awslabs.aws-location-mcp-server@latest"
                ),
            ),
        )

        ui_config = UIConfig(
            app_title=os.getenv(
                "APP_TITLE",
                config_data.get("ui", {}).get("app_title", "PlaceFinder & Weather"),
            ),
            welcome_message=os.getenv(
                "WELCOME_MESSAGE",
                config_data.get("ui", {}).get(
                    "welcome_message",
                    "Ask about locations, routes, nearby places, or weather conditions.",
                ),
            ),
            prompt_text=os.getenv(
                "PROMPT_TEXT",
                config_data.get("ui", {}).get("prompt_text", "How can I help you? "),
            ),
        )

        return cls(
            opentelemetry=otel_config,
            bedrock=bedrock_config,
            weather_api=weather_config,
            mcp=mcp_config,
            ui=ui_config,
        )


# Global config instance
config = AppConfig.load()
