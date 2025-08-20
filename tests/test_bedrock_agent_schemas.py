"""
Unit tests for Bedrock Agent OpenAPI schemas.

This module tests the OpenAPI schema generation and validation for Bedrock Agent
action groups, ensuring they meet the requirements for proper tool integration.
"""

from src.strands_location_service_weather.bedrock_agent_schemas import (
    get_alerts_action_group_schema,
    get_combined_action_group_schema,
    get_weather_action_group_schema,
    validate_schema,
)


class TestWeatherActionGroupSchema:
    """Test weather action group OpenAPI schema."""

    def test_weather_schema_structure(self):
        """Test that weather schema has correct structure."""
        schema = get_weather_action_group_schema()

        # Check top-level structure
        assert schema["openapi"] == "3.0.0"
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema

        # Check info section
        assert schema["info"]["title"] == "Weather Services"
        assert schema["info"]["version"] == "1.0.0"
        assert "description" in schema["info"]

        # Check paths
        assert "/get_weather" in schema["paths"]
        weather_path = schema["paths"]["/get_weather"]
        assert "post" in weather_path

        # Check operation details
        post_op = weather_path["post"]
        assert post_op["operationId"] == "get_weather"
        assert "summary" in post_op
        assert "description" in post_op
        assert "requestBody" in post_op
        assert "responses" in post_op

    def test_weather_request_schema(self):
        """Test weather request body schema."""
        schema = get_weather_action_group_schema()
        request_body = schema["paths"]["/get_weather"]["post"]["requestBody"]

        assert request_body["required"] is True
        assert "application/json" in request_body["content"]

        json_schema = request_body["content"]["application/json"]["schema"]
        assert json_schema["type"] == "object"
        assert "latitude" in json_schema["properties"]
        assert "longitude" in json_schema["properties"]
        assert json_schema["required"] == ["latitude", "longitude"]
        assert json_schema["additionalProperties"] is False

        # Check parameter constraints
        lat_prop = json_schema["properties"]["latitude"]
        assert lat_prop["type"] == "number"
        assert lat_prop["minimum"] == -90
        assert lat_prop["maximum"] == 90

        lon_prop = json_schema["properties"]["longitude"]
        assert lon_prop["type"] == "number"
        assert lon_prop["minimum"] == -180
        assert lon_prop["maximum"] == 180

    def test_weather_response_schema(self):
        """Test weather response schema."""
        schema = get_weather_action_group_schema()
        responses = schema["paths"]["/get_weather"]["post"]["responses"]

        # Check success response
        assert "200" in responses
        success_response = responses["200"]
        assert "application/json" in success_response["content"]

        response_schema = success_response["content"]["application/json"]["schema"]
        assert response_schema["type"] == "object"

        # Check required fields
        required_fields = [
            "temperature",
            "windSpeed",
            "windDirection",
            "shortForecast",
            "detailedForecast",
            "success",
        ]
        assert set(response_schema["required"]) == set(required_fields)

        # Check temperature structure
        temp_prop = response_schema["properties"]["temperature"]
        assert temp_prop["type"] == "object"
        assert "value" in temp_prop["properties"]
        assert "unit" in temp_prop["properties"]

        # Check error responses
        assert "400" in responses
        assert "500" in responses

    def test_weather_error_schema(self):
        """Test weather error response schema."""
        schema = get_weather_action_group_schema()

        # Check components section has ErrorResponse
        assert "ErrorResponse" in schema["components"]["schemas"]
        error_schema = schema["components"]["schemas"]["ErrorResponse"]

        assert error_schema["type"] == "object"
        assert "error" in error_schema["properties"]
        assert "success" in error_schema["properties"]
        assert error_schema["required"] == ["error", "success"]

        # Check error_type enum
        error_type_prop = error_schema["properties"]["error_type"]
        expected_types = ["parameter_validation", "http_request", "internal_error"]
        assert error_type_prop["enum"] == expected_types


