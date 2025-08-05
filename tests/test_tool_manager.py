"""
Tests for the ToolManager and tool integration strategy.

This test suite validates the Strands tool integration strategy across
different deployment modes and protocols as specified in requirements 8.1-8.5.
"""

from unittest.mock import Mock

from src.strands_location_service_weather.config import DeploymentMode
from src.strands_location_service_weather.tool_manager import (
    HTTPRestAdapter,
    MCPAdapter,
    PythonDirectAdapter,
    ToolDefinition,
    ToolManager,
    ToolProtocol,
)


class TestToolProtocolAdapters:
    """Test the protocol adapters for different tool execution methods."""

    def test_python_direct_adapter_validation_success(self):
        """Test PythonDirectAdapter validates tools correctly."""
        adapter = PythonDirectAdapter()

        # Create a mock tool function with @tool decoration
        mock_function = Mock()
        mock_function.__name__ = "test_tool"
        mock_function.__doc__ = "Test tool function"
        mock_function.__tool_metadata__ = {"name": "test_tool"}

        tool_def = ToolDefinition(
            name="test_tool",
            description="Test tool",
            function=mock_function,
            protocol=ToolProtocol.PYTHON_DIRECT,
            parameters_schema={},
            return_schema={},
        )

        result = adapter.validate_tool(tool_def)

        assert result.valid is True
        assert result.tool_name == "test_tool"
        assert result.protocol == ToolProtocol.PYTHON_DIRECT
        assert result.error_message is None

    def test_python_direct_adapter_validation_non_callable(self):
        """Test PythonDirectAdapter rejects non-callable tools."""
        adapter = PythonDirectAdapter()

        tool_def = ToolDefinition(
            name="invalid_tool",
            description="Invalid tool",
            function="not_a_function",  # String instead of callable
            protocol=ToolProtocol.PYTHON_DIRECT,
            parameters_schema={},
            return_schema={},
        )

        result = adapter.validate_tool(tool_def)

        assert result.valid is False
        assert "not callable" in result.error_message

    def test_python_direct_adapter_execution_success(self):
        """Test PythonDirectAdapter executes tools successfully."""
        adapter = PythonDirectAdapter()

        # Create a mock tool function
        mock_function = Mock(return_value={"result": "success"})
        mock_function.__name__ = "test_tool"

        tool_def = ToolDefinition(
            name="test_tool",
            description="Test tool",
            function=mock_function,
            protocol=ToolProtocol.PYTHON_DIRECT,
            parameters_schema={},
            return_schema={},
        )

        result = adapter.execute_tool(tool_def, param1="value1", param2="value2")

        assert result.success is True
        assert result.result == {"result": "success"}
        assert result.tool_name == "test_tool"
        assert result.protocol == ToolProtocol.PYTHON_DIRECT
        assert result.execution_time > 0
        mock_function.assert_called_once_with(param1="value1", param2="value2")

    def test_python_direct_adapter_execution_failure(self):
        """Test PythonDirectAdapter handles execution failures."""
        adapter = PythonDirectAdapter()

        # Create a mock tool function that raises an exception
        mock_function = Mock(side_effect=Exception("Tool execution failed"))
        mock_function.__name__ = "failing_tool"

        tool_def = ToolDefinition(
            name="failing_tool",
            description="Failing tool",
            function=mock_function,
            protocol=ToolProtocol.PYTHON_DIRECT,
            parameters_schema={},
            return_schema={},
        )

        result = adapter.execute_tool(tool_def, param1="value1")

        assert result.success is False
        assert result.result is None
        assert "Tool execution failed" in result.error_message
        assert result.execution_time > 0

    def test_mcp_adapter_validation(self):
        """Test MCPAdapter validates tools correctly."""
        adapter = MCPAdapter()

        mock_function = Mock()
        mock_function.__name__ = "mcp_tool"
        mock_function.__mcp_metadata__ = {"name": "mcp_tool"}

        tool_def = ToolDefinition(
            name="mcp_tool",
            description="MCP tool",
            function=mock_function,
            protocol=ToolProtocol.MCP,
            parameters_schema={"type": "object"},
            return_schema={"type": "object"},
        )

        result = adapter.validate_tool(tool_def)

        assert result.valid is True
        assert result.protocol == ToolProtocol.MCP

    def test_mcp_adapter_validation_invalid_schema(self):
        """Test MCPAdapter rejects invalid parameter schemas."""
        adapter = MCPAdapter()

        mock_function = Mock()
        mock_function.__name__ = "invalid_mcp_tool"

        tool_def = ToolDefinition(
            name="invalid_mcp_tool",
            description="Invalid MCP tool",
            function=mock_function,
            protocol=ToolProtocol.MCP,
            parameters_schema="invalid_schema",  # Should be dict
            return_schema={},
        )

        result = adapter.validate_tool(tool_def)

        assert result.valid is False
        assert "parameters_schema must be a dictionary" in result.error_message

    def test_http_rest_adapter_validation(self):
        """Test HTTPRestAdapter validates tools for AgentCore deployment."""
        adapter = HTTPRestAdapter()

        mock_function = Mock()
        mock_function.__name__ = "agentcore_tool"

        tool_def = ToolDefinition(
            name="agentcore_tool",
            description="AgentCore tool",
            function=mock_function,
            protocol=ToolProtocol.HTTP_REST,
            parameters_schema={
                "type": "object",
                "properties": {"param": {"type": "string"}},
            },
            return_schema={"type": "object"},
        )

        result = adapter.validate_tool(tool_def)

        assert result.valid is True
        assert result.protocol == ToolProtocol.HTTP_REST

    def test_http_rest_adapter_validation_warnings(self):
        """Test HTTPRestAdapter generates warnings for missing schemas."""
        adapter = HTTPRestAdapter()

        mock_function = Mock()
        mock_function.__name__ = "incomplete_tool"

        tool_def = ToolDefinition(
            name="incomplete_tool",
            description="Tool missing schemas",
            function=mock_function,
            protocol=ToolProtocol.HTTP_REST,
            parameters_schema=None,  # Missing schema
            return_schema=None,  # Missing schema
        )

        result = adapter.validate_tool(tool_def)

        assert result.valid is True  # Still valid but with warnings
        assert len(result.warnings) >= 2  # Should have warnings about missing schemas
        assert any("parameters_schema" in warning for warning in result.warnings)
        assert any("return_schema" in warning for warning in result.warnings)


