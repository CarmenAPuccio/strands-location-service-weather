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
- `requests`: HTTP client for weather API calls (with session reuse optimization)
- `boto3`: AWS SDK for Bedrock services
- `fastmcp`: FastMCP framework for MCP server implementation
- `opentelemetry-*`: Full observability stack

## Build System

Uses `uv` as the Python package manager and runner with modern `pyproject.toml` configuration.

### Common Commands

```bash
# Install dependencies
uv sync

# Install with development tools (Black, Ruff)
uv sync --extra dev

# Run the application (interactive CLI)
uv run location-weather
# or
uv run src/strands_location_service_weather/main.py

# Run as MCP server (for Q CLI integration)
uv run location-weather-mcp

# Development mode with verbose logging and tracing
DEVELOPMENT=true uv run location-weather

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src

# Run only fast tests (skip slow benchmarks)
uv run pytest -m "not slow"
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

#### Core Configuration
- `DEVELOPMENT=true`: Enables verbose logging, console span export, and detailed trace output
- `BEDROCK_MODEL_ID`: Claude model to use (default: claude-3-sonnet)
- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)
- `WEATHER_API_TIMEOUT`: Request timeout in seconds (default: 10)
- `FASTMCP_LOG_LEVEL`: FastMCP logging level for MCP server mode (default: ERROR)
- `OTEL_SERVICE_NAME`: OpenTelemetry service name
- AWS credentials required for Bedrock access (via standard AWS credential chain)
- No additional API keys needed (uses public National Weather Service API)

#### Multi-Mode Deployment Configuration
- `DEPLOYMENT_MODE`: Deployment mode (`local`, `mcp`, `agentcore`) - default: `local`
- `AGENTCORE_AGENT_ID`: AWS Bedrock AgentCore agent ID (required for `agentcore` mode)
- `AGENTCORE_AGENT_ALIAS_ID`: AgentCore agent alias ID (default: `TSTALIASID`)
- `AGENTCORE_SESSION_ID`: AgentCore session ID for session continuity (optional)
- `AGENTCORE_ENABLE_TRACE`: Enable AgentCore tracing (default: `true`)
- `DEPLOYMENT_TIMEOUT`: Deployment-specific timeout in seconds (default: 30)

#### Guardrail Configuration
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

This provides location service tools without manual installation.
## Mu
lti-Mode Usage Patterns

### Programmatic Client Creation

```python
from strands_location_service_weather import LocationWeatherClient, DeploymentMode

# Local mode (default) - for development and testing
client = LocationWeatherClient(deployment_mode=DeploymentMode.LOCAL)

# MCP mode - for MCP client integration
client = LocationWeatherClient(deployment_mode=DeploymentMode.MCP)

# AgentCore mode - for AWS Bedrock AgentCore integration
client = LocationWeatherClient(
    deployment_mode=DeploymentMode.AGENTCORE,
    config_override={
        "agentcore_agent_id": "AGENT123",
        "aws_region": "us-east-1"
    }
)

# Backward compatibility - old constructor interface still works
client = LocationWeatherClient(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-west-2"
)
```

### Deployment Information and Health Checks

```python
# Get deployment information
info = client.get_deployment_info()
print(f"Mode: {info.mode.value}")
print(f"Model Type: {info.model_type}")
print(f"Model ID: {info.model_id}")  # None for AgentCore
print(f"Agent ID: {info.agent_id}")  # None for Bedrock models
print(f"Region: {info.region}")
print(f"Tools Count: {info.tools_count}")

# Perform health check
health = client.health_check()
print(f"Overall Health: {health.healthy}")
print(f"Model Health: {health.model_healthy}")
print(f"Tools Available: {health.tools_available}")
if health.error_message:
    print(f"Error: {health.error_message}")
```

### Mode-Specific Tool Configuration

- **LOCAL/MCP modes**: Include full MCP tools + custom weather tools
- **AGENTCORE mode**: Base weather tools + AgentCore action groups for location services
  - Location services are configured as Action Groups within the AgentCore agent
  - Weather tools remain as custom tools since they're application-specific
  - AgentCore handles tool orchestration via the Bedrock AgentCore runtime

### Configuration Override Patterns

```python
# Override specific configuration values
config_override = {
    "bedrock_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
    "aws_region": "eu-west-1",
    "timeout": 60
}

client = LocationWeatherClient(
    deployment_mode=DeploymentMode.LOCAL,
    config_override=config_override
)
```
## A
gentCore Best Practices

### Agent Configuration
- **Agent ID**: Unique identifier for the AgentCore agent
- **Agent Alias**: Use `TSTALIASID` for testing, create specific aliases for production
- **Session Management**: Use unique session IDs per user conversation for context continuity
- **Tracing**: Enable tracing for monitoring and debugging AgentCore invocations

### Action Groups Setup
For location services, configure Action Groups in your AgentCore agent with:
- Amazon Location Service APIs (SearchPlaceIndexForText, CalculateRoute, etc.)
- Proper IAM permissions for location service access
- OpenAPI schema definitions for tool parameters

### Security Considerations
- Apply guardrails at both model and agent levels
- Use least-privilege IAM policies for AgentCore execution
- Enable CloudTrail logging for AgentCore invocations
- Consider VPC endpoints for enhanced security

### Performance Optimization
- Use appropriate timeout values for AgentCore invocations (default: 30s)
- Implement proper error handling for AgentCore failures
- Monitor AgentCore metrics via CloudWatch
- Cache session state when appropriate

### Development vs Production
- **Development**: Use `TSTALIASID` and enable detailed tracing
- **Production**: Create dedicated agent aliases and implement proper session management
- **Testing**: Use separate AgentCore agents for different environments