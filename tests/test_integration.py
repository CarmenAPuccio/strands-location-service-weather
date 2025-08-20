"""
Integration tests for end-to-end functionality.
"""

from unittest.mock import Mock, patch

import pytest
import responses

from src.strands_location_service_weather.location_weather import LocationWeatherClient


class TestIntegration:
    """Test end-to-end integration scenarios."""

    @responses.activate
    @patch("src.strands_location_service_weather.model_factory.BedrockModel")
    @patch("src.strands_location_service_weather.location_weather.stdio_mcp_client")
    def test_complete_weather_query_flow(self, mock_mcp, mock_bedrock):
        """Test complete flow from query to response."""
        # Setup mocks
        mock_mcp.list_tools_sync.return_value = []

        # Mock weather API responses
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/47.6062,-122.3321",
            json={
                "properties": {
                    "forecast": "https://api.weather.gov/gridpoints/SEW/125,67/forecast"
                }
            },
            status=200,
        )

        # Create client and mock the agent directly on the instance
        client = LocationWeatherClient()
        mock_agent_instance = Mock()
        mock_agent_instance.return_value = "Weather: 72°F, no alerts"
        client.agent = mock_agent_instance

        result = client.chat("What's the weather in Seattle?")

        # Verify agent was called with the query
        mock_agent_instance.assert_called_with("What's the weather in Seattle?")
        assert result == "Weather: 72°F, no alerts"

    def test_tool_registration(self):
        """Test that all required tools are registered."""
        from src.strands_location_service_weather.location_weather import (
            get_alerts,
            get_weather,
        )

        # Verify tools are callable
        assert callable(get_weather)
        assert callable(get_alerts)

        # Verify tools have proper docstrings
        assert get_weather.__doc__ is not None
        assert get_alerts.__doc__ is not None
        assert "latitude" in get_weather.__doc__
        assert "longitude" in get_weather.__doc__


class TestErrorHandling:
    """Test error handling in various scenarios."""

    @responses.activate
    def test_weather_api_network_error(self):
        """Test handling of network errors from weather API."""
        from src.strands_location_service_weather.location_weather import get_weather

        # Don't add any responses to simulate network error
        result = get_weather(47.6062, -122.3321)

        assert "error" in result
        assert isinstance(result["error"], str)

    @patch("src.strands_location_service_weather.location_weather.Agent")
    def test_bedrock_error_handling(
        self, mock_agent, mock_bedrock_model, mock_mcp_client
    ):
        """Test handling of Bedrock/Agent errors."""
        mock_agent.side_effect = Exception("Bedrock service unavailable")

        with pytest.raises(Exception):  # noqa: B017
            LocationWeatherClient()

    def test_invalid_coordinates_handling(self):
        """Test handling of invalid coordinate inputs."""
        from src.strands_location_service_weather.location_weather import (
            get_alerts,
            get_weather,
        )

        # Test with None values
        result_weather = get_weather(None, None)
        result_alerts = get_alerts(None, None)

        assert "error" in result_weather
        assert len(result_alerts) > 0 and "error" in result_alerts[0]
