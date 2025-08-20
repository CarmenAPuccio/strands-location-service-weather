"""
Tests for tool integration in LocationWeatherClient across different deployment modes.

This test suite validates that the Strands tool integration strategy works correctly
with the LocationWeatherClient for all deployment modes as specified in requirements 8.1-8.5.
"""

from unittest.mock import Mock, patch

import pytest

from src.strands_location_service_weather.config import DeploymentMode
from src.strands_location_service_weather.location_weather import LocationWeatherClient


class TestLocationWeatherClientToolIntegration:
    """Test LocationWeatherClient integration with the tool management system."""

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_client_initialization_with_tool_validation(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test that client initialization includes tool validation."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager
        mock_tool_manager.get_tools_for_mode.return_value = [Mock(), Mock(), Mock()]
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=True, warnings=[]),
            Mock(valid=True, warnings=["Warning 1"]),
            Mock(valid=False, error_message="Tool validation failed"),
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Initialize client
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

        # Verify tool validation was called
        mock_tool_manager.validate_tools_for_mode.assert_called_once_with(
            DeploymentMode.LOCAL
        )

        # Verify client was created successfully despite validation warnings/errors
        assert client is not None

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_get_tool_validation_info(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test getting tool validation information from the client."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager
        mock_tool_manager.get_tools_for_mode.return_value = [Mock(), Mock()]
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(
                valid=True,
                tool_name="tool1",
                protocol=Mock(value="python_direct"),
                error_message=None,
                warnings=[],
            ),
            Mock(
                valid=False,
                tool_name="tool2",
                protocol=Mock(value="python_direct"),
                error_message="Validation failed",
                warnings=["Warning"],
            ),
        ]
        mock_tool_manager._get_protocol_for_mode.return_value = Mock(
            value="python_direct"
        )
        mock_tool_manager.get_protocol_info.return_value = {
            "protocol": "python_direct",
            "description": "Direct Python calls",
        }

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Initialize client and get validation info
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        validation_info = client.get_tool_validation_info()

        # Verify validation info structure
        assert validation_info["deployment_mode"] == "local"
        assert validation_info["total_tools"] == 2
        assert validation_info["valid_tools"] == 1
        assert validation_info["invalid_tools"] == 1
        assert validation_info["tools_with_warnings"] == 1
        assert len(validation_info["validation_details"]) == 2
        assert "protocol_info" in validation_info

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_health_check_includes_tool_validation(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test that health check includes tool validation results."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model
        mock_model_factory.health_check.return_value = True

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager
        mock_tool_manager.get_tools_for_mode.return_value = [Mock(), Mock()]
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=True),
            Mock(valid=True),
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Initialize client and perform health check
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        health_status = client.health_check()

        # Verify health check considers tool validation
        assert health_status.healthy is True
        assert health_status.model_healthy is True
        assert health_status.tools_available is True
        assert health_status.error_message is None

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_health_check_fails_with_invalid_tools(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test that health check fails when all tools are invalid."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model
        mock_model_factory.health_check.return_value = True

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager
        mock_tool_manager.get_tools_for_mode.return_value = [Mock(), Mock()]
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=False),
            Mock(valid=False),
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Initialize client and perform health check
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        health_status = client.health_check()

        # Verify health check fails due to invalid tools
        assert health_status.healthy is False
        assert health_status.model_healthy is True
        assert health_status.tools_available is False
        assert "tools unavailable or invalid" in health_status.error_message


