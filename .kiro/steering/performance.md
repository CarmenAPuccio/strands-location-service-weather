# Performance Optimization Guidelines

## Key Performance Optimizations

This project has been optimized for fast response times in both CLI and MCP server modes.

### HTTP Session Reuse
- **Implementation**: Global `_http_session = requests.Session()` in `location_weather.py`
- **Benefit**: Eliminates TCP connection overhead for multiple weather API calls
- **Impact**: Reduces response time by 2-5 seconds per query

### Streamlined System Prompts
- **Approach**: Minimal, focused prompts that emphasize essential functionality
- **Current**: ~50 words vs original ~500 words
- **Impact**: Significantly faster Bedrock processing (3-5x improvement)

### Optimized Timeouts
- **Weather API**: 10 seconds (down from 30s)
- **MCP Server**: 90 second timeout with graceful error handling
- **Rationale**: Weather APIs are typically fast; quick failure detection improves UX

### FastMCP Configuration
- **Log Level**: ERROR (minimal logging overhead)
- **Debug Mode**: Only enabled in development
- **Cache**: Disabled for Q CLI (process-per-request architecture)

## Performance Targets

### Response Time Expectations
- **Simple weather queries**: 15-20 seconds
- **Complex route queries**: 20-30 seconds
- **Location searches**: 10-15 seconds

### Architecture Considerations
- **Q CLI**: Each request spawns new MCP server process (no persistent cache benefit)
- **Lambda Deployment**: Would benefit from connection pooling and caching
- **Local CLI**: Fastest due to persistent process and pre-loaded tools

## Monitoring Performance

### Key Metrics to Track
- **Total response time**: End-to-end user experience
- **Tool execution time**: Individual API call performance
- **Bedrock inference time**: LLM processing duration
- **HTTP request duration**: Weather API response times

### OpenTelemetry Spans
- `user_interaction`: Top-level request span
- `agent_interaction`: Bedrock processing
- `bedrock_model_inference`: LLM inference with token metrics
- `get_weather_api`: Weather service calls
- `get_weather_alerts`: Alert service calls

## Performance Best Practices

### When Making Changes
1. **Test both CLI and MCP modes**: Performance characteristics differ
2. **Monitor system prompt length**: Longer prompts = slower Bedrock processing
3. **Use HTTP session reuse**: Always use `_http_session` for external API calls
4. **Set appropriate timeouts**: Balance reliability vs speed
5. **Measure before optimizing**: Use OpenTelemetry data to identify bottlenecks

### Avoid Performance Anti-Patterns
- ❌ Creating new HTTP connections for each API call
- ❌ Verbose system prompts with excessive instructions
- ❌ Long timeouts for fast APIs
- ❌ Synchronous processing when async would help
- ❌ Excessive logging in production mode