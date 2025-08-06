"""
Tests for OpenAPI schema generation and validation.

This module tests the OpenAPI 3.0 schema generation for AgentCore action groups,
ensuring compliance with AWS Bedrock AgentCore requirements.
"""

import json

import pytest

from src.strands_location_service_weather.openapi_schemas import (
    create_action_group_schema,
    create_location_action_group_schema,
    create_weather_action_group_schema,
    export_schemas_to_files,
    extract_function_schema,
    generate_openapi_schema_for_tool,
    get_all_action_group_schemas,
    python_type_to_openapi_type,
    validate_openapi_schema,
)
from src.strands_location_service_weather.schema_validation import (
    OpenAPIValidator,
    SchemaValidationConfig,
    ToolSchemaValidator,
    ValidationResult,
    generate_validation_report,
    validate_all_schemas,
)


class TestPythonTypeConversion:
    """Test Python type to OpenAPI type conversion."""

    def test_basic_types(self):
        """Test conversion of basic Python types."""
        assert python_type_to_openapi_type(str) == {"type": "string"}
        assert python_type_to_openapi_type(int) == {"type": "integer"}
        assert python_type_to_openapi_type(float) == {"type": "number"}
        assert python_type_to_openapi_type(bool) == {"type": "boolean"}
        assert python_type_to_openapi_type(dict) == {"type": "object"}

    def test_list_types(self):
        """Test conversion of list types."""

        # Basic list
        result = python_type_to_openapi_type(list)
        assert result == {"type": "array", "items": {"type": "string"}}

        # Typed list
        result = python_type_to_openapi_type(list[str])
        assert result == {"type": "array", "items": {"type": "string"}}

        result = python_type_to_openapi_type(list[int])
        assert result == {"type": "array", "items": {"type": "integer"}}

    def test_optional_types(self):
        """Test conversion of Optional types."""

        result = python_type_to_openapi_type(str | None)
        assert result == {"type": "string", "nullable": True}

        result = python_type_to_openapi_type(int | None)
        assert result == {"type": "integer", "nullable": True}

    def test_unknown_types(self):
        """Test handling of unknown types."""

        class CustomType:
            pass

        result = python_type_to_openapi_type(CustomType)
        assert result == {"type": "string"}


class TestFunctionSchemaExtraction:
    """Test schema extraction from Python functions."""

    def test_simple_function(self):
        """Test schema extraction from simple function."""

        def sample_function(name: str, age: int) -> dict:
            """Sample function for testing.

            Args:
                name: Person's name
                age: Person's age

            Returns:
                Dictionary with person info
            """
            return {"name": name, "age": age}

        schema = extract_function_schema(sample_function)

        assert schema.name == "sample_function"
        assert "Sample function for testing" in schema.description

        # Check parameters schema
        params = schema.parameters_schema
        assert params["type"] == "object"
        assert "name" in params["properties"]
        assert "age" in params["properties"]
        assert params["properties"]["name"]["type"] == "string"
        assert params["properties"]["age"]["type"] == "integer"
        assert set(params["required"]) == {"name", "age"}

    def test_function_with_optional_params(self):
        """Test function with optional parameters."""

        def optional_function(required: str, optional: int = 10) -> str:
            """Function with optional parameter."""
            return f"{required}: {optional}"

        schema = extract_function_schema(optional_function)

        params = schema.parameters_schema
        assert "required" in params["properties"]
        assert "optional" in params["properties"]
        assert params["required"] == ["required"]  # Only required param

    def test_function_without_type_hints(self):
        """Test function without type hints."""

        def no_hints_function(param1, param2):
            """Function without type hints."""
            return {"param1": param1, "param2": param2}

        schema = extract_function_schema(no_hints_function)

        params = schema.parameters_schema
        assert params["properties"]["param1"]["type"] == "string"
        assert params["properties"]["param2"]["type"] == "string"

    def test_weather_tools_schema_extraction(self):
        """Test schema extraction from actual weather tools."""
        from src.strands_location_service_weather.location_weather import (
            get_alerts,
            get_weather,
        )

        # Test get_weather schema
        weather_schema = extract_function_schema(get_weather)
        assert weather_schema.name == "get_weather"
        assert "latitude" in weather_schema.parameters_schema["properties"]
        assert "longitude" in weather_schema.parameters_schema["properties"]
        assert (
            weather_schema.parameters_schema["properties"]["latitude"]["type"]
            == "number"
        )
        assert (
            weather_schema.parameters_schema["properties"]["longitude"]["type"]
            == "number"
        )

        # Test get_alerts schema
        alerts_schema = extract_function_schema(get_alerts)
        assert alerts_schema.name == "get_alerts"
        assert "latitude" in alerts_schema.parameters_schema["properties"]
        assert "longitude" in alerts_schema.parameters_schema["properties"]


