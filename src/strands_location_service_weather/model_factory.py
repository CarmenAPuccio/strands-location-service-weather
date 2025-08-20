"""
Model factory for creating Strands model instances based on deployment configuration.
"""

import logging

from strands.models import BedrockModel

from .config import DeploymentConfig, DeploymentMode

# Get logger for this module
logger = logging.getLogger(__name__)


class ModelCreationError(Exception):
    """Exception raised when model creation fails."""

    pass


class ModelFactory:
    """Factory class for creating Strands BedrockModel instances based on deployment configuration."""

    @staticmethod
    def create_model(config: DeploymentConfig):
        """Create appropriate model based on deployment mode.

        Args:
            config: Deployment configuration containing mode and model parameters

        Returns:
            Configured model instance (BedrockModel for LOCAL/MCP, AgentRuntimeModel for BEDROCK_AGENT)

        Raises:
            ModelCreationError: If model creation fails
            ValueError: If configuration is invalid
        """
        logger.info(f"Creating model for deployment mode: {config.mode.value}")

        try:
            # Validate configuration first
            ModelFactory.validate_model_config(config)

            if config.mode == DeploymentMode.BEDROCK_AGENT:
                # For BEDROCK_AGENT mode, we use BedrockModel but with agent runtime invocation
                # The difference is in tool execution (Lambda functions vs Python functions)
                return ModelFactory._create_bedrock_agent_runtime_model(config)
            else:
                # LOCAL and MCP modes use standard BedrockModel
                return ModelFactory._create_bedrock_model(config)

        except Exception as e:
            error_msg = f"Failed to create model for mode {config.mode.value}: {str(e)}"
            logger.error(error_msg)
            raise ModelCreationError(error_msg) from e

    @staticmethod
    def _create_bedrock_model(config: DeploymentConfig) -> BedrockModel:
        """Create BedrockModel for all deployment modes.

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
    def _create_bedrock_agent_runtime_model(config: DeploymentConfig) -> BedrockModel:
        """Create BedrockModel configured for Bedrock Agent runtime invocation.

        For BEDROCK_AGENT mode, we still use BedrockModel but the tools are executed
        as Lambda functions by the Bedrock Agent runtime, not as Python functions.

        Args:
            config: Deployment configuration with bedrock_agent_id

        Returns:
            Configured BedrockModel instance for agent runtime

        Raises:
            ModelCreationError: If model creation fails
            ValueError: If bedrock_agent_id is not provided
        """
        if not config.bedrock_agent_id:
            raise ValueError("bedrock_agent_id is required for BEDROCK_AGENT mode")

        logger.info(
            f"Creating BedrockModel for Bedrock Agent runtime with agent_id={config.bedrock_agent_id}"
        )

        try:
            # For BEDROCK_AGENT mode, we create a BedrockModel but store the agent_id
            # The actual agent invocation will be handled by the LocationWeatherClient
            model_params = {
                "model_id": config.bedrock_model_id,
                "region_name": config.aws_region,
            }

            # Add timeout configuration if specified
            if hasattr(config, "timeout") and config.timeout:
                model_params["timeout"] = config.timeout

            logger.info(f"BedrockModel parameters for agent runtime: {model_params}")
            model = BedrockModel(**model_params)

            # Store the agent_id as a custom attribute for later use
            model._bedrock_agent_id = config.bedrock_agent_id
            model._deployment_mode = DeploymentMode.BEDROCK_AGENT

            logger.info(
                f"BedrockModel created for Bedrock Agent runtime: {config.bedrock_agent_id}"
            )
            return model

        except Exception as e:
            error_msg = (
                f"Failed to create BedrockModel for Bedrock Agent runtime: {str(e)}"
            )
            logger.error(error_msg)
            raise ModelCreationError(error_msg) from e

    @staticmethod
    def validate_model_config(config: DeploymentConfig) -> bool:
        """Validate model configuration for the specified deployment mode.

        This follows AWS Bedrock Agent configuration best practices.

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
        if config.mode == DeploymentMode.BEDROCK_AGENT:
            if not config.bedrock_agent_id:
                raise ValueError("bedrock_agent_id is required for BEDROCK_AGENT mode")

            # Validate Bedrock agent ID format (should be alphanumeric with possible hyphens)
            if not config.bedrock_agent_id.replace("-", "").isalnum():
                raise ValueError(
                    f"Invalid Bedrock agent ID format: {config.bedrock_agent_id}"
                )

            # Check for additional Bedrock agent configuration
            from .config import config as app_config

            if hasattr(app_config, "bedrock_agent"):
                bedrock_agent_config = app_config.bedrock_agent

                # Validate agent alias ID if present
                if (
                    bedrock_agent_config.agent_alias_id
                    and not bedrock_agent_config.agent_alias_id.replace("-", "")
                    .replace("_", "")
                    .isalnum()
                ):
                    raise ValueError(
                        f"Invalid Bedrock agent alias ID format: {bedrock_agent_config.agent_alias_id}"
                    )

                logger.info(
                    f"Bedrock agent configuration validated: alias_id={bedrock_agent_config.agent_alias_id}, trace_enabled={bedrock_agent_config.enable_trace}"
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
    def health_check(model) -> bool:
        """Perform health check on the created model.

        This follows AWS best practices for model validation and readiness checks.

        Args:
            model: Model instance to check (BedrockModel)

        Returns:
            True if model is healthy, False otherwise
        """
        logger.info(f"Performing health check for model type: {type(model).__name__}")

        try:
            if isinstance(model, BedrockModel):
                # Verify BedrockModel has required attributes
                required_attrs = ["model_id", "region_name"]
                for attr in required_attrs:
                    if not hasattr(model, attr):
                        logger.warning(
                            f"BedrockModel missing required attribute: {attr}"
                        )
                        return False

                logger.info(
                    f"BedrockModel health check passed for model_id: {model.model_id}"
                )
                return True

            else:
                logger.warning(f"Unknown model type: {type(model).__name__}")
                return False

        except Exception as e:
            logger.error(f"Model health check failed with exception: {str(e)}")
            return False
