# Product Overview

## Strands Location Service Weather

A location-based weather information service that combines Amazon Location Service with weather data from the National Weather Service. The application provides natural language processing capabilities through Amazon Bedrock (Claude 3 Sonnet) to answer location and weather queries.

## Core Features

- **Location Services**: Search places, get coordinates, calculate routes using Amazon Location Service
- **Weather Data**: Current conditions and alerts from National Weather Service API
- **Natural Language Interface**: Conversational queries powered by Amazon Bedrock
- **Observability**: Comprehensive OpenTelemetry integration with tracing and metrics
- **MCP Integration**: Uses Model Context Protocol for Amazon Location Service tools

## Target Use Cases

- Location-based weather queries ("What's the weather in Seattle?")
- Place discovery ("Find coffee shops open now in Boston")
- Route planning ("Route from Trenton to Philadelphia")
- Coordinate-based searches ("Places near 47.6062,-122.3321")
- Weather alerts and warnings for specific locations

## Architecture Philosophy

Unified client architecture where MCP tools provide location services, custom tools handle weather data, and a single LocationWeatherClient manages all Bedrock interactions with full observability through OpenTelemetry.