# Strands Location Service Weather

[![CI](https://github.com/CarmenAPuccio/strands-location-service-weather/actions/workflows/ci.yml/badge.svg)](https://github.com/CarmenAPuccio/strands-location-service-weather/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This project combines Amazon Location Service MCP Server with weather data to provide location-based weather information using Amazon Bedrock for natural language processing.

## Features

- **Location Services**: Search for places, get coordinates, calculate routes using Amazon Location Service
- **Weather Data**: Current weather conditions and alerts from the National Weather Service
- **Natural Language Processing**: Powered by Amazon Bedrock (Claude 3 Sonnet)
- **MCP Server**: Compatible with Amazon Q CLI and other MCP clients using FastMCP
- **High Performance**: Optimized HTTP session reuse and streamlined processing (~18s response time)
- **Observability**: Full OpenTelemetry integration with tracing, logging, and metrics
- **Error Handling**: Robust error handling with graceful degradation
- **OpenAPI Schema Generation**: Automatic generation of OpenAPI 3.0 schemas for AgentCore action groups

## Architecture

The application uses a unified architecture where:

- MCP (Model Context Protocol) tools provide Amazon Location Service integration
- Custom weather tools fetch data from the National Weather Service API
- A single LocationWeatherClient class handles all Bedrock interactions
- OpenTelemetry provides comprehensive observability

## OpenTelemetry Observability

The application provides comprehensive observability through OpenTelemetry integration:

### Trace Structure

Each user interaction creates a hierarchical trace with the following spans:

- **user_interaction**: Top-level span for the entire request
  - **agent_interaction**: Agent processing and response generation
    - **bedrock_model_inference**: LLM inference with token usage metrics
      - **get_weather_api**: Weather data retrieval
        - **get_grid_points**: NWS grid point lookup
        - **get_forecast**: Weather forecast retrieval
      - **get_weather_alerts**: Weather alert checking
        - **get_zone_info**: Zone information lookup
        - **get_alerts_data**: Active alerts retrieval

### Captured Metrics

- **Token Usage**: Input tokens, output tokens, total tokens
- **Execution Time**: Total duration and cycle count
- **Tool Usage**: Tools used and tool count
- **HTTP Requests**: Status codes, URLs, response times
- **Weather Data**: Temperature, forecast conditions, alert counts

### Development Mode

Run with `DEVELOPMENT=true` to see detailed trace output including:

- JSON-formatted spans with trace IDs and timing
- HTTP request/response details
- Model inference metrics
- Tool execution flow

## Examples

Ask natural language questions like:

- "What's the weather in Seattle?"
- "Find coffee shops open now in Boston"
- "Route from Trenton to Philadelphia"
- "Places near 47.6062,-122.3321"
- "What's the weather in Trenton, NJ and are there any alerts?"
- "What's it like in Philadelphia?"

## Project Structure

The project follows Python packaging best practices with a `src/` layout:

```
├── src/
│   └── strands_location_service_weather/
│       ├── __init__.py
│       ├── main.py               # CLI entry point with OpenTelemetry setup
│       └── location_weather.py   # Core module with unified client and tools
├── pyproject.toml                # Modern Python project configuration
└── .kiro/steering/               # AI assistant guidance documents
```

## Installation & Setup

```bash
# Install dependencies
uv sync

# Install with development tools (Black, Ruff, pytest, coverage)
uv sync --extra dev
```

## AWS Permissions Setup

This application requires specific AWS permissions to access Amazon Bedrock and Amazon Location Service. The standard AWS managed policies are insufficient, so custom policies are required.

### Required Custom Policies

#### 1. Amazon Location Service Access

AWS doesn't provide a managed readonly policy for Location Service, so create this custom policy:

**Policy Name**: `AmazonLocationServiceReadOnlyAccess`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "geo:DescribeGeofenceCollection",
        "geo:DescribeMap",
        "geo:DescribePlaceIndex",
        "geo:DescribeRouteCalculator",
        "geo:DescribeTracker",
        "geo:GetDevicePosition",
        "geo:GetDevicePositionHistory",
        "geo:GetGeofence",
        "geo:GetMapGlyphs",
        "geo:GetMapSprites",
        "geo:GetMapStyleDescriptor",
        "geo:GetMapTile",
        "geo:ListDevicePositions",
        "geo:ListGeofenceCollections",
        "geo:ListGeofences",
        "geo:ListMaps",
        "geo:ListPlaceIndexes",
        "geo:ListRouteCalculators",
        "geo:ListTagsForResource",
        "geo:ListTrackerConsumers",
        "geo:ListTrackers",
        "geo:SearchPlaceIndexForPosition",
        "geo:SearchPlaceIndexForSuggestions",
        "geo:SearchPlaceIndexForText",
        "geo:CalculateRoute",
        "geo:CalculateRouteMatrix",
        "geo-maps:GetStaticMap",
        "geo-maps:GetTile",
        "geo-places:GetPlace",
        "geo-places:SearchNearby",
        "geo-places:SearchText",
        "geo-places:Suggest",
        "geo-places:ReverseGeocode",
        "geo-places:Geocode",
        "geo-routes:CalculateIsolines",
        "geo-routes:CalculateRoutes",
        "geo-routes:CalculateRouteMatrix"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 2. Amazon Bedrock Invoke Access

The managed `AmazonBedrockReadOnly` policy lacks model invocation permissions. Create this custom policy:

**Policy Name**: `AmazonBedrockInvokeAccess`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels",
        "bedrock:GetModelInvocationLoggingConfiguration",
        "bedrock:GetProvisionedModelThroughput",
        "bedrock:ListProvisionedModelThroughputs",
        "bedrock:GetModelCustomizationJob",
        "bedrock:ListModelCustomizationJobs",
        "bedrock:ListCustomModels",
        "bedrock:GetCustomModel",
        "bedrock:ListTagsForResource",
        "bedrock:GetFoundationModelAvailability"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockInvokeAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

### Important Notes

- **Amazon Location Service**: No AWS managed readonly policy exists, so the custom policy above is required
- **Amazon Bedrock**: The `AmazonBedrockReadOnly` managed policy doesn't include invoke permissions needed for actual model usage
- Both policies follow the principle of least privilege while providing necessary permissions for typical application usage
- The Location Service policy includes all major operations: geocoding, reverse geocoding, maps, routes, and places search

## Configuration

The application can be configured through environment variables or an optional config file.

### Environment Variables

Create a `.env` file for local development if needed:

```bash
# Create .env file with your overrides
echo "DEVELOPMENT=true" > .env
```

Key environment variables:

- `DEVELOPMENT=true` - Enable verbose logging and tracing
- `BEDROCK_MODEL_ID` - Claude model to use
- `AWS_REGION` - AWS region for Bedrock
- `WEATHER_API_TIMEOUT` - Request timeout in seconds (default: 10)
- `FASTMCP_LOG_LEVEL` - FastMCP logging level (default: ERROR)

#### Multi-Mode Deployment Configuration

The application supports multiple deployment modes for different use cases:

- `DEPLOYMENT_MODE` - Deployment mode: `local`, `mcp`, or `agentcore` (default: `local`)
- `AGENTCORE_AGENT_ID` - AWS Bedrock AgentCore agent ID (required for `agentcore` mode)
- `AGENTCORE_AGENT_ALIAS_ID` - AgentCore agent alias ID (default: `TSTALIASID`)
- `AGENTCORE_SESSION_ID` - AgentCore session ID for session continuity (optional)
- `AGENTCORE_ENABLE_TRACE` - Enable AgentCore tracing (default: `true`)
- `DEPLOYMENT_TIMEOUT` - Deployment-specific timeout in seconds (default: 30)
- `GUARDRAIL_ID` - Bedrock Guardrail ID for content filtering (optional)
- `GUARDRAIL_VERSION` - Guardrail version (default: `DRAFT`)
- `GUARDRAIL_CONTENT_FILTERING` - Enable content filtering (default: `true`)
- `GUARDRAIL_PII_DETECTION` - Enable PII detection (default: `true`)
- `GUARDRAIL_TOXICITY_DETECTION` - Enable toxicity detection (default: `true`)


### Config File

The project includes `config.toml` with sensible defaults. To customize without modifying the tracked file:

**Option 1: Local override file**

```bash
# Create local overrides (not tracked in git)
cp config.toml config.local.toml
# Edit config.local.toml with your changes
```

**Option 2: Environment variables**
Environment variables take precedence over all config files.

**Configuration priority (highest to lowest):**

1. Environment variables
2. `config.local.toml` (local overrides)
3. `config.toml` (project defaults)

## Deployment Modes

The application supports three deployment modes to accommodate different use cases:

### LOCAL Mode (Default)
- **Use Case**: Local development and testing
- **Model**: Amazon Bedrock with direct API calls
- **Tools**: Full MCP tools + custom weather tools
- **Configuration**: Standard Bedrock model configuration

```bash
# Run in local mode (default)
DEPLOYMENT_MODE=local uv run location-weather
```

### MCP Mode
- **Use Case**: Integration with MCP-compatible clients
- **Model**: Amazon Bedrock with MCP server interface
- **Tools**: Full MCP tools + custom weather tools
- **Configuration**: Same as LOCAL mode but optimized for MCP clients

```bash
# Run in MCP mode
DEPLOYMENT_MODE=mcp uv run location-weather-mcp
```

### AGENTCORE Mode
- **Use Case**: AWS Bedrock AgentCore integration with pre-configured agents
- **Model**: AWS Bedrock AgentCore with agent runtime invocation
- **Tools**: Base weather tools + AgentCore action groups for location services
- **Configuration**: Requires AgentCore agent ID, alias, and optional session ID
- **Architecture**: Location services configured as Action Groups within the AgentCore agent

```bash
# Run in AgentCore mode
DEPLOYMENT_MODE=agentcore \
AGENTCORE_AGENT_ID=your-agent-id \
AGENTCORE_AGENT_ALIAS_ID=your-alias-id \
AGENTCORE_SESSION_ID=unique-session-id \
uv run location-weather
```

**AgentCore Setup Requirements:**
- Pre-configured AgentCore agent with location service action groups
- Proper IAM permissions for AgentCore invocation
- Action groups configured for Amazon Location Service APIs
- Optional guardrails for content filtering

For detailed Lambda function deployment instructions, see [infrastructure/lambda_deployment_guide.md](infrastructure/lambda_deployment_guide.md).

### Mode-Specific Configuration

Each mode can be configured programmatically:

```python
from strands_location_service_weather import LocationWeatherClient, DeploymentMode

# Local mode (default)
client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

# MCP mode
client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)

# AgentCore mode with configuration
client = LocationWeatherClient(
    deployment_mode=DeploymentMode.AGENTCORE,
    config_override={
        "agentcore_agent_id": "your-agent-id",
        "aws_region": "us-east-1"
    }
)

# Get deployment information
info = client.get_deployment_info()
print(f"Mode: {info.mode}, Model: {info.model_type}, Tools: {info.tools_count}")

# Health check
health = client.health_check()
print(f"Healthy: {health.healthy}, Model OK: {health.model_healthy}")
```

## OpenAPI Schema Generation

The application includes comprehensive OpenAPI 3.0 schema generation for AWS Bedrock AgentCore action groups. This enables automatic creation of action group definitions from Python tool functions.

### Features

- **Automatic Schema Generation**: Converts Python functions to OpenAPI 3.0 schemas
- **Type Inference**: Supports all Python types including Optional, List, Dict, Union
- **AgentCore Compliance**: Validates schemas for AWS Bedrock AgentCore compatibility
- **CLI Tools**: Complete command-line interface for generation and validation
- **Comprehensive Validation**: 25+ validation rules with detailed error reporting

### Generated Schemas

The system generates schemas for two action groups:

- **Weather Services**: `get_weather`, `get_alerts`, `current_time` operations
- **Location Services**: `search_places`, `calculate_route` operations

### CLI Usage

```bash
# Generate all schemas and export to files
uv run python -m src.strands_location_service_weather.schema_cli generate --output-dir infrastructure/schemas

# Validate all generated schemas
uv run python -m src.strands_location_service_weather.schema_cli validate --verbose

# Show a specific schema
uv run python -m src.strands_location_service_weather.schema_cli show weather_services

# Generate validation report
uv run python -m src.strands_location_service_weather.schema_cli report --output validation_report.md

# List all available schemas
uv run python -m src.strands_location_service_weather.schema_cli list

# Validate a specific schema file
uv run python -m src.strands_location_service_weather.schema_cli validate-file ./schemas/weather_action_group.json
```

### Programmatic Usage

```python
from src.strands_location_service_weather.openapi_schemas import (
    create_weather_action_group_schema,
    create_location_action_group_schema,
    get_all_action_group_schemas
)
from src.strands_location_service_weather.schema_validation import validate_all_schemas

# Generate schemas
weather_schema = create_weather_action_group_schema()
location_schema = create_location_action_group_schema()
all_schemas = get_all_action_group_schemas()

# Validate schemas
validation_results = validate_all_schemas()
for name, result in validation_results.items():
    print(f"{name}: {'VALID' if result.valid else 'INVALID'}")
```

### Schema Files

Generated schemas are saved to `infrastructure/schemas/`:
- `weather_action_group.json` - Weather services OpenAPI schema
- `location_action_group.json` - Location services OpenAPI schema
- `validation_report.md` - Comprehensive validation report

These schemas can be used directly with AWS CDK or CloudFormation to create AgentCore action groups.

## Usage

### Interactive CLI

Run the application with:

```bash
# Using the installed script
uv run location-weather

# Or directly
uv run src/strands_location_service_weather/main.py
```

For development mode with verbose logging and tracing:

```bash
DEVELOPMENT=true uv run location-weather
```

### MCP Server for Q CLI

To use with Amazon Q CLI or other MCP clients:

```bash
# Run as MCP server
uv run location-weather-mcp
```

See [MCP Setup Guide](docs/mcp-setup.md) for detailed Q CLI configuration instructions.

## Documentation

Additional documentation is available in the `docs/` directory:

- **[MCP Setup Guide](docs/mcp-setup.md)** - Detailed Q CLI configuration and usage instructions
- **[Error Handling Implementation](docs/error-handling-implementation.md)** - Comprehensive error handling and fallback mechanisms
- **[OpenTelemetry & MCP Alignment](docs/opentelemetry-mcp-alignment.md)** - Best practices compliance and standards alignment
- **[Tool Integration Best Practices](docs/tool-integration-best-practices.md)** - Guidelines for tool development and integration
- **[Guardrails Best Practices](docs/guardrails-best-practices.md)** - Security and content filtering guidelines

**Note**: This project includes automated CI/CD via GitHub Actions. All tests, formatting, and linting checks run automatically on pull requests.

## Development Workflow

### Testing

This project includes a comprehensive test suite with 65% code coverage:

```bash
# Run all tests
uv run pytest

# Run fast tests only (skip performance benchmarks)
uv run pytest -m "not slow"

# Run tests with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test categories
uv run pytest tests/test_weather_tools.py      # Unit tests
uv run pytest tests/test_integration.py       # Integration tests
uv run pytest tests/test_performance.py       # Performance tests
```

#### Test Categories

- **Unit Tests**: Individual function testing with mocked dependencies
- **Integration Tests**: End-to-end functionality testing
- **Performance Tests**: Validation of optimization targets and benchmarks
- **MCP Server Tests**: FastMCP server functionality and tool registration

#### Coverage Targets

- **Core business logic**: 86% coverage (location_weather.py)
- **Configuration**: 93% coverage (config.py)
- **Overall project**: 65% coverage with focus on critical paths

### Code Quality & CI/CD

This project uses automated quality checks via GitHub Actions:

#### Local Development Workflow

**During development** (fast feedback loop):
```bash
# Format code
uv run black .

# Check and fix linting issues
uv run ruff check --fix .

# Run fast tests (~30 seconds, skips slow benchmarks)
uv run pytest -m "not slow"
```

**Before pushing** (comprehensive validation):
```bash
# Run all tests including performance benchmarks
uv run pytest

# Optional: Check coverage
uv run pytest --cov=src --cov-report=term-missing
```

#### Why This Workflow?

- **Local fast tests**: Immediate feedback while developing (30 seconds)
- **Local full tests**: Catch issues before pushing (60 seconds)  
- **CI validation**: Multi-environment testing and security checks (3-5 minutes)

This approach provides **fast local feedback** while ensuring **comprehensive validation** via CI.

#### GitHub Actions Workflows

- **Pull Request Checks**: Fast tests, formatting, and linting on every PR
- **Full CI Pipeline**: Complete test suite across Python 3.10-3.13 on main branch
- **Coverage Reporting**: Automatic coverage reports and trend tracking
- **Security Scanning**: Dependency vulnerability checks
- **Performance Validation**: Automated performance regression detection

#### Branch Protection

The main branch is protected and requires:
- All status checks to pass
- Code review approval
- Up-to-date branches before merging

**Recommended development cycle:**

1. **Make changes** → **Quick local validation**:
   ```bash
   uv run black .
   uv run ruff check --fix .
   uv run pytest -m "not slow"    # Fast feedback (30s)
   ```

2. **Before committing** → **Full local validation**:
   ```bash
   uv run pytest                  # All tests (60s)
   git add .
   git commit -m "your message"
   ```

3. **Push & PR** → **Automated CI validation** (multi-Python, security, coverage)

## Contributing

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/CarmenAPuccio/strands-location-service-weather.git
   cd strands-location-service-weather
   ```

2. **Install dependencies**:
   ```bash
   uv sync --extra dev
   ```

3. **Run tests to verify setup**:
   ```bash
   uv run pytest -m "not slow"
   ```

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Run the full quality check**:
   ```bash
   uv run black .
   uv run ruff check --fix .
   uv run pytest                  # Full test suite including slow tests
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: describe your changes"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub

### Coding Standards

- **Code Formatting**: Black (88 character line length)
- **Linting**: Ruff with modern Python patterns
- **Type Hints**: Required for public functions
- **Testing**: New features require tests with >80% coverage
- **Documentation**: Update README and docstrings for public APIs
- **Performance**: Maintain response time targets (15-20s for simple queries)

### Performance Guidelines

- Use HTTP session reuse for external API calls
- Keep system prompts concise (<100 words)
- Set appropriate timeouts (10s for weather APIs)
- Test performance impact with benchmark tests
- Follow the performance steering guidelines in `.kiro/steering/performance.md`

### Configuration

- **Black**: Formats code to PEP 8 standards (88 character line length)
- **Ruff**: Fast linter that catches style issues, unused imports, and applies modern Python patterns
- **Target Python**: 3.10+ (required by strands-agents dependency)
