"""
Tests for the ModelFactory class.
"""

from unittest.mock import Mock, patch

import pytest

from src.strands_location_service_weather.config import DeploymentConfig, DeploymentMode
from src.strands_location_service_weather.model_factory import (
    ModelCreationError,
    ModelFactory,
)


class TestModelFactory:
    """Test the ModelFactory class."""

    def test_create_bedrock_model_for_local_mode(self):
        """Test creating BedrockModel for LOCAL deployment mode."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )

        with patch(
            "src.strands_location_service_weather.model_factory.BedrockModel"
        ) as mock_bedrock:
            mock_model = Mock()
            mock_bedrock.return_value = mock_model

            result = ModelFactory.create_model(config)

            # Check that BedrockModel was called with the expected parameters
            # The enhanced implementation includes additional parameters like timeout
            call_args = mock_bedrock.call_args
            assert call_args[1]["model_id"] == "anthropic.claude-3-sonnet-20240229-v1:0"
            assert call_args[1]["region_name"] == "us-east-1"
            # Timeout should be included from the config
            assert "timeout" in call_args[1]
            assert result == mock_model

    def test_create_bedrock_model_for_mcp_mode(self):
        """Test creating BedrockModel for MCP deployment mode."""
        config = DeploymentConfig(
            mode=DeploymentMode.MCP,
            bedrock_model_id="anthropic.claude-3-haiku-20240307-v1:0",
            aws_region="us-west-2",
        )

        with patch(
            "src.strands_location_service_weather.model_factory.BedrockModel"
        ) as mock_bedrock:
            mock_model = Mock()
            mock_bedrock.return_value = mock_model

            result = ModelFactory.create_model(config)

            # Check that BedrockModel was called with the expected parameters
            call_args = mock_bedrock.call_args
            assert call_args[1]["model_id"] == "anthropic.claude-3-haiku-20240307-v1:0"
            assert call_args[1]["region_name"] == "us-west-2"
            # Timeout should be included from the config
            assert "timeout" in call_args[1]
            assert result == mock_model

    def test_create_agentcore_model_for_agentcore_mode(self):
        """Test creating AgentCoreModel for AGENTCORE deployment mode."""
        config = DeploymentConfig(
            mode=DeploymentMode.AGENTCORE,
            agentcore_agent_id="test-agent-123",
            aws_region="eu-west-1",
        )

        # Mock the import inside the _create_agentcore_model method
        mock_agentcore_class = Mock()
        mock_model = Mock()
        mock_agentcore_class.return_value = mock_model

        with patch.dict(
            "sys.modules", {"strands.models": Mock(AgentCoreModel=mock_agentcore_class)}
        ):
            result = ModelFactory.create_model(config)

            # Check that AgentCoreModel was called with the expected parameters
            # The enhanced implementation includes additional AgentCore-specific parameters
            call_args = mock_agentcore_class.call_args
            assert call_args[1]["agent_id"] == "test-agent-123"
            assert call_args[1]["region_name"] == "eu-west-1"
            # Should include agent_alias_id from config
            assert "agent_alias_id" in call_args[1]
            assert result == mock_model

    def test_create_agentcore_model_without_agent_id_raises_error(self):
        """Test that creating AgentCoreModel without agent_id raises ValueError."""
        # Create config with LOCAL mode first, then modify to avoid validation
        config = DeploymentConfig(mode=DeploymentMode.LOCAL, aws_region="us-east-1")
        # Manually set the mode to AGENTCORE to bypass __post_init__ validation
        config.mode = DeploymentMode.AGENTCORE
        config.agentcore_agent_id = None

        with pytest.raises(ModelCreationError, match="agentcore_agent_id is required"):
            ModelFactory.create_model(config)

    def test_bedrock_model_creation_failure_raises_model_creation_error(self):
        """Test that BedrockModel creation failure raises ModelCreationError."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="invalid-model",
            aws_region="us-east-1",
        )

        with patch(
            "src.strands_location_service_weather.model_factory.BedrockModel"
        ) as mock_bedrock:
            mock_bedrock.side_effect = Exception("AWS credentials not found")

            with pytest.raises(
                ModelCreationError, match="Failed to create model for mode local"
            ):
                ModelFactory.create_model(config)

    def test_agentcore_model_creation_failure_raises_model_creation_error(self):
        """Test that AgentCoreModel creation failure raises ModelCreationError."""
        config = DeploymentConfig(
            mode=DeploymentMode.AGENTCORE,
            agentcore_agent_id="test-agent",
            aws_region="us-east-1",
        )

        # Mock the import inside the _create_agentcore_model method
        mock_agentcore_class = Mock()
        mock_agentcore_class.side_effect = Exception("Agent not found")

        with patch.dict(
            "sys.modules", {"strands.models": Mock(AgentCoreModel=mock_agentcore_class)}
        ):
            with pytest.raises(
                ModelCreationError, match="Failed to create model for mode agentcore"
            ):
                ModelFactory.create_model(config)

    def test_agentcore_model_import_error_raises_model_creation_error(self):
        """Test that AgentCoreModel import error raises ModelCreationError."""
        config = DeploymentConfig(
            mode=DeploymentMode.AGENTCORE,
            agentcore_agent_id="test-agent",
            aws_region="us-east-1",
        )

        # Mock the import to raise ImportError by patching the import statement
        with patch("builtins.__import__") as mock_import:

            def side_effect(name, *args, **kwargs):
                if name == "strands.models" and "AgentCoreModel" in str(args):
                    raise ImportError("No module named 'strands.models.AgentCoreModel'")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = side_effect

            with pytest.raises(
                ModelCreationError,
                match="AgentCoreModel is not available in the current Strands version",
            ):
                ModelFactory.create_model(config)


