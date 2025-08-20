# Bedrock Agent Weather Tools Infrastructure

This directory contains AWS CDK infrastructure code for deploying weather and alerts tools as Lambda functions for use with Amazon Bedrock Agents.

## Project Structure

```
infrastructure/
├── app.py                      # CDK application entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # CDK Python dependencies
├── deploy.py                   # Deployment automation script
├── build_lambda_layers.py      # Lambda layers and functions build script
├── README.md                   # This file
├── stacks/
│   ├── __init__.py
│   └── bedrock_agent_stack.py  # Main CDK stack definition
├── cdk_lib/
│   ├── __init__.py
│   ├── lambda_construct.py     # Lambda functions construct (with layers)
│   └── bedrock_construct.py    # Bedrock agent construct
├── lambda_functions/           # Original Lambda function source
│   ├── shared/
│   ├── get_weather/
│   └── get_alerts/

└── layers/                     # Generated Lambda layers
    ├── dependencies/           # Python dependencies layer
    └── shared-code/           # Shared code layer
```

## Quick Start

### Prerequisites

1. **Install dependencies**: Ensure you have uv installed and run `uv sync` from the project root
2. **Configure AWS credentials**: Set up your AWS credentials via `aws configure` or environment variables
3. **Install AWS CDK CLI**: See the [CDK Deployment Notes](../docs/DEPLOYMENT_NOTES.md) for detailed setup instructions

### Build and Deploy

1. **Build Lambda layers and functions**:
   ```bash
   uv run python infrastructure/build_lambda_layers.py
   ```

2. **Deploy the stack**:
   ```bash
   cd infrastructure && cdk deploy
   ```

## Configuration

### Environment Variables

The deployment can be configured using environment variables:

```bash
export FUNCTION_PREFIX="bedrock-agent-weather"
export WEATHER_API_TIMEOUT="10"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://your-endpoint"
export LOG_RETENTION_DAYS="14"
export AWS_REGION="us-east-1"
```

### Command Line Options

```bash
python deploy.py --help
```

Available options:

- `--region`: AWS region (default: us-east-1)
- `--profile`: AWS profile name
- `--function-prefix`: Prefix for function names
- `--weather-api-timeout`: Weather API timeout in seconds
- `--otlp-endpoint`: OpenTelemetry OTLP endpoint
- `--log-retention-days`: CloudWatch log retention
- `--auto-approve`: Skip confirmation prompts
- `--destroy`: Destroy the stack
- `--schemas-only`: Export OpenAPI schemas only

## Architecture

### Components Created

1. **Lambda Functions**:

   - `{prefix}-get-weather`: Weather information retrieval
   - `{prefix}-get-alerts`: Weather alerts retrieval

2. **IAM Roles**:

   - Lambda execution role with CloudWatch and X-Ray permissions
   - Bedrock Agent role with Lambda invoke permissions

3. **Bedrock Resources**:

   - Guardrail for content filtering and security
   - Bedrock Agent with action groups

4. **Monitoring**:
   - CloudWatch log groups with configurable retention
   - X-Ray tracing enabled

### Security Features

- **Content Filtering**: Blocks inappropriate content
- **PII Protection**: Blocks sensitive personal information
- **Topic Restrictions**: Limits responses to weather/location topics
- **Least Privilege**: Minimal required IAM permissions

## Development

For detailed development instructions, testing procedures, and deployment workflows, see the [CDK Deployment Notes](../docs/DEPLOYMENT_NOTES.md).

## Deployment

### Lambda Deployment with CDK

The infrastructure uses AWS CDK for automated deployment with Lambda layers for optimal performance and maintainability.

#### 1. Build Lambda Layers

```bash
# Build dependencies and shared code layers
uv run python infrastructure/build_lambda_layers.py
```

This creates:
- **Dependencies layer**: Python packages (requests, opentelemetry, etc.)
- **Shared code layer**: Common Lambda utilities and source modules

#### 2. Deploy Infrastructure

```bash
# Deploy the complete stack
cd infrastructure && cdk deploy
```

This creates:
- **Lambda Functions**: `get_weather` and `get_alerts` with layers
- **IAM Roles**: Execution roles with minimal required permissions
- **Bedrock Agent**: Bedrock Agent with action groups
- **Guardrails**: Content filtering and security policies
- **Monitoring**: CloudWatch logs and X-Ray tracing

#### 3. Bedrock Agent Integration

The deployed Lambda functions are automatically configured as Bedrock Agent action groups:

- **Weather Action Group**: `/get_weather` endpoint
- **Alerts Action Group**: `/get_alerts` endpoint
- **OpenAPI Schemas**: Auto-generated from function signatures
- **Error Handling**: Standardized Bedrock Agent response format

#### Environment Variables

Key Lambda environment variables (set automatically by CDK):

```bash
WEATHER_API_TIMEOUT=10                    # Weather API timeout
OTEL_SERVICE_NAME=location-weather-lambda # Tracing service name
AWS_REGION=us-east-1                     # AWS region
```

#### Testing Deployed Functions

```bash
# Test weather function
aws lambda invoke \
  --function-name bedrock-agent-weather-get-weather \
  --payload '{"parameters":[{"name":"latitude","value":"47.6062","type":"number"},{"name":"longitude","value":"-122.3321","type":"number"}]}' \
  response.json

# Test alerts function  
aws lambda invoke \
  --function-name bedrock-agent-weather-get-alerts \
  --payload '{"parameters":[{"name":"latitude","value":"47.6062","type":"number"},{"name":"longitude","value":"-122.3321","type":"number"}]}' \
  response.json
```

For detailed deployment instructions and best practices, see [CDK Deployment Notes](../docs/DEPLOYMENT_NOTES.md).

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Required**:

   ```bash
   cdk bootstrap
   ```

2. **Permission Denied**:

   - Check AWS credentials and permissions
   - Ensure IAM user has CDK deployment permissions

3. **Lambda Layer Build Issues**:

   - Ensure `uv` is installed and available
   - Run `uv run python infrastructure/build_lambda_layers.py` to rebuild layers
   - Check that dependencies are properly installed in the layers

4. **Bedrock Service Not Available**:
   - Ensure Bedrock is available in your region
   - Check service quotas and limits

### Debug Mode

Enable verbose CDK output:

```bash
cdk deploy --verbose
```

View CloudWatch logs:

```bash
aws logs tail /aws/lambda/bedrock-agent-weather-get-weather --follow
```

## Cost Optimization

- Lambda functions use minimal memory (256MB)
- CloudWatch logs have configurable retention
- X-Ray tracing can be disabled if not needed
- Consider reserved capacity for high-traffic scenarios

## Security Considerations

- All resources follow least-privilege access
- Bedrock Guardrails prevent misuse
- Lambda functions run in isolated environments
- CloudTrail logging recommended for audit trails
