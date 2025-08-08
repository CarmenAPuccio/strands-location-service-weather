"""
AWS CDK Stack for AgentCore Weather Tools Lambda Functions.

This module provides CDK infrastructure definitions for deploying weather and alerts
tools as Lambda functions for use with Amazon Bedrock AgentCore, following AWS CDK
best practices for Python project structure.
"""

from aws_cdk import (
    Stack,
)
from cdk_lib.bedrock_construct import BedrockAgentConstruct
from cdk_lib.lambda_construct import WeatherLambdaConstruct
from constructs import Construct


class LocationWeatherAgentCoreStack(Stack):
    """CDK Stack for AgentCore weather tools deployment."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        function_name_prefix: str = "agentcore-weather",
        weather_api_timeout: int = 10,
        otlp_endpoint: str = "",
        log_retention_days: int = 14,
        **kwargs,
    ) -> None:
        """
        Initialize the LocationWeatherAgentCoreStack.

        Args:
            scope: CDK scope
            construct_id: Stack construct ID
            function_name_prefix: Prefix for Lambda function names
            weather_api_timeout: Timeout for Weather API requests in seconds
            otlp_endpoint: OpenTelemetry OTLP endpoint URL (optional)
            log_retention_days: CloudWatch log retention in days
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.function_name_prefix = function_name_prefix
        self.weather_api_timeout = weather_api_timeout
        self.otlp_endpoint = otlp_endpoint
        self.log_retention_days = log_retention_days

        # Create Lambda functions using construct
        self.lambda_construct = WeatherLambdaConstruct(
            self,
            "WeatherLambdas",
            function_name_prefix=function_name_prefix,
            weather_api_timeout=weather_api_timeout,
            otlp_endpoint=otlp_endpoint,
            log_retention_days=log_retention_days,
        )

        # Create Bedrock agent using construct
        self.bedrock_construct = BedrockAgentConstruct(
            self,
            "BedrockAgent",
            weather_function=self.lambda_construct.weather_function,
            alerts_function=self.lambda_construct.alerts_function,
        )

    def get_outputs(self) -> dict[str, str]:
        """Get stack outputs for reference."""
        return {
            "weather_function_arn": self.lambda_construct.weather_function.function_arn,
            "alerts_function_arn": self.lambda_construct.alerts_function.function_arn,
            "agent_id": self.bedrock_construct.agent.attr_agent_id,
            "guardrail_id": self.bedrock_construct.guardrail.attr_guardrail_id,
            "execution_role_arn": self.lambda_construct.execution_role.role_arn,
        }
