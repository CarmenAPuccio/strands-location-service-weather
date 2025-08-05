"""
Model factory for creating appropriate Strands models based on deployment configuration.
"""

import logging
from typing import TYPE_CHECKING, Union

from strands.models import BedrockModel

from .config import DeploymentConfig, DeploymentMode

if TYPE_CHECKING:
    # Import AgentCoreModel only for type checking to avoid runtime import errors
    try:
        from strands.models import AgentCoreModel
    except ImportError:
        # Define a placeholder type if AgentCoreModel is not available
        AgentCoreModel = object

# Get logger for this module
logger = logging.getLogger(__name__)


class ModelCreationError(Exception):
    """Exception raised when model creation fails."""

    pass


class ModelFactory:
    """Factory class for creating Strands models based on deployment configuration."""

    @staticmethod
    def create_model(config: DeploymentConfig) -> Union[BedrockModel, "AgentCoreModel"]:
        """Create appropriate Strands model based on deployment mode.

        Args:
            config: Deployment configuration containing mode and model parameters

        Returns:
            BedrockModel for LOCAL/MCP modes, AgentCoreModel for AGENTCORE mode

        Raises:
            ModelCreationError: If model creation fails
            ValueError: If configuration is invalid
        """
        logger.info(f"Creating model for deployment mode: {config.mode.value}")

        try:
            if config.mode == DeploymentMode.AGENTCORE:
                return ModelFactory._create_agentcore_model(config)
            else:
                return ModelFactory._create_bedrock_model(config)

        except Exception as e:
            error_msg = f"Failed to create model for mode {config.mode.value}: {str(e)}"
            logger.error(error_msg)
            raise ModelCreationError(error_msg) from e

    @staticmethod
    def _create_bedrock_model(config: DeploymentConfig) -> BedrockModel:
        """Create BedrockModel for LOCAL and MCP deployment modes.

        Args:
            config: Deployment configuration

        Returns:
            Configured BedrockModel instance

        Raises:
            ModelCreationError: If BedrockModel creation fails
        """
        logger.info(
            f"Creating BedrockModel with model_id={config.bedrock_model_id}, region={config.aws_region}"
        )

        try:
            # Build model parameters following Strands SDK best practices
            model_params = {
                "model_id": config.bedrock_model_id,
                "region_name": config.aws_region,
            }

            # Add optional configuration parameters if available
            from .config import config as app_config

            # Add guardrail configuration if available (Bedrock models can use guardrails too)
            if hasattr(app_config, "guardrail") and app_config.guardrail.guardrail_id:
                guardrail_config = app_config.guardrail
                model_params["guardrail_id"] = guardrail_config.guardrail_id
                model_params["guardrail_version"] = guardrail_config.guardrail_version
                logger.info(
                    f"Adding guardrail configuration: {guardrail_config.guardrail_id}"
                )

            # Add timeout configuration if specified
            if hasattr(config, "timeout") and config.timeout:
                model_params["timeout"] = config.timeout

            logger.info(f"BedrockModel parameters: {model_params}")
            model = BedrockModel(**model_params)

            logger.info("BedrockModel created successfully")
            return model

        except Exception as e:
            error_msg = f"Failed to create BedrockModel: {str(e)}"
            logger.error(error_msg)
            raise ModelCreationError(error_msg) from e

    @staticmethod
    def _create_agentcore_model(config: DeploymentConfig) -> "AgentCoreModel":
        """Create AgentCoreModel for AGENTCORE deployment mode.

        Args:
            config: Deployment configuration

        Returns:
            Configured AgentCoreModel instance

        Raises:
            ModelCreationError: If AgentCoreModel creation fails
            ImportError: If AgentCoreModel is not available
        """
        if not config.agentcore_agent_id:
            raise ValueError("agentcore_agent_id is required for AGENTCORE mode")

        logger.info(
            f"Creating AgentCoreModel with agent_id={config.agentcore_agent_id}, region={config.aws_region}"
        )

        try:
            # Import AgentCoreModel only when needed to avoid import errors
            # if it's not available in the current Strands version
            from strands.models import AgentCoreModel

            # AgentCore models follow AWS Bedrock AgentCore best practices
            # Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
            model_params = {
                "agent_id": config.agentcore_agent_id,
                "region_name": config.aws_region,
            }

            # Add optional AgentCore-specific parameters following AWS best practices
            from .config import config as app_config

            if hasattr(app_config, "agentcore"):
                agentcore_config = app_config.agentcore

                # Agent alias ID is required for AgentCore invocation
                # Default to TSTALIASID for testing, but should be configured for production
                if agentcore_config.agent_alias_id:
                    model_params["agent_alias_id"] = agentcore_config.agent_alias_id

                # Session ID enables conversation continuity across invocations
                # Should be unique per user session for proper context management
                if agentcore_config.session_id:
                    model_params["session_id"] = agentcore_config.session_id

                # Enable tracing for AgentCore monitoring and debugging
                # Recommended for production environments
                if hasattr(agentcore_config, "enable_trace"):
                    model_params["enable_trace"] = agentcore_config.enable_trace

            # Guardrails can be applied at the agent level for content filtering
            # This provides additional safety controls beyond model-level guardrails
            if hasattr(app_config, "guardrail") and app_config.guardrail.guardrail_id:
                guardrail_config = app_config.guardrail
                model_params["guardrail_id"] = guardrail_config.guardrail_id
                model_params["guardrail_version"] = guardrail_config.guardrail_version
                logger.info(
                    f"Adding AgentCore guardrail configuration: {guardrail_config.guardrail_id}"
                )

            # Add timeout configuration for AgentCore invocations
            if hasattr(config, "timeout") and config.timeout:
                model_params["timeout"] = config.timeout

            logger.info(f"AgentCoreModel parameters: {model_params}")
            model = AgentCoreModel(**model_params)

            logger.info("AgentCoreModel created successfully")
            return model

        except ImportError as e:
            error_msg = "AgentCoreModel is not available in the current Strands version. Please ensure you have the latest strands-agents package with AgentCore support."
            logger.error(error_msg)
            raise ModelCreationError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to create AgentCoreModel: {str(e)}"
            logger.error(error_msg)
            raise ModelCreationError(error_msg) from e

    @staticmethod
    def validate_model_config(config: DeploymentConfig) -> bool:
        """Validate model configuration for the specified deployment mode.

        This follows AWS Bedrock and AgentCore configuration best practices.

        Args:
            config: Deployment configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        logger.info(f"Validating model configuration for mode: {config.mode.value}")

        # Validate common configuration
        if not config.bedrock_model_id:
            raise ValueError("bedrock_model_id is required")

        if not config.aws_region:
            raise ValueError("aws_region is required")

        # Validate AWS region format (basic check)
        if not config.aws_region.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid AWS region format: {config.aws_region}")

        # Validate mode-specific configuration
        if config.mode == DeploymentMode.AGENTCORE:
            if not config.agentcore_agent_id:
                raise ValueError("agentcore_agent_id is required for AGENTCORE mode")

            # Validate AgentCore agent ID format (should be alphanumeric with possible hyphens)
            if not config.agentcore_agent_id.replace("-", "").isalnum():
                raise ValueError(
                    f"Invalid AgentCore agent ID format: {config.agentcore_agent_id}"
                )

            # Check for additional AgentCore configuration
            from .config import config as app_config

            if hasattr(app_config, "agentcore"):
                agentcore_config = app_config.agentcore

                # Validate agent alias ID if present
                if (
                    agentcore_config.agent_alias_id
                    and not agentcore_config.agent_alias_id.replace("-", "")
                    .replace("_", "")
                    .isalnum()
                ):
                    raise ValueError(
                        f"Invalid AgentCore agent alias ID format: {agentcore_config.agent_alias_id}"
                    )

                logger.info(
                    f"AgentCore configuration validated: alias_id={agentcore_config.agent_alias_id}, trace_enabled={agentcore_config.enable_trace}"
                )

        # Validate Bedrock model ID format for both modes
        if config.mode in [DeploymentMode.LOCAL, DeploymentMode.MCP]:
            # Basic validation for Bedrock model ID format
            if not config.bedrock_model_id or "." not in config.bedrock_model_id:
                raise ValueError(
                    f"Invalid Bedrock model ID format: {config.bedrock_model_id}"
                )

        # Validate guardrail configuration if present
        from .config import config as app_config

        if hasattr(app_config, "guardrail") and app_config.guardrail.guardrail_id:
            guardrail_config = app_config.guardrail
            if not guardrail_config.guardrail_id.replace("-", "").isalnum():
                raise ValueError(
                    f"Invalid guardrail ID format: {guardrail_config.guardrail_id}"
                )

            logger.info(
                f"Guardrail configuration validated: {guardrail_config.guardrail_id}"
            )

        logger.info("Model configuration is valid")
        return True

    @staticmethod
    def health_check(model: Union[BedrockModel, "AgentCoreModel"]) -> bool:
        """Perform health check on the created model.

        This follows AWS best practices for model validation and readiness checks.

        Args:
            model: Model instance to check

        Returns:
            True if model is healthy, False otherwise
        """
        logger.info("Performing model health check")

        try:
            # Check basic model attributes
            if hasattr(model, "model_id"):
                # BedrockModel health check
                logger.info(
                    f"Checking BedrockModel health for model_id: {model.model_id}"
                )

                # Verify model has required attributes for Bedrock
                required_attrs = ["model_id", "region_name"]
                for attr in required_attrs:
                    if not hasattr(model, attr):
                        logger.warning(
                            f"BedrockModel missing required attribute: {attr}"
                        )
                        return False

                logger.info("BedrockModel health check passed")
                return True

            elif hasattr(model, "agent_id"):
                # AgentCoreModel health check
                logger.info(
                    f"Checking AgentCoreModel health for agent_id: {model.agent_id}"
                )

                # Verify model has required attributes for AgentCore
                required_attrs = ["agent_id", "region_name"]
                for attr in required_attrs:
                    if not hasattr(model, attr):
                        logger.warning(
                            f"AgentCoreModel missing required attribute: {attr}"
                        )
                        return False

                # Check AgentCore-specific attributes
                if hasattr(model, "agent_alias_id"):
                    logger.info(f"AgentCore alias ID: {model.agent_alias_id}")

                if hasattr(model, "session_id") and model.session_id:
                    logger.info(f"AgentCore session ID: {model.session_id}")

                logger.info("AgentCoreModel health check passed")
                return True
            else:
                logger.warning(
                    "Model health check failed: missing required model_id or agent_id"
                )
                return False

        except Exception as e:
            logger.error(f"Model health check failed with exception: {str(e)}")
            return False
