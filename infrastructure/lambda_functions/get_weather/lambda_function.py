"""
Lambda function for get_weather tool with correct Bedrock Agent response format.
"""

import json
import logging
import os
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def format_error_response(error_message, event):
    """Format error response for Bedrock Agent."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "weather-tools"),
            "apiPath": event.get("apiPath", "/get_weather"),
            "httpMethod": event.get("httpMethod", "POST"),
            "httpStatusCode": 500,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(
                        {
                            "error": error_message,
                            "success": False,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                }
            },
        },
    }


def get_weather_data(latitude, longitude):
    """Get weather data from National Weather Service API."""
    import requests

    base_url = os.environ.get("WEATHER_API_BASE_URL", "https://api.weather.gov")
    timeout = int(os.environ.get("WEATHER_API_TIMEOUT", "10"))
    user_agent = os.environ.get("USER_AGENT_WEATHER", "BedrockAgentWeatherService/1.0")

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


def lambda_handler(event, context):
    """
    AWS Lambda entry point for get_weather function.
    """
    try:
        logger.info(f"Processing request - Event type: {type(event)}")

        # Parse Bedrock Agent event safely
        if not isinstance(event, dict):
            logger.error(f"Event is not a dictionary: {type(event)}")
            return format_error_response(
                "Invalid event format - expected dictionary", event
            )

        # Extract parameters from Bedrock Agent event
        params = {}

        # Method 1: Extract from parameters array (if not empty)
        if (
            "parameters" in event
            and isinstance(event["parameters"], list)
            and len(event["parameters"]) > 0
        ):
            logger.info(f"Found parameters array with {len(event['parameters'])} items")
            for param in event["parameters"]:
                if isinstance(param, dict) and "name" in param and "value" in param:
                    param_name = param["name"]
                    param_value = param["value"]
                    param_type = param.get("type", "string")

                    # Type conversion
                    if param_type == "number":
                        try:
                            param_value = float(param_value)
                        except (ValueError, TypeError):
                            return format_error_response(
                                f"Invalid number value for {param_name}", event
                            )

                    params[param_name] = param_value

        # Method 2: Extract from requestBody.content["application/json"].properties
        if not params and "requestBody" in event:
            logger.info("Extracting from requestBody.content")
            request_body = event.get("requestBody", {})
            content = request_body.get("content", {})

            if "application/json" in content:
                app_json = content["application/json"]
                if "properties" in app_json and isinstance(
                    app_json["properties"], list
                ):
                    logger.info(
                        f"Found properties array with {len(app_json['properties'])} items"
                    )

                    for prop in app_json["properties"]:
                        if (
                            isinstance(prop, dict)
                            and "name" in prop
                            and "value" in prop
                        ):
                            param_name = prop["name"]
                            param_value = prop["value"]
                            param_type = prop.get("type", "string")

                            logger.info(
                                f"Processing property: {param_name} = {param_value} (type: {param_type})"
                            )

                            # Type conversion
                            if param_type == "number":
                                try:
                                    param_value = float(param_value)
                                except (ValueError, TypeError):
                                    return format_error_response(
                                        f"Invalid number value for {param_name}", event
                                    )

                            params[param_name] = param_value

        logger.info(f"Final extracted parameters: {params}")

        # Validate required parameters
        latitude = params.get("latitude")
        longitude = params.get("longitude")

        if latitude is None or longitude is None:
            return format_error_response(
                "Both latitude and longitude parameters are required", event
            )

        # Call weather API
        weather_data = get_weather_data(latitude, longitude)

        # Format successful response in Bedrock Agent format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "weather-tools"),
                "apiPath": event.get("apiPath", "/get_weather"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(
                            weather_data, default=str, ensure_ascii=False
                        )
                    }
                },
            },
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return format_error_response(f"Internal error: {str(e)}", event)
