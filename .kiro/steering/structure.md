# Project Structure

## Root Directory Layout

```
├── src/                           # Source code directory
│   └── strands_location_service_weather/
│       ├── __init__.py           # Package initialization
│       ├── main.py               # CLI entry point with OpenTelemetry setup
│       ├── location_weather.py   # Core module with unified client and tools
│       ├── mcp_server.py         # FastMCP server for Q CLI integration
│       ├── config.py             # Multi-mode deployment configuration
│       ├── model_factory.py      # Model factory for Bedrock/AgentCore selection
│       └── tool_manager.py       # Tool management and validation
├── infrastructure/               # AWS infrastructure and deployment
│   ├── lambda_functions/         # Lambda function implementations
│   │   ├── shared/              # Shared Lambda utilities
│   │   │   ├── lambda_handler.py # Common Lambda handler with OpenTelemetry
│   │   │   └── requirements.txt  # Lambda dependencies
│   │   ├── get_weather/         # Weather tool Lambda function
│   │   └── get_alerts/          # Weather alerts Lambda function
│   └── lambda_deployment_guide.md # Lambda deployment documentation
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── test_*.py                # Unit and integration tests
│   └── test_lambda_handler.py   # Lambda function tests
├── pyproject.toml                # Modern Python project configuration
├── README.md                     # Project documentation
├── LICENSE                       # Project license
├── .gitignore                    # Git ignore rules
├── .pre-commit-config.yaml       # Pre-commit hooks configuration
├── .venv/                        # Virtual environment (local)
├── __pycache__/                  # Python bytecode cache
└── .kiro/                        # Kiro IDE configuration
    ├── steering/                 # AI assistant guidance documents
    └── specs/                    # Feature specifications
        └── agentcore-migration/  # AgentCore migration spec
```

## Module Organization

### Core Application Modules

#### src/strands_location_service_weather/main.py
- Application entry point and CLI interface
- OpenTelemetry configuration and instrumentation
- Environment-based logging setup (development vs production)
- User interaction loop with tracing spans

#### src/strands_location_service_weather/location_weather.py
- **LocationWeatherClient**: Main client class with multi-mode support (LOCAL/MCP/AGENTCORE)
- **Custom Tools**: `get_weather()` and `get_alerts()` for National Weather Service
- **MCP Integration**: Automatic loading of Amazon Location Service tools
- **System Prompt**: Optimized assistant instructions for fast processing
- **HTTP Session Reuse**: Persistent session for weather API calls
- **Observability**: Detailed span creation and metrics collection

#### src/strands_location_service_weather/mcp_server.py
- **FastMCP Server**: Q CLI compatible MCP server implementation
- **Tool Wrapper**: Exposes `ask_location_weather` tool for external clients
- **Performance Optimized**: Pre-initialized client and timeout handling
- **Error Handling**: Graceful degradation with user-friendly messages

### Multi-Mode Architecture Modules

#### src/strands_location_service_weather/config.py
- **DeploymentMode**: Enum for LOCAL, MCP, and AGENTCORE modes
- **DeploymentConfig**: Configuration dataclass with mode-specific parameters
- **GuardrailConfig**: Bedrock Guardrails configuration with PII handling
- **Environment Variable Processing**: Layered configuration system
- **Configuration Validation**: Type checking and required parameter validation

#### src/strands_location_service_weather/model_factory.py
- **ModelFactory**: Dynamic model selection based on deployment mode
- **BedrockModel Integration**: Direct Bedrock model access for LOCAL/MCP modes
- **AgentCoreModel Integration**: Strands AgentCore model for AGENTCORE mode
- **Health Checks**: Model connectivity and configuration validation
- **Error Handling**: Graceful model creation failure handling

#### src/strands_location_service_weather/tool_manager.py
- **Tool Registration**: Mode-specific tool selection and validation
- **Protocol Handling**: MCP vs Python direct tool execution
- **Tool Validation**: Ensures tools are properly decorated and functional
- **Error Handling**: Unified error handling across tool protocols

### Infrastructure Components

#### infrastructure/lambda_functions/shared/lambda_handler.py
- **AgentCore Lambda Handler**: Common handler for AgentCore action groups
- **OpenTelemetry Integration**: Distributed tracing across AgentCore → Lambda calls
- **Event Processing**: AgentCore event parsing and response formatting
- **Error Handling**: Structured error responses with proper HTTP status codes
- **Performance Optimization**: Efficient request/response handling

#### infrastructure/lambda_functions/get_weather/ & get_alerts/
- **Weather Tool Lambda Functions**: AgentCore-compliant implementations
- **National Weather Service Integration**: HTTP client with session reuse
- **Trace Propagation**: Maintains observability across service boundaries
- **Error Recovery**: Graceful handling of weather API failures

## Code Organization Patterns

### Tool Definition
- Use `@tool` decorator for custom functions
- Include comprehensive docstrings with Args and Returns
- Implement proper error handling and logging
- Create spans for external API calls

### Client Architecture
- Single unified client class (`LocationWeatherClient`)
- Dependency injection for model configuration
- Centralized tool registration (MCP + custom tools)
- Consistent error handling and user-friendly responses

### Observability Structure
- Hierarchical span organization: `user_interaction` → `agent_interaction` → `bedrock_model_inference`
- Tool-specific spans for external API calls
- Comprehensive attribute setting for debugging and metrics
- Environment-based span export configuration