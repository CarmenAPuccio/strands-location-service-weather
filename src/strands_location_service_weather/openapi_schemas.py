"""
OpenAPI 3.0 schema generation for Bedrock Agent action groups.

This module provides utilities to generate OpenAPI schemas from Strands tool definitions
for AWS Bedrock Agent integration. It supports automatic schema generation from
Python function signatures and manual schema definitions.
"""

import inspect
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Union, get_type_hints

# Get logger for this module
logger = logging.getLogger(__name__)


@dataclass
class OpenAPISchema:
    """OpenAPI 3.0 schema definition for an action group."""

    openapi: str = "3.0.0"
    info: dict[str, Any] = None
    paths: dict[str, Any] = None
    components: dict[str, Any] | None = None

    def __post_init__(self):
        if self.info is None:
            self.info = {"title": "Generated API", "version": "1.0.0"}
        if self.paths is None:
            self.paths = {}


@dataclass
class ToolSchemaDefinition:
    """Schema definition for a single tool."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    return_schema: dict[str, Any]
    http_method: str = "post"
    path: str | None = None

    def __post_init__(self):
        if self.path is None:
            self.path = f"/{self.name}"


def python_type_to_openapi_type(python_type: type) -> dict[str, Any]:
    """Convert Python type to OpenAPI schema type.

    Args:
        python_type: Python type to convert

    Returns:
        OpenAPI schema type definition
    """
    # Handle basic types
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array", "items": {"type": "string"}},
        dict: {"type": "object"},
    }

    # Handle typing module types and new union syntax
    if hasattr(python_type, "__origin__") or hasattr(python_type, "__args__"):
        origin = getattr(python_type, "__origin__", None)
        args = getattr(python_type, "__args__", ())

        # Handle List[T] types
        if origin is list or origin is list:
            if args:
                item_type = python_type_to_openapi_type(args[0])
                return {"type": "array", "items": item_type}
            return {"type": "array", "items": {"type": "string"}}

        # Handle Dict types
        elif origin is dict or origin is dict:
            return {"type": "object"}

        # Handle Union types (including new | syntax and Optional)
        elif (
            origin is Union
            or str(origin) == "<class 'types.UnionType'>"
            or (args and len(args) == 2 and type(None) in args)
        ):
            if len(args) == 2 and type(None) in args:
                # This is Optional[T] or T | None
                non_none_type = args[0] if args[1] is type(None) else args[1]
                schema = python_type_to_openapi_type(non_none_type)
                schema["nullable"] = True
                return schema
            # For other unions, default to string
            return {"type": "string"}

    return type_mapping.get(python_type, {"type": "string"})


def extract_function_schema(func: Callable) -> ToolSchemaDefinition:
    """Extract OpenAPI schema from a Python function.

    Args:
        func: Function to analyze

    Returns:
        Tool schema definition
    """
    logger.debug(f"Extracting schema from function: {func.__name__}")

    # Get function signature and type hints
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Extract parameters schema
    parameters = {}
    required_params = []

    for param_name, param in sig.parameters.items():
        param_type = type_hints.get(param_name, str)
        param_schema = python_type_to_openapi_type(param_type)

        # Add description from docstring if available
        if func.__doc__:
            # Simple docstring parsing - look for Args section
            doc_lines = func.__doc__.split("\n")
            in_args_section = False
            for line in doc_lines:
                line = line.strip()
                if line.startswith("Args:"):
                    in_args_section = True
                    continue
                elif line.startswith("Returns:") or line.startswith("Raises:"):
                    in_args_section = False
                    continue
                elif in_args_section and line.startswith(f"{param_name}:"):
                    description = line.split(":", 1)[1].strip()
                    param_schema["description"] = description
                    break

        parameters[param_name] = param_schema

        # Check if parameter is required (no default value)
        if param.default == inspect.Parameter.empty:
            required_params.append(param_name)

    parameters_schema = {
        "type": "object",
        "properties": parameters,
        "required": required_params,
    }

    # Extract return schema
    return_type = type_hints.get("return", dict)
    return_schema = python_type_to_openapi_type(return_type)

    # Get description from docstring
    description = (
        func.__doc__.split("\n")[0].strip()
        if func.__doc__
        else f"Execute {func.__name__}"
    )

    return ToolSchemaDefinition(
        name=func.__name__,
        description=description,
        parameters_schema=parameters_schema,
        return_schema=return_schema,
    )


def generate_openapi_schema_for_tool(func: Callable) -> dict[str, Any]:
    """Generate OpenAPI schema for a single tool function.

    Args:
        func: Tool function to generate schema for

    Returns:
        Dictionary containing parameters_schema and return_schema
    """
    logger.info(f"Generating OpenAPI schema for tool: {func.__name__}")

    try:
        tool_schema = extract_function_schema(func)

        return {
            "parameters_schema": tool_schema.parameters_schema,
            "return_schema": tool_schema.return_schema,
            "description": tool_schema.description,
        }

    except Exception as e:
        logger.error(f"Failed to generate schema for {func.__name__}: {str(e)}")
        # Return minimal schema as fallback
        return {
            "parameters_schema": {"type": "object", "properties": {}},
            "return_schema": {"type": "object"},
            "description": f"Tool: {func.__name__}",
        }


def create_action_group_schema(
    action_group_name: str,
    tools: list[Callable],
    title: str | None = None,
    version: str = "1.0.0",
    description: str | None = None,
) -> OpenAPISchema:
    """Create OpenAPI schema for an action group.

    Args:
        action_group_name: Name of the action group
        tools: List of tool functions to include
        title: API title (defaults to action group name)
        version: API version
        description: API description

    Returns:
        Complete OpenAPI schema for the action group
    """
    logger.info(f"Creating action group schema for: {action_group_name}")

    if title is None:
        title = f"{action_group_name.replace('_', ' ').title()} API"

    if description is None:
        description = f"API for {action_group_name} action group"

    # Create base schema
    schema = OpenAPISchema(
        info={"title": title, "version": version, "description": description}
    )

    # Add paths for each tool
    for tool_func in tools:
        try:
            tool_schema = extract_function_schema(tool_func)

            # Create path definition
            path_def = {
                tool_schema.http_method: {
                    "description": tool_schema.description,
                    "operationId": tool_schema.name,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": tool_schema.parameters_schema
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": tool_schema.return_schema
                                }
                            },
                        },
                        "400": {
                            "description": "Bad request",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"error": {"type": "string"}},
                                    }
                                }
                            },
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"error": {"type": "string"}},
                                    }
                                }
                            },
                        },
                    },
                }
            }

            schema.paths[tool_schema.path] = path_def
            logger.debug(f"Added path {tool_schema.path} for tool {tool_schema.name}")

        except Exception as e:
            logger.error(f"Failed to add tool {tool_func.__name__} to schema: {str(e)}")
            continue

    logger.info(f"Created schema with {len(schema.paths)} paths")
    return schema


def create_weather_action_group_schema() -> dict[str, Any]:
    """Create OpenAPI schema for weather action group.

    Returns:
        OpenAPI 3.0 schema for weather tools
    """
    logger.info("Creating weather action group schema")

    # Import weather tools
    from .location_weather import current_time, get_alerts, get_weather

    weather_tools = [get_weather, get_alerts, current_time]

    schema = create_action_group_schema(
        action_group_name="weather_services",
        tools=weather_tools,
        title="Weather Services API",
        description="Weather information and alerts from National Weather Service",
    )

    return {"openapi": schema.openapi, "info": schema.info, "paths": schema.paths}


def create_location_action_group_schema() -> dict[str, Any]:
    """Create OpenAPI schema for location action group.

    Note: This creates a placeholder schema since location services
    are typically handled by MCP tools or pre-configured Bedrock Agent action groups.

    Returns:
        OpenAPI 3.0 schema for location services
    """
    logger.info("Creating location action group schema")

    # Define location service operations based on Amazon Location Service capabilities
    location_schema = OpenAPISchema(
        info={
            "title": "Location Services API",
            "version": "1.0.0",
            "description": "Location search and routing services via Amazon Location Service",
        }
    )

    # Add search places operation
    location_schema.paths["/search_places"] = {
        "post": {
            "description": "Search for places by text query",
            "operationId": "search_places",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "Search query text",
                                },
                                "bias_position": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Bias position as [longitude, latitude]",
                                    "nullable": True,
                                },
                                "filter_bbox": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Bounding box filter as [west, south, east, north]",
                                    "nullable": True,
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of results",
                                    "default": 10,
                                },
                            },
                            "required": ["text"],
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Search results",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "results": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "place_id": {"type": "string"},
                                                "label": {"type": "string"},
                                                "geometry": {
                                                    "type": "object",
                                                    "properties": {
                                                        "point": {
                                                            "type": "array",
                                                            "items": {"type": "number"},
                                                        }
                                                    },
                                                },
                                                "address": {"type": "object"},
                                            },
                                        },
                                    }
                                },
                            }
                        }
                    },
                }
            },
        }
    }

    # Add calculate route operation
    location_schema.paths["/calculate_route"] = {
        "post": {
            "description": "Calculate route between two points",
            "operationId": "calculate_route",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "departure_position": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Starting position as [longitude, latitude]",
                                },
                                "destination_position": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "Destination position as [longitude, latitude]",
                                },
                                "travel_mode": {
                                    "type": "string",
                                    "enum": ["Car", "Truck", "Walking"],
                                    "default": "Car",
                                },
                            },
                            "required": ["departure_position", "destination_position"],
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Route calculation result",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "summary": {
                                        "type": "object",
                                        "properties": {
                                            "distance": {"type": "number"},
                                            "duration_seconds": {"type": "number"},
                                            "route_bbox": {
                                                "type": "array",
                                                "items": {"type": "number"},
                                            },
                                        },
                                    },
                                    "legs": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    },
                                },
                            }
                        }
                    },
                }
            },
        }
    }

    return {
        "openapi": location_schema.openapi,
        "info": location_schema.info,
        "paths": location_schema.paths,
    }


def validate_openapi_schema(schema: dict[str, Any]) -> list[str]:
    """Validate OpenAPI 3.0 schema compliance.

    Args:
        schema: OpenAPI schema to validate

    Returns:
        List of validation errors (empty if valid)
    """
    logger.debug("Validating OpenAPI schema")

    errors = []

    # Check required top-level fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in schema:
            errors.append(f"Missing required field: {field}")

    # Validate OpenAPI version
    if "openapi" in schema:
        version = schema["openapi"]
        if not version.startswith("3.0"):
            errors.append(f"Unsupported OpenAPI version: {version} (expected 3.0.x)")

    # Validate info object
    if "info" in schema:
        info = schema["info"]
        if not isinstance(info, dict):
            errors.append("'info' must be an object")
        else:
            if "title" not in info:
                errors.append("Missing required field: info.title")
            if "version" not in info:
                errors.append("Missing required field: info.version")

    # Validate paths object
    if "paths" in schema:
        paths = schema["paths"]
        if not isinstance(paths, dict):
            errors.append("'paths' must be an object")
        else:
            for path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    errors.append(f"Path '{path}' must be an object")
                    continue

                # Check for valid HTTP methods
                valid_methods = [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "head",
                    "options",
                    "trace",
                ]
                for method, operation in path_item.items():
                    if method.lower() not in valid_methods:
                        errors.append(
                            f"Invalid HTTP method '{method}' in path '{path}'"
                        )
                        continue

                    if not isinstance(operation, dict):
                        errors.append(
                            f"Operation '{method}' in path '{path}' must be an object"
                        )
                        continue

                    # Validate operation object
                    if "responses" not in operation:
                        errors.append(f"Missing 'responses' in {method.upper()} {path}")

    if errors:
        logger.warning(f"Schema validation found {len(errors)} errors")
        for error in errors:
            logger.warning(f"  - {error}")
    else:
        logger.info("Schema validation passed")

    return errors


def export_schemas_to_files(
    output_dir: str = "infrastructure/schemas",
) -> dict[str, str]:
    """Export generated schemas to JSON files.

    Args:
        output_dir: Directory to save schema files

    Returns:
        Dictionary mapping schema names to file paths
    """
    import os

    logger.info(f"Exporting schemas to {output_dir}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    schemas = {
        "weather_action_group": create_weather_action_group_schema(),
        "location_action_group": create_location_action_group_schema(),
    }

    file_paths = {}

    for schema_name, schema_data in schemas.items():
        file_path = os.path.join(output_dir, f"{schema_name}.json")

        try:
            with open(file_path, "w") as f:
                json.dump(schema_data, f, indent=2)

            file_paths[schema_name] = file_path
            logger.info(f"Exported {schema_name} to {file_path}")

            # Validate the exported schema
            validation_errors = validate_openapi_schema(schema_data)
            if validation_errors:
                logger.warning(f"Schema {schema_name} has validation issues")
            else:
                logger.info(f"Schema {schema_name} validation passed")

        except Exception as e:
            logger.error(f"Failed to export {schema_name}: {str(e)}")

    return file_paths


def get_all_action_group_schemas() -> dict[str, dict[str, Any]]:
    """Get all action group schemas.

    Returns:
        Dictionary mapping action group names to their schemas
    """
    logger.info("Generating all action group schemas")

    return {
        "weather_services": create_weather_action_group_schema(),
        "location_services": create_location_action_group_schema(),
    }
