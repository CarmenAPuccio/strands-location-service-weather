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

### 3. Test the MCP Server

```bash
# Test the interactive CLI first
uv run location-weather

# Test the MCP server directly
uv run location-weather-mcp
```

### 4. Quick Setup Example

For a typical setup on macOS, if you cloned to your home directory:

```bash
# Create the Q CLI config directory
mkdir -p ~/.aws/q

# Create the MCP configuration
cat > ~/.aws/q/mcp.json << 'EOF'
{
  "mcpServers": {
    "location-weather": {
      "command": "uv",
      "args": ["run", "--directory", "$HOME/strands-location-service-weather", "location-weather-mcp"],
      "disabled": false,
      "autoApprove": ["ask_location_weather"]
    }
  }
}
EOF
```

**Note:** Replace `$HOME/strands-location-service-weather` with your actual clone path.

## Q CLI Configuration

### Configuration File Location

Create or edit the Q CLI MCP configuration file:

**macOS/Linux:**

```bash
~/.aws/q/mcp.json
```

**Windows:**

```bash
%USERPROFILE%\.aws\q\mcp.json
```

### Option 1: Direct Command (Recommended)

Add this configuration to your `~/.aws/q/mcp.json` file:

```json
{
  "mcpServers": {
    "location-weather": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/strands-location-service-weather",
        "location-weather-mcp"
      ],
      "env": {
        "DEVELOPMENT": "false",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": ["ask_location_weather"]
    }
  }
}
```

**Important:** Replace `/absolute/path/to/strands-location-service-weather` with the actual absolute path to your cloned repository.

### Option 2: Global Installation

If you want to install globally with uv:

```bash
# Install globally
uv tool install --editable .
```

Then add this to your `~/.aws/q/mcp.json`:

```json
{
  "mcpServers": {
    "location-weather": {
      "command": "location-weather-mcp",
      "args": [],
      "disabled": false,
      "autoApprove": ["ask_location_weather"]
    }
  }
}
```

### Creating the Configuration File

If the file doesn't exist, create it:

```bash
# macOS/Linux
mkdir -p ~/.aws/q
touch ~/.aws/q/mcp.json

# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.aws\q"
New-Item -ItemType File -Force -Path "$env:USERPROFILE\.aws\q\mcp.json"
```

## Usage in Q CLI

Once configured, you can ask Q CLI location and weather questions:

```bash
q chat
```

Example queries:

- "What's the weather in Seattle?"
- "Find coffee shops open now in Boston"
- "Route from Trenton to Philadelphia"
- "Places near 47.6062,-122.3321"
- "Any weather alerts for Miami?"

## Performance

The MCP server is optimized for fast responses:
- **Simple weather queries**: ~15-20 seconds
- **Complex route queries**: ~20-30 seconds
- **HTTP session reuse**: Eliminates connection overhead
- **Streamlined processing**: Optimized system prompts for faster Bedrock responses

## Available Tool

The MCP server exposes one main tool:

- **ask_location_weather**: Natural language interface for location, weather, and routing queries

## Environment Variables

- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)
- `BEDROCK_MODEL_ID`: Claude model to use (default: claude-3-sonnet)
- `DEVELOPMENT`: Set to "true" for verbose logging
- AWS credentials via standard AWS credential chain

## Troubleshooting

### MCP Server Won't Start

- Check that all dependencies are installed: `uv sync`
- Verify AWS credentials are configured
- Ensure the path in `mcp.json` is absolute and correct
- Check the Q CLI logs for connection errors

### No Response from Tools

- Ensure the MCP server is listed in `~/.aws/q/mcp.json`
- Check that `autoApprove` includes `ask_location_weather`
- Verify the server isn't disabled in the configuration
- Restart Q CLI after configuration changes

### Configuration File Issues

- Verify the JSON syntax is valid
- Check file permissions on `~/.aws/q/mcp.json`
- Ensure the directory `~/.aws/q/` exists

### Permission Errors

- Ensure AWS credentials have Bedrock access
- Check that the Location Service is available in your AWS region

## Development

To modify the MCP server:

1. Edit `src/strands_location_service_weather/mcp_server.py`
2. Test changes: `uv run location-weather-mcp`
3. Restart Q CLI to pick up changes

The MCP server wraps the existing `LocationWeatherClient`, so most functionality comes from `location_weather.py`.
