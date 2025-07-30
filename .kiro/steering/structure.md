# Project Structure

## Root Directory Layout

```
├── src/                           # Source code directory
│   └── strands_location_service_weather/
│       ├── __init__.py           # Package initialization
│       ├── main.py               # CLI entry point with OpenTelemetry setup
│       └── location_weather.py   # Core module with unified client and tools
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
- **System Prompt**: Comprehensive assistant instructions and guidelines
- **Observability**: Detailed span creation and metrics collection

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