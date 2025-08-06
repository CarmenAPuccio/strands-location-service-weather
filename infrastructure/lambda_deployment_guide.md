# Lambda Function Deployment Guide for AgentCore

This guide explains how to deploy the weather and alerts Lambda functions for use with AWS Bedrock AgentCore.

## Overview

The Lambda functions provide AgentCore-compliant implementations of the weather tools:
- `get_weather`: Retrieves current weather information for coordinates
- `get_alerts`: Retrieves active weather alerts for coordinates

## Files Structure

```
infrastructure/lambda_functions/
├── shared/
│   ├── lambda_handler.py          # Shared Lambda handler logic
│   └── weather_tools.py           # Weather tool implementations
├── get_weather/
│   └── lambda_function.py         # Weather Lambda entry point
├── get_alerts/
│   └── lambda_function.py         # Alerts Lambda entry point
└── lambda_deployment_guide.md     # This file
```

## Deployment Steps

### 1. Package Lambda Functions

Each Lambda function should be packaged with its dependencies:

```bash
# Create deployment packages
mkdir -p lambda-packages/get-weather
mkdir -p lambda-packages/get-alerts

# Copy source files
cp -r infrastructure/lambda_functions/shared lambda-packages/get-weather/
cp infrastructure/lambda_functions/get_weather/lambda_function.py lambda-packages/get-weather/
cp -r infrastructure/lambda_functions/shared lambda-packages/get-alerts/
cp infrastructure/lambda_functions/get_alerts/lambda_function.py lambda-packages/get-alerts/

# Install dependencies (if any additional ones are needed)
pip install -r requirements.txt -t lambda-packages/get-weather/
pip install -r requirements.txt -t lambda-packages/get-alerts/
```

### 2. Create Lambda Functions

#### Weather Lambda Function

```bash
# Create deployment package
cd lambda-packages/get-weather
zip -r ../get-weather-lambda.zip .

# Create Lambda function
aws lambda create-function \
  --function-name agentcore-get-weather \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://../get-weather-lambda.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables='{
    "WEATHER_API_TIMEOUT":"10",
    "OTEL_EXPORTER_OTLP_ENDPOINT":"https://your-otlp-endpoint"
  }'
```

#### Alerts Lambda Function

```bash
# Create deployment package
cd lambda-packages/get-alerts
zip -r ../get-alerts-lambda.zip .

# Create Lambda function
aws lambda create-function \
  --function-name agentcore-get-alerts \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://../get-alerts-lambda.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables='{
    "WEATHER_API_TIMEOUT":"10",
    "OTEL_EXPORTER_OTLP_ENDPOINT":"https://your-otlp-endpoint"
  }'
```

### 3. Configure AgentCore Action Groups

#### Weather Action Group

```json
{
  "actionGroupName": "weather-tools",
  "description": "Weather information services",
  "actionGroupExecutor": {
    "lambda": {
      "lambdaArn": "arn:aws:lambda:REGION:ACCOUNT:function:agentcore-get-weather"
    }
  },
  "apiSchema": {
    "payload": "<OpenAPI schema from agentcore_schemas.py>"
  }
}
```

#### Alerts Action Group

```json
{
  "actionGroupName": "weather-alerts-tools", 
  "description": "Weather alerts and warnings services",
  "actionGroupExecutor": {
    "lambda": {
      "lambdaArn": "arn:aws:lambda:REGION:ACCOUNT:function:agentcore-get-alerts"
    }
  },
  "apiSchema": {
    "payload": "<OpenAPI schema from agentcore_schemas.py>"
  }
}
```

### 4. Generate OpenAPI Schemas

Use the provided schema functions to generate the required OpenAPI specifications:

```python
from src.strands_location_service_weather.agentcore_schemas import (
    get_weather_action_group_schema,
    get_alerts_action_group_schema
)

# Generate schemas
weather_schema = get_weather_action_group_schema()
alerts_schema = get_alerts_action_group_schema()

# Save to files for AgentCore configuration
import json
with open('weather-action-group-schema.json', 'w') as f:
    json.dump(weather_schema, f, indent=2)

with open('alerts-action-group-schema.json', 'w') as f:
    json.dump(alerts_schema, f, indent=2)
```

## Environment Variables

### Required Environment Variables

- `WEATHER_API_BASE_URL`: National Weather Service API base URL (default: https://api.weather.gov)
- `WEATHER_API_TIMEOUT`: Request timeout in seconds (default: 10)
- `USER_AGENT_WEATHER`: User agent for weather requests (default: LocationWeatherService/1.0)
- `USER_AGENT_ALERTS`: User agent for alerts requests (default: LocationWeatherAlertsService/1.0)

### Optional Environment Variables

- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry OTLP endpoint for distributed tracing
- `FASTMCP_LOG_LEVEL`: Logging level (default: ERROR)

## IAM Permissions

The Lambda execution role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream", 
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Test Lambda handlers
uv run pytest tests/test_lambda_handler.py -v

# Test OpenAPI schemas
uv run pytest tests/test_agentcore_schemas.py -v

# Test Lambda function entry points
uv run pytest tests/test_lambda_functions.py -v
```

### Integration Testing

Test the deployed Lambda functions:

```bash
# Test weather function
aws lambda invoke \
  --function-name agentcore-get-weather \
  --payload '{"requestBody":{"content":[{"text":"{\"latitude\":47.6062,\"longitude\":-122.3321}"}]},"agent":{"agentId":"test"},"function":{"functionName":"get_weather"}}' \
  response.json

# Test alerts function  
aws lambda invoke \
  --function-name agentcore-get-alerts \
  --payload '{"requestBody":{"content":[{"text":"{\"latitude\":47.6062,\"longitude\":-122.3321}"}]},"agent":{"agentId":"test"},"function":{"functionName":"get_alerts"}}' \
  response.json
```

## Monitoring and Observability

### CloudWatch Metrics

Monitor the following metrics:
- Function duration
- Error rate
- Invocation count
- Throttles

### Distributed Tracing

The Lambda functions include OpenTelemetry instrumentation for distributed tracing:
- Lambda execution spans
- HTTP request spans to weather APIs
- Error tracking and exception recording

### Logging

Structured logging is provided with:
- Request/response logging
- Error details
- Performance metrics
- Trace correlation IDs

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase Lambda timeout or reduce `WEATHER_API_TIMEOUT`
2. **Memory Issues**: Increase Lambda memory allocation
3. **API Rate Limits**: Implement exponential backoff in weather API calls
4. **Cold Start Performance**: Consider provisioned concurrency for high-traffic scenarios

### Debug Mode

Enable verbose logging by setting environment variables:
```bash
DEVELOPMENT=true
FASTMCP_LOG_LEVEL=DEBUG
```

## Performance Optimization

### HTTP Session Reuse

The Lambda functions use persistent HTTP sessions for better performance:
- Reduces connection overhead
- Improves response times by 2-5 seconds per request

### Optimized Timeouts

- Weather API timeout: 10 seconds (fast failure detection)
- Lambda timeout: 30 seconds (allows for retries)

### Memory Configuration

Recommended memory settings:
- Development: 256 MB
- Production: 512 MB (for better performance)

## Security Considerations

### Network Security

- Lambda functions make outbound HTTPS calls to weather.gov
- No inbound network access required
- Consider VPC configuration for enhanced security

### Data Privacy

- No sensitive data is stored or logged
- Weather data is public information
- Coordinate data is processed but not persisted

### Error Handling

- Comprehensive error handling prevents information leakage
- Structured error responses for AgentCore
- Exception details are logged but not exposed to end users