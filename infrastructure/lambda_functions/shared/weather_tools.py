"""
Weather tools implementation for Lambda functions.

This module contains the core weather and alerts functionality that can be
shared across Lambda functions without including unnecessary application code.
"""

import logging
from datetime import datetime

import requests
from lambda_handler import (
    ACCEPT_HEADER,
    USER_AGENT_ALERTS,
    USER_AGENT_WEATHER,
    WEATHER_API_BASE_URL,
    WEATHER_API_TIMEOUT,
    _http_session,
    _tracer,
    format_agentcore_response,
    lambda_error_handler,
    parse_agentcore_event,
)

logger = logging.getLogger(__name__)


@lambda_error_handler
def get_weather_handler(event, context):
    """
    Lambda handler for getting weather information.

    This function implements weather data retrieval adapted for AgentCore Lambda
    execution with proper event parsing, response formatting, and AWS Lambda best practices.

    Args:
        event: AgentCore Lambda event
        context: Lambda context

    Returns:
        AgentCore-formatted response with weather data
    """
    # Parse parameters from AgentCore event
    parameters = parse_agentcore_event(event)

    # Extract required parameters with validation
    latitude = parameters.get("latitude")
    longitude = parameters.get("longitude")

    if latitude is None or longitude is None:
        raise ValueError("Both latitude and longitude parameters are required")

    # Validate parameter types and ranges
    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got: {longitude}"
            )

    except (TypeError, ValueError) as e:
        raise ValueError(
            f"Invalid coordinate values: latitude={latitude}, longitude={longitude}"
        ) from e

    logger.info(f"Getting weather for coordinates: {latitude}, {longitude}")

    # Create a span for the weather API call process
    with _tracer.start_as_current_span("get_weather_api") as span:
        # Add attributes to the span for context
        span.set_attribute("latitude", latitude)
        span.set_attribute("longitude", longitude)
        span.set_attribute("api.service", "weather.gov")

        # Set headers for the request
        headers = {
            "User-Agent": USER_AGENT_WEATHER,
            "Accept": ACCEPT_HEADER,
        }

        # First, get the grid endpoint for the coordinates
        with _tracer.start_as_current_span("get_grid_points") as grid_span:
            points_url = f"{WEATHER_API_BASE_URL}/points/{latitude},{longitude}"
            grid_span.set_attribute("http.url", points_url)
            grid_span.set_attribute("http.method", "GET")

            points_response = _http_session.get(
                points_url, headers=headers, timeout=WEATHER_API_TIMEOUT
            )
            grid_span.set_attribute("http.status_code", points_response.status_code)
            grid_span.set_attribute("http.response_size", len(points_response.content))

            if points_response.status_code != 200:
                error_msg = (
                    f"Failed to get grid data: HTTP {points_response.status_code}"
                )
                logger.error(f"{error_msg} - URL: {points_url}")
                span.set_attribute("error", error_msg)
                raise requests.RequestException(error_msg)

        points_data = points_response.json()
        forecast_url = points_data["properties"]["forecast"]

        # Get the forecast data
        with _tracer.start_as_current_span("get_forecast") as forecast_span:
            forecast_span.set_attribute("http.url", forecast_url)
            forecast_span.set_attribute("http.method", "GET")

            forecast_response = _http_session.get(
                forecast_url, headers=headers, timeout=WEATHER_API_TIMEOUT
            )
            forecast_span.set_attribute(
                "http.status_code", forecast_response.status_code
            )
            forecast_span.set_attribute(
                "http.response_size", len(forecast_response.content)
            )

            if forecast_response.status_code != 200:
                error_msg = (
                    f"Failed to get forecast data: HTTP {forecast_response.status_code}"
                )
                logger.error(f"{error_msg} - URL: {forecast_url}")
                span.set_attribute("error", error_msg)
                raise requests.RequestException(error_msg)

        forecast_data = forecast_response.json()
        current_period = forecast_data["properties"]["periods"][0]

        # Return formatted weather data with enhanced metadata
        result = {
            "temperature": {
                "value": current_period["temperature"],
                "unit": current_period["temperatureUnit"],
            },
            "windSpeed": {"value": current_period["windSpeed"], "unit": "mph"},
            "windDirection": current_period["windDirection"],
            "shortForecast": current_period["shortForecast"],
            "detailedForecast": current_period["detailedForecast"],
            "location": {"latitude": latitude, "longitude": longitude},
            "source": "National Weather Service",
            "period": {
                "name": current_period.get("name", "Current"),
                "startTime": current_period.get("startTime"),
                "endTime": current_period.get("endTime"),
            },
        }

        # Add success attributes to the span
        span.set_attribute("temperature", current_period["temperature"])
        span.set_attribute("forecast", current_period["shortForecast"])
        span.set_attribute("api.success", True)

        logger.info(
            f"Weather retrieved: {current_period['temperature']}°{current_period['temperatureUnit']}, {current_period['shortForecast']}"
        )

        return format_agentcore_response(result)


