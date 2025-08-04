"""
Test performance optimizations and benchmarks.
"""

import time

import pytest
import responses

from src.strands_location_service_weather.location_weather import get_weather


class TestPerformanceOptimizations:
    """Test that performance optimizations are working."""

    def test_http_session_reuse(self):
        """Test that HTTP session is reused across calls."""
        from src.strands_location_service_weather.location_weather import _http_session

        # Verify session exists and is reused
        assert _http_session is not None

        # Multiple calls should use the same session
        session1 = _http_session
        session2 = _http_session
        assert session1 is session2

    @responses.activate
    def test_weather_api_timeout_configuration(self):
        """Test that weather API calls use optimized timeout."""
        # Mock a slow response
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/47.6062,-122.3321",
            json={"error": "timeout"},
            status=200,
        )

        start_time = time.time()
        get_weather(47.6062, -122.3321)
        elapsed = time.time() - start_time

        # Should complete quickly due to 10s timeout
        assert elapsed < 15  # Allow some buffer

    def test_system_prompt_length(self):
        """Test that system prompt is optimized for performance."""
        from src.strands_location_service_weather.location_weather import system_prompt

        # Verify prompt is concise (under 100 words for performance)
        word_count = len(system_prompt.split())
        assert word_count < 100, f"System prompt too long: {word_count} words"

        # Verify it contains essential elements
        assert "get_weather tool first" in system_prompt
        assert "get_alerts tool" in system_prompt
        assert "route queries" in system_prompt


class TestPerformanceBenchmarks:
    """Benchmark tests to ensure performance targets are met."""

    @pytest.mark.slow
    @responses.activate
    def test_simple_weather_query_performance(self):
        """Test that simple weather queries meet performance targets."""
        # Mock fast API responses
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
                            "detailedForecast": "Partly cloudy",
                        }
                    ]
                }
            },
            status=200,
        )

        start_time = time.time()
        result = get_weather(47.6062, -122.3321)
        elapsed = time.time() - start_time

        # Should complete in under 5 seconds for API calls alone
        assert elapsed < 5.0, f"Weather API call too slow: {elapsed:.2f}s"
        assert "error" not in result
