# Technology Stack

## Core Technologies

- **Python 3.10+**: Primary programming language
- **Amazon Bedrock**: LLM inference using Claude Sonnet 4.6 model
- **Amazon Location Service**: Location search, geocoding, and routing via MCP
- **National Weather Service API**: Weather data and alerts
- **OpenTelemetry**: Comprehensive observability (tracing, logging, metrics)
- **Model Context Protocol (MCP)**: Tool integration for location services

## Key Dependencies

- `strands-agents`: Core agent framework for Bedrock integration
- `strands-agents-tools`: Additional tooling including MCP client
- `requests`: HTTP client for weather API calls (with session reuse optimization)
- `boto3`: AWS SDK for Bedrock services and Lambda deployment
- `fastmcp`: FastMCP framework for MCP server implementation
- `opentelemetry-*`: Full observability stack with distributed tracing
- `aws-cdk-lib`: AWS CDK for infrastructure as code

## Build System

Uses `uv` as the Python package manager and runner with modern `pyproject.toml` configuration.

### Common Commands

```bash
# Install dependencies
uv sync

# Install with development tools (Black, Ruff, pytest)
uv sync --extra dev

# Run the application (interactive CLI)
uv run location-weather

# Run as MCP server (for Q CLI integration)
uv run location-weather-mcp

# Development mode with verbose logging and tracing
DEVELOPMENT=true uv run location-weather

# Run tests
uv run python -m pytest

# Run tests with coverage
uv run python -m pytest --cov=src

# Run only fast tests (skip slow benchmarks)
uv run python -m pytest -m "not slow"

# OpenAPI Schema Operations
uv run python -m src.strands_location_service_weather.schema_cli generate --output-dir infrastructure/schemas
uv run python -m src.strands_location_service_weather.schema_cli validate --verbose
uv run python -m src.strands_location_service_weather.schema_cli list
```

### Development Workflow

```bash
# Format code (run before committing)
uv run black .
uv run ruff check --fix .

# Standard commit workflow
git add .
git commit -m "your message"
```

### Code Quality Tools

- **Black**: Code formatter (88 character line length, Python 3.10+ target)
- **Ruff**: Fast linter with import sorting, unused variable detection, and modern Python patterns
- **Manual formatting**: Required (git hook managers prevent pre-commit hook installation)

## Configuration Management

The application uses a layered configuration system:

1. **Default values** in `config.py` dataclass defaults
2. **Config file** (`config.toml`) — optional
3. **Environment variables** — highest priority

### Key Environment Variables

#### Core Configuration
- `DEVELOPMENT=true`: Enables verbose logging, console span export
- `BEDROCK_MODEL_ID`: Claude model to use (default: `us.anthropic.claude-sonnet-4-6`)
- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)
- `WEATHER_API_TIMEOUT`: Request timeout in seconds (default: 10)
- `OTEL_SERVICE_NAME`: OpenTelemetry service name

#### Multi-Mode Deployment
- `DEPLOYMENT_MODE`: Deployment mode (`local`, `mcp`, `bedrock_agent`) — default: `local`
- `BEDROCK_AGENT_ID`: Bedrock Agent ID (required for `bedrock_agent` mode)
- `BEDROCK_AGENT_ALIAS_ID`: Agent alias ID (default: `TSTALIASID`)
- `BEDROCK_AGENT_SESSION_ID`: Session ID for continuity (optional)
- `BEDROCK_AGENT_ENABLE_TRACE`: Enable Bedrock Agent tracing (default: `true`)
- `DEPLOYMENT_TIMEOUT`: Deployment-specific timeout in seconds (default: 30)

#### Guardrails
- `GUARDRAIL_ID`: Bedrock Guardrail ID for content filtering (optional)
- `GUARDRAIL_VERSION`: Guardrail version (default: `DRAFT`)
- `GUARDRAIL_CONTENT_FILTERING`: Enable content filtering (default: `true`)
- `GUARDRAIL_PII_DETECTION`: Enable PII detection (default: `true`)
- `GUARDRAIL_TOXICITY_DETECTION`: Enable toxicity detection (default: `true`)

## MCP Server Integration

The application automatically downloads and runs the AWS Location MCP server:
```bash
uvx awslabs.aws-location-mcp-server@latest
```

## Multi-Mode Usage Patterns

### Programmatic Client Creation

```python
from strands_location_service_weather import LocationWeatherClient, DeploymentMode

# Local mode (default) - for development and testing
client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

# MCP mode - for MCP client integration
client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)

# Bedrock Agent mode - for AWS Bedrock Agent integration
client = LocationWeatherClient(
    deployment_mode=DeploymentMode.BEDROCK_AGENT,
    config_override={
        "bedrock_agent_id": "AGENT123",
        "aws_region": "us-east-1"
    }
)

# Backward compatibility - old constructor interface still works
client = LocationWeatherClient(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name="us-east-1"
)
```

### Mode-Specific Tool Configuration

- **LOCAL/MCP modes**: Full MCP tools (location services) + custom weather tools
- **BEDROCK_AGENT mode**: Weather Lambda functions + Location Lambda functions as action groups
