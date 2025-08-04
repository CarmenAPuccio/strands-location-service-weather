# Project Structure

## Root Directory Layout

```
├── src/                           # Source code directory
│   └── strands_location_service_weather/
│       ├── __init__.py           # Package initialization
│       ├── main.py               # CLI entry point with OpenTelemetry setup
│       ├── location_weather.py   # Core module with unified client and tools
│       └── mcp_server.py         # FastMCP server for Q CLI integration
├── pyproject.toml                # Modern Python project configuration
├── README.md                     # Project documentation
├── LICENSE                       # Project license
├── .gitignore                    # Git ignore rules
├── .pre-commit-config.yaml       # Pre-commit hooks configuration
├── .venv/                        # Virtual environment (local)
├── __pycache__/                  # Python bytecode cache
└── .kiro/                        # Kiro IDE configuration
    └── steering/                 # AI assistant guidance documents
```

## Module Organization

### src/strands_location_service_weather/main.py
- Application entry point and CLI interface
- OpenTelemetry configuration and instrumentation
- Environment-based logging setup (development vs production)
- User interaction loop with tracing spans

### src/strands_location_service_weather/location_weather.py
- **LocationWeatherClient**: Main client class for Bedrock integration
- **Custom Tools**: `get_weather()` and `get_alerts()` for National Weather Service
- **MCP Integration**: Automatic loading of Amazon Location Service tools
- **System Prompt**: Optimized assistant instructions for fast processing
- **HTTP Session Reuse**: Persistent session for weather API calls
- **Observability**: Detailed span creation and metrics collection

### src/strands_location_service_weather/mcp_server.py
- **FastMCP Server**: Q CLI compatible MCP server implementation
- **Tool Wrapper**: Exposes `ask_location_weather` tool for external clients
- **Performance Optimized**: Pre-initialized client and timeout handling
- **Error Handling**: Graceful degradation with user-friendly messages

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