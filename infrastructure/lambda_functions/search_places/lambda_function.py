"""
Lambda function for search_places tool with correct Bedrock Agent response format.
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
            "actionGroup": event.get("actionGroup", "search-places"),
            "apiPath": event.get("apiPath", "/search_places"),
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


def search_places_data(text, max_results=10, bias_position=None, filter_bbox=None):
    """Search for places using Amazon Location Service."""
    # Get configuration from environment
    region = os.environ.get("AWS_REGION", "us-east-1")
    place_index = os.environ.get("PLACE_INDEX_NAME", "ExamplePlaceIndex")

    try:
        # Create Location Service client
        location_client = boto3.client("location", region_name=region)

        # Build search parameters
        search_params = {
            "IndexName": place_index,
            "Text": text,
            "MaxResults": max_results,
        }

        # Add optional parameters
        if bias_position:
            search_params["BiasPosition"] = bias_position

        if filter_bbox:
            search_params["FilterBBox"] = filter_bbox

        logger.info(f"Searching places with params: {search_params}")

        # Call Amazon Location Service
        response = location_client.search_place_index_for_text(**search_params)

        # Format results
        results = []
        for result in response.get("Results", []):
            place = result.get("Place", {})
            results.append(
                {
                    "place_id": result.get("PlaceId", ""),
                    "label": place.get("Label", ""),
                    "geometry": {"point": place.get("Geometry", {}).get("Point", [])},
                    "address": {
                        "street": place.get("AddressNumber", "")
                        + " "
                        + place.get("Street", ""),
                        "city": place.get("Municipality", ""),
                        "state": place.get("Region", ""),
                        "postalCode": place.get("PostalCode", ""),
                        "country": place.get("Country", ""),
                    },
                }
            )

        logger.info(f"Found {len(results)} places")

        return {
            "results": results,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"Location Service error {error_code}: {error_message}")
        raise Exception(f"Location Service error: {error_message}") from e

    except Exception as e:
        logger.error(f"Unexpected error in search_places_data: {str(e)}")
        raise


def lambda_handler(event, context):
    """Lambda handler for search_places action group."""
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
                                # Handle array parameters (bias_position, filter_bbox)
                                if param_name in [
                                    "bias_position",
                                    "filter_bbox",
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

        elif "inputText" in event:
            # Another possible Bedrock Agent format
            logger.info(f"Found inputText in event: {event['inputText']}")
            try:
                params = json.loads(event["inputText"])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse inputText: {e}")
                return format_error_response("Invalid JSON in inputText", event)

        else:
            logger.error(
                f"No parameters, requestBody, or inputText found in event: {event}"
            )
            logger.error(f"Event keys: {list(event.keys())}")
            return format_error_response("No parameters found in event", event)

        logger.info(f"Extracted parameters: {params}")

        # Validate required parameters
        if "text" not in params:
            return format_error_response("Missing required parameter: text", event)

        text = params["text"]
        max_results = int(params.get("max_results", 10))
        bias_position = params.get("bias_position")
        filter_bbox = params.get("filter_bbox")

        # Validate parameter types
        if not isinstance(text, str) or not text.strip():
            return format_error_response(
                "Parameter 'text' must be a non-empty string", event
            )

        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            return format_error_response(
                "Parameter 'max_results' must be an integer between 1 and 50", event
            )

        # Get search results
        search_data = search_places_data(text, max_results, bias_position, filter_bbox)

        # Format successful response in Bedrock Agent format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "search-places"),
                "apiPath": event.get("apiPath", "/search_places"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 200,
                "responseBody": {"application/json": {"body": json.dumps(search_data)}},
            },
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return format_error_response(str(e), event)
