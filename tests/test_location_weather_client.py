"""
Test LocationWeatherClient integration and behavior.
"""

from unittest.mock import Mock

from src.strands_location_service_weather.location_weather import LocationWeatherClient


class TestLocationWeatherClient:
    """Test the main LocationWeatherClient class."""

    def test_client_initialization(
        self, mock_bedrock_model, mock_mcp_client, mock_mcp_tools
    ):
        """Test that client initializes correctly with mocked dependencies."""
        client = LocationWeatherClient()

        # Verify BedrockModel was called
        mock_bedrock_model.assert_called_once()

        # MCP client list_tools_sync is called during module import, not client init
        # So we just verify the client was created successfully
        assert client is not None

    def test_client_with_custom_model_id(self, mock_bedrock_model, mock_mcp_client):
        """Test client initialization with custom model ID."""
        custom_model = "anthropic.claude-3-haiku-20240307-v1:0"
        LocationWeatherClient(model_id=custom_model)

        # Verify custom model ID was used (now includes timeout parameter)
        mock_bedrock_model.assert_called_with(
            model_id=custom_model, region_name="us-east-1", timeout=30
        )

    def test_chat_method_calls_agent(self, weather_client):
        """Test that chat method properly calls the agent."""
        # Mock the agent instance directly on the client after it's created
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = "Weather response"
        weather_client.agent = mock_agent_instance

        # Call chat method
        result = weather_client.chat("What's the weather in Seattle?")

        # Verify the agent instance was called with the prompt
        mock_agent_instance.assert_called_once_with("What's the weather in Seattle?")
        assert result == "Weather response"

    def test_chat_method_handles_exceptions(self, weather_client):
        """Test that chat method handles agent exceptions gracefully."""
        # Mock the agent instance to raise an exception
        mock_agent_instance = Mock()
        mock_agent_instance.side_effect = Exception("Bedrock error")
        weather_client.agent = mock_agent_instance

        # Call chat method
        result = weather_client.chat("What's the weather?")

        # Verify error handling
        assert "error processing your request" in result.lower()
        assert "Bedrock error" in result


class TestSystemPromptBehavior:
    """Test that the system prompt produces expected behavior."""

    def test_system_prompt_emphasizes_weather_first(self):
        """Test that system prompt instructs to get weather data first."""
        from src.strands_location_service_weather.location_weather import system_prompt

        assert "get_weather tool first" in system_prompt
        assert "then use get_alerts tool" in system_prompt

    def test_system_prompt_includes_route_safety(self):
        """Test that system prompt includes route safety instructions."""
        from src.strands_location_service_weather.location_weather import system_prompt

        assert "route queries" in system_prompt
        assert "travel safety" in system_prompt
