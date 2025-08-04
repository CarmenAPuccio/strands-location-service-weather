# Strands Location Service Weather

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

# Install with development tools (Black, Ruff)
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

## Development Workflow

### Code Formatting

This project uses Black and Ruff for code formatting and linting:

```bash
# Format code
uv run black .

# Check and fix linting issues
uv run ruff check --fix .
```

**Before committing code, always run:**

```bash
uv run black .
uv run ruff check --fix .
git add .
git commit -m "your message"
```

### Configuration

- **Black**: Formats code to PEP 8 standards (88 character line length)
- **Ruff**: Fast linter that catches style issues, unused imports, and applies modern Python patterns
- **Target Python**: 3.10+ (required by strands-agents dependency)
