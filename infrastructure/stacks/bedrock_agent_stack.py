"""
AWS CDK Stack for Bedrock Agent Weather Tools Lambda Functions.

This module provides CDK infrastructure definitions for deploying weather and alerts
tools as Lambda functions for use with Amazon Bedrock Agents, following AWS CDK
best practices for Python project structure.
"""

from aws_cdk import (
    CfnOutput,
    Stack,
)
from cdk_lib.bedrock_construct import BedrockAgentConstruct
from cdk_lib.lambda_construct import WeatherLambdaConstruct
from cdk_lib.location_construct import LocationServiceConstruct
from constructs import Construct


class LocationWeatherBedrockAgentStack(Stack):
    """CDK Stack for Bedrock Agent weather tools deployment."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        function_name_prefix: str = "bedrock-agent-weather",
        weather_api_timeout: int = 10,
        otlp_endpoint: str = "",
        log_retention_days: int = 14,
        **kwargs,
    ) -> None:
        """
        Initialize the LocationWeatherBedrockAgentStack.

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

        # Create Amazon Location Service resources
        self.location_construct = LocationServiceConstruct(
            self,
            "LocationService",
            resource_name_prefix="LocationWeather",
        )

        # Create Lambda functions using construct
        self.lambda_construct = WeatherLambdaConstruct(
            self,
            "WeatherLambdas",
            function_name_prefix=function_name_prefix,
            weather_api_timeout=weather_api_timeout,
            otlp_endpoint=otlp_endpoint,
            log_retention_days=log_retention_days,
            place_index_name=self.location_construct.get_place_index_name(),
            route_calculator_name=self.location_construct.get_route_calculator_name(),
        )

        # Create Bedrock agent using construct
        self.bedrock_construct = BedrockAgentConstruct(
            self,
            "BedrockAgent",
            weather_function=self.lambda_construct.weather_function,
            alerts_function=self.lambda_construct.alerts_function,
            search_places_function=self.lambda_construct.search_places_function,
            calculate_route_function=self.lambda_construct.calculate_route_function,
        )

        # Create CloudFormation outputs
        CfnOutput(
            self,
            "AgentId",
            value=self.bedrock_construct.agent.attr_agent_id,
            description="Bedrock Agent ID for location weather service",
        )

        CfnOutput(
            self,
            "GuardrailId",
            value=self.bedrock_construct.guardrail.attr_guardrail_id,
            description="Bedrock Guardrail ID for content filtering",
        )

        CfnOutput(
            self,
            "PlaceIndexName",
            value=self.location_construct.get_place_index_name(),
            description="Amazon Location Service Place Index name",
        )

        CfnOutput(
            self,
            "RouteCalculatorName",
            value=self.location_construct.get_route_calculator_name(),
            description="Amazon Location Service Route Calculator name",
        )

    def get_outputs(self) -> dict[str, str]:
        """Get stack outputs for reference."""
        return {
            "weather_function_arn": self.lambda_construct.weather_function.function_arn,
            "alerts_function_arn": self.lambda_construct.alerts_function.function_arn,
            "search_places_function_arn": self.lambda_construct.search_places_function.function_arn,
            "calculate_route_function_arn": self.lambda_construct.calculate_route_function.function_arn,
            "place_index_name": self.location_construct.get_place_index_name(),
            "route_calculator_name": self.location_construct.get_route_calculator_name(),
            "agent_id": self.bedrock_construct.agent.attr_agent_id,
            "guardrail_id": self.bedrock_construct.guardrail.attr_guardrail_id,
            "execution_role_arn": self.lambda_construct.execution_role.role_arn,
        }
