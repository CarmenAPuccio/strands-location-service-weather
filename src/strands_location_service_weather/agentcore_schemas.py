"""
OpenAPI schemas for AgentCore action groups.

This module defines the OpenAPI 3.0 schemas required for AgentCore action groups
that expose the weather and alerts tools as HTTP endpoints.
"""

from typing import Any


def get_weather_action_group_schema() -> dict[str, Any]:
    """
    Generate OpenAPI 3.0 schema for the weather action group.

    Returns:
        OpenAPI schema dictionary for get_weather tool
    """
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Weather Services",
            "version": "1.0.0",
            "description": "Weather information services using National Weather Service API",
        },
        "paths": {
            "/get_weather": {
                "post": {
                    "operationId": "get_weather",
                    "summary": "Get weather information for coordinates",
                    "description": "Get current weather information for the specified coordinates using the National Weather Service API.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {
                                            "type": "number",
                                            "format": "float",
                                            "description": "The latitude coordinate",
                                            "minimum": -90,
                                            "maximum": 90,
                                            "example": 47.6062,
                                        },
                                        "longitude": {
                                            "type": "number",
                                            "format": "float",
                                            "description": "The longitude coordinate",
                                            "minimum": -180,
                                            "maximum": 180,
                                            "example": -122.3321,
                                        },
                                    },
                                    "required": ["latitude", "longitude"],
                                    "additionalProperties": False,
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Weather data retrieved successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "temperature": {
                                                "type": "object",
                                                "description": "Temperature information with value and unit",
                                                "properties": {
                                                    "value": {
                                                        "type": "integer",
                                                        "description": "Temperature value",
                                                    },
                                                    "unit": {
                                                        "type": "string",
                                                        "description": "Temperature unit (F or C)",
                                                        "enum": ["F", "C"],
                                                    },
                                                },
                                                "required": ["value", "unit"],
                                            },
                                            "windSpeed": {
                                                "type": "object",
                                                "description": "Wind speed information with value and unit",
                                                "properties": {
                                                    "value": {
                                                        "type": "string",
                                                        "description": "Wind speed value with unit",
                                                    },
                                                    "unit": {
                                                        "type": "string",
                                                        "description": "Wind speed unit",
                                                        "enum": ["mph"],
                                                    },
                                                },
                                                "required": ["value", "unit"],
                                            },
                                            "windDirection": {
                                                "type": "string",
                                                "description": "Wind direction (e.g., 'NW', 'SE')",
                                            },
                                            "shortForecast": {
                                                "type": "string",
                                                "description": "Brief weather description",
                                            },
                                            "detailedForecast": {
                                                "type": "string",
                                                "description": "Detailed weather forecast",
                                            },
                                            "success": {
                                                "type": "boolean",
                                                "description": "Whether the request was successful",
                                            },
                                        },
                                        "required": [
                                            "temperature",
                                            "windSpeed",
                                            "windDirection",
                                            "shortForecast",
                                            "detailedForecast",
                                            "success",
                                        ],
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Bad request - invalid parameters",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "Error message"},
                        "error_type": {
                            "type": "string",
                            "description": "Type of error",
                            "enum": [
                                "parameter_validation",
                                "http_request",
                                "internal_error",
                            ],
                        },
                        "success": {
                            "type": "boolean",
                            "description": "Always false for error responses",
                        },
                    },
                    "required": ["error", "success"],
                }
            }
        },
    }


