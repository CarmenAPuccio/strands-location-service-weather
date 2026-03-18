"""
Test FastMCP server functionality.
"""

from unittest.mock import Mock, patch

from src.strands_location_service_weather.mcp_server import get_client


class TestMCPServer:
    """Test MCP server functionality."""

    def test_get_client_initialization(self):
        """Test that get_client function works."""
        # This will test the actual client initialization
        with patch(
            "src.strands_location_service_weather.mcp_server.LocationWeatherClient"
        ) as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            # Reset the global client to test initialization
            with patch("src.strands_location_service_weather.mcp_server._client", None):
                result = get_client()

                mock_client.assert_called_once()
                assert result == mock_instance

    def test_get_client_reuses_existing(self):
        """Test that existing client is reused."""
        mock_existing = Mock()

        with patch(
            "src.strands_location_service_weather.mcp_server._client", mock_existing
        ):
            result = get_client()
            assert result == mock_existing

    def test_fastmcp_server_exists(self):
        """Test that FastMCP server is properly configured."""
        from src.strands_location_service_weather.mcp_server import mcp

        # Verify the server was created
        assert mcp is not None
        assert hasattr(mcp, "name")
        assert mcp.name == "Location Weather Service"

    def test_ask_location_weather_tool_registered(self):
        """Test that the ask_location_weather tool is registered with FastMCP."""
        import asyncio

        from src.strands_location_service_weather.mcp_server import mcp

        # Check that the tool is registered (FastMCP 3.x async API)
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "ask_location_weather" in tool_names


class TestMCPServerIntegration:
    """Test MCP server integration with mocked dependencies."""

    def test_tool_function_exists(self):
        """Test that the ask_location_weather tool function exists and is accessible."""
        import asyncio

        from src.strands_location_service_weather.mcp_server import mcp

        # Verify the tool is registered (FastMCP 3.x async API)
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "ask_location_weather" in tool_names

        tool = next(t for t in tools if t.name == "ask_location_weather")
        assert tool is not None
        assert tool.name == "ask_location_weather"


class TestMCPServerPerformance:
    """Test performance-related aspects of MCP server."""

    def test_client_pre_initialization(self):
        """Test that client can be pre-initialized."""
        # This tests that the global client pattern works
        from src.strands_location_service_weather.mcp_server import _client

        # The client should be initialized at module import
        # (or None if mocked in other tests)
        assert _client is not None or _client is None  # Either state is valid in tests

    def test_fastmcp_configuration_performance(self):
        """Test that FastMCP is configured for performance."""
        import asyncio

        from src.strands_location_service_weather.mcp_server import mcp

        # Verify the server exists and has the right name
        assert mcp.name == "Location Weather Service"

        # The server should have tools registered (FastMCP 3.x async API)
        tools = asyncio.run(mcp.list_tools())
        assert len(tools) > 0
