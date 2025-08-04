"""
Pytest configuration and shared fixtures.
"""

import pytest
import responses
from unittest.mock import Mock, patch

from src.strands_location_service_weather.location_weather import LocationWeatherClient


@pytest.fixture
def mock_bedrock_model():
    """Mock BedrockModel for testing without AWS calls."""
    with patch(
        "src.strands_location_service_weather.location_weather.BedrockModel"
    ) as mock:
        yield mock


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client to avoid external MCP server dependency."""
    with patch(
        "src.strands_location_service_weather.location_weather.stdio_mcp_client"
    ) as mock:
        mock.list_tools_sync.return_value = []
        yield mock


@pytest.fixture
def mock_agent():
    """Mock Strands Agent for testing without Bedrock."""
    with patch("src.strands_location_service_weather.location_weather.Agent") as mock:
        agent_instance = Mock()
        mock.return_value = agent_instance
        yield agent_instance


@pytest.fixture
def mock_mcp_tools():
    """Mock the mcp_tools list to avoid MCP server dependency."""
    with patch("src.strands_location_service_weather.location_weather.mcp_tools", []):
        yield


@pytest.fixture
def weather_client(mock_bedrock_model, mock_mcp_client, mock_agent, mock_mcp_tools):
    """Create a LocationWeatherClient with mocked dependencies."""
    return LocationWeatherClient()


@pytest.fixture
def mock_weather_responses():
    """Mock HTTP responses for weather API calls."""
    with responses.RequestsMock() as rsps:
        # Mock NWS points API
        rsps.add(
            responses.GET,
            "https://api.weather.gov/points/47.6062,-122.3321",
            json={
                "properties": {
                    "forecast": "https://api.weather.gov/gridpoints/SEW/125,67/forecast"
                }
            },
            status=200,
        )

        # Mock NWS forecast API
        rsps.add(
            responses.GET,
            "https://api.weather.gov/gridpoints/SEW/125,67/forecast",
            json={
                "properties": {
                    "periods": [
                        {
                            "temperature": 72,
                            "temperatureUnit": "F",
                            "windSpeed": "10 mph",
                            "windDirection": "W",
                            "shortForecast": "Partly Cloudy",
                            "detailedForecast": "Partly cloudy with light winds",
                        }
                    ]
                }
            },
            status=200,
        )

        yield rsps
