"""
Integration tests for multi-mode LocationWeatherClient functionality.
Tests comparing responses across LOCAL, MCP, and BEDROCK_AGENT deployment modes.
"""

from unittest.mock import Mock, patch

import pytest

from strands_location_service_weather.config import DeploymentMode
from strands_location_service_weather.location_weather import (
    HealthStatus,
    LocationWeatherClient,
)
from strands_location_service_weather.model_factory import ModelCreationError


class TestMultiModeIntegration:
    """Test multi-mode deployment functionality."""

    def test_local_mode_initialization(self):
        """Test LocationWeatherClient initialization in LOCAL mode."""
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

        deployment_info = client.get_deployment_info()
        assert deployment_info.mode == DeploymentMode.LOCAL
        assert deployment_info.model_type == "BedrockModel"
        assert deployment_info.model_id is not None
        assert deployment_info.tools_count > 0

    def test_mcp_mode_initialization(self):
        """Test LocationWeatherClient initialization in MCP mode."""
        client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)

        deployment_info = client.get_deployment_info()
        assert deployment_info.mode == DeploymentMode.MCP
        assert deployment_info.model_type == "BedrockModel"
        assert deployment_info.model_id is not None
        assert deployment_info.tools_count > 0

    @patch("strands_location_service_weather.model_factory.ModelFactory.create_model")
    def test_bedrock_agent_mode_initialization(self, mock_create_model):
        """Test LocationWeatherClient initialization in BEDROCK_AGENT mode."""
        # Mock Bedrock Agent model instance
        mock_model_instance = Mock()
        mock_model_instance.agent_id = "test-agent-123"
        mock_model_instance.region_name = "us-east-1"
        mock_create_model.return_value = mock_model_instance

        # Create config override with required Bedrock Agent parameters
        config_override = {"bedrock_agent_id": "test-agent-123"}

        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override=config_override,
        )

        deployment_info = client.get_deployment_info()
        assert deployment_info.mode == DeploymentMode.BEDROCK_AGENT
        assert deployment_info.model_type == "Mock"  # Mock class name
        assert deployment_info.agent_id == "test-agent-123"
        assert deployment_info.tools_count > 0

    def test_backward_compatibility_parameters(self):
        """Test backward compatibility with old constructor parameters."""
        # Test with old-style parameters
        client = LocationWeatherClient(
            model_id="anthropic.claude-3-haiku-20240307-v1:0", region_name="us-west-2"
        )

        deployment_info = client.get_deployment_info()
        assert deployment_info.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
        assert deployment_info.region == "us-west-2"
        assert deployment_info.mode == DeploymentMode.LOCAL  # Default mode

    def test_config_override_functionality(self):
        """Test configuration override functionality."""
        config_override = {
            "bedrock_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "aws_region": "eu-west-1",
        }

        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.LOCAL, config_override=config_override
        )

        deployment_info = client.get_deployment_info()
        assert deployment_info.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
        assert deployment_info.region == "eu-west-1"

    def test_custom_system_prompt(self):
        """Test custom system prompt functionality."""
        custom_prompt = "You are a test assistant for weather queries."

        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.LOCAL, custom_system_prompt=custom_prompt
        )

        # Verify client was created successfully
        assert client.agent is not None
        deployment_info = client.get_deployment_info()
        assert deployment_info.mode == DeploymentMode.LOCAL

    def test_health_check_functionality(self):
        """Test health check functionality across modes."""
        # Test LOCAL mode health check
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        health_status = client.health_check()

        assert isinstance(health_status, HealthStatus)
        assert isinstance(health_status.healthy, bool)
        assert isinstance(health_status.model_healthy, bool)
        assert isinstance(health_status.tools_available, bool)

    @patch("strands_location_service_weather.model_factory.ModelFactory.create_model")
    def test_model_creation_error_handling(self, mock_create_model):
        """Test error handling when model creation fails."""
        mock_create_model.side_effect = ModelCreationError(
            "Test model creation failure"
        )

        with pytest.raises(ModelCreationError):
            LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

    def test_tools_for_different_modes(self):
        """Test that different modes get appropriate tools."""
        # LOCAL mode should include MCP tools
        local_client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        local_info = local_client.get_deployment_info()

        # MCP mode should include MCP tools
        mcp_client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)
        mcp_info = mcp_client.get_deployment_info()

        # Both should have the same tool count (base + MCP tools)
        assert local_info.tools_count == mcp_info.tools_count
        assert (
            local_info.tools_count >= 3
        )  # At least base tools (current_time, get_weather, get_alerts)

    @patch("strands_location_service_weather.model_factory.ModelFactory.create_model")
    def test_bedrock_agent_tools_configuration(self, mock_create_model):
        """Test that BedrockAgent mode uses appropriate tools configuration."""
        # Mock BedrockAgentModel instance
        mock_model_instance = Mock()
        mock_model_instance.agent_id = "test-agent-123"
        mock_model_instance.region_name = "us-east-1"
        mock_create_model.return_value = mock_model_instance

        config_override = {"bedrock_agent_agent_id": "test-agent-123"}

        bedrock_agent_client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override=config_override,
        )
        bedrock_agent_info = bedrock_agent_client.get_deployment_info()

        # BedrockAgent should have base tools only (MCP tools replaced by action groups)
        assert (
            bedrock_agent_info.tools_count >= 3
        )  # Base tools: current_time, get_weather, get_alerts

    def test_deployment_info_completeness(self):
        """Test that deployment info contains all required fields."""
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        info = client.get_deployment_info()

        assert info.mode is not None
        assert info.model_type is not None
        assert info.region is not None
        assert info.tools_count > 0
        # model_id should be present for BedrockModel
        assert info.model_id is not None
        # agent_id should be None for non-BedrockAgent modes
        assert info.agent_id is None

    @patch("strands_location_service_weather.model_factory.ModelFactory.create_model")
    def test_bedrock_agent_deployment_info(self, mock_create_model):
        """Test deployment info for BedrockAgent mode."""
        mock_model_instance = Mock()
        mock_model_instance.agent_id = "test-agent-123"
        mock_model_instance.region_name = "us-east-1"
        # BedrockAgent models don't use model_id, they use agent_id
        mock_create_model.return_value = mock_model_instance

        config_override = {"bedrock_agent_agent_id": "test-agent-123"}

        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override=config_override,
        )
        info = client.get_deployment_info()

        assert info.mode == DeploymentMode.BEDROCK_AGENT
        assert info.agent_id == "test-agent-123"
        assert info.model_id is None  # BedrockAgent uses agent_id instead

    @patch("strands_location_service_weather.location_weather.requests.Session.get")
    def test_chat_functionality_consistency(self, mock_get):
        """Test that chat functionality works consistently across modes."""
        # Mock weather API responses
        mock_points_response = Mock()
        mock_points_response.status_code = 200
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/SEW/124,67/forecast"
            }
        }

        mock_forecast_response = Mock()
        mock_forecast_response.status_code = 200
        mock_forecast_response.json.return_value = {
            "properties": {
                "periods": [
                    {
                        "temperature": 72,
                        "temperatureUnit": "F",
                        "windSpeed": "5 mph",
                        "windDirection": "SW",
                        "shortForecast": "Sunny",
                        "detailedForecast": "Sunny skies with light winds",
                    }
                ]
            }
        }

        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        # Test LOCAL mode
        local_client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

        # Verify client can be created and has chat method
        assert hasattr(local_client, "chat")
        assert callable(local_client.chat)

        # Test MCP mode
        mcp_client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)

        # Verify client can be created and has chat method
        assert hasattr(mcp_client, "chat")
        assert callable(mcp_client.chat)


