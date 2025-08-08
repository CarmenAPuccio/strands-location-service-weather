"""
Bedrock construct for AgentCore agent and guardrails.

This module provides a reusable CDK construct for creating Bedrock AgentCore
agents with guardrails following AWS CDK best practices.
"""

import json
from pathlib import Path

from aws_cdk import (
    Stack,
)
from aws_cdk import (
    aws_bedrock as bedrock,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from constructs import Construct


class BedrockAgentConstruct(Construct):
    """Construct for Bedrock AgentCore agent with guardrails."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        weather_function: lambda_.Function,
        alerts_function: lambda_.Function,
    ) -> None:
        """
        Initialize the BedrockAgentConstruct.

        Args:
            scope: CDK scope
            construct_id: Construct ID
            weather_function: Lambda function for weather tool
            alerts_function: Lambda function for alerts tool
        """
        super().__init__(scope, construct_id)

        self.weather_function = weather_function
        self.alerts_function = alerts_function

        # Get AWS account and region for ARN construction
        self.account = Stack.of(self).account
        self.region = Stack.of(self).region

        # Create Bedrock Guardrail for security
        self.guardrail = self._create_bedrock_guardrail()

        # Create AgentCore agent with action groups
        self.agent = self._create_agentcore_agent()

    def _create_bedrock_guardrail(self) -> bedrock.CfnGuardrail:
        """Create Bedrock Guardrail for content filtering and security."""
        guardrail = bedrock.CfnGuardrail(
            self,
            "LocationWeatherGuardrail",
            name="location-weather-guardrail",
            description="Guardrail for location weather service to prevent misuse",
            blocked_input_messaging="This input is blocked by the guardrail policy.",
            blocked_outputs_messaging="This output is blocked by the guardrail policy.",
            content_policy_config={
                "filtersConfig": [
                    {
                        "type": "SEXUAL",
                        "inputStrength": "HIGH",
                        "outputStrength": "HIGH",
                    },
                    {
                        "type": "VIOLENCE",
                        "inputStrength": "HIGH",
                        "outputStrength": "HIGH",
                    },
                    {
                        "type": "HATE",
                        "inputStrength": "HIGH",
                        "outputStrength": "HIGH",
                    },
                    {
                        "type": "INSULTS",
                        "inputStrength": "MEDIUM",
                        "outputStrength": "MEDIUM",
                    },
                    {
                        "type": "MISCONDUCT",
                        "inputStrength": "HIGH",
                        "outputStrength": "HIGH",
                    },
                ]
            },
            sensitive_information_policy_config={
                "piiEntitiesConfig": [
                    {"type": "PHONE", "action": "BLOCK"},
                    {"type": "EMAIL", "action": "BLOCK"},
                    {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
                    {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
                    {"type": "US_BANK_ACCOUNT_NUMBER", "action": "BLOCK"},
                    {"type": "US_BANK_ROUTING_NUMBER", "action": "BLOCK"},
                    {"type": "US_PASSPORT_NUMBER", "action": "BLOCK"},
                    {"type": "DRIVER_ID", "action": "BLOCK"},
                    {"type": "LICENSE_PLATE", "action": "BLOCK"},
                    {"type": "USERNAME", "action": "BLOCK"},
                    {"type": "PASSWORD", "action": "BLOCK"},
                    # NOTE: NAME is intentionally excluded as location services require place names
                    # NOTE: ADDRESS is intentionally excluded as location services require address processing
                    # US_STATE, CITY, ZIP_CODE, COUNTRY are also allowed for location queries
                    # Removed VEHICLE_VIN and PIN as they may not be supported in all regions
                ]
            },
            topic_policy_config={
                "topicsConfig": [
                    {
                        "name": "Non-Weather Topics",
                        "definition": "Topics unrelated to weather, location, or travel that should be blocked",
                        "examples": [
                            "Tell me a joke",
                            "What is the meaning of life?",
                            "Help me with my homework",
                            "Write me a poem",
                            "What's your favorite movie?",
                        ],
                        "type": "DENY",
                    }
                ]
            },
        )

        return guardrail

    def _create_agentcore_agent(self) -> bedrock.CfnAgent:
        """Create Bedrock AgentCore agent with action groups."""
        # Create execution role for the agent
        agent_role = iam.Role(
            self,
            "AgentCoreExecutionRole",
            role_name="agentcore-weather-agent-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        # Add permissions for the agent to invoke Lambda functions
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    self.weather_function.function_arn,
                    self.alerts_function.function_arn,
                ],
            )
        )

        # Add permissions for the agent to invoke Bedrock models
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-*",
                ],
            )
        )

        # Add permissions for the agent to use guardrails
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ApplyGuardrail",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account}:guardrail/*",
                ],
            )
        )

        # System prompt for the agent
        system_prompt = """You are a location and weather assistant. Use available tools to find locations and provide weather information.

For weather queries, always use get_weather tool first to get temperature, conditions, and wind, then use get_alerts tool to check for warnings.

For route queries, always check weather alerts at both the origin and destination locations for travel safety.

Guidelines: Only provide information for public places. Respect privacy and prevent API abuse.

Be concise and helpful."""

        # Create the agent
        agent = bedrock.CfnAgent(
            self,
            "LocationWeatherAgent",
            agent_name="location-weather-agent",
            description="Agent for location-based weather information and alerts",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            instruction=system_prompt,
            agent_resource_role_arn=agent_role.role_arn,
            idle_session_ttl_in_seconds=3600,
            guardrail_configuration={
                "guardrailIdentifier": self.guardrail.attr_guardrail_id,
                "guardrailVersion": "DRAFT",
            },
            action_groups=[
                {
                    "actionGroupName": "weather-tools",
                    "description": "Tools for weather information retrieval",
                    "actionGroupExecutor": {
                        "lambda": self.weather_function.function_arn
                    },
                    "apiSchema": {"payload": self._get_weather_openapi_schema()},
                },
                {
                    "actionGroupName": "alerts-tools",
                    "description": "Tools for weather alerts retrieval",
                    "actionGroupExecutor": {
                        "lambda": self.alerts_function.function_arn
                    },
                    "apiSchema": {"payload": self._get_alerts_openapi_schema()},
                },
            ],
        )

        return agent

    def _get_weather_openapi_schema(self) -> str:
        """Get OpenAPI schema for weather action group."""
        # Import the schema from the application source
        import sys

        # Add the source directory to the path to import schemas
        src_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "strands_location_service_weather"
        )
        sys.path.insert(0, str(src_path))

        try:
            from agentcore_schemas import get_weather_action_group_schema

            return json.dumps(get_weather_action_group_schema())
        except ImportError:
            # Fallback minimal schema if import fails
            return json.dumps(
                {
                    "openapi": "3.0.0",
                    "info": {"title": "Weather Services", "version": "1.0.0"},
                    "paths": {
                        "/get_weather": {
                            "post": {
                                "description": "Get weather information",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "latitude": {"type": "number"},
                                                    "longitude": {"type": "number"},
                                                },
                                                "required": ["latitude", "longitude"],
                                            }
                                        }
                                    },
                                },
                                "responses": {"200": {"description": "Weather data"}},
                            }
                        }
                    },
                }
            )

    def _get_alerts_openapi_schema(self) -> str:
        """Get OpenAPI schema for alerts action group."""
        # Import the schema from the application source
        import sys

        # Add the source directory to the path to import schemas
        src_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "strands_location_service_weather"
        )
        sys.path.insert(0, str(src_path))

        try:
            from agentcore_schemas import get_alerts_action_group_schema

            return json.dumps(get_alerts_action_group_schema())
        except ImportError:
            # Fallback minimal schema if import fails
            return json.dumps(
                {
                    "openapi": "3.0.0",
                    "info": {"title": "Weather Alerts Services", "version": "1.0.0"},
                    "paths": {
                        "/get_alerts": {
                            "post": {
                                "description": "Get weather alerts",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "latitude": {"type": "number"},
                                                    "longitude": {"type": "number"},
                                                },
                                                "required": ["latitude", "longitude"],
                                            }
                                        }
                                    },
                                },
                                "responses": {"200": {"description": "Weather alerts"}},
                            }
                        }
                    },
                }
            )