class TestModelConfigValidation:
    """Test model configuration validation."""

    def test_validate_valid_local_config(self):
        """Test validation of valid LOCAL mode configuration."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )

        result = ModelFactory.validate_model_config(config)
        assert result is True

    def test_validate_valid_mcp_config(self):
        """Test validation of valid MCP mode configuration."""
        config = DeploymentConfig(
            mode=DeploymentMode.MCP,
            bedrock_model_id="anthropic.claude-3-haiku-20240307-v1:0",
            aws_region="us-west-2",
        )

        result = ModelFactory.validate_model_config(config)
        assert result is True

    def test_validate_valid_agentcore_config(self):
        """Test validation of valid AGENTCORE mode configuration."""
        config = DeploymentConfig(
            mode=DeploymentMode.AGENTCORE,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            agentcore_agent_id="test-agent-123",
            aws_region="eu-west-1",
        )

        result = ModelFactory.validate_model_config(config)
        assert result is True

    def test_validate_config_missing_bedrock_model_id(self):
        """Test validation fails when bedrock_model_id is missing."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="",  # Empty model ID
            aws_region="us-east-1",
        )

        with pytest.raises(ValueError, match="bedrock_model_id is required"):
            ModelFactory.validate_model_config(config)

    def test_validate_config_missing_aws_region(self):
        """Test validation fails when aws_region is missing."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="",  # Empty region
        )

        with pytest.raises(ValueError, match="aws_region is required"):
            ModelFactory.validate_model_config(config)

    def test_validate_agentcore_config_missing_agent_id(self):
        """Test validation fails when AGENTCORE mode is missing agent_id."""
        # Create config with LOCAL mode first, then modify to avoid __post_init__ validation
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )
        # Manually set the mode to AGENTCORE to bypass __post_init__ validation
        config.mode = DeploymentMode.AGENTCORE
        config.agentcore_agent_id = None

        with pytest.raises(
            ValueError, match="agentcore_agent_id is required for AGENTCORE mode"
        ):
            ModelFactory.validate_model_config(config)


class TestModelHealthCheck:
    """Test model health check functionality."""

    def test_health_check_bedrock_model_with_model_id(self):
        """Test health check passes for BedrockModel with model_id attribute."""
        mock_model = Mock()
        mock_model.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

        result = ModelFactory.health_check(mock_model)
        assert result is True

    def test_health_check_agentcore_model_with_agent_id(self):
        """Test health check passes for AgentCoreModel with agent_id attribute."""
        mock_model = Mock()
        mock_model.agent_id = "test-agent-123"

        result = ModelFactory.health_check(mock_model)
        assert result is True

    def test_health_check_model_with_both_attributes(self):
        """Test health check passes for model with both model_id and agent_id."""
        mock_model = Mock()
        mock_model.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        mock_model.agent_id = "test-agent-123"

        result = ModelFactory.health_check(mock_model)
        assert result is True

    def test_health_check_model_without_required_attributes(self):
        """Test health check fails for model without required attributes."""
        mock_model = Mock()
        # Remove the default attributes that Mock creates
        del mock_model.model_id
        del mock_model.agent_id

        # Mock hasattr to return False for both attributes
        with patch("builtins.hasattr", return_value=False):
            result = ModelFactory.health_check(mock_model)
            assert result is False

    def test_health_check_with_exception(self):
        """Test health check handles exceptions gracefully."""
        mock_model = Mock()

        # Mock hasattr to raise an exception when called, but avoid affecting logging
        original_hasattr = hasattr

        def hasattr_side_effect(obj, name):
            # Only raise exception for our mock model, not for logging operations
            if obj is mock_model:
                raise Exception("Connection error")
            return original_hasattr(obj, name)

        with patch("builtins.hasattr", side_effect=hasattr_side_effect):
            result = ModelFactory.health_check(mock_model)
            assert result is False


class TestModelFactoryIntegration:
    """Integration tests for ModelFactory with different configurations."""

    def test_create_and_validate_local_model(self):
        """Test creating and validating a LOCAL mode model."""
        config = DeploymentConfig(
            mode=DeploymentMode.LOCAL,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            aws_region="us-east-1",
        )

        # First validate the configuration
        assert ModelFactory.validate_model_config(config) is True

        # Then create the model
        with patch(
            "src.strands_location_service_weather.model_factory.BedrockModel"
        ) as mock_bedrock:
            mock_model = Mock()
            mock_model.model_id = config.bedrock_model_id
            mock_bedrock.return_value = mock_model

            model = ModelFactory.create_model(config)

            # Verify model was created correctly
            call_args = mock_bedrock.call_args
            assert call_args[1]["model_id"] == config.bedrock_model_id
            assert call_args[1]["region_name"] == config.aws_region

            # Verify health check passes
            assert ModelFactory.health_check(model) is True

    def test_create_and_validate_agentcore_model(self):
        """Test creating and validating an AGENTCORE mode model."""
        config = DeploymentConfig(
            mode=DeploymentMode.AGENTCORE,
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            agentcore_agent_id="test-agent-456",
            aws_region="us-west-2",
        )

        # First validate the configuration
        assert ModelFactory.validate_model_config(config) is True

        # Then create the model
        mock_agentcore_class = Mock()
        mock_model = Mock()
        mock_model.agent_id = config.agentcore_agent_id
        mock_agentcore_class.return_value = mock_model

        with patch.dict(
            "sys.modules", {"strands.models": Mock(AgentCoreModel=mock_agentcore_class)}
        ):
            model = ModelFactory.create_model(config)

            # Verify model was created correctly
            call_args = mock_agentcore_class.call_args
            assert call_args[1]["agent_id"] == config.agentcore_agent_id
            assert call_args[1]["region_name"] == config.aws_region

            # Verify health check passes
            assert ModelFactory.health_check(model) is True

    def test_end_to_end_model_creation_workflow(self):
        """Test the complete workflow of validation, creation, and health check."""
        configs = [
            DeploymentConfig(
                mode=DeploymentMode.LOCAL,
                bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                aws_region="us-east-1",
            ),
            DeploymentConfig(
                mode=DeploymentMode.MCP,
                bedrock_model_id="anthropic.claude-3-haiku-20240307-v1:0",
                aws_region="us-west-2",
            ),
            DeploymentConfig(
                mode=DeploymentMode.AGENTCORE,
                bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                agentcore_agent_id="test-agent-789",
                aws_region="eu-west-1",
            ),
        ]

        for config in configs:
            # Step 1: Validate configuration
            assert ModelFactory.validate_model_config(config) is True

            # Step 2: Create model (with appropriate mocking)
            if config.mode == DeploymentMode.AGENTCORE:
                mock_model_class = Mock()
                mock_model = Mock()
                mock_model.agent_id = config.agentcore_agent_id
                mock_model_class.return_value = mock_model

                with patch.dict(
                    "sys.modules",
                    {"strands.models": Mock(AgentCoreModel=mock_model_class)},
                ):
                    model = ModelFactory.create_model(config)
                    assert model == mock_model

                    # Verify the model was called with expected parameters
                    call_args = mock_model_class.call_args
                    assert call_args[1]["agent_id"] == config.agentcore_agent_id
                    assert call_args[1]["region_name"] == config.aws_region
            else:
                with patch(
                    "src.strands_location_service_weather.model_factory.BedrockModel"
                ) as mock_model_class:
                    mock_model = Mock()
                    mock_model.model_id = config.bedrock_model_id
                    mock_model_class.return_value = mock_model

                    model = ModelFactory.create_model(config)
                    assert model == mock_model

                    # Verify the model was called with expected parameters
                    call_args = mock_model_class.call_args
                    assert call_args[1]["model_id"] == config.bedrock_model_id
                    assert call_args[1]["region_name"] == config.aws_region

            # Step 3: Health check
            assert ModelFactory.health_check(model) is True
