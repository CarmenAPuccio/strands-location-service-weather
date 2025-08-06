# Infrastructure Guidelines

## Lambda Function Architecture

The project uses a shared Lambda handler pattern for AgentCore integration, optimized for performance and observability.

### Shared Handler Pattern

#### infrastructure/lambda_functions/shared/lambda_handler.py
- **Common Handler**: Single handler implementation for all weather tools
- **Tool Registration**: Dynamic tool loading based on Lambda function configuration
- **Event Processing**: Standardized AgentCore event parsing and response formatting
- **OpenTelemetry Integration**: Distributed tracing with proper trace context propagation
- **Error Handling**: Consistent error responses with appropriate HTTP status codes

### Lambda Function Structure

Each Lambda function follows this pattern:
```
infrastructure/lambda_functions/{tool_name}/
├── lambda_function.py    # Function entry point (imports shared handler)
├── requirements.txt      # Function-specific dependencies
└── README.md            # Function documentation
```

### Tool Implementation Guidelines

#### Weather Tool Functions
- **get_weather**: Current weather conditions from National Weather Service
- **get_alerts**: Weather alerts and warnings for specific locations
- **HTTP Session Reuse**: Use persistent sessions for API calls within Lambda execution context
- **Timeout Handling**: Implement appropriate timeouts for external API calls (10s for weather APIs)

#### AgentCore Event Handling
- **Input Validation**: Validate required parameters from AgentCore events
- **Response Formatting**: Return properly structured responses for AgentCore consumption
- **Error Responses**: Include error details and appropriate HTTP status codes
- **Trace Context**: Maintain OpenTelemetry trace context across service boundaries

## Deployment Patterns

### Lambda Deployment Requirements

#### Dependencies
- **strands-agents**: Core agent framework (must be included in Lambda layer or package)
- **requests**: HTTP client for weather API calls
- **opentelemetry-***: Full observability stack for tracing
- **boto3**: AWS SDK (available in Lambda runtime)

#### Environment Variables
- **OTEL_SERVICE_NAME**: Service name for tracing (e.g., "location-weather-lambda")
- **AWS_REGION**: AWS region for service calls
- **WEATHER_API_TIMEOUT**: Timeout for weather API calls (default: 10)
- **DEVELOPMENT**: Enable verbose logging and tracing (false in production)

#### IAM Permissions
Lambda functions require these permissions:
- **CloudWatch Logs**: For function logging
- **X-Ray**: For distributed tracing (if using X-Ray instead of OTEL)
- **Bedrock**: For model access (if needed for error handling)

### CDK Infrastructure Patterns

#### Stack Organization
- **LocationWeatherStack**: Main CDK stack for all infrastructure
- **Lambda Functions**: Individual constructs for each weather tool
- **IAM Roles**: Least-privilege roles for Lambda execution
- **Action Groups**: Bedrock Agent action group configuration

#### Resource Naming
Use consistent naming patterns:
- **Lambda Functions**: `location-weather-{tool-name}`
- **IAM Roles**: `location-weather-lambda-{tool-name}-role`
- **Log Groups**: `/aws/lambda/location-weather-{tool-name}`

## Testing Infrastructure

### Lambda Function Testing

#### Unit Tests
- **Handler Testing**: Test shared handler with mock AgentCore events
- **Tool Testing**: Test individual weather tools with mock API responses
- **Error Handling**: Test error scenarios and response formatting
- **Trace Validation**: Verify OpenTelemetry spans are created correctly

#### Integration Tests
- **End-to-End**: Test complete AgentCore → Lambda → Weather API flow
- **Performance**: Validate response times meet requirements (15-20s total)
- **Error Recovery**: Test graceful degradation when weather APIs fail

### Infrastructure Testing

#### CDK Tests
- **Stack Validation**: Test CDK stack synthesis and deployment
- **Resource Configuration**: Validate IAM policies and Lambda configuration
- **Action Group Setup**: Test Bedrock Agent action group creation

#### Deployment Validation
- **Health Checks**: Verify deployed Lambda functions are healthy
- **Integration Testing**: Test AgentCore agent can invoke Lambda functions
- **Monitoring Setup**: Validate CloudWatch metrics and alarms

## Performance Considerations

### Lambda Optimization

#### Cold Start Mitigation
- **Minimal Dependencies**: Keep Lambda packages as small as possible
- **Connection Reuse**: Use persistent HTTP sessions within execution context
- **Initialization**: Minimize initialization time in Lambda handler

#### Memory and Timeout Configuration
- **Memory**: 256MB sufficient for weather API calls
- **Timeout**: 30 seconds to handle weather API latency
- **Concurrent Executions**: Monitor and adjust based on usage patterns

### Observability Best Practices

#### Tracing Strategy
- **Distributed Tracing**: Maintain trace context from AgentCore through Lambda execution
- **Custom Spans**: Create spans for external API calls and business logic
- **Trace Attributes**: Include relevant metadata (location, weather service, response times)

#### Metrics and Monitoring
- **Custom Metrics**: Track tool execution times and success rates
- **CloudWatch Dashboards**: Monitor Lambda performance and error rates
- **Alerts**: Set up alerts for high error rates or performance degradation

## Security Guidelines

### Lambda Security

#### Code Security
- **Input Validation**: Validate all inputs from AgentCore events
- **Output Sanitization**: Ensure responses don't leak sensitive information
- **Error Handling**: Don't expose internal errors to AgentCore responses

#### Runtime Security
- **Least Privilege**: Use minimal IAM permissions for Lambda execution
- **Environment Variables**: Use AWS Systems Manager for sensitive configuration
- **VPC Configuration**: Consider VPC deployment for enhanced network security

### AgentCore Integration Security

#### Guardrails Configuration
- **Content Filtering**: Enable appropriate content filtering for location services
- **PII Detection**: Configure PII detection to allow addresses while blocking other PII
- **Input Validation**: Validate AgentCore requests before processing

#### Access Control
- **Agent Permissions**: Restrict AgentCore agent access to specific action groups
- **Session Management**: Implement proper session handling for multi-turn conversations
- **Audit Logging**: Enable CloudTrail logging for AgentCore invocations