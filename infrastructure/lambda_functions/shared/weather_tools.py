"""
Shared weather tools for Lambda functions.

This module provides the actual weather tool implementations that are
called by the Lambda function handlers.
"""

import json
import os
from typing import Any

import requests
from lambda_handler import parse_agentcore_event


def get_weather_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle get_weather requests from AgentCore.

    Args:
        event: AgentCore Lambda event
        context: AWS Lambda context

    Returns:
        AgentCore-formatted response
    """
    try:
        # Parse AgentCore event to extract parameters
        params = parse_agentcore_event(event)

        latitude = params.get("latitude")
        longitude = params.get("longitude")

        if latitude is None or longitude is None:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Missing required parameters: latitude and longitude",
                        "error_type": "parameter_validation",
                        "success": False,
                    }
                ),
            }

        # Call weather API
        weather_data = get_weather_data(latitude, longitude)

        return {"statusCode": 200, "body": json.dumps(weather_data)}

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": str(e), "error_type": "internal_error", "success": False}
            ),
        }


def get_alerts_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle get_alerts requests from AgentCore.

    Args:
        event: AgentCore Lambda event
        context: AWS Lambda context

    Returns:
        AgentCore-formatted response
    """
    try:
        # Parse AgentCore event to extract parameters
        params = parse_agentcore_event(event)

        latitude = params.get("latitude")
        longitude = params.get("longitude")

        if latitude is None or longitude is None:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Missing required parameters: latitude and longitude",
                        "error_type": "parameter_validation",
                        "success": False,
                    }
                ),
            }

        # Call alerts API
        alerts_data = get_alerts_data(latitude, longitude)

        return {"statusCode": 200, "body": json.dumps(alerts_data)}

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": str(e), "error_type": "internal_error", "success": False}
            ),
        }


def get_weather_data(latitude: float, longitude: float) -> dict[str, Any]:
    """Get weather data from National Weather Service API."""
    base_url = os.environ.get("WEATHER_API_BASE_URL", "https://api.weather.gov")
    timeout = int(os.environ.get("WEATHER_API_TIMEOUT", "10"))
    user_agent = os.environ.get("USER_AGENT_WEATHER", "AgentCoreWeatherService/1.0")

    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}

    try:
        # Get grid point
        points_url = f"{base_url}/points/{latitude},{longitude}"
        response = requests.get(points_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        points_data = response.json()
        forecast_url = points_data["properties"]["forecast"]

        # Get forecast
        forecast_response = requests.get(forecast_url, headers=headers, timeout=timeout)
        forecast_response.raise_for_status()

        forecast_data = forecast_response.json()
        current_period = forecast_data["properties"]["periods"][0]

        return {
            "temperature": {
                "value": current_period["temperature"],
                "unit": current_period["temperatureUnit"],
            },
            "windSpeed": {"value": current_period["windSpeed"], "unit": "mph"},
            "windDirection": current_period["windDirection"],
            "shortForecast": current_period["shortForecast"],
            "detailedForecast": current_period["detailedForecast"],
            "success": True,
        }

    except requests.RequestException as e:
        raise Exception(f"Weather API request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Unexpected weather API response format: {str(e)}") from e


def get_alerts_data(latitude: float, longitude: float) -> dict[str, Any]:
    """Get weather alerts from National Weather Service API."""
    base_url = os.environ.get("WEATHER_API_BASE_URL", "https://api.weather.gov")
    timeout = int(os.environ.get("WEATHER_API_TIMEOUT", "10"))
    user_agent = os.environ.get("USER_AGENT_ALERTS", "AgentCoreAlertsService/1.0")

    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}

    try:
        # Get alerts for the point
        alerts_url = f"{base_url}/alerts/active"
        params = {"point": f"{latitude},{longitude}"}

        response = requests.get(
            alerts_url, headers=headers, params=params, timeout=timeout
        )
        response.raise_for_status()

        alerts_data = response.json()
        features = alerts_data.get("features", [])

        alerts = []
        for feature in features:
            properties = feature.get("properties", {})
            alerts.append(
                {
                    "event": properties.get("event", ""),
                    "headline": properties.get("headline", ""),
                    "description": properties.get("description", ""),
                    "severity": properties.get("severity", ""),
                    "urgency": properties.get("urgency", ""),
                    "effective": properties.get("effective", ""),
                    "expires": properties.get("expires", ""),
                    "instruction": properties.get("instruction", ""),
                }
            )

        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "success": True,
        }

    except requests.RequestException as e:
        raise Exception(f"Weather alerts API request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Unexpected alerts API response format: {str(e)}") from e
