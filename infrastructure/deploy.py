#!/usr/bin/env python3
"""
CDK deployment automation script for AgentCore weather tools.

This script follows AWS CDK best practices for Python project deployment,
handling Lambda packaging and CDK deployment in a structured way.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


class CDKDeploymentManager:
    """Manages CDK deployment for AgentCore weather tools."""

    def __init__(self, infrastructure_dir: Path = None):
        """Initialize the deployment manager."""
        self.infrastructure_dir = infrastructure_dir or Path(__file__).parent
        self.project_root = self.infrastructure_dir.parent
        self.source_dir = self.project_root / "src" / "strands_location_service_weather"

    def package_lambda_functions(self) -> Path:
        """Package Lambda functions for deployment."""
        print("Packaging Lambda functions...")

        # Create lambda-packages directory in infrastructure
        packages_dir = self.infrastructure_dir / "lambda-packages"
        if packages_dir.exists():
            shutil.rmtree(packages_dir)
        packages_dir.mkdir()

        # Package weather function
        weather_dir = packages_dir / "get-weather"
        weather_dir.mkdir()
        self._package_function("weather", weather_dir)

        # Package alerts function
        alerts_dir = packages_dir / "get-alerts"
        alerts_dir.mkdir()
        self._package_function("alerts", alerts_dir)

        print(f"Lambda packages created in {packages_dir}")
        return packages_dir

    def _package_function(self, function_type: str, target_dir: Path):
        """Package a single Lambda function."""
        # Copy shared Lambda code
        shared_source = self.infrastructure_dir / "lambda_functions" / "shared"
        shutil.copy2(shared_source / "lambda_handler.py", target_dir)
        shutil.copy2(shared_source / "weather_tools.py", target_dir)

        # Copy function-specific entry point
        if function_type == "weather":
            function_source = (
                self.infrastructure_dir / "lambda_functions" / "get_weather"
            )
            shutil.copy2(function_source / "lambda_function.py", target_dir)
        elif function_type == "alerts":
            function_source = (
                self.infrastructure_dir / "lambda_functions" / "get_alerts"
            )
            shutil.copy2(function_source / "lambda_function.py", target_dir)

        # Install dependencies
        requirements = [
            "requests",
            "opentelemetry-api",
            "opentelemetry-sdk",
            "opentelemetry-exporter-otlp-proto-grpc",
            "opentelemetry-instrumentation-requests",
        ]

        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                str(target_dir),
                "--no-deps",
                *requirements,
            ],
            check=True,
            capture_output=True,
        )

    def install_cdk_dependencies(self):
        """Install CDK Python dependencies."""
        print("Installing CDK dependencies...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(self.infrastructure_dir / "requirements.txt"),
            ],
            check=True,
        )

    def run_cdk_command(
        self, command: list[str], env_vars: dict[str, str] = None
    ) -> subprocess.CompletedProcess:
        """Run a CDK command with proper environment setup."""
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        print(f"Running: {' '.join(command)}")
        return subprocess.run(
            command,
            cwd=self.infrastructure_dir,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def bootstrap_cdk(self, env_vars: dict[str, str] = None):
        """Bootstrap CDK environment if needed."""
        try:
            self.run_cdk_command(["cdk", "bootstrap"], env_vars)
            print("CDK bootstrap completed")
        except subprocess.CalledProcessError as e:
            if "is already bootstrapped" in e.stderr:
                print("CDK environment already bootstrapped")
            else:
                print(f"CDK bootstrap warning: {e.stderr}")

    def synthesize_stack(self, env_vars: dict[str, str] = None):
        """Synthesize CDK stack."""
        print("Synthesizing CDK stack...")
        result = self.run_cdk_command(["cdk", "synth"], env_vars)
        print("CDK synthesis completed")
        return result

    def deploy_stack(self, auto_approve: bool = False, env_vars: dict[str, str] = None):
        """Deploy CDK stack."""
        print("Deploying CDK stack...")

        deploy_cmd = ["cdk", "deploy"]
        if auto_approve:
            deploy_cmd.append("--require-approval=never")

        result = self.run_cdk_command(deploy_cmd, env_vars)
        print("CDK deployment completed")
        return result

    def destroy_stack(
        self, auto_approve: bool = False, env_vars: dict[str, str] = None
    ):
        """Destroy CDK stack."""
        print("Destroying CDK stack...")

        destroy_cmd = ["cdk", "destroy"]
        if auto_approve:
            destroy_cmd.append("--force")

        result = self.run_cdk_command(destroy_cmd, env_vars)
        print("CDK stack destroyed")
        return result

    def export_schemas(self, output_dir: Path = None):
        """Export OpenAPI schemas for reference."""
        if output_dir is None:
            output_dir = self.infrastructure_dir / "schemas"

        output_dir.mkdir(exist_ok=True)

        # Import and export schemas
        import sys

        sys.path.insert(0, str(self.source_dir))

        try:
            import json

            from agentcore_schemas import (
                get_alerts_action_group_schema,
                get_weather_action_group_schema,
            )

            with open(output_dir / "weather-schema.json", "w") as f:
                json.dump(get_weather_action_group_schema(), f, indent=2)

            with open(output_dir / "alerts-schema.json", "w") as f:
                json.dump(get_alerts_action_group_schema(), f, indent=2)

            print(f"Schemas exported to {output_dir}")

        except ImportError as e:
            print(f"Warning: Could not export schemas: {e}")

    def full_deployment(
        self,
        function_prefix: str = "agentcore-weather",
        weather_api_timeout: int = 10,
        otlp_endpoint: str = "",
        log_retention_days: int = 14,
        auto_approve: bool = False,
        region: str = "us-east-1",
        profile: str = None,
    ) -> dict[str, str]:
        """Perform full deployment process."""
        # Set up environment variables
        env_vars = {
            "FUNCTION_PREFIX": function_prefix,
            "WEATHER_API_TIMEOUT": str(weather_api_timeout),
            "OTEL_EXPORTER_OTLP_ENDPOINT": otlp_endpoint,
            "LOG_RETENTION_DAYS": str(log_retention_days),
            "CDK_DEFAULT_REGION": region,
            "AWS_REGION": region,
        }

        if profile:
            env_vars["AWS_PROFILE"] = profile

        # Package Lambda functions
        self.package_lambda_functions()

        # Install CDK dependencies
        self.install_cdk_dependencies()

        # Export schemas for reference
        self.export_schemas()

        # Bootstrap CDK
        self.bootstrap_cdk(env_vars)

        # Synthesize stack
        self.synthesize_stack(env_vars)

        # Deploy stack
        self.deploy_stack(auto_approve, env_vars)

        return {
            "status": "success",
            "stack_name": "LocationWeatherAgentCore",
            "region": region,
        }


def main():
    """Main deployment script."""
    parser = argparse.ArgumentParser(
        description="Deploy AgentCore weather tools using CDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic deployment
  python deploy.py

  # Custom configuration
  python deploy.py --function-prefix my-weather --region us-west-2 --auto-approve

  # Destroy stack
  python deploy.py --destroy --auto-approve

  # Export schemas only
  python deploy.py --schemas-only
        """,
    )

    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile name")
    parser.add_argument(
        "--function-prefix",
        default="agentcore-weather",
        help="Prefix for function names",
    )
    parser.add_argument(
        "--weather-api-timeout",
        type=int,
        default=10,
        help="Weather API timeout in seconds",
    )
    parser.add_argument(
        "--otlp-endpoint", default="", help="OpenTelemetry OTLP endpoint"
    )
    parser.add_argument(
        "--log-retention-days",
        type=int,
        default=14,
        help="CloudWatch log retention in days",
    )
    parser.add_argument(
        "--auto-approve", action="store_true", help="Auto-approve CDK operations"
    )
    parser.add_argument(
        "--destroy", action="store_true", help="Destroy the stack instead of deploying"
    )
    parser.add_argument(
        "--schemas-only",
        action="store_true",
        help="Export schemas only, skip deployment",
    )

    args = parser.parse_args()

    try:
        manager = CDKDeploymentManager()

        if args.schemas_only:
            manager.export_schemas()
            print("\n" + "=" * 60)
            print("SCHEMA EXPORT COMPLETE")
            print("=" * 60)

        elif args.destroy:
            env_vars = {
                "CDK_DEFAULT_REGION": args.region,
                "AWS_REGION": args.region,
            }
            if args.profile:
                env_vars["AWS_PROFILE"] = args.profile

            manager.destroy_stack(args.auto_approve, env_vars)
            print("\n" + "=" * 60)
            print("STACK DESTRUCTION COMPLETE")
            print("=" * 60)

        else:
            result = manager.full_deployment(
                function_prefix=args.function_prefix,
                weather_api_timeout=args.weather_api_timeout,
                otlp_endpoint=args.otlp_endpoint,
                log_retention_days=args.log_retention_days,
                auto_approve=args.auto_approve,
                region=args.region,
                profile=args.profile,
            )

            print("\n" + "=" * 60)
            print("DEPLOYMENT COMPLETE")
            print("=" * 60)
            print(f"Stack: {result['stack_name']}")
            print(f"Region: {result['region']}")
            print(f"Status: {result['status']}")

            print("\nNext steps:")
            print("1. Test the deployed agent in AWS Console")
            print("2. Monitor CloudWatch logs and metrics")
            print("3. Configure application to use AgentCore mode")
            print("4. Set up additional monitoring and alerting")

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}", file=sys.stderr)
        if e.stdout:
            print(f"stdout: {e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Deployment failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
