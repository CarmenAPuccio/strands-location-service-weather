"""
Essential tests for the ModelFactory class.

This file contains only the core functionality tests that are critical
for ensuring the ModelFactory works correctly across deployment modes.
"""

import pytest

from src.strands_location_service_weather.config import DeploymentConfig, DeploymentMode
from src.strands_location_service_weather.model_factory import (
    ModelFactory,
)


class TestModelFactoryEssential:
    """Test essential ModelFactory functionality."""

    def test_create_model_for_local_mode(self):
        """Test creating model for LOCAL mode."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )

        model = ModelFactory.create_model(config)
        assert model is not None

    def test_create_model_for_mcp_mode(self):
        """Test creating model for MCP mode."""
        config = DeploymentConfig(
            mode=DeploymentMode.MCP,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )

        model = ModelFactory.create_model(config)
        assert model is not None

    def test_create_model_for_bedrock_agent_mode(self):
        """Test creating model for BEDROCK_AGENT mode."""
        config = DeploymentConfig(
            mode=DeploymentMode.BEDROCK_AGENT,
            bedrock_agent_id="test-agent-123",
            aws_region="us-east-1",
        )

        model = ModelFactory.create_model(config)
        assert model is not None
        # Verify the agent ID is stored
        assert hasattr(model, "_bedrock_agent_id")
        assert model._bedrock_agent_id == "test-agent-123"

    def test_bedrock_agent_mode_requires_agent_id(self):
        """Test that BEDROCK_AGENT mode requires agent_id."""
        with pytest.raises(ValueError, match="bedrock_agent_id is required"):
            DeploymentConfig(
                mode=DeploymentMode.BEDROCK_AGENT,
                bedrock_agent_id=None,  # Missing agent ID
                aws_region="us-east-1",
            )

    def test_validate_config_missing_region(self):
        """Test validation fails when AWS region is missing."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="",  # Empty region
        )

        with pytest.raises(ValueError, match="aws_region is required"):
            ModelFactory.validate_model_config(config)

    def test_validate_config_missing_model_id(self):
        """Test validation fails when model ID is missing."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="",  # Empty model ID
            aws_region="us-east-1",
        )

        with pytest.raises(ValueError, match="bedrock_model_id is required"):
            ModelFactory.validate_model_config(config)


class TestModelFactoryValidation:
    """Test ModelFactory validation functionality."""

    def test_validate_valid_local_config(self):
        """Test validation passes for valid LOCAL config."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )

        # Should not raise any exception
        ModelFactory.validate_model_config(config)

    def test_validate_valid_bedrock_agent_config(self):
        """Test validation passes for valid BEDROCK_AGENT config."""
        config = DeploymentConfig(
            mode=DeploymentMode.BEDROCK_AGENT,
            bedrock_agent_id="test-agent-123",
            aws_region="us-east-1",
        )

        # Should not raise any exception
        ModelFactory.validate_model_config(config)
