"""
Lambda construct for weather tools using Lambda layers.

This module provides a reusable CDK construct for creating Lambda functions
with Lambda layers for dependencies and shared code, following AWS best practices.
"""

import aws_cdk
from aws_cdk import (
    Duration,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_logs as logs,
)
from constructs import Construct


class WeatherLambdaConstruct(Construct):
    """Construct for weather and alerts Lambda functions."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        function_name_prefix: str = "agentcore-weather",
        weather_api_timeout: int = 10,
        otlp_endpoint: str = "",
        log_retention_days: int = 14,
    ) -> None:
        """
        Initialize the WeatherLambdaConstruct.

        Args:
            scope: CDK scope
            construct_id: Construct ID
            function_name_prefix: Prefix for Lambda function names
            weather_api_timeout: Timeout for Weather API requests in seconds
            otlp_endpoint: OpenTelemetry OTLP endpoint URL (optional)
            log_retention_days: CloudWatch log retention in days
        """
        super().__init__(scope, construct_id)

        self.function_name_prefix = function_name_prefix
        self.weather_api_timeout = weather_api_timeout
        self.otlp_endpoint = otlp_endpoint
        self.log_retention_days = log_retention_days

        # Create IAM execution role for Lambda functions
        self.execution_role = self._create_lambda_execution_role()

        # Create Lambda layers
        self.dependencies_layer = self._create_dependencies_layer()
        self.shared_code_layer = self._create_shared_code_layer()

        # Create Lambda functions
        self.weather_function = self._create_weather_lambda()
        self.alerts_function = self._create_alerts_lambda()

        # Create CloudWatch log groups
        self._create_log_groups()

    def _create_lambda_execution_role(self) -> iam.Role:
        """Create IAM role for Lambda function execution."""
        role = iam.Role(
            self,
            "LambdaExecutionRole",
            role_name=f"{self.function_name_prefix}-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Add tracing permissions
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                resources=["*"],
            )
        )

        return role

    def _create_dependencies_layer(self) -> lambda_.LayerVersion:
        """Create Lambda layer for Python dependencies."""
        layer = lambda_.LayerVersion(
            self,
            "DependenciesLayer",
            code=lambda_.Code.from_asset("layers/dependencies"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Python dependencies for weather Lambda functions",
        )
        return layer

    def _create_shared_code_layer(self) -> lambda_.LayerVersion:
        """Create Lambda layer for shared code."""
        layer = lambda_.LayerVersion(
            self,
            "SharedCodeLayer",
            code=lambda_.Code.from_asset("layers/shared-code"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared code for weather Lambda functions",
        )
        return layer

    def _create_weather_lambda(self) -> lambda_.Function:
        """Create Lambda function for weather tool."""
        function = lambda_.Function(
            self,
            "WeatherFunction",
            function_name=f"{self.function_name_prefix}-get-weather",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda_functions/get_weather"),
            layers=[self.dependencies_layer, self.shared_code_layer],
            role=self.execution_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=self._get_weather_environment_vars(),
            tracing=lambda_.Tracing.ACTIVE,
            description="Weather tool for AgentCore - v2.0 with fixed error handling",
        )

        # Add permission for Bedrock to invoke the function
        function.add_permission(
            "BedrockInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        return function

    def _create_alerts_lambda(self) -> lambda_.Function:
        """Create Lambda function for alerts tool."""
        function = lambda_.Function(
            self,
            "AlertsFunction",
            function_name=f"{self.function_name_prefix}-get-alerts",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda_functions/get_alerts"),
            layers=[self.dependencies_layer, self.shared_code_layer],
            role=self.execution_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=self._get_alerts_environment_vars(),
            tracing=lambda_.Tracing.ACTIVE,
            description="Weather alerts tool for AgentCore - v2.0 with fixed error handling",
        )

        # Add permission for Bedrock to invoke the function
        function.add_permission(
            "BedrockInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        return function

    def _get_weather_environment_vars(self) -> dict:
        """Get environment variables for weather Lambda function."""
        env_vars = {
            "WEATHER_API_BASE_URL": "https://api.weather.gov",
            "WEATHER_API_TIMEOUT": str(self.weather_api_timeout),
            "USER_AGENT_WEATHER": "AgentCoreWeatherService/1.0",
            "ACCEPT_HEADER": "application/geo+json",
            "FASTMCP_LOG_LEVEL": "ERROR",
            "LAMBDA_VERSION": "2.0",
        }

        if self.otlp_endpoint:
            env_vars["OTEL_EXPORTER_OTLP_ENDPOINT"] = self.otlp_endpoint

        return env_vars

    def _get_alerts_environment_vars(self) -> dict:
        """Get environment variables for alerts Lambda function."""
        env_vars = {
            "WEATHER_API_BASE_URL": "https://api.weather.gov",
            "WEATHER_API_TIMEOUT": str(self.weather_api_timeout),
            "USER_AGENT_ALERTS": "AgentCoreAlertsService/1.0",
            "ACCEPT_HEADER": "application/geo+json",
            "FASTMCP_LOG_LEVEL": "ERROR",
            "LAMBDA_VERSION": "2.0",
        }

        if self.otlp_endpoint:
            env_vars["OTEL_EXPORTER_OTLP_ENDPOINT"] = self.otlp_endpoint

        return env_vars

    def _create_log_groups(self) -> None:
        """Create CloudWatch log groups with retention."""
        # Determine retention enum value
        retention_mapping = {
            1: logs.RetentionDays.ONE_DAY,
            3: logs.RetentionDays.THREE_DAYS,
            5: logs.RetentionDays.FIVE_DAYS,
            7: logs.RetentionDays.ONE_WEEK,
            14: logs.RetentionDays.TWO_WEEKS,
            30: logs.RetentionDays.ONE_MONTH,
            60: logs.RetentionDays.TWO_MONTHS,
            90: logs.RetentionDays.THREE_MONTHS,
            120: logs.RetentionDays.FOUR_MONTHS,
            150: logs.RetentionDays.FIVE_MONTHS,
            180: logs.RetentionDays.SIX_MONTHS,
            365: logs.RetentionDays.ONE_YEAR,
            400: logs.RetentionDays.THIRTEEN_MONTHS,
            545: logs.RetentionDays.EIGHTEEN_MONTHS,
            731: logs.RetentionDays.TWO_YEARS,
            1827: logs.RetentionDays.FIVE_YEARS,
            3653: logs.RetentionDays.TEN_YEARS,
        }

        retention_mapping.get(self.log_retention_days, logs.RetentionDays.TWO_WEEKS)

        logs.LogGroup(
            self,
            "WeatherLogGroup",
            log_group_name=f"/aws/lambda/{self.weather_function.function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )

        logs.LogGroup(
            self,
            "AlertsLogGroup",
            log_group_name=f"/aws/lambda/{self.alerts_function.function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )
