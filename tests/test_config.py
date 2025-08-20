"""
Tests for configuration management system.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.strands_location_service_weather.config import (
    AppConfig,
    BedrockAgentConfig,
    BedrockConfig,
    DeploymentConfig,
    DeploymentMode,
    GuardrailConfig,
    MCPConfig,
    OpenTelemetryConfig,
    UIConfig,
    WeatherAPIConfig,
)


class TestDeploymentMode:
    """Test DeploymentMode enum."""

    def test_deployment_mode_values(self):
        """Test that DeploymentMode has correct values."""
        assert DeploymentMode.LOCAL.value == "local"
        assert DeploymentMode.MCP.value == "mcp"
        assert DeploymentMode.BEDROCK_AGENT.value == "bedrock_agent"

    def test_deployment_mode_from_string(self):
        """Test creating DeploymentMode from string values."""
        assert DeploymentMode("local") == DeploymentMode.LOCAL
        assert DeploymentMode("mcp") == DeploymentMode.MCP
        assert DeploymentMode("bedrock_agent") == DeploymentMode.BEDROCK_AGENT

    def test_invalid_deployment_mode(self):
        """Test that invalid deployment mode raises ValueError."""
        with pytest.raises(ValueError):
            DeploymentMode("invalid")


class TestDeploymentConfig:
    """Test DeploymentConfig dataclass."""

    def test_default_values(self):
        """Test DeploymentConfig default values."""
        config = DeploymentConfig()
        assert config.mode == DeploymentMode.LOCAL
        assert config.bedrock_model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert config.bedrock_agent_id is None
        assert config.aws_region == "us-east-1"
        assert config.enable_tracing is True
        assert config.timeout == 30

    def test_bedrock_agent_mode_requires_agent_id(self):
        """Test that BEDROCK_AGENT mode requires agent_id."""
        with pytest.raises(ValueError, match="bedrock_agent_id is required"):
            DeploymentConfig(mode=DeploymentMode.BEDROCK_AGENT)

    def test_bedrock_agent_mode_with_agent_id(self):
        """Test that BEDROCK_AGENT mode works with agent_id."""
        config = DeploymentConfig(
            mode=DeploymentMode.BEDROCK_AGENT, bedrock_agent_id="test-agent-id"
        )
        assert config.mode == DeploymentMode.BEDROCK_AGENT
        assert config.bedrock_agent_id == "test-agent-id"

    def test_local_and_mcp_modes_without_agent_id(self):
        """Test that LOCAL and MCP modes work without agent_id."""
        local_config = DeploymentConfig(mode=DeploymentMode.LOCAL)
        assert local_config.mode == DeploymentMode.LOCAL
        assert local_config.bedrock_agent_id is None

        mcp_config = DeploymentConfig(mode=DeploymentMode.MCP)
        assert mcp_config.mode == DeploymentMode.MCP
        assert mcp_config.bedrock_agent_id is None

    @patch.dict(
        os.environ,
        {
            "DEPLOYMENT_MODE": "bedrock_agent",
            "BEDROCK_MODEL_ID": "custom-model",
            "BEDROCK_AGENT_ID": "test-agent",
            "AWS_REGION": "us-west-2",
            "ENABLE_TRACING": "false",
            "DEPLOYMENT_TIMEOUT": "60",
        },
    )
    def test_from_env_and_config_with_env_vars(self):
        """Test DeploymentConfig.from_env_and_config with environment variables."""
        config_data = {}
        config = DeploymentConfig.from_env_and_config(config_data)

        assert config.mode == DeploymentMode.BEDROCK_AGENT
        assert config.bedrock_model_id == "custom-model"
        assert config.bedrock_agent_id == "test-agent"
        assert config.aws_region == "us-west-2"
        assert config.enable_tracing is False
        assert config.timeout == 60

    def test_from_env_and_config_with_config_data(self):
        """Test DeploymentConfig.from_env_and_config with config file data."""
        config_data = {
            "deployment": {
                "mode": "mcp",
                "bedrock_model_id": "config-model",
                "aws_region": "eu-west-1",
                "timeout": 45,
            }
        }
        config = DeploymentConfig.from_env_and_config(config_data)

        assert config.mode == DeploymentMode.MCP
        assert config.bedrock_model_id == "config-model"
        assert config.aws_region == "eu-west-1"
        assert config.timeout == 45

    @patch.dict(os.environ, {"DEPLOYMENT_MODE": "invalid"})
    def test_from_env_and_config_invalid_mode(self):
        """Test that invalid deployment mode raises ValueError."""
        config_data = {}
        with pytest.raises(ValueError, match="Invalid deployment mode: invalid"):
            DeploymentConfig.from_env_and_config(config_data)

    @patch.dict(
        os.environ, {"DEPLOYMENT_MODE": "local", "BEDROCK_MODEL_ID": "env-model"}
    )
    def test_env_vars_override_config_data(self):
        """Test that environment variables override config file data."""
        config_data = {
            "deployment": {"mode": "mcp", "bedrock_model_id": "config-model"}
        }
        config = DeploymentConfig.from_env_and_config(config_data)

        # Environment variables should override config file
        assert config.mode == DeploymentMode.LOCAL
        assert config.bedrock_model_id == "env-model"


class TestBedrockAgentConfig:
    """Test BedrockAgentConfig dataclass."""

    def test_default_values(self):
        """Test BedrockAgentConfig default values."""
        config = BedrockAgentConfig()
        assert config.agent_id is None
        assert config.agent_alias_id == "TSTALIASID"
        assert config.session_id is None
        assert config.enable_trace is True

    def test_custom_values(self):
        """Test BedrockAgentConfig with custom values."""
        config = BedrockAgentConfig(
            agent_id="custom-agent",
            agent_alias_id="CUSTOM",
            session_id="session-123",
            enable_trace=False,
        )
        assert config.agent_id == "custom-agent"
        assert config.agent_alias_id == "CUSTOM"
        assert config.session_id == "session-123"
        assert config.enable_trace is False


class TestGuardrailConfig:
    """Test GuardrailConfig dataclass."""

    def test_default_values(self):
        """Test GuardrailConfig default values."""
        config = GuardrailConfig()
        assert config.guardrail_id is None
        assert config.guardrail_version == "DRAFT"
        assert config.enable_content_filtering is True
        assert config.enable_pii_detection is True
        assert config.enable_toxicity_detection is True

    def test_custom_values(self):
        """Test GuardrailConfig with custom values."""
        config = GuardrailConfig(
            guardrail_id="guard-123",
            guardrail_version="1.0",
            enable_content_filtering=False,
            enable_pii_detection=False,
            enable_toxicity_detection=False,
        )
        assert config.guardrail_id == "guard-123"
        assert config.guardrail_version == "1.0"
        assert config.enable_content_filtering is False
        assert config.enable_pii_detection is False
        assert config.enable_toxicity_detection is False


class TestAppConfigIntegration:
    """Test AppConfig integration with new deployment configuration."""

    def test_app_config_has_deployment_config(self):
        """Test that AppConfig includes deployment configuration."""
        config = AppConfig.load()
        assert hasattr(config, "deployment")
        assert isinstance(config.deployment, DeploymentConfig)
        assert hasattr(config, "bedrock_agent")
        assert isinstance(config.bedrock_agent, BedrockAgentConfig)
        assert hasattr(config, "guardrail")
        assert isinstance(config.guardrail, GuardrailConfig)

    @patch.dict(
        os.environ,
        {
            "DEPLOYMENT_MODE": "bedrock_agent",
            "BEDROCK_AGENT_ID": "test-agent",
            "BEDROCK_AGENT_ALIAS_ID": "PROD",
            "BEDROCK_AGENT_SESSION_ID": "session-456",
            "BEDROCK_AGENT_ENABLE_TRACE": "false",
            "GUARDRAIL_ID": "guard-456",
            "GUARDRAIL_VERSION": "2.0",
            "GUARDRAIL_CONTENT_FILTERING": "false",
        },
    )
    def test_app_config_load_with_deployment_env_vars(self):
        """Test AppConfig.load with deployment-related environment variables."""
        config = AppConfig.load()

        # Test deployment config
        assert config.deployment.mode == DeploymentMode.BEDROCK_AGENT
        assert config.deployment.bedrock_agent_id == "test-agent"

        # Test bedrock_agent config
        assert config.bedrock_agent.agent_id == "test-agent"
        assert config.bedrock_agent.agent_alias_id == "PROD"
        assert config.bedrock_agent.session_id == "session-456"
        assert config.bedrock_agent.enable_trace is False

        # Test guardrail config
        assert config.guardrail.guardrail_id == "guard-456"
        assert config.guardrail.guardrail_version == "2.0"
        assert config.guardrail.enable_content_filtering is False

    def test_app_config_load_with_toml_file(self):
        """Test AppConfig.load with TOML configuration file."""
        toml_content = """
