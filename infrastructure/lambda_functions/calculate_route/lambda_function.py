"""
Lambda function for calculate_route tool with correct Bedrock Agent response format.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def format_error_response(error_message, event):
    """Format error response for Bedrock Agent."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "calculate-route"),
            "apiPath": event.get("apiPath", "/calculate_route"),
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


def calculate_route_data(departure_position, destination_position, travel_mode="Car"):
    """Calculate route using Amazon Location Service."""
    # Get configuration from environment
    region = os.environ.get("AWS_REGION", "us-east-1")
    route_calculator = os.environ.get("ROUTE_CALCULATOR_NAME", "ExampleRouteCalculator")

    try:
        # Create Location Service client
        location_client = boto3.client("location", region_name=region)

        # Build route calculation parameters
        route_params = {
            "CalculatorName": route_calculator,
            "DeparturePosition": departure_position,
            "DestinationPosition": destination_position,
            "TravelMode": travel_mode,
            "IncludeLegGeometry": True,
            "DistanceUnit": "Miles",
        }

        logger.info(f"Calculating route with params: {route_params}")

        # Call Amazon Location Service
        response = location_client.calculate_route(**route_params)

        # Format route summary
        summary = response.get("Summary", {})
        route_summary = {
            "distance": summary.get("Distance", 0),
            "duration_seconds": summary.get("DurationSeconds", 0),
            "route_bbox": summary.get("RouteBBox", []),
        }

        # Format route legs with step-by-step directions
        legs = []
        for leg in response.get("Legs", []):
            leg_data = {
                "distance": leg.get("Distance", 0),
                "duration_seconds": leg.get("DurationSeconds", 0),
                "start_position": leg.get("StartPosition", []),
                "end_position": leg.get("EndPosition", []),
                "steps": [],
            }

            # Add step-by-step directions if available
            for step in leg.get("Steps", []):
                step_data = {
                    "distance": step.get("Distance", 0),
                    "duration_seconds": step.get("DurationSeconds", 0),
                    "start_position": step.get("StartPosition", []),
                    "end_position": step.get("EndPosition", []),
                    "geometry_offset": step.get("GeometryOffset", 0),
                }
                leg_data["steps"].append(step_data)

            legs.append(leg_data)

        logger.info(
            f"Route calculated: {route_summary['distance']:.2f} miles, {route_summary['duration_seconds']} seconds"
        )

        return {
            "summary": route_summary,
            "legs": legs,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"Location Service error {error_code}: {error_message}")
        raise Exception(f"Location Service error: {error_message}") from e

    except Exception as e:
        logger.error(f"Unexpected error in calculate_route_data: {str(e)}")
        raise


def lambda_handler(event, context):
    """Lambda handler for calculate_route action group."""
    try:
        logger.info(f"Processing request - Event type: {type(event)}")

        # Parse Bedrock Agent event safely
        if not isinstance(event, dict):
            logger.error(f"Event is not a dictionary: {type(event)}")
            return format_error_response(
                "Invalid event format - expected dictionary", event
            )

        # Log the full event for debugging
        logger.info(f"Full event received: {json.dumps(event, default=str)}")

        # Extract parameters from Bedrock Agent event
        params = {}

        # Handle different event formats - check requestBody first as it's more reliable
        if "requestBody" in event and event["requestBody"]:
            # Bedrock Agent format with requestBody
            logger.info(f"Found requestBody in event: {event['requestBody']}")
            try:
                request_body = event["requestBody"]
                if isinstance(request_body, dict) and "content" in request_body:
                    # Handle Bedrock Agent format: requestBody.content.application/json.properties[]
                    content = request_body["content"]
                    if (
                        "application/json" in content
                        and "properties" in content["application/json"]
                    ):
                        properties = content["application/json"]["properties"]
                        for prop in properties:
                            param_name = prop.get("name")
                            param_value = prop.get("value")
                            if param_name and param_value is not None:
                                # Handle array parameters (departure_position, destination_position)
                                if param_name in [
                                    "departure_position",
                                    "destination_position",
                                ] and isinstance(param_value, str):
                                    try:
                                        params[param_name] = json.loads(param_value)
                                    except json.JSONDecodeError:
                                        params[param_name] = param_value
                                else:
                                    params[param_name] = param_value
                elif isinstance(request_body, str):
                    params = json.loads(request_body)
                elif isinstance(request_body, dict):
                    params = request_body
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse request body: {e}")
                return format_error_response("Invalid JSON in request body", event)

        elif "parameters" in event and event["parameters"]:
            # Standard Bedrock Agent format (fallback)
            for param in event["parameters"]:
                param_name = param.get("name")
                param_value = param.get("value")
                if param_name and param_value is not None:
                    params[param_name] = param_value

        else:
            logger.error(f"No parameters or requestBody found in event: {event}")
            return format_error_response("No parameters found in event", event)

        logger.info(f"Extracted parameters: {params}")

        # Validate required parameters
        required_params = ["departure_position", "destination_position"]
        for param in required_params:
            if param not in params:
                return format_error_response(
                    f"Missing required parameter: {param}", event
                )

        departure_position = params["departure_position"]
        destination_position = params["destination_position"]
        travel_mode = params.get("travel_mode", "Car")

        # Map common travel mode values to Location Service format
        travel_mode_mapping = {
            "driving": "Car",
            "car": "Car",
            "Car": "Car",
            "truck": "Truck",
            "Truck": "Truck",
            "walking": "Walking",
            "Walking": "Walking",
            "pedestrian": "Walking",
        }

        if travel_mode in travel_mode_mapping:
            travel_mode = travel_mode_mapping[travel_mode]
        else:
            return format_error_response(
                f"Invalid travel_mode '{travel_mode}'. Must be one of: driving, car, truck, walking",
                event,
            )

        # Validate parameter types and values
        if not isinstance(departure_position, list) or len(departure_position) != 2:
            return format_error_response(
                "Parameter 'departure_position' must be an array of [longitude, latitude]",
                event,
            )

        if not isinstance(destination_position, list) or len(destination_position) != 2:
            return format_error_response(
                "Parameter 'destination_position' must be an array of [longitude, latitude]",
                event,
            )

        # Validate coordinate ranges
        for pos_name, position in [
            ("departure_position", departure_position),
            ("destination_position", destination_position),
        ]:
            longitude, latitude = position
            if not (-180 <= longitude <= 180):
                return format_error_response(
                    f"Invalid longitude in {pos_name}: {longitude} (must be between -180 and 180)",
                    event,
                )
            if not (-90 <= latitude <= 90):
                return format_error_response(
                    f"Invalid latitude in {pos_name}: {latitude} (must be between -90 and 90)",
                    event,
                )

        # Calculate route
        route_data = calculate_route_data(
            departure_position, destination_position, travel_mode
        )

        # Format successful response in Bedrock Agent format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "calculate-route"),
                "apiPath": event.get("apiPath", "/calculate_route"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 200,
                "responseBody": {"application/json": {"body": json.dumps(route_data)}},
            },
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return format_error_response(str(e), event)
