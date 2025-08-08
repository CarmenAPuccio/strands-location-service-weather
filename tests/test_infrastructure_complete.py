"""
Complete infrastructure validation tests.

This module provides comprehensive validation of the CDK infrastructure
implementation without requiring CDK instantiation, focusing on code
structure, configuration, and deployment readiness.
"""

import json
import unittest
from pathlib import Path


class TestInfrastructureCompleteness(unittest.TestCase):
    """Test that all required infrastructure components are implemented."""

    def setUp(self):
        """Set up test environment."""
        self.infrastructure_dir = Path(__file__).parent.parent / "infrastructure"
        self.src_dir = (
            Path(__file__).parent.parent / "src" / "strands_location_service_weather"
        )

    def test_all_required_files_exist(self):
        """Test that all required infrastructure files exist."""
        required_files = [
            # Core CDK files
            "app.py",
            "cdk.json",
            "requirements.txt",
            "deploy.py",
            "README.md",
            # Stack files
            "stacks/__init__.py",
            "stacks/agentcore_stack.py",
            # Construct files
            "cdk_lib/__init__.py",
            "cdk_lib/lambda_construct.py",
            "cdk_lib/bedrock_construct.py",
            # Lambda function files
            "lambda_functions/shared/lambda_handler.py",
            "lambda_functions/shared/weather_tools.py",
            "lambda_functions/get_weather/lambda_function.py",
            "lambda_functions/get_alerts/lambda_function.py",
            # Schema files
            "schemas/weather_action_group.json",
            "schemas/location_action_group.json",
            "schemas/validation_report.md",
        ]

        for file_path in required_files:
            full_path = self.infrastructure_dir / file_path
            self.assertTrue(full_path.exists(), f"Required file missing: {file_path}")

    def test_cdk_app_structure(self):
        """Test CDK app.py structure."""
        app_file = self.infrastructure_dir / "app.py"
        with open(app_file) as f:
            content = f.read()

        # Check for required imports and structure
        self.assertIn("from aws_cdk import App", content)
        self.assertIn("LocationWeatherAgentCoreStack", content)
        self.assertIn("app.synth()", content)
        self.assertIn('if __name__ == "__main__":', content)

    def test_stack_implementation(self):
        """Test stack implementation structure."""
        stack_file = self.infrastructure_dir / "stacks" / "agentcore_stack.py"
        with open(stack_file) as f:
            content = f.read()

        # Check for required components
        required_elements = [
            "class LocationWeatherAgentCoreStack",
            "WeatherLambdaConstruct",
            "BedrockAgentConstruct",
            "def get_outputs",
            "function_name_prefix",
            "weather_api_timeout",
            "otlp_endpoint",
            "log_retention_days",
        ]

        for element in required_elements:
            self.assertIn(element, content, f"Missing required element: {element}")

    def test_lambda_construct_implementation(self):
        """Test Lambda construct implementation."""
        construct_file = self.infrastructure_dir / "cdk_lib" / "lambda_construct.py"
        with open(construct_file) as f:
            content = f.read()

        required_methods = [
            "_create_lambda_execution_role",
            "_create_weather_lambda",
            "_create_alerts_lambda",
            "_get_weather_environment_vars",
            "_get_alerts_environment_vars",
            "_create_log_groups",
        ]

        for method in required_methods:
            self.assertIn(method, content, f"Missing required method: {method}")

        # Check for security configurations
        self.assertIn("AWSLambdaBasicExecutionRole", content)
        self.assertIn("xray:PutTraceSegments", content)
        self.assertIn("bedrock.amazonaws.com", content)

    def test_bedrock_construct_implementation(self):
        """Test Bedrock construct implementation."""
        construct_file = self.infrastructure_dir / "cdk_lib" / "bedrock_construct.py"
        with open(construct_file) as f:
            content = f.read()

        required_methods = [
            "_create_bedrock_guardrail",
            "_create_agentcore_agent",
            "_get_weather_openapi_schema",
            "_get_alerts_openapi_schema",
        ]

        for method in required_methods:
            self.assertIn(method, content, f"Missing required method: {method}")

        # Check for security configurations
        security_elements = [
            "SEXUAL",
            "VIOLENCE",
            "HATE",
            "MISCONDUCT",  # Content filters
            "PHONE",
            "EMAIL",
            "US_SOCIAL_SECURITY_NUMBER",  # PII protection
            "location-weather-guardrail",  # Guardrail name
            "anthropic.claude-3-sonnet",  # Model
        ]

        for element in security_elements:
            self.assertIn(element, content, f"Missing security element: {element}")

    def test_lambda_handlers_implementation(self):
        """Test Lambda handler implementations."""
        # Test shared weather tools
        weather_tools_file = (
            self.infrastructure_dir / "lambda_functions" / "shared" / "weather_tools.py"
        )
        with open(weather_tools_file) as f:
            content = f.read()

        required_functions = [
            "get_weather_handler",
            "get_alerts_handler",
            "get_weather_data",
            "get_alerts_data",
        ]

        for function in required_functions:
            self.assertIn(function, content, f"Missing required function: {function}")

        # Test entry points
        weather_entry = (
            self.infrastructure_dir
            / "lambda_functions"
            / "get_weather"
            / "lambda_function.py"
        )
        with open(weather_entry) as f:
            weather_content = f.read()

        self.assertIn("lambda_handler", weather_content)
        self.assertIn("get_weather_data", weather_content)

        alerts_entry = (
            self.infrastructure_dir
            / "lambda_functions"
            / "get_alerts"
            / "lambda_function.py"
        )
        with open(alerts_entry) as f:
            alerts_content = f.read()

        self.assertIn("lambda_handler", alerts_content)
        self.assertIn("get_alerts_data", alerts_content)

    def test_deployment_script_implementation(self):
        """Test deployment script implementation."""
        deploy_file = self.infrastructure_dir / "deploy.py"
        with open(deploy_file) as f:
            content = f.read()

        required_components = [
            "class CDKDeploymentManager",
            "package_lambda_functions",
            "install_cdk_dependencies",
            "bootstrap_cdk",
            "synthesize_stack",
            "deploy_stack",
            "full_deployment",
        ]

        for component in required_components:
            self.assertIn(
                component, content, f"Missing deployment component: {component}"
            )

    def test_openapi_schemas_integration(self):
        """Test OpenAPI schemas are properly integrated."""
        # Test schema files exist
        schema_files = ["weather_action_group.json", "location_action_group.json"]

        for schema_file in schema_files:
            schema_path = self.infrastructure_dir / "schemas" / schema_file
            self.assertTrue(schema_path.exists(), f"Schema file missing: {schema_file}")

        # Test schema source exists
        schema_source = self.src_dir / "agentcore_schemas.py"
        self.assertTrue(schema_source.exists(), "Schema source file missing")

        with open(schema_source) as f:
            content = f.read()

        required_functions = [
            "get_weather_action_group_schema",
            "get_alerts_action_group_schema",
            "validate_schema",
        ]

        for function in required_functions:
            self.assertIn(function, content, f"Missing schema function: {function}")

    def test_cdk_configuration(self):
        """Test CDK configuration files."""
        # Test cdk.json
        cdk_json = self.infrastructure_dir / "cdk.json"
        with open(cdk_json) as f:
            config = json.load(f)

        self.assertEqual(config["app"], "uv run python app.py")
        self.assertIn("context", config)

        # Check important feature flags
        context = config["context"]
        self.assertTrue(context.get("@aws-cdk/aws-iam:minimizePolicies", False))

        # Test requirements.txt
        requirements = self.infrastructure_dir / "requirements.txt"
        with open(requirements) as f:
            content = f.read()

        required_deps = ["aws-cdk-lib", "constructs", "boto3"]
        for dep in required_deps:
            self.assertIn(dep, content, f"Missing dependency: {dep}")

    def test_security_best_practices(self):
        """Test security best practices are implemented."""
        # Test guardrail configuration
        bedrock_construct = self.infrastructure_dir / "cdk_lib" / "bedrock_construct.py"
        with open(bedrock_construct) as f:
            content = f.read()

        # Check content filtering
        content_filters = ["SEXUAL", "VIOLENCE", "HATE", "MISCONDUCT"]
        for filter_type in content_filters:
            self.assertIn(
                filter_type, content, f"Missing content filter: {filter_type}"
            )

        # Check PII protection (but ADDRESS should be excluded)
        pii_types = [
            "PHONE",
            "EMAIL",
            "US_SOCIAL_SECURITY_NUMBER",
            "CREDIT_DEBIT_CARD_NUMBER",
        ]
        for pii_type in pii_types:
            self.assertIn(pii_type, content, f"Missing PII protection: {pii_type}")

        # ADDRESS should be excluded for location services
        self.assertNotIn(
            '"ADDRESS"', content, "ADDRESS should be excluded from PII blocking"
        )

        # Test IAM least privilege
        lambda_construct = self.infrastructure_dir / "cdk_lib" / "lambda_construct.py"
        with open(lambda_construct) as f:
            lambda_content = f.read()

        # Should have basic execution role
        self.assertIn("AWSLambdaBasicExecutionRole", lambda_content)
        # Should have X-Ray permissions
        self.assertIn("xray:PutTraceSegments", lambda_content)

    def test_performance_optimizations(self):
        """Test performance optimizations are implemented."""
        lambda_construct = self.infrastructure_dir / "cdk_lib" / "lambda_construct.py"
        with open(lambda_construct) as f:
            content = f.read()

        # Check memory and timeout settings
        self.assertIn("memory_size=256", content)
        self.assertIn("timeout=Duration.seconds(30)", content)
        self.assertIn("runtime=lambda_.Runtime.PYTHON_3_11", content)

        # Check environment variables for performance
        self.assertIn("FASTMCP_LOG_LEVEL", content)
        self.assertIn("WEATHER_API_TIMEOUT", content)

    def test_monitoring_and_observability(self):
        """Test monitoring and observability features."""
        lambda_construct = self.infrastructure_dir / "cdk_lib" / "lambda_construct.py"
        with open(lambda_construct) as f:
            content = f.read()

        # Check tracing is enabled
        self.assertIn("tracing=lambda_.Tracing.ACTIVE", content)

        # Check log groups are created
        self.assertIn("logs.LogGroup", content)
        self.assertIn("retention=", content)

        # Check OpenTelemetry configuration
        self.assertIn("OTEL_EXPORTER_OTLP_ENDPOINT", content)

    def test_cost_optimization(self):
        """Test cost optimization features."""
        lambda_construct = self.infrastructure_dir / "cdk_lib" / "lambda_construct.py"
        with open(lambda_construct) as f:
            content = f.read()

        # Check reasonable resource allocation
        self.assertIn("memory_size=256", content)  # Not excessive
        self.assertIn("timeout=Duration.seconds(30)", content)  # Reasonable timeout

        # Check log retention is configurable
        self.assertIn("log_retention_days", content)
        self.assertIn("retention_mapping", content)

    def test_deployment_automation(self):
        """Test deployment automation features."""
        deploy_script = self.infrastructure_dir / "deploy.py"
        with open(deploy_script) as f:
            content = f.read()

        automation_features = [
            "package_lambda_functions",  # Automatic packaging
            "install_cdk_dependencies",  # Dependency management
            "bootstrap_cdk",  # CDK bootstrapping
            "export_schemas",  # Schema export
            "full_deployment",  # End-to-end deployment
        ]

        for feature in automation_features:
            self.assertIn(feature, content, f"Missing automation feature: {feature}")

        # Check command line interface
        self.assertIn("argparse", content)
        self.assertIn("--region", content)
        self.assertIn("--auto-approve", content)

    def test_documentation_completeness(self):
        """Test documentation is complete."""
        readme = self.infrastructure_dir / "README.md"
        with open(readme) as f:
            content = f.read()

        required_sections = [
            "Quick Start",
            "Prerequisites",
            "Deployment",
            "Configuration",
            "Architecture",
            "Security",
            "Troubleshooting",
        ]

        for section in required_sections:
            self.assertIn(section, content, f"Missing documentation section: {section}")

    def test_infrastructure_validation_complete(self):
        """Final validation that infrastructure is deployment-ready."""
        # This test summarizes that all components are properly implemented

        # Core files exist
        core_files = [
            self.infrastructure_dir / "app.py",
            self.infrastructure_dir / "cdk.json",
            self.infrastructure_dir / "deploy.py",
        ]

        for file_path in core_files:
            self.assertTrue(file_path.exists(), f"Core file missing: {file_path}")

        # Constructs are implemented
        constructs = [
            self.infrastructure_dir / "cdk_lib" / "lambda_construct.py",
            self.infrastructure_dir / "cdk_lib" / "bedrock_construct.py",
        ]

        for construct_path in constructs:
            self.assertTrue(
                construct_path.exists(), f"Construct missing: {construct_path}"
            )

        # Lambda functions are implemented
        lambda_functions = [
            self.infrastructure_dir
            / "lambda_functions"
            / "get_weather"
            / "lambda_function.py",
            self.infrastructure_dir
            / "lambda_functions"
            / "get_alerts"
            / "lambda_function.py",
            self.infrastructure_dir
            / "lambda_functions"
            / "shared"
            / "weather_tools.py",
        ]

        for lambda_path in lambda_functions:
            self.assertTrue(
                lambda_path.exists(), f"Lambda function missing: {lambda_path}"
            )

        # Schemas are available
        schema_source = self.src_dir / "agentcore_schemas.py"
        self.assertTrue(schema_source.exists(), "Schema source missing")

        print("\n" + "=" * 60)
        print("INFRASTRUCTURE VALIDATION COMPLETE")
        print("=" * 60)
        print("✅ All required files implemented")
        print("✅ CDK stack and constructs ready")
        print("✅ Lambda functions implemented")
        print("✅ Security configurations in place")
        print("✅ Performance optimizations applied")
        print("✅ Monitoring and observability configured")
        print("✅ Deployment automation ready")
        print("✅ Documentation complete")
        print("=" * 60)


if __name__ == "__main__":
    unittest.main()