def get_alerts_action_group_schema() -> dict[str, Any]:
    """
    Generate OpenAPI 3.0 schema for the alerts action group.

    Returns:
        OpenAPI schema dictionary for get_alerts tool
    """
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Weather Alerts Services",
            "version": "1.0.0",
            "description": "Weather alerts and warnings services using National Weather Service API",
        },
        "paths": {
            "/get_alerts": {
                "post": {
                    "operationId": "get_alerts",
                    "summary": "Get active weather alerts for coordinates",
                    "description": "Retrieves active weather alerts and warnings for the specified coordinates using the National Weather Service API.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {
                                            "type": "number",
                                            "format": "float",
                                            "description": "The latitude coordinate",
                                            "minimum": -90,
                                            "maximum": 90,
                                            "example": 47.6062,
                                        },
                                        "longitude": {
                                            "type": "number",
                                            "format": "float",
                                            "description": "The longitude coordinate",
                                            "minimum": -180,
                                            "maximum": 180,
                                            "example": -122.3321,
                                        },
                                    },
                                    "required": ["latitude", "longitude"],
                                    "additionalProperties": False,
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Weather alerts retrieved successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "alerts": {
                                                "type": "array",
                                                "description": "List of active weather alerts",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "event": {
                                                            "type": "string",
                                                            "description": "Type of weather event",
                                                        },
                                                        "headline": {
                                                            "type": "string",
                                                            "description": "Alert headline",
                                                        },
                                                        "description": {
                                                            "type": "string",
                                                            "description": "Detailed alert description",
                                                        },
                                                        "severity": {
                                                            "type": "string",
                                                            "description": "Alert severity level",
                                                            "enum": [
                                                                "Minor",
                                                                "Moderate",
                                                                "Severe",
                                                                "Extreme",
                                                            ],
                                                        },
                                                        "urgency": {
                                                            "type": "string",
                                                            "description": "Alert urgency level",
                                                            "enum": [
                                                                "Past",
                                                                "Future",
                                                                "Expected",
                                                                "Immediate",
                                                            ],
                                                        },
                                                        "effective": {
                                                            "type": "string",
                                                            "description": "When the alert becomes effective",
                                                        },
                                                        "expires": {
                                                            "type": "string",
                                                            "description": "When the alert expires",
                                                        },
                                                        "instruction": {
                                                            "type": "string",
                                                            "description": "Instructions for the alert",
                                                        },
                                                        "message": {
                                                            "type": "string",
                                                            "description": "Message when no alerts are active",
                                                        },
                                                    },
                                                },
                                            },
                                            "alert_count": {
                                                "type": "integer",
                                                "description": "Number of active alerts",
                                                "minimum": 0,
                                            },
                                            "success": {
                                                "type": "boolean",
                                                "description": "Whether the request was successful",
                                            },
                                        },
                                        "required": [
                                            "alerts",
                                            "alert_count",
                                            "success",
                                        ],
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Bad request - invalid parameters",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "Error message"},
                        "error_type": {
                            "type": "string",
                            "description": "Type of error",
                            "enum": [
                                "parameter_validation",
                                "http_request",
                                "internal_error",
                            ],
                        },
                        "success": {
                            "type": "boolean",
                            "description": "Always false for error responses",
                        },
                    },
                    "required": ["error", "success"],
                }
            }
        },
    }


def get_combined_action_group_schema() -> dict[str, Any]:
    """
    Generate combined OpenAPI 3.0 schema for both weather and alerts tools.

    This can be used if both tools are deployed in a single action group.

    Returns:
        Combined OpenAPI schema dictionary for both tools
    """
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Weather and Alerts Services",
            "version": "1.0.0",
            "description": "Combined weather information and alerts services using National Weather Service API",
        },
        "paths": {
            "/get_weather": {
                "post": get_weather_action_group_schema()["paths"]["/get_weather"][
                    "post"
                ]
            },
            "/get_alerts": {
                "post": get_alerts_action_group_schema()["paths"]["/get_alerts"]["post"]
            },
        },
        "components": {
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "Error message"},
                        "error_type": {
                            "type": "string",
                            "description": "Type of error",
                            "enum": [
                                "parameter_validation",
                                "http_request",
                                "internal_error",
                            ],
                        },
                        "success": {
                            "type": "boolean",
                            "description": "Always false for error responses",
                        },
                    },
                    "required": ["error", "success"],
                }
            }
        },
    }


def validate_schema(schema: dict[str, Any]) -> list[str]:
    """
    Validate an OpenAPI schema for common issues.

    Args:
        schema: OpenAPI schema dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required top-level fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in schema:
            errors.append(f"Missing required field: {field}")

    # Check OpenAPI version
    if "openapi" in schema and not schema["openapi"].startswith("3.0"):
        errors.append("OpenAPI version must be 3.0.x")

    # Check info section
    if "info" in schema:
        info = schema["info"]
        if "title" not in info:
            errors.append("Missing required field: info.title")
        if "version" not in info:
            errors.append("Missing required field: info.version")

    # Check paths section
    if "paths" in schema:
        paths = schema["paths"]
        if not paths:
            errors.append("Paths section cannot be empty")

        for path, path_obj in paths.items():
            if not isinstance(path_obj, dict):
                errors.append(f"Path {path} must be an object")
                continue

            # Check for at least one HTTP method
            http_methods = ["get", "post", "put", "delete", "patch"]
            if not any(method in path_obj for method in http_methods):
                errors.append(f"Path {path} must have at least one HTTP method")

    return errors
