"""
Schema validation utilities for OpenAPI schemas and tool definitions.

This module provides comprehensive validation for OpenAPI 3.0 schemas used in
AgentCore action groups, ensuring compliance with AWS Bedrock AgentCore requirements.
"""

import logging
from dataclasses import dataclass
from typing import Any

# Get logger for this module
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    schema_type: str

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class SchemaValidationConfig:
    """Configuration for schema validation."""

    strict_mode: bool = True
    check_examples: bool = True
    validate_references: bool = True
    require_descriptions: bool = True
    max_nesting_depth: int = 10


class OpenAPIValidator:
    """Validator for OpenAPI 3.0 schemas."""

    def __init__(self, config: SchemaValidationConfig | None = None):
        """Initialize validator with configuration.

        Args:
            config: Validation configuration
        """
        self.config = config or SchemaValidationConfig()
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_schema(self, schema: dict[str, Any]) -> ValidationResult:
        """Validate complete OpenAPI 3.0 schema.

        Args:
            schema: OpenAPI schema to validate

        Returns:
            Validation result with errors and warnings
        """
        logger.info("Starting OpenAPI 3.0 schema validation")

        self.errors = []
        self.warnings = []

        try:
            # Validate top-level structure
            self._validate_root_object(schema)

            # Validate info object
            if "info" in schema:
                self._validate_info_object(schema["info"])

            # Validate paths object
            if "paths" in schema:
                self._validate_paths_object(schema["paths"])

            # Validate components if present
            if "components" in schema:
                self._validate_components_object(schema["components"])

            # AgentCore-specific validations
            self._validate_agentcore_compatibility(schema)

        except Exception as e:
            self.errors.append(f"Validation failed with exception: {str(e)}")
            logger.error(f"Schema validation exception: {str(e)}")

        is_valid = len(self.errors) == 0

        logger.info(
            f"Schema validation completed: {'PASSED' if is_valid else 'FAILED'}"
        )
        logger.info(f"Errors: {len(self.errors)}, Warnings: {len(self.warnings)}")

        return ValidationResult(
            valid=is_valid,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            schema_type="openapi_3.0",
        )

    def _validate_root_object(self, schema: dict[str, Any]) -> None:
        """Validate root OpenAPI object."""
        required_fields = ["openapi", "info", "paths"]

        for field in required_fields:
            if field not in schema:
                self.errors.append(f"Missing required root field: {field}")

        # Validate OpenAPI version
        if "openapi" in schema:
            version = schema["openapi"]
            if not isinstance(version, str):
                self.errors.append("'openapi' field must be a string")
            elif not version.startswith("3.0"):
                self.errors.append(
                    f"Unsupported OpenAPI version: {version} (expected 3.0.x)"
                )

        # Check for unknown root fields
        known_fields = {
            "openapi",
            "info",
            "servers",
            "paths",
            "components",
            "security",
            "tags",
            "externalDocs",
        }
        unknown_fields = set(schema.keys()) - known_fields
        if unknown_fields:
            self.warnings.append(f"Unknown root fields: {', '.join(unknown_fields)}")

    def _validate_info_object(self, info: dict[str, Any]) -> None:
        """Validate info object."""
        if not isinstance(info, dict):
            self.errors.append("'info' must be an object")
            return

        # Required fields
        required_fields = ["title", "version"]
        for field in required_fields:
            if field not in info:
                self.errors.append(f"Missing required info field: {field}")
            elif not isinstance(info[field], str):
                self.errors.append(f"info.{field} must be a string")

        # Optional but recommended fields
        if self.config.require_descriptions and "description" not in info:
            self.warnings.append(
                "info.description is recommended for better documentation"
            )

        # Validate contact and license if present
        if "contact" in info and not isinstance(info["contact"], dict):
            self.errors.append("info.contact must be an object")

        if "license" in info and not isinstance(info["license"], dict):
            self.errors.append("info.license must be an object")

    def _validate_paths_object(self, paths: dict[str, Any]) -> None:
        """Validate paths object."""
        if not isinstance(paths, dict):
            self.errors.append("'paths' must be an object")
            return

        if len(paths) == 0:
            self.warnings.append("No paths defined in schema")
            return

        valid_methods = {
            "get",
            "put",
            "post",
            "delete",
            "options",
            "head",
            "patch",
            "trace",
        }

        for path, path_item in paths.items():
            if not isinstance(path, str):
                self.errors.append(f"Path key must be a string: {path}")
                continue

            if not path.startswith("/"):
                self.errors.append(f"Path must start with '/': {path}")

            if not isinstance(path_item, dict):
                self.errors.append(f"Path item must be an object: {path}")
                continue

            # Validate operations
            for method, operation in path_item.items():
                method_lower = method.lower()

                if method_lower not in valid_methods:
                    # Check if it's a path-level parameter or other valid field
                    if method not in [
                        "summary",
                        "description",
                        "servers",
                        "parameters",
                    ]:
                        self.errors.append(
                            f"Invalid HTTP method '{method}' in path '{path}'"
                        )
                    continue

                self._validate_operation_object(operation, f"{method.upper()} {path}")

    def _validate_operation_object(
        self, operation: dict[str, Any], context: str
    ) -> None:
        """Validate operation object."""
        if not isinstance(operation, dict):
            self.errors.append(f"Operation must be an object: {context}")
            return

        # Required fields
        if "responses" not in operation:
            self.errors.append(f"Missing required 'responses' field: {context}")
        else:
            self._validate_responses_object(operation["responses"], context)

        # Validate optional fields
        if "requestBody" in operation:
            self._validate_request_body_object(operation["requestBody"], context)

        if "parameters" in operation:
            self._validate_parameters_array(operation["parameters"], context)

        # AgentCore recommendations
        if "operationId" not in operation:
            self.warnings.append(f"operationId recommended for AgentCore: {context}")

        if self.config.require_descriptions and "description" not in operation:
            self.warnings.append(f"description recommended: {context}")

    def _validate_responses_object(
        self, responses: dict[str, Any], context: str
    ) -> None:
        """Validate responses object."""
        if not isinstance(responses, dict):
            self.errors.append(f"responses must be an object: {context}")
            return

        if len(responses) == 0:
            self.errors.append(f"At least one response required: {context}")
            return

        # Check for success response
        success_codes = {"200", "201", "202", "204", "default"}
        has_success = any(code in success_codes for code in responses.keys())
        if not has_success:
            self.warnings.append(f"No success response defined: {context}")

        # Validate individual responses
        for status_code, response in responses.items():
            if not isinstance(response, dict):
                self.errors.append(
                    f"Response must be an object: {context} {status_code}"
                )
                continue

            # Validate status code format
            if status_code != "default" and not (
                status_code.isdigit() and len(status_code) == 3
            ):
                self.errors.append(
                    f"Invalid status code format: {status_code} in {context}"
                )

            self._validate_response_object(response, f"{context} {status_code}")

    def _validate_response_object(self, response: dict[str, Any], context: str) -> None:
        """Validate individual response object."""
        if "description" not in response:
            self.errors.append(f"Missing required 'description' field: {context}")

        if "content" in response:
            self._validate_content_object(response["content"], context)

    def _validate_request_body_object(
        self, request_body: dict[str, Any], context: str
    ) -> None:
        """Validate request body object."""
        if not isinstance(request_body, dict):
            self.errors.append(f"requestBody must be an object: {context}")
            return

        if "content" not in request_body:
            self.errors.append(
                f"Missing required 'content' field in requestBody: {context}"
            )
        else:
            self._validate_content_object(
                request_body["content"], f"{context} requestBody"
            )

    def _validate_content_object(self, content: dict[str, Any], context: str) -> None:
        """Validate content object."""
        if not isinstance(content, dict):
            self.errors.append(f"content must be an object: {context}")
            return

        # Check for JSON content type
        has_json = "application/json" in content

        if not has_json and self.config.strict_mode:
            self.warnings.append(
                f"application/json content type recommended for AgentCore: {context}"
            )

        # Validate media type objects
        for media_type, media_type_obj in content.items():
            if not isinstance(media_type_obj, dict):
                self.errors.append(
                    f"Media type object must be an object: {context} {media_type}"
                )
                continue

            if "schema" in media_type_obj:
                self._validate_schema_object(
                    media_type_obj["schema"], f"{context} {media_type}"
                )

    def _validate_schema_object(
        self, schema: dict[str, Any], context: str, depth: int = 0
    ) -> None:
        """Validate schema object (recursive)."""
        if depth > self.config.max_nesting_depth:
            self.warnings.append(f"Schema nesting depth exceeded: {context}")
            return

        if not isinstance(schema, dict):
            self.errors.append(f"Schema must be an object: {context}")
            return

        # Validate type field
        if "type" in schema:
            valid_types = {
                "null",
                "boolean",
                "object",
                "array",
                "number",
                "string",
                "integer",
            }
            if schema["type"] not in valid_types:
                self.errors.append(f"Invalid schema type '{schema['type']}': {context}")

        # Validate object properties
        if schema.get("type") == "object" and "properties" in schema:
            if not isinstance(schema["properties"], dict):
                self.errors.append(f"properties must be an object: {context}")
            else:
                for prop_name, prop_schema in schema["properties"].items():
                    self._validate_schema_object(
                        prop_schema, f"{context}.{prop_name}", depth + 1
                    )

        # Validate array items
        if schema.get("type") == "array" and "items" in schema:
            self._validate_schema_object(schema["items"], f"{context}[]", depth + 1)

        # Validate required array
        if "required" in schema:
            if not isinstance(schema["required"], list):
                self.errors.append(f"required must be an array: {context}")
            elif schema.get("type") == "object" and "properties" in schema:
                # Check that required properties exist
                properties = schema["properties"]
                for req_prop in schema["required"]:
                    if req_prop not in properties:
                        self.errors.append(
                            f"Required property '{req_prop}' not defined: {context}"
                        )

    def _validate_parameters_array(self, parameters: list[Any], context: str) -> None:
        """Validate parameters array."""
        if not isinstance(parameters, list):
            self.errors.append(f"parameters must be an array: {context}")
            return

        for i, param in enumerate(parameters):
            if not isinstance(param, dict):
                self.errors.append(f"Parameter must be an object: {context}[{i}]")
                continue

            # Required fields
            required_fields = ["name", "in"]
            for field in required_fields:
                if field not in param:
                    self.errors.append(
                        f"Missing required parameter field '{field}': {context}[{i}]"
                    )

            # Validate 'in' field
            if "in" in param:
                valid_locations = {"query", "header", "path", "cookie"}
                if param["in"] not in valid_locations:
                    self.errors.append(
                        f"Invalid parameter location '{param['in']}': {context}[{i}]"
                    )

    def _validate_components_object(self, components: dict[str, Any]) -> None:
        """Validate components object."""
        if not isinstance(components, dict):
            self.errors.append("components must be an object")
            return

        # Validate schemas if present
        if "schemas" in components:
            if not isinstance(components["schemas"], dict):
                self.errors.append("components.schemas must be an object")
            else:
                for schema_name, schema in components["schemas"].items():
                    self._validate_schema_object(
                        schema, f"components.schemas.{schema_name}"
                    )

    def _validate_agentcore_compatibility(self, schema: dict[str, Any]) -> None:
        """Validate AgentCore-specific requirements."""
        logger.debug("Validating AgentCore compatibility")

        # Check for POST operations (AgentCore preference)
        if "paths" in schema:
            post_operations = 0
            total_operations = 0

            for _path, path_item in schema["paths"].items():
                if isinstance(path_item, dict):
                    for method in path_item.keys():
                        if method.lower() in {"get", "post", "put", "delete", "patch"}:
                            total_operations += 1
                            if method.lower() == "post":
                                post_operations += 1

            if total_operations > 0 and post_operations == 0:
                self.warnings.append(
                    "AgentCore works best with POST operations for action groups"
                )

        # Check for operationId in all operations
        missing_operation_ids = []
        if "paths" in schema:
            for path, path_item in schema["paths"].items():
                if isinstance(path_item, dict):
                    for method, operation in path_item.items():
                        if method.lower() in {"get", "post", "put", "delete", "patch"}:
                            if (
                                isinstance(operation, dict)
                                and "operationId" not in operation
                            ):
                                missing_operation_ids.append(f"{method.upper()} {path}")

        if missing_operation_ids:
            self.warnings.append(
                f"Missing operationId for AgentCore operations: {', '.join(missing_operation_ids)}"
            )

        # Check for JSON content types
        non_json_operations = []
        if "paths" in schema:
            for path, path_item in schema["paths"].items():
                if isinstance(path_item, dict):
                    for method, operation in path_item.items():
                        if method.lower() in {"post", "put", "patch"}:
                            if (
                                isinstance(operation, dict)
                                and "requestBody" in operation
                            ):
                                request_body = operation["requestBody"]
                                if (
                                    isinstance(request_body, dict)
                                    and "content" in request_body
                                ):
                                    content = request_body["content"]
                                    if (
                                        isinstance(content, dict)
                                        and "application/json" not in content
                                    ):
                                        non_json_operations.append(
                                            f"{method.upper()} {path}"
                                        )

        if non_json_operations:
            self.warnings.append(
                f"AgentCore prefers application/json content: {', '.join(non_json_operations)}"
            )


