# Infrastructure Guidelines

## Lambda Function Architecture

The project uses Lambda functions for Bedrock Agent integration, with shared utilities and per-function handlers.

### Lambda Functions

```
infrastructure/lambda_functions/
├── shared/
│   ├── lambda_handler.py    # Common Bedrock Agent event handling + OpenTelemetry
│   └── weather_tools.py     # Shared weather tool implementations
├── get_weather/
│   └── lambda_function.py   # Current weather conditions
├── get_alerts/
│   └── lambda_function.py   # Weather alerts and warnings
├── search_places/
│   └── lambda_function.py   # Amazon Location Service place search
└── calculate_route/
    └── lambda_function.py   # Amazon Location Service routing
```

### Bedrock Agent Event Contract

Lambda functions follow the Bedrock Agent action group format:
- Input: parameters extracted from the agent's parsed request
- Output: `{'response': {'body': json_string}}` format
- Error: same format with error details in body

### CDK Constructs

```
infrastructure/cdk_lib/
├── bedrock_construct.py    # BedrockAgentConstruct: agent + guardrails
├── lambda_construct.py     # WeatherLambdaConstruct: functions + layers
└── location_construct.py   # LocationConstruct: Amazon Location Service resources
```

#### Stack: `bedrock_agent_stack.py`
- Composes all constructs into a single deployable stack
- Configurable parameters for environment-specific deployment

## Deployment

### CDK Deployment

```bash
# From infrastructure/ directory
python deploy.py
```

The deploy script handles:
1. Lambda layer building (`build_lambda_layers.py`)
2. CDK synthesis and deployment
3. Post-deployment validation

### Resource Naming Convention

- **Lambda Functions**: `location-weather-{tool-name}`
- **IAM Roles**: `location-weather-lambda-{tool-name}-role`
- **Log Groups**: `/aws/lambda/location-weather-{tool-name}`
- **Bedrock Agent**: `location-weather-agent`

### IAM Permissions

Lambda execution roles follow least-privilege:
- CloudWatch Logs for function logging
- Weather Lambda: outbound HTTPS only (public NWS API)
- Location Lambda: `geo:SearchPlaceIndexForText`, `geo:CalculateRoute`
- Bedrock Agent role: `lambda:InvokeFunction` for its action group Lambdas

### Guardrails Configuration

- Content filtering: HIGH for sexual/violence/hate, MEDIUM for insults
- PII detection: blocks phone, email, SSN, credit cards
- ADDRESS intentionally excluded from PII blocking (required for location services)

## Testing Infrastructure

### Lambda Function Tests
- `test_lambda_handler.py`: Bedrock Agent event/response format compliance
- `test_lambda_functions.py`: Individual function logic
- `test_infrastructure_complete.py`: CDK stack synthesis and resource validation

### Performance
- Lambda memory: 256MB
- Lambda timeout: 30 seconds
- HTTP session reuse within execution context for weather API calls
