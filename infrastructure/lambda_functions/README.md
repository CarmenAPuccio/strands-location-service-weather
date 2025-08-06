# Lambda Functions for AgentCore Weather Tools

This directory contains Lambda function implementations for AgentCore weather and alerts tools, following AWS Lambda best practices for code organization and deployment.

## Directory Structure

```
lambda_functions/
├── README.md                   # This file
├── shared/                     # Shared Lambda code
│   ├── lambda_handler.py       # Common handler utilities and decorators
│   └── weather_tools.py        # Weather and alerts business logic
├── get_weather/                # Weather Lambda function
│   └── lambda_function.py      # Entry point for weather function
└── get_alerts/                 # Alerts Lambda function
    └── lambda_function.py      # Entry point for alerts function
```

## Design Principles

### 1. **Separation of Concerns**
- **Application Code**: Located in `src/strands_location_service_weather/` for local/MCP modes
- **Lambda Code**: Located in `infrastructure/lambda_functions/` for AgentCore deployment
- **Infrastructure**: Located in `infrastructure/` for CDK deployment

### 2. **Code Reuse**
- **Shared Logic**: Common Lambda utilities in `shared/` directory
- **Function-Specific**: Only entry points in individual function directories
- **Minimal Duplication**: Business logic shared between functions

### 3. **AWS Lambda Best Practices**
- **Container Reuse**: Global initialization with lazy loading
- **Minimal Dependencies**: Only necessary packages included in deployment
- **Structured Logging**: JSON logging for CloudWatch integration
- **Performance Optimization**: HTTP session reuse and efficient resource management

## Shared Components

### `shared/lambda_handler.py`
Contains common Lambda utilities:
- **Event Parsing**: AgentCore event format handling
- **Response Formatting**: Proper AgentCore response structure
- **Error Handling**: Comprehensive error handling with proper categorization
- **Tracing**: OpenTelemetry integration with Lambda context
- **Logging**: Structured JSON logging for CloudWatch

### `shared/weather_tools.py`
Contains business logic:
- **Weather Handler**: Weather information retrieval from National Weather Service
- **Alerts Handler**: Weather alerts retrieval with proper formatting
- **API Integration**: HTTP client management and error handling
- **Data Processing**: Response formatting and validation

## Function Implementations

### `get_weather/lambda_function.py`
- **Purpose**: Entry point for weather information retrieval
- **Handler**: `lambda_handler(event, context)`
- **Dependencies**: Imports from shared components
- **Deployment**: Packaged as standalone Lambda function

### `get_alerts/lambda_function.py`
- **Purpose**: Entry point for weather alerts retrieval
- **Handler**: `lambda_handler(event, context)`
- **Dependencies**: Imports from shared components
- **Deployment**: Packaged as standalone Lambda function

## Deployment Process

### 1. **Packaging**
The CDK deployment script automatically:
1. Copies shared components to each function directory
2. Copies function-specific entry points
3. Installs required dependencies
4. Creates deployment packages

### 2. **Dependencies**
Each Lambda function includes:
- `requests`: HTTP client for weather API calls
- `opentelemetry-*`: Distributed tracing and observability
- Shared Lambda handler code
- Function-specific entry point

### 3. **Environment Variables**
- `WEATHER_API_BASE_URL`: National Weather Service API base URL
- `WEATHER_API_TIMEOUT`: API request timeout in seconds
- `USER_AGENT_WEATHER`: User agent for weather requests
- `USER_AGENT_ALERTS`: User agent for alerts requests
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry endpoint (optional)

## Benefits of This Structure

### 1. **Clean Separation**
- Application code stays in `src/` for local development
- Lambda code isolated in `infrastructure/` for deployment
- No unnecessary dependencies in Lambda packages

### 2. **Maintainability**
- Shared logic in one place reduces duplication
- Function-specific code is minimal and focused
- Easy to add new Lambda functions

### 3. **Performance**
- Minimal package size for faster cold starts
- Only necessary dependencies included
- Optimized for Lambda execution environment

### 4. **Testing**
- Shared components can be unit tested independently
- Function entry points are simple and testable
- Integration tests can validate end-to-end functionality

### 5. **Security**
- No application secrets or configuration in Lambda packages
- Minimal attack surface with focused functionality
- Proper error handling prevents information leakage

## Usage

### Local Development
```bash
# Test shared components
python -m pytest infrastructure/lambda_functions/shared/

# Test function entry points
python -m pytest infrastructure/lambda_functions/get_weather/
python -m pytest infrastructure/lambda_functions/get_alerts/
```

### Deployment
```bash
# Deploy via CDK
cd infrastructure
python deploy.py

# Or manual CDK commands
cdk deploy
```

### Testing Deployed Functions
```bash
# Test weather function
aws lambda invoke \
  --function-name agentcore-weather-get-weather \
  --payload '{"parameters":[{"name":"latitude","value":"47.6062"},{"name":"longitude","value":"-122.3321"}]}' \
  response.json

# Test alerts function
aws lambda invoke \
  --function-name agentcore-weather-get-alerts \
  --payload '{"parameters":[{"name":"latitude","value":"47.6062"},{"name":"longitude","value":"-122.3321"}]}' \
  response.json
```

This structure follows AWS Lambda best practices and ensures clean separation between application code and Lambda deployment artifacts.