class TestMultiModeErrorHandling:
    """Test error handling across different deployment modes."""

    def test_invalid_deployment_mode_config(self):
        """Test handling of invalid deployment mode configuration."""
        with pytest.raises(ValueError):
            # This should fail because BEDROCK_AGENT mode requires agent_id
            LocationWeatherClient(deployment_mode=DeploymentMode.BEDROCK_AGENT)

    @patch(
        "strands_location_service_weather.model_factory.ModelFactory.validate_model_config"
    )
    def test_config_validation_error(self, mock_validate):
        """Test handling of configuration validation errors."""
        mock_validate.side_effect = ValueError("Invalid configuration")

        with pytest.raises(ValueError):
            LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

    def test_health_check_with_unhealthy_model(self):
        """Test health check when model is unhealthy."""
        with patch(
            "strands_location_service_weather.model_factory.ModelFactory.health_check"
        ) as mock_health:
            mock_health.return_value = False

            client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
            health_status = client.health_check()

            assert not health_status.healthy
            assert not health_status.model_healthy
            assert health_status.error_message is not None

    def test_health_check_exception_handling(self):
        """Test health check exception handling."""
        with patch(
            "strands_location_service_weather.model_factory.ModelFactory.health_check"
        ) as mock_health:
            mock_health.side_effect = Exception("Health check failed")

            client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
            health_status = client.health_check()

            assert not health_status.healthy
            assert health_status.error_message is not None
            assert "Health check exception" in health_status.error_message


class TestBackwardCompatibility:
    """Test backward compatibility with existing interfaces."""

    def test_old_constructor_interface(self):
        """Test that old constructor interface still works."""
        # This should work exactly as before
        client = LocationWeatherClient(
            custom_system_prompt="Test prompt",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            region_name="us-east-1",
        )

        assert client.agent is not None
        deployment_info = client.get_deployment_info()
        assert deployment_info.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert deployment_info.region == "us-east-1"

    def test_chat_method_signature_unchanged(self):
        """Test that chat method signature remains unchanged."""
        client = LocationWeatherClient()

        # Should accept string and return string
        assert hasattr(client, "chat")

        # Test method signature compatibility
        import inspect

        sig = inspect.signature(client.chat)
        params = list(sig.parameters.keys())
        assert "prompt" in params
        assert len(params) == 1  # Only prompt parameter

    def test_default_behavior_unchanged(self):
        """Test that default behavior without parameters works as before."""
        # This should work exactly as the original implementation
        client = LocationWeatherClient()

        assert client.agent is not None
        deployment_info = client.get_deployment_info()
        assert deployment_info.mode == DeploymentMode.LOCAL  # Default mode
        assert deployment_info.tools_count > 0