class TestOpenAPISchemaGeneration:
    """Test OpenAPI schema generation."""

    def test_generate_schema_for_tool(self):
        """Test generating schema for a single tool."""

        def test_tool(param1: str, param2: int = 5) -> dict:
            """Test tool function."""
            return {"result": f"{param1}_{param2}"}

        schema = generate_openapi_schema_for_tool(test_tool)

        assert "parameters_schema" in schema
        assert "return_schema" in schema
        assert "description" in schema

        params = schema["parameters_schema"]
        assert params["type"] == "object"
        assert "param1" in params["properties"]
        assert "param2" in params["properties"]
        assert params["required"] == ["param1"]

    def test_create_action_group_schema(self):
        """Test creating complete action group schema."""

        def tool1(x: int) -> str:
            """First tool."""
            return str(x)

        def tool2(y: str, z: bool = True) -> dict:
            """Second tool."""
            return {"y": y, "z": z}

        schema = create_action_group_schema(
            action_group_name="test_group",
            tools=[tool1, tool2],
            title="Test API",
            description="Test action group",
        )

        # Check basic structure
        assert schema.openapi == "3.0.0"
        assert schema.info["title"] == "Test API"
        assert schema.info["description"] == "Test action group"

        # Check paths
        assert "/tool1" in schema.paths
        assert "/tool2" in schema.paths

        # Check tool1 path
        tool1_path = schema.paths["/tool1"]["post"]
        assert tool1_path["operationId"] == "tool1"
        assert "requestBody" in tool1_path
        assert "responses" in tool1_path

        # Check request body schema
        request_schema = tool1_path["requestBody"]["content"]["application/json"][
            "schema"
        ]
        assert request_schema["type"] == "object"
        assert "x" in request_schema["properties"]
        assert request_schema["properties"]["x"]["type"] == "integer"

    def test_weather_action_group_schema(self):
        """Test weather action group schema generation."""
        schema = create_weather_action_group_schema()

        # Check basic structure
        assert schema["openapi"] == "3.0.0"
        assert "Weather Services API" in schema["info"]["title"]
        assert "paths" in schema

        # Check for weather tools
        expected_paths = ["/get_weather", "/get_alerts", "/current_time"]
        for path in expected_paths:
            assert path in schema["paths"], f"Missing path: {path}"

        # Check get_weather operation
        get_weather_op = schema["paths"]["/get_weather"]["post"]
        assert get_weather_op["operationId"] == "get_weather"

        # Check parameters
        request_schema = get_weather_op["requestBody"]["content"]["application/json"][
            "schema"
        ]
        assert "latitude" in request_schema["properties"]
        assert "longitude" in request_schema["properties"]
        assert request_schema["properties"]["latitude"]["type"] == "number"
        assert request_schema["properties"]["longitude"]["type"] == "number"
        assert set(request_schema["required"]) == {"latitude", "longitude"}

    def test_location_action_group_schema(self):
        """Test location action group schema generation."""
        schema = create_location_action_group_schema()

        # Check basic structure
        assert schema["openapi"] == "3.0.0"
        assert "Location Services API" in schema["info"]["title"]
        assert "paths" in schema

        # Check for location operations
        expected_paths = ["/search_places", "/calculate_route"]
        for path in expected_paths:
            assert path in schema["paths"], f"Missing path: {path}"

        # Check search_places operation
        search_op = schema["paths"]["/search_places"]["post"]
        assert search_op["operationId"] == "search_places"

        # Check parameters
        request_schema = search_op["requestBody"]["content"]["application/json"][
            "schema"
        ]
        assert "text" in request_schema["properties"]
        assert request_schema["required"] == ["text"]

    def test_get_all_action_group_schemas(self):
        """Test getting all action group schemas."""
        schemas = get_all_action_group_schemas()

        assert "weather_services" in schemas
        assert "location_services" in schemas

        # Verify each schema is valid OpenAPI
        for _name, schema in schemas.items():
            assert "openapi" in schema
            assert "info" in schema
            assert "paths" in schema
            assert schema["openapi"] == "3.0.0"