class TestToolManager:
    """Test the ToolManager class for mode-specific tool selection."""

    def test_tool_manager_initialization(self):
        """Test ToolManager initializes with all protocol adapters."""
        manager = ToolManager()

        assert len(manager._adapters) == 3
        assert ToolProtocol.PYTHON_DIRECT in manager._adapters
        assert ToolProtocol.MCP in manager._adapters
        assert ToolProtocol.HTTP_REST in manager._adapters

    def test_register_tool_success(self):
        """Test successful tool registration."""
        manager = ToolManager()

        mock_function = Mock()
        mock_function.__name__ = "test_tool"
        mock_function.__doc__ = "Test tool function"
        mock_function.__tool_metadata__ = {"name": "test_tool"}

        success = manager.register_tool(
            name="test_tool",
            function=mock_function,
            protocol=ToolProtocol.PYTHON_DIRECT,
            description="Test tool",
            parameters_schema={"type": "object"},
        )

        assert success is True
        assert "test_tool" in manager._tool_registry

    def test_register_tool_validation_failure(self):
        """Test tool registration fails when validation fails."""
        manager = ToolManager()

        # Register a tool with invalid function (not callable)
        success = manager.register_tool(
            name="invalid_tool",
            function="not_callable",
            protocol=ToolProtocol.PYTHON_DIRECT,
            description="Invalid tool",
        )

        assert success is False
        assert "invalid_tool" not in manager._tool_registry

    def test_get_tools_for_local_mode(self):
        """Test getting tools for LOCAL deployment mode."""
        manager = ToolManager()

        # Test the actual implementation - it should return tools for LOCAL mode
        tools = manager.get_tools_for_mode(DeploymentMode.LOCAL)

        # Should include base tools + MCP tools for LOCAL mode
        assert (
            len(tools) >= 3
        )  # At least the base tools (current_time, get_weather, get_alerts)

        # Verify we got a list of tools (don't check specific properties since MCP tools vary)
        assert isinstance(tools, list)
        assert all(tool is not None for tool in tools)

    def test_get_tools_for_mcp_mode(self):
        """Test getting tools for MCP deployment mode."""
        manager = ToolManager()

        # Test the actual implementation - it should return tools for MCP mode
        tools = manager.get_tools_for_mode(DeploymentMode.MCP)

        # Should include base tools + MCP tools for MCP mode
        assert (
            len(tools) >= 3
        )  # At least the base tools (current_time, get_weather, get_alerts)

        # Verify we got a list of tools (don't check specific properties since MCP tools vary)
        assert isinstance(tools, list)
        assert all(tool is not None for tool in tools)

    def test_get_tools_for_agentcore_mode(self):
        """Test getting tools for AGENTCORE deployment mode."""
        manager = ToolManager()

        # Test the actual implementation - it should return tools for AGENTCORE mode
        tools = manager.get_tools_for_mode(DeploymentMode.AGENTCORE)

        # Should include only base tools for AGENTCORE mode
        # (location services handled by AgentCore action groups)
        assert (
            len(tools) == 3
        )  # Only base tools (current_time, get_weather, get_alerts)

        # Verify we got a list of tools (don't check specific properties since MCP tools vary)
        assert isinstance(tools, list)
        assert all(tool is not None for tool in tools)

    def test_validate_tools_for_mode(self):
        """Test validating all tools for a specific deployment mode."""
        manager = ToolManager()

        # Test validation with actual tools
        results = manager.validate_tools_for_mode(DeploymentMode.LOCAL)

        assert len(results) >= 3  # At least the base tools
        # Most tools should be valid for LOCAL mode (Python direct)
        valid_count = sum(1 for r in results if r.valid)
        assert valid_count >= 2  # At least 2 tools should be valid

        # Check that results have proper structure
        for result in results:
            assert hasattr(result, "valid")
            assert hasattr(result, "tool_name")
            assert hasattr(result, "protocol")

    def test_protocol_mapping_for_modes(self):
        """Test that correct protocols are mapped to deployment modes."""
        manager = ToolManager()

        # Test protocol mapping (accessing private method for testing)
        assert (
            manager._get_protocol_for_mode(DeploymentMode.LOCAL)
            == ToolProtocol.PYTHON_DIRECT
        )
        assert manager._get_protocol_for_mode(DeploymentMode.MCP) == ToolProtocol.MCP
        assert (
            manager._get_protocol_for_mode(DeploymentMode.AGENTCORE)
            == ToolProtocol.HTTP_REST
        )

    def test_execute_tool_by_name(self):
        """Test executing a registered tool by name."""
        manager = ToolManager()

        # Register a test tool
        mock_function = Mock(return_value={"result": "test_success"})
        mock_function.__name__ = "test_tool"
        mock_function.__tool_metadata__ = {"name": "test_tool"}

        manager.register_tool(
            name="test_tool",
            function=mock_function,
            protocol=ToolProtocol.PYTHON_DIRECT,
            description="Test tool",
        )

        # Execute the tool
        result = manager.execute_tool_by_name("test_tool", param1="value1")

        assert result is not None
        assert result.success is True
        assert result.result == {"result": "test_success"}
        mock_function.assert_called_once_with(param1="value1")

    def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist."""
        manager = ToolManager()

        result = manager.execute_tool_by_name("nonexistent_tool", param1="value1")

        assert result is None

    def test_get_protocol_info(self):
        """Test getting protocol information."""
        manager = ToolManager()

        info = manager.get_protocol_info(ToolProtocol.PYTHON_DIRECT)

        assert info is not None
        assert info["protocol"] == ToolProtocol.PYTHON_DIRECT.value
        assert "description" in info
        assert "typical_latency" in info

    def test_get_all_protocol_info(self):
        """Test getting information for all protocols."""
        manager = ToolManager()

        all_info = manager.get_all_protocol_info()

        assert len(all_info) == 3
        assert ToolProtocol.PYTHON_DIRECT.value in all_info
        assert ToolProtocol.MCP.value in all_info
        assert ToolProtocol.HTTP_REST.value in all_info

    def test_health_check(self):
        """Test ToolManager health check."""
        manager = ToolManager()

        health = manager.health_check()

        assert health["healthy"] is True
        assert health["adapter_count"] == 3
        assert len(health["missing_adapters"]) == 0
        assert health["total_tools"] >= 0


class TestToolIntegrationRequirements:
    """Test that tool integration meets specific requirements 8.1-8.5."""

    def test_requirement_8_1_local_mode_python_direct(self):
        """Test requirement 8.1: LOCAL mode uses direct Python function calls."""
        manager = ToolManager()

        # Verify LOCAL mode maps to PYTHON_DIRECT protocol
        protocol = manager._get_protocol_for_mode(DeploymentMode.LOCAL)
        assert protocol == ToolProtocol.PYTHON_DIRECT

        # Verify the adapter can execute Python functions directly
        adapter = manager._adapters[ToolProtocol.PYTHON_DIRECT]
        assert isinstance(adapter, PythonDirectAdapter)

        # Test actual execution
        mock_function = Mock(return_value="direct_call_result")
        mock_function.__name__ = "test_direct"

        tool_def = ToolDefinition(
            name="test_direct",
            description="Test direct call",
            function=mock_function,
            protocol=ToolProtocol.PYTHON_DIRECT,
            parameters_schema={},
            return_schema={},
        )

        result = adapter.execute_tool(tool_def, test_param="test_value")

        assert result.success is True
        assert result.result == "direct_call_result"
        mock_function.assert_called_once_with(test_param="test_value")

    def test_requirement_8_2_mcp_mode_protocol(self):
        """Test requirement 8.2: MCP mode uses Model Context Protocol."""
        manager = ToolManager()

        # Verify MCP mode maps to MCP protocol
        protocol = manager._get_protocol_for_mode(DeploymentMode.MCP)
        assert protocol == ToolProtocol.MCP

        # Verify the adapter exists and is correct type
        adapter = manager._adapters[ToolProtocol.MCP]
        assert isinstance(adapter, MCPAdapter)

        # Verify protocol info indicates MCP usage
        info = adapter.get_protocol_info()
        assert info["protocol"] == ToolProtocol.MCP.value
        assert "Model Context Protocol" in info["description"]

    def test_requirement_8_3_agentcore_mode_http_rest(self):
        """Test requirement 8.3: AGENTCORE mode uses HTTP/REST via Lambda."""
        manager = ToolManager()

        # Verify AGENTCORE mode maps to HTTP_REST protocol
        protocol = manager._get_protocol_for_mode(DeploymentMode.AGENTCORE)
        assert protocol == ToolProtocol.HTTP_REST

        # Verify the adapter exists and is correct type
        adapter = manager._adapters[ToolProtocol.HTTP_REST]
        assert isinstance(adapter, HTTPRestAdapter)

        # Verify protocol info indicates HTTP/REST and Lambda usage
        info = adapter.get_protocol_info()
        assert info["protocol"] == ToolProtocol.HTTP_REST.value
        assert "HTTP/REST" in info["description"]
        assert "Lambda" in info["description"]

    def test_requirement_8_4_consistent_tool_schemas(self):
        """Test requirement 8.4: Tool input/output schemas remain consistent."""
        manager = ToolManager()

        # Create a tool definition with specific schema
        test_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "number"}},
            "required": ["param1"],
        }

        mock_function = Mock(return_value={"output": "test"})
        mock_function.__name__ = "consistent_tool"

        # Test that the same tool definition works across all protocols
        for protocol in ToolProtocol:
            tool_def = ToolDefinition(
                name=f"consistent_tool_{protocol.value}",
                description="Tool with consistent schema",
                function=mock_function,
                protocol=protocol,
                parameters_schema=test_schema,
                return_schema={"type": "object"},
            )

            # Validation should succeed for all protocols with same schema
            validation_result = manager.validate_tool(tool_def)
            assert validation_result.valid is True

            # Schema should be preserved
            assert tool_def.parameters_schema == test_schema

    def test_requirement_8_5_standardized_error_handling(self):
        """Test requirement 8.5: Standardized error handling and timeout behavior."""
        manager = ToolManager()

        # Test error handling across all adapters
        for protocol, adapter in manager._adapters.items():
            # Create a tool that will fail
            failing_function = Mock(side_effect=Exception("Test error"))
            failing_function.__name__ = f"failing_tool_{protocol.value}"

            tool_def = ToolDefinition(
                name=f"failing_tool_{protocol.value}",
                description="Tool that fails",
                function=failing_function,
                protocol=protocol,
                parameters_schema={},
                return_schema={},
                timeout=5,  # Test timeout configuration
            )

            # Execute the failing tool
            result = adapter.execute_tool(tool_def, test_param="value")

            # All adapters should handle errors consistently
            assert result.success is False
            assert result.error_message is not None
            assert "Test error" in result.error_message
            assert result.execution_time > 0
            assert result.protocol == protocol

            # Metadata should be available for debugging
            assert result.metadata is not None
            assert "exception" in result.metadata or "error" in str(result.metadata)


class TestToolManagerIntegration:
    """Integration tests for ToolManager with actual tool functions."""

    def test_integration_with_weather_tools(self):
        """Test ToolManager integration with actual weather tools."""
        manager = ToolManager()

        # Test tool selection for different modes with actual tools
        for mode in DeploymentMode:
            tools = manager.get_tools_for_mode(mode)
            assert len(tools) >= 2  # At least weather tools

            # Validate tools for each mode
            validation_results = manager.validate_tools_for_mode(mode)
            assert len(validation_results) >= 2

            # At least some tools should be valid
            valid_count = sum(1 for r in validation_results if r.valid)
            assert valid_count >= 1  # At least one tool should be valid

    def test_end_to_end_tool_workflow(self):
        """Test complete workflow: register, validate, execute tools."""
        manager = ToolManager()

        # Create a test tool
        def test_calculation_tool(x: float, y: float) -> dict:
            """Calculate sum and product of two numbers."""
            return {"sum": x + y, "product": x * y}

        test_calculation_tool.__tool_metadata__ = {"name": "test_calculation_tool"}

        # Step 1: Register the tool
        success = manager.register_tool(
            name="test_calculation_tool",
            function=test_calculation_tool,
            protocol=ToolProtocol.PYTHON_DIRECT,
            description="Test calculation tool",
            parameters_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
                "required": ["x", "y"],
            },
            return_schema={
                "type": "object",
                "properties": {
                    "sum": {"type": "number"},
                    "product": {"type": "number"},
                },
            },
        )

        assert success is True

        # Step 2: Validate the tool
        tool_def = manager._tool_registry["test_calculation_tool"]
        validation_result = manager.validate_tool(tool_def)

        assert validation_result.valid is True
        assert validation_result.tool_name == "test_calculation_tool"

        # Step 3: Execute the tool
        execution_result = manager.execute_tool_by_name(
            "test_calculation_tool", x=5.0, y=3.0
        )

        assert execution_result is not None
        assert execution_result.success is True
        assert execution_result.result == {"sum": 8.0, "product": 15.0}
        assert execution_result.execution_time > 0

        # Step 4: Verify health check includes our tool
        health = manager.health_check()
        assert health["healthy"] is True
        assert health["total_tools"] >= 1
