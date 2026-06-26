# Project Structure

## Root Directory Layout

```
├── src/                           # Source code directory
│   └── strands_location_service_weather/
│       ├── __init__.py           # Package initialization (v0.1.0)
│       ├── main.py               # CLI entry point with OpenTelemetry setup
│       ├── location_weather.py   # Core client with unified tools and multi-mode support
│       ├── mcp_server.py         # FastMCP server for Q CLI integration
│       ├── config.py             # Multi-mode deployment configuration
│       ├── model_factory.py      # Model factory for BedrockModel creation
│       ├── tool_manager.py       # Tool management and mode-specific selection
│       ├── error_handling.py     # Protocol-specific error handling with OpenTelemetry
│       ├── fallback_mechanisms.py # Graceful degradation and fallback strategies
│       ├── guardrails.py         # Bedrock Guardrails utilities
│       ├── openapi_schemas.py    # OpenAPI 3.0 schema generation for action groups
│       ├── bedrock_agent_schemas.py # Weather/alerts action group schemas
│       ├── schema_validation.py  # Schema validation utilities
│       └── schema_cli.py         # CLI utility for schema operations
├── infrastructure/               # AWS infrastructure and deployment
│   ├── app.py                   # CDK application entry point
│   ├── deploy.py               # Deployment automation script
│   ├── build_lambda_layers.py  # Lambda layer build script
│   ├── cdk.json                # CDK configuration
│   ├── cdk_lib/                # Reusable CDK constructs
│   │   ├── bedrock_construct.py  # Bedrock Agent + guardrails construct
│   │   ├── lambda_construct.py   # Weather Lambda functions construct
│   │   └── location_construct.py # Amazon Location Service construct
│   ├── stacks/
│   │   └── bedrock_agent_stack.py # Main CDK stack
│   ├── lambda_functions/        # Lambda function implementations
│   │   ├── shared/              # Shared Lambda utilities
│   │   │   ├── lambda_handler.py # Common handler with OpenTelemetry
│   │   │   └── weather_tools.py  # Shared weather tool implementations
│   │   ├── get_weather/         # Weather tool Lambda
│   │   ├── get_alerts/          # Alerts tool Lambda
│   │   ├── search_places/       # Place search Lambda
│   │   └── calculate_route/     # Route calculation Lambda
│   ├── schemas/                 # Generated OpenAPI schemas
│   │   ├── weather_action_group.json
│   │   ├── location_action_group.json
│   │   └── validation_report.md
│   └── layers/                  # Lambda layers (shared code)
├── tests/                        # Test suite (~21 test files)
├── docs/                         # Documentation
│   └── mcp-setup.md            # Q CLI MCP setup guide
├── pyproject.toml                # Python project configuration
├── config.toml                   # Runtime configuration defaults
├── pytest.ini                    # Pytest configuration
├── uv.lock                       # Dependency lock file
└── .kiro/                        # Kiro IDE configuration
    ├── steering/                 # AI assistant guidance documents
    └── specs/                    # Feature specifications
```

## Module Responsibilities

### Core Application

#### main.py
- Application entry point and interactive CLI loop
- OpenTelemetry configuration (development vs production)
- User interaction with tracing spans

#### location_weather.py
- **LocationWeatherClient**: Main client class with multi-mode support (LOCAL/MCP/BEDROCK_AGENT)
- Custom tools: `get_weather()`, `get_alerts()`, `current_time()`
- MCP integration for Amazon Location Service tools
- HTTP session reuse for weather API calls
- System prompt management

#### mcp_server.py
- FastMCP server for Q CLI integration
- Exposes `ask_location_weather` tool for external clients
- Pre-initialized client with timeout handling

### Multi-Mode Architecture

#### config.py
- **DeploymentMode** enum: LOCAL, MCP, BEDROCK_AGENT
- **DeploymentConfig**: Mode-specific parameters
- **GuardrailConfig**: Bedrock Guardrails with location-aware PII handling
- Layered configuration: defaults → config.toml → environment variables

#### model_factory.py
- **ModelFactory**: Creates BedrockModel based on deployment configuration
- Health checks and configuration validation
- Graceful error handling for model creation failures

#### tool_manager.py
- Mode-specific tool selection and validation
- LOCAL/MCP: full MCP tools + custom weather tools
- BEDROCK_AGENT: base weather tools (location via Lambda action groups)

### Error Handling & Resilience

#### error_handling.py
- Protocol-specific error handlers (Python Direct, MCP, HTTP REST)
- Standardized error classification with severity levels
- OpenTelemetry span integration for error tracking

#### fallback_mechanisms.py
- Fallback strategies: retry, circuit breaker, alternative tools, cached responses
- Cross-protocol graceful degradation

#### guardrails.py
- Bedrock Guardrails configuration utilities
- Content filtering, PII detection (ADDRESS excluded for location services)
- Prompt injection protection

### Schema & Validation

#### openapi_schemas.py
- Automatic OpenAPI 3.0 schema generation from Python tool functions
- Type inference for complex types (Optional, List, Dict, Union)

#### bedrock_agent_schemas.py
- Pre-built schemas for weather and alerts action groups
- Bedrock Agent-compliant endpoint definitions

#### schema_validation.py & schema_cli.py
- Validation against OpenAPI 3.0 spec
- CLI for generate, validate, export, and report operations

## Code Patterns

### Tool Definition
- Use `@tool` decorator for custom functions
- Include comprehensive docstrings with Args and Returns
- Create OpenTelemetry spans for external API calls

### Client Architecture
- Single unified client class (`LocationWeatherClient`)
- Configuration-driven model selection via ModelFactory
- Centralized tool registration (MCP + custom tools)

### Observability
- Hierarchical spans: `user_interaction` → `agent_interaction` → `bedrock_model_inference`
- Tool-specific spans for external API calls
- Environment-based span export (console in dev, OTLP in prod)