[deployment]
mode = "mcp"
bedrock_model_id = "custom-claude"
aws_region = "ap-southeast-1"
timeout = 120

[bedrock_agent]
agent_alias_id = "STAGING"
enable_trace = false

[guardrail]
guardrail_version = "3.0"
enable_pii_detection = false
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                config = AppConfig.load(Path(f.name))

                # Test deployment config from TOML
                assert config.deployment.mode == DeploymentMode.MCP
                assert config.deployment.bedrock_model_id == "custom-claude"
                assert config.deployment.aws_region == "ap-southeast-1"
                assert config.deployment.timeout == 120

                # Test bedrock_agent config from TOML
                assert config.bedrock_agent.agent_alias_id == "STAGING"
                assert config.bedrock_agent.enable_trace is False

                # Test guardrail config from TOML
                assert config.guardrail.guardrail_version == "3.0"
                assert config.guardrail.enable_pii_detection is False

            finally:
                os.unlink(f.name)

    def test_backward_compatibility(self):
        """Test that existing configuration still works."""
        config = AppConfig.load()

        # Ensure all existing config sections still exist
        assert hasattr(config, "opentelemetry")
        assert hasattr(config, "bedrock")
        assert hasattr(config, "weather_api")
        assert hasattr(config, "mcp")
        assert hasattr(config, "ui")

        # Ensure they are the correct types
        assert isinstance(config.opentelemetry, OpenTelemetryConfig)
        assert isinstance(config.bedrock, BedrockConfig)
        assert isinstance(config.weather_api, WeatherAPIConfig)
        assert isinstance(config.mcp, MCPConfig)
        assert isinstance(config.ui, UIConfig)