class ToolSchemaValidator:
    """Validator for tool schema definitions."""

    def __init__(self, config: SchemaValidationConfig | None = None):
        """Initialize validator.

        Args:
            config: Validation configuration
        """
        self.config = config or SchemaValidationConfig()

    def validate_tool_schema(
        self,
        tool_name: str,
        parameters_schema: dict[str, Any],
        return_schema: dict[str, Any],
    ) -> ValidationResult:
        """Validate tool parameter and return schemas.

        Args:
            tool_name: Name of the tool
            parameters_schema: Parameters schema to validate
            return_schema: Return schema to validate

        Returns:
            Validation result
        """
        logger.info(f"Validating tool schema for: {tool_name}")

        errors = []
        warnings = []

        # Validate parameters schema
        param_result = self._validate_json_schema(
            parameters_schema, f"{tool_name} parameters"
        )
        errors.extend(param_result.errors)
        warnings.extend(param_result.warnings)

        # Validate return schema
        return_result = self._validate_json_schema(return_schema, f"{tool_name} return")
        errors.extend(return_result.errors)
        warnings.extend(return_result.warnings)

        # Tool-specific validations
        if parameters_schema.get("type") != "object":
            warnings.append(
                f"Tool {tool_name}: parameters should be object type for AgentCore compatibility"
            )

        if (
            "properties" not in parameters_schema
            and parameters_schema.get("type") == "object"
        ):
            warnings.append(
                f"Tool {tool_name}: object parameters should define properties"
            )

        is_valid = len(errors) == 0

        logger.info(
            f"Tool schema validation for {tool_name}: {'PASSED' if is_valid else 'FAILED'}"
        )

        return ValidationResult(
            valid=is_valid, errors=errors, warnings=warnings, schema_type="tool_schema"
        )

    def _validate_json_schema(
        self, schema: dict[str, Any], context: str
    ) -> ValidationResult:
        """Validate JSON schema object.

        Args:
            schema: Schema to validate
            context: Context for error messages

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        if not isinstance(schema, dict):
            errors.append(f"{context}: schema must be an object")
            return ValidationResult(
                valid=False, errors=errors, warnings=warnings, schema_type="json_schema"
            )

        # Validate type field
        if "type" not in schema:
            warnings.append(f"{context}: missing 'type' field")
        else:
            valid_types = {
                "null",
                "boolean",
                "object",
                "array",
                "number",
                "string",
                "integer",
            }
            if schema["type"] not in valid_types:
                errors.append(f"{context}: invalid type '{schema['type']}'")

        # Validate object properties
        if schema.get("type") == "object":
            if "properties" in schema:
                if not isinstance(schema["properties"], dict):
                    errors.append(f"{context}: properties must be an object")
                else:
                    # Recursively validate property schemas
                    for prop_name, prop_schema in schema["properties"].items():
                        prop_result = self._validate_json_schema(
                            prop_schema, f"{context}.{prop_name}"
                        )
                        errors.extend(prop_result.errors)
                        warnings.extend(prop_result.warnings)

            # Validate required array
            if "required" in schema:
                if not isinstance(schema["required"], list):
                    errors.append(f"{context}: required must be an array")
                elif "properties" in schema:
                    # Check that required properties exist
                    properties = schema["properties"]
                    for req_prop in schema["required"]:
                        if req_prop not in properties:
                            errors.append(
                                f"{context}: required property '{req_prop}' not defined"
                            )

        # Validate array items
        if schema.get("type") == "array":
            if "items" in schema:
                items_result = self._validate_json_schema(
                    schema["items"], f"{context}[]"
                )
                errors.extend(items_result.errors)
                warnings.extend(items_result.warnings)
            else:
                warnings.append(f"{context}: array should define items schema")

        is_valid = len(errors) == 0

        return ValidationResult(
            valid=is_valid, errors=errors, warnings=warnings, schema_type="json_schema"
        )


def validate_all_schemas() -> dict[str, ValidationResult]:
    """Validate all generated schemas.

    Returns:
        Dictionary mapping schema names to validation results
    """
    logger.info("Validating all generated schemas")

    from .openapi_schemas import get_all_action_group_schemas

    validator = OpenAPIValidator()
    results = {}

    schemas = get_all_action_group_schemas()

    for schema_name, schema_data in schemas.items():
        logger.info(f"Validating schema: {schema_name}")
        result = validator.validate_schema(schema_data)
        results[schema_name] = result

        if result.valid:
            logger.info(f"✓ {schema_name} validation passed")
        else:
            logger.error(
                f"✗ {schema_name} validation failed with {len(result.errors)} errors"
            )
            for error in result.errors:
                logger.error(f"  - {error}")

        if result.warnings:
            logger.warning(f"⚠ {schema_name} has {len(result.warnings)} warnings")
            for warning in result.warnings:
                logger.warning(f"  - {warning}")

    return results


def generate_validation_report() -> str:
    """Generate a comprehensive validation report.

    Returns:
        Formatted validation report
    """
    logger.info("Generating validation report")

    results = validate_all_schemas()

    report_lines = [
        "# OpenAPI Schema Validation Report",
        "",
        f"Generated on: {__import__('datetime').datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
    ]

    total_schemas = len(results)
    valid_schemas = sum(1 for r in results.values() if r.valid)
    total_errors = sum(len(r.errors) for r in results.values())
    total_warnings = sum(len(r.warnings) for r in results.values())

    report_lines.extend(
        [
            f"- Total schemas: {total_schemas}",
            f"- Valid schemas: {valid_schemas}",
            f"- Invalid schemas: {total_schemas - valid_schemas}",
            f"- Total errors: {total_errors}",
            f"- Total warnings: {total_warnings}",
            "",
        ]
    )

    # Detailed results
    report_lines.append("## Detailed Results")
    report_lines.append("")

    for schema_name, result in results.items():
        status = "✓ PASS" if result.valid else "✗ FAIL"
        report_lines.append(f"### {schema_name} - {status}")
        report_lines.append("")

        if result.errors:
            report_lines.append("**Errors:**")
            for error in result.errors:
                report_lines.append(f"- {error}")
            report_lines.append("")

        if result.warnings:
            report_lines.append("**Warnings:**")
            for warning in result.warnings:
                report_lines.append(f"- {warning}")
            report_lines.append("")

    return "\n".join(report_lines)