@lambda_error_handler
def get_alerts_handler(event, context):
    """
    Lambda handler for getting weather alerts.

    This function implements weather alerts retrieval adapted for AgentCore Lambda
    execution with proper event parsing, response formatting, and AWS Lambda best practices.

    Args:
        event: AgentCore Lambda event
        context: Lambda context

    Returns:
        AgentCore-formatted response with weather alerts data
    """
    # Parse parameters from AgentCore event
    parameters = parse_agentcore_event(event)

    # Extract required parameters with validation
    latitude = parameters.get("latitude")
    longitude = parameters.get("longitude")

    if latitude is None or longitude is None:
        raise ValueError("Both latitude and longitude parameters are required")

    # Validate parameter types and ranges
    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got: {longitude}"
            )

    except (TypeError, ValueError) as e:
        raise ValueError(
            f"Invalid coordinate values: latitude={latitude}, longitude={longitude}"
        ) from e

    logger.info(f"Getting weather alerts for coordinates: {latitude}, {longitude}")

    # Create a span for the alerts API call
    with _tracer.start_as_current_span("get_weather_alerts") as span:
        # Add attributes to the span for context
        span.set_attribute("latitude", latitude)
        span.set_attribute("longitude", longitude)
        span.set_attribute("api.service", "weather.gov")

        # Set headers for the request
        headers = {
            "User-Agent": USER_AGENT_ALERTS,
            "Accept": ACCEPT_HEADER,
        }

        # First, get the zone for the coordinates
        with _tracer.start_as_current_span("get_zone_info") as zone_span:
            points_url = f"{WEATHER_API_BASE_URL}/points/{latitude},{longitude}"
            zone_span.set_attribute("http.url", points_url)
            zone_span.set_attribute("http.method", "GET")

            points_response = _http_session.get(
                points_url, headers=headers, timeout=WEATHER_API_TIMEOUT
            )
            zone_span.set_attribute("http.status_code", points_response.status_code)
            zone_span.set_attribute("http.response_size", len(points_response.content))

            if points_response.status_code != 200:
                error_msg = (
                    f"Failed to get zone data: HTTP {points_response.status_code}"
                )
                logger.error(f"{error_msg} - URL: {points_url}")
                span.set_attribute("error", error_msg)
                raise requests.RequestException(error_msg)

        points_data = points_response.json()

        # Get the county/zone code
        county_zone = points_data["properties"]["county"].split("/")[-1]
        logger.debug(f"Found county/zone code: {county_zone}")

        # Get active alerts for the zone
        with _tracer.start_as_current_span("get_alerts_data") as alerts_span:
            alerts_url = f"{WEATHER_API_BASE_URL}/alerts/active/zone/{county_zone}"
            alerts_span.set_attribute("http.url", alerts_url)
            alerts_span.set_attribute("http.method", "GET")

            alerts_response = _http_session.get(
                alerts_url, headers=headers, timeout=WEATHER_API_TIMEOUT
            )
            alerts_span.set_attribute("http.status_code", alerts_response.status_code)
            alerts_span.set_attribute(
                "http.response_size", len(alerts_response.content)
            )

            if alerts_response.status_code != 200:
                error_msg = (
                    f"Failed to get alerts data: HTTP {alerts_response.status_code}"
                )
                logger.error(f"{error_msg} - URL: {alerts_url}")
                span.set_attribute("error", error_msg)
                raise requests.RequestException(error_msg)

        alerts_data = alerts_response.json()

        # Process and format the alerts
        alerts = []
        for feature in alerts_data.get("features", []):
            properties = feature.get("properties", {})

            # Convert effective and expires times to more readable format
            effective = properties.get("effective")
            expires = properties.get("expires")

            try:
                if effective:
                    effective_dt = datetime.fromisoformat(
                        effective.replace("Z", "+00:00")
                    )
                    effective = effective_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

                if expires:
                    expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    expires = expires_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
            except Exception as date_error:
                logger.warning(f"Error parsing date: {date_error}")
                # Keep original format if parsing fails
                pass

            alert = {
                "event": properties.get("event"),
                "headline": properties.get("headline"),
                "description": properties.get("description"),
                "severity": properties.get("severity"),
                "urgency": properties.get("urgency"),
                "certainty": properties.get("certainty"),
                "effective": effective,
                "expires": expires,
                "instruction": properties.get("instruction"),
                "areas": properties.get("areaDesc"),
                "sender": properties.get("senderName"),
            }
            alerts.append(alert)

        # Add count to span
        alert_count = len(alerts)
        span.set_attribute("alert_count", alert_count)
        span.set_attribute("api.success", True)

        # Prepare result with enhanced metadata
        if not alerts:
            logger.info("No active weather alerts found for this location")
            result = {
                "alerts": [],
                "alert_count": 0,
                "message": "No active weather alerts for this location",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "zone": county_zone,
                },
                "source": "National Weather Service",
            }
        else:
            logger.info(f"Found {alert_count} active weather alert(s)")
            result = {
                "alerts": alerts,
                "alert_count": alert_count,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "zone": county_zone,
                },
                "source": "National Weather Service",
            }

        return format_agentcore_response(result)
