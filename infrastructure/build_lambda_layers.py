#!/usr/bin/env python3
"""
Build script for Lambda layers following AWS best practices.

This script creates Lambda layers for dependencies and shared code,
following the AWS Lambda layers directory structure.
"""

import shutil
import subprocess
from pathlib import Path


def build_dependencies_layer():
    """Build the dependencies layer with Python packages."""
    print("Building dependencies layer...")

    # Paths
    script_dir = Path(__file__).parent
    layer_dir = (
        script_dir
        / "layers"
        / "dependencies"
        / "python"
        / "lib"
        / "python3.11"
        / "site-packages"
    )
    requirements_file = script_dir / "lambda_functions" / "shared" / "requirements.txt"

    # Clean existing layer
    if layer_dir.exists():
        shutil.rmtree(layer_dir)
    layer_dir.mkdir(parents=True, exist_ok=True)

    # Install dependencies using uv
    if requirements_file.exists():
        print(f"  Installing dependencies from {requirements_file}")
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "-r",
                str(requirements_file),
                "--target",
                str(layer_dir),
                "--upgrade",
            ],
            check=True,
        )
        print(f"  Dependencies installed to {layer_dir}")
    else:
        print(f"  Warning: {requirements_file} not found")

    print("  Dependencies layer built successfully")


def build_shared_code_layer():
    """Build the shared code layer with common Lambda code."""
    print("Building shared code layer...")

    # Paths
    script_dir = Path(__file__).parent
    layer_dir = script_dir / "layers" / "shared-code" / "python"
    shared_dir = script_dir / "lambda_functions" / "shared"
    src_dir = script_dir.parent / "src" / "strands_location_service_weather"

    # Clean existing layer
    if layer_dir.exists():
        shutil.rmtree(layer_dir)
    layer_dir.mkdir(parents=True, exist_ok=True)

    # Copy shared Lambda code
    if shared_dir.exists():
        for file in shared_dir.glob("*.py"):
            shutil.copy2(file, layer_dir / file.name)
            print(f"  Copied shared file: {file.name}")

    # Copy source code modules
    if src_dir.exists():
        # Create src directory structure in layer
        layer_src_dir = layer_dir / "src" / "strands_location_service_weather"
        layer_src_dir.mkdir(parents=True, exist_ok=True)

        # Copy specific modules needed by Lambda functions
        modules_to_copy = ["config.py", "error_handling.py", "__init__.py"]

        for module in modules_to_copy:
            module_file = src_dir / module
            if module_file.exists():
                shutil.copy2(module_file, layer_src_dir / module)
                print(f"  Copied source module: {module}")

    print("  Shared code layer built successfully")


def main():
    """Main build function."""
    print("Building Lambda layers...")

    # Build layers
    build_dependencies_layer()
    build_shared_code_layer()

    print("\nLambda layers built successfully!")
    print("Layers:")
    print("  - infrastructure/layers/dependencies/")
    print("  - infrastructure/layers/shared-code/")
    print("\nLambda functions are in:")
    print("  - infrastructure/lambda_functions/")


if __name__ == "__main__":
    main()
