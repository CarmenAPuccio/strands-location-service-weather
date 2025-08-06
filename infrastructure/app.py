#!/usr/bin/env python3
"""
AWS CDK App for AgentCore Weather Tools.

This is the main CDK application entry point following AWS CDK best practices
for Python project structure.
"""

import os

from aws_cdk import App, Environment
from stacks.agentcore_stack import LocationWeatherAgentCoreStack


def main():
    """Main CDK application."""
    app = App()

    # Get environment configuration
    account = os.environ.get("CDK_DEFAULT_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID"))
    region = os.environ.get(
        "CDK_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1")
    )

    env = Environment(account=account, region=region) if account else None

    # Create the main stack
    LocationWeatherAgentCoreStack(
        app,
        "LocationWeatherAgentCore",
        env=env,
        description="AgentCore weather and alerts tools with Lambda functions",
        # Stack configuration from environment variables
        function_name_prefix=os.environ.get("FUNCTION_PREFIX", "agentcore-weather"),
        weather_api_timeout=int(os.environ.get("WEATHER_API_TIMEOUT", "10")),
        otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        log_retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "14")),
    )

    app.synth()


if __name__ == "__main__":
    main()