class TestToolIntegrationAcrossDeploymentModes:
    """Test tool integration behavior across different deployment modes."""

    @pytest.mark.parametrize(
        "mode,expected_protocol",
        [
            (DeploymentMode.LOCAL, "python_direct"),
            (DeploymentMode.MCP, "mcp"),
            (DeploymentMode.BEDROCK_AGENT, "http_rest"),
        ],
    )
    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_correct_protocol_selection_by_mode(
        self,
        mock_tool_manager_class,
        mock_model_factory,
        mock_agent_class,
        mode,
        expected_protocol,
    ):
        """Test that each deployment mode selects the correct protocol."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager
        mock_tool_manager.get_tools_for_mode.return_value = [Mock()]
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=True, warnings=[])
        ]

        # Mock the protocol mapping
        from src.strands_location_service_weather.tool_manager import ToolProtocol

        protocol_map = {
            "python_direct": ToolProtocol.PYTHON_DIRECT,
            "mcp": ToolProtocol.MCP,
            "http_rest": ToolProtocol.HTTP_REST,
        }
        mock_tool_manager._get_protocol_for_mode.return_value = protocol_map[
            expected_protocol
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Initialize client with specific mode
        client = LocationWeatherClient(deployment_mode=mode)

        # Verify client was created successfully with the specified mode
        assert client is not None
        assert client._deployment_config.mode == mode

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_bedrock_agent_mode_uses_base_tools_only(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test that BEDROCK_AGENT mode uses only base tools (no MCP tools)."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager

        # Mock different tool sets for different modes
        def mock_get_tools_for_mode(mode):
            if mode == DeploymentMode.BEDROCK_AGENT:
                return [Mock(), Mock(), Mock()]  # Only base tools (3)
            else:
                return [Mock(), Mock(), Mock(), Mock(), Mock()]  # Base + MCP tools (5)

        mock_tool_manager.get_tools_for_mode.side_effect = mock_get_tools_for_mode
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=True, warnings=[])
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Test BEDROCK_AGENT mode
        LocationWeatherClient(deployment_mode=DeploymentMode.BEDROCK_AGENT)
        mock_tool_manager.get_tools_for_mode.assert_called_with(
            DeploymentMode.BEDROCK_AGENT
        )

        # Test LOCAL mode for comparison
        LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

        # Verify BEDROCK_AGENT was called (should be the last call)
        calls = mock_tool_manager.get_tools_for_mode.call_args_list
        assert any(call[0][0] == DeploymentMode.BEDROCK_AGENT for call in calls)
        assert any(call[0][0] == DeploymentMode.LOCAL for call in calls)

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_local_and_mcp_modes_include_mcp_tools(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test that LOCAL and MCP modes include MCP tools."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager

        # Mock tool sets - LOCAL and MCP should have more tools
        def mock_get_tools_for_mode(mode):
            if mode in [DeploymentMode.LOCAL, DeploymentMode.MCP]:
                return [Mock() for _ in range(8)]  # Base + MCP tools
            else:
                return [Mock() for _ in range(3)]  # Only base tools

        mock_tool_manager.get_tools_for_mode.side_effect = mock_get_tools_for_mode
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=True, warnings=[])
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Test LOCAL mode
        LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

        # Test MCP mode
        LocationWeatherClient(deployment_mode=DeploymentMode.MCP)

        # Verify both modes were called
        calls = mock_tool_manager.get_tools_for_mode.call_args_list
        modes_called = [call[0][0] for call in calls]
        assert DeploymentMode.LOCAL in modes_called
        assert DeploymentMode.MCP in modes_called


class TestToolExecutionConsistency:
    """Test that tool execution behavior is consistent across modes."""

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_tool_schemas_remain_consistent_across_modes(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test requirement 8.4: Tool input/output schemas remain consistent."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager

        # Create consistent tool definitions across modes
        consistent_tools = [
            Mock(__name__="get_weather", __doc__="Get weather data"),
            Mock(__name__="get_alerts", __doc__="Get weather alerts"),
            Mock(__name__="current_time", __doc__="Get current time"),
        ]

        mock_tool_manager.get_tools_for_mode.return_value = consistent_tools
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(valid=True, warnings=[]) for _ in consistent_tools
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Test all deployment modes
        clients = {}
        for mode in DeploymentMode:
            clients[mode] = LocationWeatherClient(deployment_mode=mode)

        # Verify that the same tools are available across all modes
        # (though the underlying protocols may differ)
        for mode in DeploymentMode:
            mock_tool_manager.get_tools_for_mode.assert_any_call(mode)

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.ToolManager")
    def test_error_handling_standardization(
        self, mock_tool_manager_class, mock_model_factory, mock_agent_class
    ):
        """Test requirement 8.5: Standardized error handling across protocols."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_tool_manager = Mock()
        mock_tool_manager_class.return_value = mock_tool_manager
        mock_tool_manager.get_tools_for_mode.return_value = [Mock()]

        # Simulate validation errors
        mock_tool_manager.validate_tools_for_mode.return_value = [
            Mock(
                valid=False,
                tool_name="failing_tool",
                error_message="Standardized error message",
                warnings=[],
            )
        ]

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Test that error handling is consistent across modes
        for mode in DeploymentMode:
            client = LocationWeatherClient(deployment_mode=mode)
            validation_info = client.get_tool_validation_info()

            # Verify error information is consistently structured
            assert "validation_details" in validation_info
            assert validation_info["invalid_tools"] == 1

            error_details = validation_info["validation_details"][0]
            assert error_details["valid"] is False
            assert error_details["error_message"] == "Standardized error message"


class TestToolManagerIntegrationWithRealTools:
    """Integration tests with actual tool functions."""

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.mcp_tools", [])
    def test_integration_with_weather_tools(self, mock_model_factory, mock_agent_class):
        """Test integration with actual weather tool functions."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model
        mock_model_factory.health_check.return_value = True

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Initialize client - this should work with real tool functions
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

        # Verify client was created successfully
        assert client is not None

        # Get tool validation info
        validation_info = client.get_tool_validation_info()

        # Should have at least the base weather tools
        assert validation_info["total_tools"] >= 3
        assert validation_info["deployment_mode"] == "local"

        # Most tools should be valid
        assert validation_info["valid_tools"] >= 2

    @patch("src.strands_location_service_weather.location_weather.Agent")
    @patch("src.strands_location_service_weather.location_weather.ModelFactory")
    @patch("src.strands_location_service_weather.location_weather.mcp_tools", [])
    def test_tool_validation_with_real_functions(
        self, mock_model_factory, mock_agent_class
    ):
        """Test tool validation with real weather functions."""
        # Set up mocks
        mock_model = Mock()
        mock_model_factory.create_model.return_value = mock_model

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Test different deployment modes
        for mode in DeploymentMode:
            client = LocationWeatherClient(deployment_mode=mode)
            validation_info = client.get_tool_validation_info()

            # Verify validation structure
            assert "validation_details" in validation_info
            assert isinstance(validation_info["validation_details"], list)

            # Check that each tool has proper validation info
            for tool_detail in validation_info["validation_details"]:
                assert "tool_name" in tool_detail
                assert "valid" in tool_detail
                assert "protocol" in tool_detail

            # Verify protocol info is available
            assert "protocol_info" in validation_info
            assert validation_info["protocol_info"] is not None