class TestSchemaValidation:
    """Test OpenAPI schema validation."""

    def test_validate_valid_schema(self):
        """Test validation of valid OpenAPI schema."""
        valid_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "Test API description",
            },
            "paths": {
                "/test": {
                    "post": {
                        "description": "Test operation",
                        "operationId": "test_op",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"param": {"type": "string"}},
                                        "required": ["param"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "result": {"type": "string"}
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }

        errors = validate_openapi_schema(valid_schema)
        assert len(errors) == 0

    def test_validate_invalid_schema(self):
        """Test validation of invalid OpenAPI schema."""
        invalid_schema = {
            "openapi": "2.0",  # Wrong version
            "info": {
                "title": "Test API"
                # Missing version
            },
            "paths": {
                "/test": {
                    "post": {
                        # Missing responses
                    }
                }
            },
        }

        errors = validate_openapi_schema(invalid_schema)
        assert len(errors) > 0

        # Check for specific errors
        error_messages = " ".join(errors)
        assert "version" in error_messages.lower()
        assert "responses" in error_messages.lower()

    def test_openapi_validator_class(self):
        """Test OpenAPIValidator class."""
        validator = OpenAPIValidator()

        # Test valid schema
        valid_schema = create_weather_action_group_schema()
        result = validator.validate_schema(valid_schema)

        assert isinstance(result, ValidationResult)
        assert result.valid
        assert result.schema_type == "openapi_3.0"
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_tool_schema_validator(self):
        """Test ToolSchemaValidator class."""
        validator = ToolSchemaValidator()

        # Valid tool schema
        params_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
            "required": ["param1"],
        }

        return_schema = {"type": "object", "properties": {"result": {"type": "string"}}}

        result = validator.validate_tool_schema(
            "test_tool", params_schema, return_schema
        )

        assert isinstance(result, ValidationResult)
        assert result.valid
        assert result.schema_type == "tool_schema"

    def test_validate_all_schemas(self):
        """Test validation of all generated schemas."""
        results = validate_all_schemas()

        assert isinstance(results, dict)
        assert "weather_services" in results
        assert "location_services" in results

        for name, result in results.items():
            assert isinstance(result, ValidationResult)
            # All generated schemas should be valid
            assert result.valid, f"Schema {name} should be valid: {result.errors}"

    def test_generate_validation_report(self):
        """Test validation report generation."""
        report = generate_validation_report()

        assert isinstance(report, str)
        assert "OpenAPI Schema Validation Report" in report
        assert "Summary" in report
        assert "Detailed Results" in report

        # Should contain schema names
        assert "weather_services" in report
        assert "location_services" in report


class TestSchemaExport:
    """Test schema export functionality."""

    def test_export_schemas_to_files(self, tmp_path):
        """Test exporting schemas to JSON files."""
        output_dir = str(tmp_path / "schemas")

        file_paths = export_schemas_to_files(output_dir)

        assert isinstance(file_paths, dict)
        assert "weather_action_group" in file_paths
        assert "location_action_group" in file_paths

        # Check that files were created
        for schema_name, file_path in file_paths.items():
            assert tmp_path / "schemas" / f"{schema_name}.json" in tmp_path.rglob(
                "*.json"
            )

            # Verify file content is valid JSON
            with open(file_path) as f:
                schema_data = json.load(f)
                assert "openapi" in schema_data
                assert "info" in schema_data
                assert "paths" in schema_data


class TestAgentCoreCompliance:
    """Test AgentCore-specific compliance requirements."""

    def test_weather_schema_agentcore_compliance(self):
        """Test weather schema compliance with AgentCore requirements."""
        schema = create_weather_action_group_schema()

        # Check OpenAPI 3.0 compliance
        assert schema["openapi"] == "3.0.0"

        # Check that all operations have operationId
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method.lower() == "post":
                    assert (
                        "operationId" in operation
                    ), f"Missing operationId in {method.upper()} {path}"

        # Check for JSON content types
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method.lower() == "post" and "requestBody" in operation:
                    content = operation["requestBody"]["content"]
                    assert (
                        "application/json" in content
                    ), f"Missing JSON content type in {method.upper()} {path}"

        # Check response structure
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method.lower() == "post":
                    responses = operation["responses"]
                    assert (
                        "200" in responses
                    ), f"Missing 200 response in {method.upper()} {path}"

                    success_response = responses["200"]
                    assert "content" in success_response
                    assert "application/json" in success_response["content"]

    def test_schema_validation_with_agentcore_config(self):
        """Test schema validation with AgentCore-specific configuration."""
        config = SchemaValidationConfig(
            strict_mode=True, require_descriptions=True, validate_references=True
        )

        validator = OpenAPIValidator(config)
        schema = create_weather_action_group_schema()

        result = validator.validate_schema(schema)

        # Should pass validation
        assert result.valid

        # May have warnings about AgentCore best practices
        if result.warnings:
            warning_text = " ".join(result.warnings)
            # Common AgentCore warnings
            assert any(
                keyword in warning_text.lower()
                for keyword in ["agentcore", "operation", "json", "post"]
            )


class TestErrorHandling:
    """Test error handling in schema generation."""

    def test_invalid_function_schema_extraction(self):
        """Test handling of invalid functions."""

        # Function that will cause issues
        def problematic_function():
            """Function with no parameters."""
            pass

        # Should not raise exception, but return minimal schema
        schema = generate_openapi_schema_for_tool(problematic_function)

        assert "parameters_schema" in schema
        assert "return_schema" in schema
        assert "description" in schema

    def test_schema_validation_error_handling(self):
        """Test error handling in schema validation."""
        # Completely invalid schema
        invalid_schema = "not a dictionary"

        validator = OpenAPIValidator()
        result = validator.validate_schema(invalid_schema)

        assert not result.valid
        assert len(result.errors) > 0

    def test_export_error_handling(self, tmp_path):
        """Test error handling in schema export."""
        # Try to export to invalid directory
        invalid_dir = str(tmp_path / "nonexistent" / "deeply" / "nested")

        # Should handle the error gracefully
        file_paths = export_schemas_to_files(invalid_dir)

        # Should still return a dictionary, even if empty
        assert isinstance(file_paths, dict)


if __name__ == "__main__":
    pytest.main([__file__])