class TestAlertsActionGroupSchema:
    """Test alerts action group OpenAPI schema."""

    def test_alerts_schema_structure(self):
        """Test that alerts schema has correct structure."""
        schema = get_alerts_action_group_schema()

        # Check top-level structure
        assert schema["openapi"] == "3.0.0"
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema

        # Check info section
        assert schema["info"]["title"] == "Weather Alerts Services"
        assert schema["info"]["version"] == "1.0.0"

        # Check paths
        assert "/get_alerts" in schema["paths"]
        alerts_path = schema["paths"]["/get_alerts"]
        assert "post" in alerts_path

        # Check operation details
        post_op = alerts_path["post"]
        assert post_op["operationId"] == "get_alerts"
        assert "summary" in post_op
        assert "description" in post_op

    def test_alerts_request_schema(self):
        """Test alerts request body schema."""
        schema = get_alerts_action_group_schema()
        request_body = schema["paths"]["/get_alerts"]["post"]["requestBody"]

        assert request_body["required"] is True
        json_schema = request_body["content"]["application/json"]["schema"]

        # Should have same coordinate requirements as weather
        assert json_schema["type"] == "object"
        assert "latitude" in json_schema["properties"]
        assert "longitude" in json_schema["properties"]
        assert json_schema["required"] == ["latitude", "longitude"]
        assert json_schema["additionalProperties"] is False

    def test_alerts_response_schema(self):
        """Test alerts response schema."""
        schema = get_alerts_action_group_schema()
        responses = schema["paths"]["/get_alerts"]["post"]["responses"]

        # Check success response
        success_response = responses["200"]
        response_schema = success_response["content"]["application/json"]["schema"]

        # Check required fields
        required_fields = ["alerts", "alert_count", "success"]
        assert set(response_schema["required"]) == set(required_fields)

        # Check alerts array structure
        alerts_prop = response_schema["properties"]["alerts"]
        assert alerts_prop["type"] == "array"
        assert "items" in alerts_prop

        alert_item = alerts_prop["items"]
        assert alert_item["type"] == "object"

        # Check alert properties
        alert_props = alert_item["properties"]
        expected_props = [
            "event",
            "headline",
            "description",
            "severity",
            "urgency",
            "effective",
            "expires",
            "instruction",
            "message",
        ]
        for prop in expected_props:
            assert prop in alert_props

        # Check severity enum
        severity_prop = alert_props["severity"]
        expected_severities = ["Minor", "Moderate", "Severe", "Extreme"]
        assert severity_prop["enum"] == expected_severities

        # Check urgency enum
        urgency_prop = alert_props["urgency"]
        expected_urgencies = ["Past", "Future", "Expected", "Immediate"]
        assert urgency_prop["enum"] == expected_urgencies

        # Check alert_count
        count_prop = response_schema["properties"]["alert_count"]
        assert count_prop["type"] == "integer"
        assert count_prop["minimum"] == 0


class TestCombinedActionGroupSchema:
    """Test combined action group OpenAPI schema."""

    def test_combined_schema_structure(self):
        """Test that combined schema includes both tools."""
        schema = get_combined_action_group_schema()

        # Check top-level structure
        assert schema["openapi"] == "3.0.0"
        assert schema["info"]["title"] == "Weather and Alerts Services"

        # Check both paths are included
        assert "/get_weather" in schema["paths"]
        assert "/get_alerts" in schema["paths"]

        # Check that both operations are present
        weather_op = schema["paths"]["/get_weather"]["post"]
        alerts_op = schema["paths"]["/get_alerts"]["post"]

        assert weather_op["operationId"] == "get_weather"
        assert alerts_op["operationId"] == "get_alerts"

    def test_combined_schema_components(self):
        """Test that combined schema has shared components."""
        schema = get_combined_action_group_schema()

        # Should have shared ErrorResponse component
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "ErrorResponse" in schema["components"]["schemas"]

        error_schema = schema["components"]["schemas"]["ErrorResponse"]
        assert error_schema["type"] == "object"
        assert "error" in error_schema["properties"]


class TestSchemaValidation:
    """Test OpenAPI schema validation functionality."""

    def test_validate_valid_schema(self):
        """Test validation of a valid schema."""
        schema = get_weather_action_group_schema()
        errors = validate_schema(schema)

        assert errors == []

    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_schema = {
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
        }  # Missing openapi field

        errors = validate_schema(invalid_schema)

        assert len(errors) > 0
        assert any("Missing required field: openapi" in error for error in errors)

    def test_validate_wrong_openapi_version(self):
        """Test validation with wrong OpenAPI version."""
        invalid_schema = {
            "openapi": "2.0",  # Wrong version
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"/test": {"get": {}}},
        }

        errors = validate_schema(invalid_schema)

        assert len(errors) > 0
        assert any("OpenAPI version must be 3.0.x" in error for error in errors)

    def test_validate_missing_info_fields(self):
        """Test validation with missing info fields."""
        invalid_schema = {
            "openapi": "3.0.0",
            "info": {"version": "1.0.0"},  # Missing title
            "paths": {"/test": {"get": {}}},
        }

        errors = validate_schema(invalid_schema)

        assert len(errors) > 0
        assert any("Missing required field: info.title" in error for error in errors)

    def test_validate_empty_paths(self):
        """Test validation with empty paths."""
        invalid_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},  # Empty paths
        }

        errors = validate_schema(invalid_schema)

        assert len(errors) > 0
        assert any("Paths section cannot be empty" in error for error in errors)

    def test_validate_path_without_http_methods(self):
        """Test validation of path without HTTP methods."""
        invalid_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"/test": {"description": "Test path"}},  # No HTTP methods
        }

        errors = validate_schema(invalid_schema)

        assert len(errors) > 0
        assert any("must have at least one HTTP method" in error for error in errors)

    def test_validate_all_generated_schemas(self):
        """Test that all generated schemas are valid."""
        schemas = [
            get_weather_action_group_schema(),
            get_alerts_action_group_schema(),
            get_combined_action_group_schema(),
        ]

        for schema in schemas:
            errors = validate_schema(schema)
            assert errors == [], f"Schema validation failed: {errors}"


