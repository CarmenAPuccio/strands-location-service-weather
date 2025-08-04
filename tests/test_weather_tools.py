"""
Test weather tool functions (get_weather, get_alerts).
"""

import responses

from src.strands_location_service_weather.location_weather import (
    get_alerts,
    get_weather,
)


class TestGetWeather:
    """Test the get_weather tool function."""

    @responses.activate
    def test_get_weather_success(self):
        """Test successful weather data retrieval."""
        # Mock NWS points API
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

        # Mock NWS forecast API
        responses.add(
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

        result = get_weather(47.6062, -122.3321)

        assert result["temperature"]["value"] == 72
        assert result["temperature"]["unit"] == "F"
        assert result["windSpeed"]["value"] == "10 mph"
        assert result["shortForecast"] == "Partly Cloudy"

    @responses.activate
    def test_get_weather_api_failure(self):
        """Test handling of weather API failures."""
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/47.6062,-122.3321",
            status=500,
        )

        result = get_weather(47.6062, -122.3321)

        assert "error" in result
        assert "Failed to get grid data" in result["error"]

    def test_get_weather_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        # Test with obviously invalid coordinates
        result = get_weather(999, 999)

        assert "error" in result


class TestGetAlerts:
    """Test the get_alerts tool function."""

    @responses.activate
    def test_get_alerts_no_alerts(self):
        """Test when no weather alerts are active."""
        # Mock points API
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/47.6062,-122.3321",
            json={
                "properties": {"county": "https://api.weather.gov/zones/county/WAC033"}
            },
            status=200,
        )

        # Mock alerts API with no alerts
        responses.add(
            responses.GET,
            "https://api.weather.gov/alerts/active/zone/WAC033",
            json={"features": []},
            status=200,
        )

        result = get_alerts(47.6062, -122.3321)

        assert len(result) == 1
        assert "No active weather alerts" in result[0]["message"]

    @responses.activate
    def test_get_alerts_with_active_alerts(self):
        """Test when weather alerts are active."""
        # Mock points API
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/47.6062,-122.3321",
            json={
                "properties": {"county": "https://api.weather.gov/zones/county/WAC033"}
            },
            status=200,
        )

        # Mock alerts API with active alert
        responses.add(
            responses.GET,
            "https://api.weather.gov/alerts/active/zone/WAC033",
            json={
                "features": [
                    {
                        "properties": {
                            "event": "High Wind Warning",
                            "headline": "High Wind Warning until 6 PM",
                            "description": "Winds 40-50 mph expected",
                            "severity": "Severe",
                            "urgency": "Expected",
                            "effective": "2024-01-01T12:00:00Z",
                            "expires": "2024-01-01T18:00:00Z",
                            "instruction": "Secure loose objects",
                        }
                    }
                ]
            },
            status=200,
        )

        result = get_alerts(47.6062, -122.3321)

        assert len(result) == 1
        assert result[0]["event"] == "High Wind Warning"
        assert result[0]["severity"] == "Severe"
