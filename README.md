# Strands Location Service Weather

[![CI](https://github.com/CarmenAPuccio/strands-location-service-weather/workflows/CI/badge.svg)](https://github.com/CarmenAPuccio/strands-location-service-weather/actions)
[![Coverage](https://codecov.io/gh/CarmenAPuccio/strands-location-service-weather/branch/main/graph/badge.svg)](https://codecov.io/gh/CarmenAPuccio/strands-location-service-weather)
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

See [MCP_SETUP.md](MCP_SETUP.md) for detailed Q CLI configuration instructions.

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
