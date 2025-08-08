"""Configuration management for the location weather service."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11


class DeploymentMode(Enum):
    """Deployment mode options for the location weather service."""

    LOCAL = "local"
    MCP = "mcp"
    AGENTCORE = "agentcore"


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
    timeout: int = 10


@dataclass
class MCPConfig:
    """Model Context Protocol configuration."""

    command: str = "uvx"
    server_package: str = "awslabs.aws-location-mcp-server@latest"


@dataclass
class AgentCoreConfig:
    """AWS Bedrock AgentCore configuration."""

    agent_id: str | None = None
    agent_alias_id: str = "TSTALIASID"
    session_id: str | None = None
    enable_trace: bool = True


@dataclass
class GuardrailConfig:
    """Bedrock Guardrails configuration for location service use case."""

    guardrail_id: str | None = None
    guardrail_version: str = "DRAFT"
    enable_content_filtering: bool = True
    enable_pii_detection: bool = True
    enable_toxicity_detection: bool = True
    # Location service specific: Allow ADDRESS PII for location queries
    blocked_pii_types: list[str] = None
    allowed_pii_types: list[str] = None
    content_filter_strength: str = "HIGH"
    pii_filter_strength: str = "HIGH"
    toxicity_filter_strength: str = "HIGH"

    def __post_init__(self):
        """Set default PII configuration for location services."""
        if self.blocked_pii_types is None:
            # Block sensitive PII but allow ADDRESS for location services
            self.blocked_pii_types = [
                "PHONE",
                "EMAIL",
                "CREDIT_DEBIT_CARD_NUMBER",
                "US_SOCIAL_SECURITY_NUMBER",
                "US_BANK_ACCOUNT_NUMBER",
                "US_BANK_ROUTING_NUMBER",
                "US_PASSPORT_NUMBER",
                "DRIVER_ID",
                "LICENSE_PLATE",
                "USERNAME",
                "PASSWORD",
                "NAME",  # Block personal names for privacy
                # Removed VEHICLE_VIN and PIN as they may not be supported in all regions
            ]

        if self.allowed_pii_types is None:
            # Explicitly allow only location-related PII for weather/location service
            self.allowed_pii_types = [
                "ADDRESS",
                "US_STATE",
                "CITY",
                "ZIP_CODE",
                "COUNTRY",
            ]

    def get_pii_entities_config(self) -> list[dict[str, str]]:
        """Generate PII entities configuration for Bedrock Guardrails."""
        pii_config = []

        # Add blocked PII types
        for pii_type in self.blocked_pii_types:
            pii_config.append({"type": pii_type, "action": "BLOCK"})

        # Note: Bedrock Guardrails doesn't have explicit "ALLOW" action
        # Instead, we exclude ADDRESS-related PII from the blocked list
        # This is handled by not including them in blocked_pii_types

        return pii_config

    def get_content_filters_config(self) -> list[dict[str, str]]:
        """Generate content filters configuration for Bedrock Guardrails."""
        return [
            {
                "type": "SEXUAL",
                "inputStrength": self.content_filter_strength,
                "outputStrength": self.content_filter_strength,
            },
            {
                "type": "VIOLENCE",
                "inputStrength": self.content_filter_strength,
                "outputStrength": self.content_filter_strength,
            },
            {
                "type": "HATE",
                "inputStrength": self.content_filter_strength,
                "outputStrength": self.content_filter_strength,
            },
            {
                "type": "INSULTS",
                "inputStrength": "MEDIUM",  # Less strict for insults
                "outputStrength": "MEDIUM",
            },
            {
                "type": "MISCONDUCT",
                "inputStrength": self.content_filter_strength,
                "outputStrength": self.content_filter_strength,
            },
        ]

    def validate(self) -> list[str]:
        """Validate guardrail configuration and return any errors."""
        errors = []

        if self.enable_content_filtering and not self.content_filter_strength:
            errors.append(
                "content_filter_strength is required when content filtering is enabled"
            )

        if self.enable_pii_detection and not self.pii_filter_strength:
            errors.append(
                "pii_filter_strength is required when PII detection is enabled"
            )

        if self.enable_toxicity_detection and not self.toxicity_filter_strength:
            errors.append(
                "toxicity_filter_strength is required when toxicity detection is enabled"
            )

        valid_strengths = ["LOW", "MEDIUM", "HIGH"]
        if self.content_filter_strength not in valid_strengths:
            errors.append(f"content_filter_strength must be one of {valid_strengths}")

        if self.pii_filter_strength not in valid_strengths:
            errors.append(f"pii_filter_strength must be one of {valid_strengths}")

        if self.toxicity_filter_strength not in valid_strengths:
            errors.append(f"toxicity_filter_strength must be one of {valid_strengths}")

        return errors


@dataclass
class DeploymentConfig:
    """Deployment mode configuration with mode-specific parameters."""

    mode: DeploymentMode = DeploymentMode.LOCAL
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    agentcore_agent_id: str | None = None
    aws_region: str = "us-east-1"
    enable_tracing: bool = True
    timeout: int = 30

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.mode == DeploymentMode.AGENTCORE and not self.agentcore_agent_id:
            raise ValueError("agentcore_agent_id is required when mode is AGENTCORE")

    @classmethod
    def from_env_and_config(cls, config_data: dict) -> "DeploymentConfig":
        """Create DeploymentConfig from environment variables and config data."""
        # Get deployment mode from environment or config
        mode_str = os.getenv(
            "DEPLOYMENT_MODE", config_data.get("deployment", {}).get("mode", "local")
        ).lower()

        try:
            mode = DeploymentMode(mode_str)
        except ValueError as err:
            raise ValueError(
                f"Invalid deployment mode: {mode_str}. Must be one of: {[m.value for m in DeploymentMode]}"
            ) from err

        return cls(
            mode=mode,
            bedrock_model_id=os.getenv(
                "BEDROCK_MODEL_ID",
                config_data.get("deployment", {}).get(
                    "bedrock_model_id", "anthropic.claude-3-sonnet-20240229-v1:0"
                ),
            ),
            agentcore_agent_id=os.getenv(
                "AGENTCORE_AGENT_ID",
                config_data.get("deployment", {}).get("agentcore_agent_id"),
            ),
            aws_region=os.getenv(
                "AWS_REGION",
                config_data.get("deployment", {}).get("aws_region", "us-east-1"),
            ),
            enable_tracing=os.getenv("ENABLE_TRACING", "true").lower() == "true",
            timeout=int(
                os.getenv(
                    "DEPLOYMENT_TIMEOUT",
                    config_data.get("deployment", {}).get("timeout", 30),
                )
            ),
        )


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
    deployment: DeploymentConfig
    agentcore: AgentCoreConfig
    guardrail: GuardrailConfig

    @classmethod
    def load(cls, config_file: Path | None = None) -> "AppConfig":
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

        deployment_config = DeploymentConfig.from_env_and_config(config_data)

        agentcore_config = AgentCoreConfig(
            agent_id=os.getenv(
                "AGENTCORE_AGENT_ID",
                config_data.get("agentcore", {}).get("agent_id"),
            ),
            agent_alias_id=os.getenv(
                "AGENTCORE_AGENT_ALIAS_ID",
                config_data.get("agentcore", {}).get("agent_alias_id", "TSTALIASID"),
            ),
            session_id=os.getenv(
                "AGENTCORE_SESSION_ID",
                config_data.get("agentcore", {}).get("session_id"),
            ),
            enable_trace=os.getenv(
                "AGENTCORE_ENABLE_TRACE",
                str(config_data.get("agentcore", {}).get("enable_trace", True)),
            ).lower()
            == "true",
        )

        guardrail_config = GuardrailConfig(
            guardrail_id=os.getenv(
                "GUARDRAIL_ID",
                config_data.get("guardrail", {}).get("guardrail_id"),
            ),
            guardrail_version=os.getenv(
                "GUARDRAIL_VERSION",
                config_data.get("guardrail", {}).get("guardrail_version", "DRAFT"),
            ),
            enable_content_filtering=os.getenv(
                "GUARDRAIL_CONTENT_FILTERING",
                str(
                    config_data.get("guardrail", {}).get(
                        "enable_content_filtering", True
                    )
                ),
            ).lower()
            == "true",
            enable_pii_detection=os.getenv(
                "GUARDRAIL_PII_DETECTION",
                str(config_data.get("guardrail", {}).get("enable_pii_detection", True)),
            ).lower()
            == "true",
            enable_toxicity_detection=os.getenv(
                "GUARDRAIL_TOXICITY_DETECTION",
                str(
                    config_data.get("guardrail", {}).get(
                        "enable_toxicity_detection", True
                    )
                ),
            ).lower()
            == "true",
            content_filter_strength=os.getenv(
                "GUARDRAIL_CONTENT_FILTER_STRENGTH",
                config_data.get("guardrail", {}).get("content_filter_strength", "HIGH"),
            ),
            pii_filter_strength=os.getenv(
                "GUARDRAIL_PII_FILTER_STRENGTH",
                config_data.get("guardrail", {}).get("pii_filter_strength", "HIGH"),
            ),
            toxicity_filter_strength=os.getenv(
                "GUARDRAIL_TOXICITY_FILTER_STRENGTH",
                config_data.get("guardrail", {}).get(
                    "toxicity_filter_strength", "HIGH"
                ),
            ),
        )

        return cls(
            opentelemetry=otel_config,
            bedrock=bedrock_config,
            weather_api=weather_config,
            mcp=mcp_config,
            ui=ui_config,
            deployment=deployment_config,
            agentcore=agentcore_config,
            guardrail=guardrail_config,
        )


# Global config instance
config = AppConfig.load()