class TestSchemaConsistency:
    """Test consistency across different schemas."""

    def test_coordinate_parameters_consistency(self):
        """Test that coordinate parameters are consistent across schemas."""
        weather_schema = get_weather_action_group_schema()
        alerts_schema = get_alerts_action_group_schema()

        # Extract coordinate schemas
        weather_coords = weather_schema["paths"]["/get_weather"]["post"]["requestBody"][
            "content"
        ]["application/json"]["schema"]["properties"]
        alerts_coords = alerts_schema["paths"]["/get_alerts"]["post"]["requestBody"][
            "content"
        ]["application/json"]["schema"]["properties"]

        # Should be identical
        assert weather_coords["latitude"] == alerts_coords["latitude"]
        assert weather_coords["longitude"] == alerts_coords["longitude"]

    def test_error_response_consistency(self):
        """Test that error responses are consistent across schemas."""
        weather_schema = get_weather_action_group_schema()
        alerts_schema = get_alerts_action_group_schema()

        weather_error = weather_schema["components"]["schemas"]["ErrorResponse"]
        alerts_error = alerts_schema["components"]["schemas"]["ErrorResponse"]

        # Should be identical
        assert weather_error == alerts_error

    def test_response_status_codes_consistency(self):
        """Test that response status codes are consistent."""
        weather_schema = get_weather_action_group_schema()
        alerts_schema = get_alerts_action_group_schema()

        weather_responses = weather_schema["paths"]["/get_weather"]["post"]["responses"]
        alerts_responses = alerts_schema["paths"]["/get_alerts"]["post"]["responses"]

        # Should have same status codes
        assert set(weather_responses.keys()) == set(alerts_responses.keys())

        # Should have same error response structure for 400 and 500
        for status_code in ["400", "500"]:
            weather_error_ref = weather_responses[status_code]["content"][
                "application/json"
            ]["schema"]["$ref"]
            alerts_error_ref = alerts_responses[status_code]["content"][
                "application/json"
            ]["schema"]["$ref"]
            assert weather_error_ref == alerts_error_ref


class TestSchemaExamples:
    """Test that schema examples are valid."""

    def test_weather_request_example(self):
        """Test that weather request example matches schema."""
        schema = get_weather_action_group_schema()
        request_schema = schema["paths"]["/get_weather"]["post"]["requestBody"][
            "content"
        ]["application/json"]["schema"]

        # Check that examples are within valid ranges
        lat_example = request_schema["properties"]["latitude"]["example"]
        lon_example = request_schema["properties"]["longitude"]["example"]

        assert -90 <= lat_example <= 90
        assert -180 <= lon_example <= 180

    def test_alerts_request_example(self):
        """Test that alerts request example matches schema."""
        schema = get_alerts_action_group_schema()
        request_schema = schema["paths"]["/get_alerts"]["post"]["requestBody"][
            "content"
        ]["application/json"]["schema"]

        # Check that examples are within valid ranges
        lat_example = request_schema["properties"]["latitude"]["example"]
        lon_example = request_schema["properties"]["longitude"]["example"]

        assert -90 <= lat_example <= 90
        assert -180 <= lon_example <= 180


class TestSchemaDocumentation:
    """Test that schemas have proper documentation."""

    def test_weather_schema_documentation(self):
        """Test that weather schema has proper descriptions."""
        schema = get_weather_action_group_schema()

        # Check info description
        assert "description" in schema["info"]
        assert len(schema["info"]["description"]) > 0

        # Check operation description
        operation = schema["paths"]["/get_weather"]["post"]
        assert "summary" in operation
        assert "description" in operation
        assert len(operation["description"]) > 0

        # Check parameter descriptions
        properties = operation["requestBody"]["content"]["application/json"]["schema"][
            "properties"
        ]
        assert "description" in properties["latitude"]
        assert "description" in properties["longitude"]

    def test_alerts_schema_documentation(self):
        """Test that alerts schema has proper descriptions."""
        schema = get_alerts_action_group_schema()

        # Check info description
        assert "description" in schema["info"]
        assert len(schema["info"]["description"]) > 0

        # Check operation description
        operation = schema["paths"]["/get_alerts"]["post"]
        assert "summary" in operation
        assert "description" in operation
        assert len(operation["description"]) > 0

    def test_response_schema_documentation(self):
        """Test that response schemas have proper descriptions."""
        schema = get_weather_action_group_schema()
        response_schema = schema["paths"]["/get_weather"]["post"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]

        # Check that all properties have descriptions
        for prop_name, prop_schema in response_schema["properties"].items():
            assert (
                "description" in prop_schema
            ), f"Property {prop_name} missing description"
            assert len(prop_schema["description"]) > 0
