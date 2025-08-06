# AgentCore Weather Tools Infrastructure

This directory contains AWS CDK infrastructure code for deploying weather and alerts tools as Lambda functions for use with Amazon Bedrock AgentCore.

## Project Structure

```
infrastructure/
├── app.py                      # CDK application entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # CDK Python dependencies
├── deploy.py                   # Deployment automation script
├── README.md                   # This file
├── stacks/
│   ├── __init__.py
│   └── agentcore_stack.py      # Main CDK stack definition
├── constructs/
│   ├── __init__.py
│   ├── lambda_construct.py     # Lambda functions construct
│   └── bedrock_construct.py    # Bedrock agent construct
└── lambda-packages/            # Generated Lambda deployment packages
    ├── get-weather/
    └── get-alerts/
```

## Quick Start

### Prerequisites

1. **Install AWS CDK CLI**:
   ```bash
   npm install -g aws-cdk
   ```

2. **Configure AWS credentials**:
   ```bash
   aws configure
   # or set environment variables
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   export AWS_REGION=us-east-1
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Deployment

#### Option 1: Automated Deployment (Recommended)

```bash
# Basic deployment
python deploy.py

# Custom configuration
python deploy.py \
  --region us-west-2 \
  --function-prefix my-weather \
  --weather-api-timeout 15 \
  --auto-approve
```

#### Option 2: Manual CDK Commands

```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Synthesize stack
cdk synth

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy
```

## Configuration

### Environment Variables

The deployment can be configured using environment variables:

```bash
export FUNCTION_PREFIX="agentcore-weather"
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
   - AgentCore agent role with Lambda invoke permissions

3. **Bedrock Resources**:
   - Guardrail for content filtering and security
   - AgentCore agent with action groups

4. **Monitoring**:
   - CloudWatch log groups with configurable retention
   - X-Ray tracing enabled

### Security Features

- **Content Filtering**: Blocks inappropriate content
- **PII Protection**: Blocks sensitive personal information
- **Topic Restrictions**: Limits responses to weather/location topics
- **Least Privilege**: Minimal required IAM permissions

## Development

### Adding New Constructs

1. Create new construct in `constructs/` directory
2. Import and use in `stacks/agentcore_stack.py`
3. Update tests and documentation

### Modifying Lambda Functions

1. Update source code in `../src/strands_location_service_weather/`
2. Run deployment script to repackage and deploy
3. Test changes using AWS Console or CLI

### Testing

```bash
# Synthesize without deploying
cdk synth

# Validate stack
cdk diff

# Export schemas for validation
python deploy.py --schemas-only
```

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Required**:
   ```bash
   cdk bootstrap
   ```

2. **Permission Denied**:
   - Check AWS credentials and permissions
   - Ensure IAM user has CDK deployment permissions

3. **Lambda Package Too Large**:
   - Check dependencies in Lambda packages
   - Consider using Lambda layers for large dependencies

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
aws logs tail /aws/lambda/agentcore-weather-get-weather --follow
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