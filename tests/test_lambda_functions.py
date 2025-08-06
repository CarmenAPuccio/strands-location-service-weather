"""
Unit tests for Lambda function structure and organization.

This module tests the Lambda function organization and ensures the new
structure follows AWS best practices.
"""

from pathlib import Path

import pytest


class TestLambdaFunctionStructure:
    """Test the Lambda function directory structure."""

    def test_lambda_functions_directory_exists(self):
        """Test that the Lambda functions directory exists."""
        lambda_dir = (
            Path(__file__).parent.parent / "infrastructure" / "lambda_functions"
        )
        assert lambda_dir.exists(), "Lambda functions directory should exist"

    def test_shared_directory_exists(self):
        """Test that the shared directory exists."""
        shared_dir = (
            Path(__file__).parent.parent
            / "infrastructure"
            / "lambda_functions"
            / "shared"
        )
        assert shared_dir.exists(), "Shared Lambda code directory should exist"

    def test_weather_function_directory_exists(self):
        """Test that the weather function directory exists."""
        weather_dir = (
            Path(__file__).parent.parent
            / "infrastructure"
            / "lambda_functions"
            / "get_weather"
        )
        assert weather_dir.exists(), "Weather function directory should exist"

    def test_alerts_function_directory_exists(self):
        """Test that the alerts function directory exists."""
        alerts_dir = (
            Path(__file__).parent.parent
            / "infrastructure"
            / "lambda_functions"
            / "get_alerts"
        )
        assert alerts_dir.exists(), "Alerts function directory should exist"

    def test_shared_files_exist(self):
        """Test that required shared files exist."""
        shared_dir = (
            Path(__file__).parent.parent
            / "infrastructure"
            / "lambda_functions"
            / "shared"
        )

        lambda_handler_file = shared_dir / "lambda_handler.py"
        assert (
            lambda_handler_file.exists()
        ), "lambda_handler.py should exist in shared directory"

        weather_tools_file = shared_dir / "weather_tools.py"
        assert (
            weather_tools_file.exists()
        ), "weather_tools.py should exist in shared directory"

    def test_function_entry_points_exist(self):
        """Test that function entry points exist."""
        lambda_functions_dir = (
            Path(__file__).parent.parent / "infrastructure" / "lambda_functions"
        )

        weather_entry = lambda_functions_dir / "get_weather" / "lambda_function.py"
        assert weather_entry.exists(), "Weather function entry point should exist"

        alerts_entry = lambda_functions_dir / "get_alerts" / "lambda_function.py"
        assert alerts_entry.exists(), "Alerts function entry point should exist"


class TestLambdaFunctionImports:
    """Test that Lambda functions can be imported correctly."""

    def test_shared_lambda_handler_imports(self):
        """Test that shared Lambda handler can be imported."""
        import sys
        from pathlib import Path

        # Add shared directory to path
        shared_dir = (
            Path(__file__).parent.parent
            / "infrastructure"
            / "lambda_functions"
            / "shared"
        )
        sys.path.insert(0, str(shared_dir))

        try:
            # Test importing key functions
            from lambda_handler import (
                format_agentcore_response,
                initialize_lambda_environment,
                lambda_error_handler,
                parse_agentcore_event,
            )

            # Verify functions are callable
            assert callable(parse_agentcore_event)
            assert callable(format_agentcore_response)
            assert callable(lambda_error_handler)
            assert callable(initialize_lambda_environment)

        except ImportError as e:
            pytest.fail(f"Failed to import shared Lambda handler: {e}")
        finally:
            # Clean up path
            if str(shared_dir) in sys.path:
                sys.path.remove(str(shared_dir))

    def test_weather_tools_imports(self):
        """Test that weather tools can be imported."""
        import sys
        from pathlib import Path

        # Add shared directory to path
        shared_dir = (
            Path(__file__).parent.parent
            / "infrastructure"
            / "lambda_functions"
            / "shared"
        )
        sys.path.insert(0, str(shared_dir))

        try:
            from weather_tools import get_alerts_handler, get_weather_handler

            # Verify handlers are callable
            assert callable(get_weather_handler)
            assert callable(get_alerts_handler)

        except ImportError as e:
            pytest.fail(f"Failed to import weather tools: {e}")
        finally:
            # Clean up path
            if str(shared_dir) in sys.path:
                sys.path.remove(str(shared_dir))


class TestLambdaFunctionSeparation:
    """Test that Lambda functions are properly separated from application code."""

    def test_no_lambda_files_in_src(self):
        """Test that Lambda-specific files are not in the src directory."""
        src_dir = (
            Path(__file__).parent.parent / "src" / "strands_location_service_weather"
        )

        # These files should NOT exist in src anymore
        lambda_files = [
            "lambda_handler.py",
            "lambda_get_weather.py",
            "lambda_get_alerts.py",
        ]

        for filename in lambda_files:
            file_path = src_dir / filename
            assert (
                not file_path.exists()
            ), f"{filename} should not exist in src directory"

    def test_application_files_still_in_src(self):
        """Test that application files are still in the src directory."""
        src_dir = (
            Path(__file__).parent.parent / "src" / "strands_location_service_weather"
        )

        # These files should still exist in src
        app_files = ["location_weather.py", "config.py", "main.py", "mcp_server.py"]

        for filename in app_files:
            file_path = src_dir / filename
            assert file_path.exists(), f"{filename} should exist in src directory"
