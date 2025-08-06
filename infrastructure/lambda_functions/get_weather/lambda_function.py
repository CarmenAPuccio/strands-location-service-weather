"""
Lambda function for get_weather tool in AgentCore deployment.

This module provides a standalone Lambda function for weather information retrieval
that can be deployed as an AgentCore action group. It imports the shared handler
logic and provides the Lambda entry point.
"""

import sys
from pathlib import Path

# Add shared directory to path
shared_dir = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_dir))

from weather_tools import get_weather_handler


def lambda_handler(event, context):
    """
    AWS Lambda entry point for get_weather function.

    This function is called by AWS Lambda runtime and AgentCore.
    It delegates to the shared handler implementation.

    Args:
        event: AgentCore Lambda event containing request parameters
        context: AWS Lambda context object

    Returns:
        AgentCore-formatted response with weather data
    """
    return get_weather_handler(event, context)