class TestConfigurationValidation:
    """Test configuration validation logic."""

    def test_valid_local_mode_configuration(self):
        """Test that LOCAL mode configuration is valid."""
        config = DeploymentConfig(mode=DeploymentMode.LOCAL)
        # Should not raise any exceptions
        assert config.mode == DeploymentMode.LOCAL

    def test_valid_mcp_mode_configuration(self):
        """Test that MCP mode configuration is valid."""
        config = DeploymentConfig(mode=DeploymentMode.MCP)
        # Should not raise any exceptions
        assert config.mode == DeploymentMode.MCP

    def test_valid_bedrock_agent_mode_configuration(self):
        """Test that BEDROCK_AGENT mode configuration is valid with agent_id."""
        config = DeploymentConfig(
            mode=DeploymentMode.BEDROCK_AGENT, bedrock_agent_id="valid-agent-id"
        )
        # Should not raise any exceptions
        assert config.mode == DeploymentMode.BEDROCK_AGENT
        assert config.bedrock_agent_id == "valid-agent-id"

    def test_configuration_type_conversion(self):
        """Test that configuration handles type conversion correctly."""
        # Test boolean conversion
        with patch.dict(os.environ, {"ENABLE_TRACING": "false"}):
            config_data = {}
            config = DeploymentConfig.from_env_and_config(config_data)
            assert config.enable_tracing is False

        with patch.dict(os.environ, {"ENABLE_TRACING": "true"}):
            config_data = {}
            config = DeploymentConfig.from_env_and_config(config_data)
            assert config.enable_tracing is True

        # Test integer conversion
        with patch.dict(os.environ, {"DEPLOYMENT_TIMEOUT": "45"}):
            config_data = {}
            config = DeploymentConfig.from_env_and_config(config_data)
            assert config.timeout == 45
            assert isinstance(config.timeout, int)
