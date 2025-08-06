#!/usr/bin/env python3
"""
CLI utility for OpenAPI schema generation and validation.

This script provides command-line tools for generating, validating, and exporting
OpenAPI 3.0 schemas for AgentCore action groups.
"""

import argparse
import json
import logging
import sys
from typing import Any

from .openapi_schemas import (
    export_schemas_to_files,
    get_all_action_group_schemas,
)
from .schema_validation import (
    OpenAPIValidator,
    generate_validation_report,
    validate_all_schemas,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_schemas(
    output_format: str = "json", output_dir: str = None
) -> dict[str, Any]:
    """Generate all OpenAPI schemas.

    Args:
        output_format: Output format ('json' or 'yaml')
        output_dir: Directory to save schemas (optional)

    Returns:
        Dictionary of generated schemas
    """
    logger.info("Generating OpenAPI schemas for action groups")

    schemas = get_all_action_group_schemas()

    if output_dir:
        logger.info(f"Exporting schemas to {output_dir}")
        file_paths = export_schemas_to_files(output_dir)

        for schema_name, file_path in file_paths.items():
            logger.info(f"✓ Exported {schema_name} to {file_path}")

    return schemas


def validate_schemas(verbose: bool = False) -> bool:
    """Validate all generated schemas.

    Args:
        verbose: Whether to show detailed validation results

    Returns:
        True if all schemas are valid, False otherwise
    """
    logger.info("Validating OpenAPI schemas")

    results = validate_all_schemas()

    all_valid = True
    for schema_name, result in results.items():
        if result.valid:
            logger.info(f"✓ {schema_name}: VALID")
            if verbose and result.warnings:
                for warning in result.warnings:
                    logger.warning(f"  ⚠ {warning}")
        else:
            logger.error(f"✗ {schema_name}: INVALID")
            all_valid = False
            for error in result.errors:
                logger.error(f"  ✗ {error}")
            if verbose and result.warnings:
                for warning in result.warnings:
                    logger.warning(f"  ⚠ {warning}")

    return all_valid


def generate_report(output_file: str = None) -> str:
    """Generate validation report.

    Args:
        output_file: File to save report to (optional)

    Returns:
        Report content as string
    """
    logger.info("Generating validation report")

    report = generate_validation_report()

    if output_file:
        with open(output_file, "w") as f:
            f.write(report)
        logger.info(f"Report saved to {output_file}")

    return report


def show_schema(schema_name: str, pretty: bool = True) -> None:
    """Show a specific schema.

    Args:
        schema_name: Name of schema to show
        pretty: Whether to pretty-print JSON
    """
    schemas = get_all_action_group_schemas()

    if schema_name not in schemas:
        logger.error(
            f"Schema '{schema_name}' not found. Available schemas: {list(schemas.keys())}"
        )
        return

    schema = schemas[schema_name]

    if pretty:
        print(json.dumps(schema, indent=2))
    else:
        print(json.dumps(schema))


def list_schemas() -> None:
    """List all available schemas."""
    schemas = get_all_action_group_schemas()

    print("Available OpenAPI schemas:")
    for schema_name, schema in schemas.items():
        info = schema.get("info", {})
        title = info.get("title", "Unknown")
        version = info.get("version", "Unknown")
        description = info.get("description", "No description")

        print(f"  {schema_name}:")
        print(f"    Title: {title}")
        print(f"    Version: {version}")
        print(f"    Description: {description}")

        # Count paths
        paths = schema.get("paths", {})
        print(f"    Operations: {len(paths)}")
        print()


def validate_file(file_path: str, verbose: bool = False) -> bool:
    """Validate a specific OpenAPI schema file.

    Args:
        file_path: Path to schema file
        verbose: Whether to show detailed results

    Returns:
        True if valid, False otherwise
    """
    logger.info(f"Validating schema file: {file_path}")

    try:
        with open(file_path) as f:
            schema = json.load(f)

        validator = OpenAPIValidator()
        result = validator.validate_schema(schema)

        if result.valid:
            logger.info(f"✓ {file_path}: VALID")
            if verbose and result.warnings:
                for warning in result.warnings:
                    logger.warning(f"  ⚠ {warning}")
            return True
        else:
            logger.error(f"✗ {file_path}: INVALID")
            for error in result.errors:
                logger.error(f"  ✗ {error}")
            if verbose and result.warnings:
                for warning in result.warnings:
                    logger.warning(f"  ⚠ {warning}")
            return False

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating {file_path}: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OpenAPI schema generation and validation for AgentCore action groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all schemas and save to directory
  python -m strands_location_service_weather.schema_cli generate --output-dir ./schemas

  # Validate all generated schemas
  python -m strands_location_service_weather.schema_cli validate --verbose

  # Show a specific schema
  python -m strands_location_service_weather.schema_cli show weather_services

  # Generate validation report
  python -m strands_location_service_weather.schema_cli report --output validation_report.md

  # List all available schemas
  python -m strands_location_service_weather.schema_cli list

  # Validate a specific file
  python -m strands_location_service_weather.schema_cli validate-file ./schemas/weather_action_group.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate OpenAPI schemas")
    generate_parser.add_argument(
        "--output-dir", "-o", help="Directory to save schema files"
    )
    generate_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)",
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate all schemas")
    validate_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation results"
    )

    # Show command
    show_parser = subparsers.add_parser("show", help="Show a specific schema")
    show_parser.add_argument("schema_name", help="Name of schema to show")
    show_parser.add_argument(
        "--compact",
        "-c",
        action="store_true",
        help="Show compact JSON (no pretty printing)",
    )

    # List command
    subparsers.add_parser("list", help="List all available schemas")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate validation report")
    report_parser.add_argument("--output", "-o", help="File to save report to")

    # Validate file command
    validate_file_parser = subparsers.add_parser(
        "validate-file", help="Validate a specific schema file"
    )
    validate_file_parser.add_argument("file_path", help="Path to schema file")
    validate_file_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation results"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "generate":
            schemas = generate_schemas(
                output_format=args.format, output_dir=args.output_dir
            )

            if not args.output_dir:
                # Print schema names if not saving to files
                print("Generated schemas:")
                for name in schemas.keys():
                    print(f"  - {name}")

        elif args.command == "validate":
            success = validate_schemas(verbose=args.verbose)
            if not success:
                sys.exit(1)

        elif args.command == "show":
            show_schema(args.schema_name, pretty=not args.compact)

        elif args.command == "list":
            list_schemas()

        elif args.command == "report":
            report = generate_report(output_file=args.output)
            if not args.output:
                print(report)

        elif args.command == "validate-file":
            success = validate_file(args.file_path, verbose=args.verbose)
            if not success:
                sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
