# Strands Location Service Weather

This project combines Amazon Location Service MCP Server with weather data to provide location-based weather information using Amazon Bedrock for natural language processing.

## Components

- **location_weather.py**: Unified module that combines Amazon Location Service MCP tools, weather data retrieval, and Bedrock integration
- **main.py**: Command-line interface with OpenTelemetry observability features

## Usage

Run the application with:

```bash
uv run main.py
```

For development mode with verbose logging and tracing:

```bash
DEVELOPMENT=true uv run main.py
```

## Features

- **Location Services**: Search for places, get coordinates, calculate routes using Amazon Location Service
- **Weather Data**: Current weather conditions and alerts from the National Weather Service
- **Natural Language Processing**: Powered by Amazon Bedrock (Claude 3 Sonnet)
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