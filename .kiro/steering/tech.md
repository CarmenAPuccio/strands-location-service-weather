# Technology Stack

## Core Technologies

- **Python 3.x**: Primary programming language
- **Amazon Bedrock**: LLM inference using Claude 3 Sonnet model
- **Amazon Location Service**: Location search, geocoding, and routing via MCP
- **National Weather Service API**: Weather data and alerts
- **OpenTelemetry**: Comprehensive observability (tracing, logging, metrics)
- **Model Context Protocol (MCP)**: Tool integration for location services

## Key Dependencies

- `strands-agents`: Core agent framework for Bedrock integration
- `strands-agents-tools`: Additional tooling including MCP client
- `requests`: HTTP client for weather API calls
- `boto3`: AWS SDK for Bedrock services
- `opentelemetry-*`: Full observability stack

## Build System

Uses `uv` as the Python package manager and runner with modern `pyproject.toml` configuration.

### Common Commands

```bash
# Install dependencies
uv sync

# Install with development tools (Black, Ruff)
uv sync --extra dev

# Run the application
uv run location-weather
# or
uv run src/strands_location_service_weather/main.py

# Development mode with verbose logging and tracing
DEVELOPMENT=true uv run location-weather
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
- **Manual formatting**: Required in corporate environments with git hook managers

## Configuration Management

The application uses a layered configuration system:

1. **Default values** in `config.py`
2. **Config file** (`config.toml`) - optional
3. **Environment variables** - highest priority

### Key Environment Variables

- `DEVELOPMENT=true`: Enables verbose logging, console span export, and detailed trace output
- `BEDROCK_MODEL_ID`: Claude model to use (default: claude-3-sonnet)
- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)
- `WEATHER_API_TIMEOUT`: Request timeout in seconds (default: 30)
- `OTEL_SERVICE_NAME`: OpenTelemetry service name
- AWS credentials required for Bedrock access (via standard AWS credential chain)
- No additional API keys needed (uses public National Weather Service API)

## MCP Server Integration

The application automatically downloads and runs the AWS Location MCP server:
```bash
uvx awslabs.aws-location-mcp-server@latest
```

This provides location service tools without manual installation.