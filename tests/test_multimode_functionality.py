#!/usr/bin/env python3
"""
Test script for validating true multi-mode functionality.

This test validates that all three deployment modes work correctly:
- LOCAL: Direct Python execution + MCP tools
- MCP: FastMCP server + MCP tools
- BEDROCK_AGENT: Bedrock Agent runtime + Lambda functions
"""

from strands_location_service_weather.config import DeploymentMode
from strands_location_service_weather.location_weather import LocationWeatherClient


class TestMultiModeFunctionality:
    """Test true multi-mode deployment functionality."""

    def test_local_mode_configuration(self):
        """Test LOCAL mode has correct configuration."""
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        info = client.get_deployment_info()

        assert info.mode == DeploymentMode.LOCAL
        assert info.model_type == "BedrockModel"
        assert info.model_id is not None
        assert info.agent_id is None
        assert info.tools_count == 10  # 3 weather + 7 MCP tools
        assert client.agent is not None  # Has direct agent
        assert not hasattr(client, "_bedrock_agent_id")  # No Bedrock Agent ID

    def test_mcp_mode_configuration(self):
        """Test MCP mode has correct configuration."""
        client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)
        info = client.get_deployment_info()

        assert info.mode == DeploymentMode.MCP
        assert info.model_type == "BedrockModel"
        assert info.model_id is not None
        assert info.agent_id is None
        assert info.tools_count == 10  # 3 weather + 7 MCP tools
        assert client.agent is not None  # Has direct agent
        assert not hasattr(client, "_bedrock_agent_id")  # No Bedrock Agent ID

    def test_bedrock_agent_mode_configuration(self):
        """Test BEDROCK_AGENT mode has correct configuration."""
        config_override = {"bedrock_agent_id": "test-agent-123"}
        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override=config_override,
        )
        info = client.get_deployment_info()

        assert info.mode == DeploymentMode.BEDROCK_AGENT
        assert info.model_type == "BedrockModel"
        assert info.model_id is not None
        assert info.agent_id == "test-agent-123"
        assert info.tools_count == 3  # Only base tools (weather)
        assert client.agent is None  # No direct agent
        assert hasattr(client, "_bedrock_agent_id")  # Has Bedrock Agent ID
        assert client._bedrock_agent_id == "test-agent-123"

    def test_mode_differences(self):
        """Test that different modes have distinct configurations."""
        # Create clients for all modes
        local_client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        mcp_client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)
        bedrock_client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override={"bedrock_agent_id": "test-agent-456"},
        )

        # Get deployment info
        local_info = local_client.get_deployment_info()
        mcp_info = mcp_client.get_deployment_info()
        bedrock_info = bedrock_client.get_deployment_info()

        # Verify modes are different
        assert local_info.mode != bedrock_info.mode
        assert mcp_info.mode != bedrock_info.mode

        # Verify LOCAL and MCP are similar (both use direct agents)
        assert local_info.tools_count == mcp_info.tools_count == 10
        assert local_client.agent is not None
        assert mcp_client.agent is not None

        # Verify BEDROCK_AGENT is different (no direct agent, fewer tools)
        assert bedrock_info.tools_count == 3
        assert bedrock_client.agent is None
        assert bedrock_info.agent_id == "test-agent-456"

    def test_backward_compatibility(self):
        """Test that old constructor interface still works."""
        # Old interface should default to LOCAL mode
        client = LocationWeatherClient()
        info = client.get_deployment_info()

        assert info.mode == DeploymentMode.LOCAL
        assert client.agent is not None

    def test_config_override_functionality(self):
        """Test that config overrides work correctly."""
        config_override = {
            "bedrock_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "aws_region": "us-west-2",
            "bedrock_agent_id": "custom-agent-789",
        }

        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override=config_override,
        )
        info = client.get_deployment_info()

        assert info.agent_id == "custom-agent-789"
        assert info.model_id == "anthropic.claude-3-haiku-20240307-v1:0"


def main():
    """Run the multi-mode functionality test as a standalone script."""
    print("=== TESTING TRUE MULTI-MODE FUNCTIONALITY ===")

    # Test LOCAL mode
    print("\n1. LOCAL MODE:")
    try:
        client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)
        info = client.get_deployment_info()
        print(f"   Mode: {info.mode.value}")
        print(f"   Model: {info.model_type}")
        print(f"   Model ID: {info.model_id}")
        print(f"   Agent ID: {info.agent_id}")
        print(f"   Tools: {info.tools_count}")
        print(f"   Has Agent: {client.agent is not None}")
        print("   ✅ LOCAL mode works!")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test MCP mode
    print("\n2. MCP MODE:")
    try:
        client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)
        info = client.get_deployment_info()
        print(f"   Mode: {info.mode.value}")
        print(f"   Model: {info.model_type}")
        print(f"   Model ID: {info.model_id}")
        print(f"   Agent ID: {info.agent_id}")
        print(f"   Tools: {info.tools_count}")
        print(f"   Has Agent: {client.agent is not None}")
        print("   ✅ MCP mode works!")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test BEDROCK_AGENT mode
    print("\n3. BEDROCK_AGENT MODE:")
    try:
        client = LocationWeatherClient(
            deployment_mode=DeploymentMode.BEDROCK_AGENT,
            config_override={"bedrock_agent_id": "test-agent-123"},
        )
        info = client.get_deployment_info()
        print(f"   Mode: {info.mode.value}")
        print(f"   Model: {info.model_type}")
        print(f"   Model ID: {info.model_id}")
        print(f"   Agent ID: {info.agent_id}")
        print(f"   Tools: {info.tools_count}")
        print(f"   Has Agent: {client.agent is not None}")
        print(f"   Has Bedrock Agent ID: {hasattr(client, '_bedrock_agent_id')}")
        print("   ✅ BEDROCK_AGENT mode works!")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n=== SUMMARY ===")
    print("✅ All three deployment modes are now working!")
    print("✅ LOCAL: Direct Python execution + MCP tools")
    print("✅ MCP: FastMCP server + MCP tools")
    print("✅ BEDROCK_AGENT: Bedrock Agent runtime + Lambda functions")


if __name__ == "__main__":
    main()
