# MCP Server Setup for Q CLI

This guide shows how to set up the Location Weather MCP server for use with Amazon Q CLI.

## Prerequisites

- Python 3.10 or higher
- `uv` package manager installed
- AWS credentials configured for Bedrock access
- Amazon Q CLI installed and configured

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/strands-location-service-weather.git
cd strands-location-service-weather
```

### 2. Install Dependencies

```bash
# Install all dependencies
uv sync

# Or install with development tools
uv sync --extra dev
```

### 3. Configure Environment

Create a `.env` file or set environment variables:

```bash
# Required for Bedrock access
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Optional configuration
export WEATHER_API_TIMEOUT=10
export DEVELOPMENT=false
```

## Q CLI Configuration

### 1. Add MCP Server to Q CLI

Add the following to your Q CLI MCP configuration:

```json
{
  "mcpServers": {
    "location-weather": {
      "command": "uv",
      "args": ["run", "location-weather-mcp"],
      "cwd": "/path/to/strands-location-service-weather",
      "env": {
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0"
      }
    }
  }
}
```

### 2. Test the Connection

```bash
# Test the MCP server directly
uv run location-weather-mcp

# Test with Q CLI
q chat "What's the weather in Seattle?"
```

## Usage Examples

### Weather Queries

```bash
q chat "What's the current weather in New York City?"
q chat "Is it going to rain in San Francisco today?"
q chat "What's the temperature in London?"
```

### Location Queries

```bash
q chat "Find coffee shops near Times Square"
q chat "What's the address of the Space Needle?"
q chat "Show me restaurants in downtown Portland"
```

### Combined Queries

```bash
q chat "What's the weather like at Yellowstone National Park?"
q chat "Find outdoor activities in Denver and check the weather"
q chat "Plan a route from Seattle to Portland and check weather conditions"
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   ```bash
   # Configure AWS credentials
   aws configure
   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   ```

2. **Bedrock Access Denied**
   - Ensure your AWS account has Bedrock access enabled
   - Check that your IAM user/role has Bedrock permissions
   - Verify the model ID is correct for your region

3. **MCP Server Not Starting**
   ```bash
   # Check dependencies
   uv sync
   
   # Test server directly
   uv run location-weather-mcp
   
   # Check logs
   DEVELOPMENT=true uv run location-weather-mcp
   ```

4. **Weather API Timeouts**
   ```bash
   # Increase timeout
   export WEATHER_API_TIMEOUT=30
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEVELOPMENT=true
export FASTMCP_LOG_LEVEL=DEBUG
uv run location-weather-mcp
```

## Performance Optimization

### Response Time Optimization

The MCP server is optimized for fast responses:

- **HTTP Session Reuse**: Persistent connections to weather APIs
- **Streamlined Prompts**: Minimal system prompts for faster processing
- **Optimized Timeouts**: 10-second weather API timeout by default

### Expected Response Times

- **Simple weather queries**: 15-20 seconds
- **Location searches**: 10-15 seconds
- **Complex route queries**: 20-30 seconds

### Memory Usage

- **Typical memory usage**: 50-100 MB
- **Peak memory usage**: 150-200 MB during complex queries

## Security Considerations

### API Keys and Credentials

- Never commit AWS credentials to version control
- Use IAM roles when possible
- Rotate credentials regularly

### Network Security

- The server only makes outbound HTTPS requests
- No inbound network connections required
- Uses public APIs (National Weather Service, Amazon Location)

### Data Privacy

- No user data is stored persistently
- Location queries are processed in real-time
- Weather data comes from public sources

## Advanced Configuration

### Custom Model Configuration

```bash
# Use different Claude model
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Use different AWS region
export AWS_REGION=us-west-2
```

### Timeout Configuration

```bash
# Weather API timeout (default: 10 seconds)
export WEATHER_API_TIMEOUT=15

# MCP server timeout (default: 90 seconds)
export MCP_SERVER_TIMEOUT=120
```

### Logging Configuration

```bash
# Enable structured logging
export DEVELOPMENT=true

# Set FastMCP log level
export FASTMCP_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Integration with Other Tools

### Using with Other MCP Clients

The server follows MCP specification and can be used with any MCP-compatible client:

```bash
# Direct MCP protocol usage
uv run location-weather-mcp
```

### Programmatic Usage

```python
from strands_location_service_weather import LocationWeatherClient

# Create client in MCP mode
client = LocationWeatherClient(deployment_mode="mcp")

# Use the client
response = client.chat("What's the weather in Seattle?")
print(response)
```

## Support and Contributing

### Getting Help

- Check the [troubleshooting section](#troubleshooting) above
- Review the main [README.md](../README.md) for additional information
- Check the [error handling documentation](error-handling-implementation.md)

### Contributing

- Follow the development setup in the main README
- Run tests before submitting changes: `uv run pytest`
- Follow the code style: `uv run black . && uv run ruff check --fix .`

### Reporting Issues

When reporting issues, please include:

- Your operating system and Python version
- The exact command that failed
- Full error messages and stack traces
- Your environment configuration (without sensitive data)