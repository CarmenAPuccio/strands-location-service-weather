# Bedrock Guardrails Best Practices Implementation

This document outlines the AWS Bedrock Guardrails best practices implemented in the location weather service, based on AWS documentation and industry standards.

## Overview

Our implementation follows AWS best practices for Bedrock Guardrails in location services:
- **Layered Security**: Guardrails applied at both model and agent levels
- **Location-Specific Configuration**: Optimized PII handling for weather/location queries
- **Comprehensive Protection**: Content filtering, PII detection, and prompt injection prevention
- **Monitoring and Validation**: Health checks and deployment validation

## Best Practices Implemented

### 1. Layered Security Architecture

Following AWS recommendations, we implement guardrails at multiple levels:

#### Model-Level Guardrails (Bedrock Models)
```python
# Applied directly to BedrockModel instances
model_params = GuardrailIntegration.apply_model_level_guardrails(
    model_params, guardrail_config
)
```

#### Agent-Level Guardrails (AgentCore)
```python
# Applied to AgentCore agents for additional protection
agent_params = GuardrailIntegration.apply_agent_level_guardrails(
    agent_params, guardrail_config
)
```

### 2. Location Service-Optimized PII Configuration

Our PII configuration is specifically tailored for location services:

#### ✅ Allowed PII Types (Essential for Location Services)
- `ADDRESS` - Street addresses for weather queries
- `US_STATE` - State names for regional weather
- `CITY` - City names for local weather
- `ZIP_CODE` - Postal codes for precise location
- `COUNTRY` - Country names for international queries

#### ❌ Blocked PII Types (Not Needed for Weather Service)
- `PHONE` - Phone numbers (no legitimate use case)
- `EMAIL` - Email addresses (no legitimate use case)
- `SSN` - Social Security Numbers (sensitive)
- `CREDIT_DEBIT_CARD_NUMBER` - Financial data (sensitive)
- `NAME` - Personal names (privacy protection)
- `USERNAME` - Usernames (not needed)

### 3. Content Filtering Configuration

Appropriate filter strengths for location services:

```python
content_filters = [
    {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},  # Less strict
    {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"}
]
```

### 4. Prompt Injection Protection

Comprehensive pattern-based detection:

#### Detection Patterns
- **Direct Instructions**: "ignore previous instructions", "forget everything"
- **Role Manipulation**: "act as", "pretend to be", "roleplay as"
- **Code Injection**: Code blocks, script tags, execution commands
- **Jailbreak Attempts**: "jailbreak", "DAN mode", "developer mode"
- **Data Extraction**: Attempts to reveal system information

#### Location Context Awareness
```python
# Reduces false positives for legitimate location queries
location_keywords = [
    "weather", "temperature", "forecast", "rain", "snow",
    "location", "address", "place", "city", "state",
    "route", "directions", "nearby", "find", "search"
]
```

### 5. Deployment Validation

Following AWS best practices for guardrail deployment:

```python
# Validate guardrail is deployed and ready
is_ready = GuardrailIntegration.validate_guardrail_deployment(guardrail_id)

# Get usage metrics for monitoring
metrics = GuardrailIntegration.get_guardrail_metrics(guardrail_id)
```

### 6. Comprehensive Validation Pipeline

Multi-layered validation approach:

```python
validation_result = validate_location_query_safety(query, config)
# Returns:
# - Bedrock Guardrails validation
# - Prompt injection detection
# - Location context analysis
# - Safety recommendations
```

## Configuration Examples

### Environment Variables
```bash
# Guardrail Configuration
GUARDRAIL_ID=your-guardrail-id
GUARDRAIL_VERSION=DRAFT
GUARDRAIL_CONTENT_FILTERING=true
GUARDRAIL_PII_DETECTION=true
GUARDRAIL_TOXICITY_DETECTION=true

# Filter Strengths
GUARDRAIL_CONTENT_FILTER_STRENGTH=HIGH
GUARDRAIL_PII_FILTER_STRENGTH=HIGH
GUARDRAIL_TOXICITY_FILTER_STRENGTH=HIGH
```

### Config File (config.toml)
```toml
[guardrail]
guardrail_id = "your-guardrail-id"
guardrail_version = "DRAFT"
enable_content_filtering = true
enable_pii_detection = true
enable_toxicity_detection = true
content_filter_strength = "HIGH"
pii_filter_strength = "HIGH"
toxicity_filter_strength = "HIGH"
```

## CDK Infrastructure

Use our optimized guardrail policy for infrastructure deployment:

```python
from src.strands_location_service_weather.guardrails import create_location_service_guardrail_policy

# Get CDK-ready guardrail configuration
guardrail_policy = create_location_service_guardrail_policy()

# Deploy with CDK
guardrail = bedrock.CfnGuardrail(
    self, "LocationServiceGuardrail",
    **guardrail_policy
)
```

## Monitoring and Metrics

### Health Checks
- Guardrail deployment validation
- Configuration validation
- Model integration testing

### Metrics to Monitor
- Guardrail invocation count
- Content blocking rate
- PII detection rate
- Prompt injection attempts
- False positive rate

### CloudWatch Metrics
```python
# Monitor guardrail effectiveness
metrics = GuardrailIntegration.get_guardrail_metrics(guardrail_id)
```

## Security Considerations

### Production Deployment
1. **Use specific guardrail versions** (not "DRAFT") in production
2. **Enable CloudTrail logging** for guardrail invocations
3. **Implement least-privilege IAM policies**
4. **Regular security reviews** of guardrail effectiveness
5. **Monitor false positive rates** and adjust as needed

### Testing Strategy
- Unit tests for all guardrail components (33 tests implemented)
- Integration tests with actual Bedrock services
- Security testing with known attack vectors
- Performance testing under load

## Compliance and Governance

### Data Privacy
- PII detection configured for location service requirements
- Personal information blocked while allowing location data
- Audit trail for all guardrail decisions

### Content Safety
- Multi-layered content filtering
- Prompt injection prevention
- Inappropriate content blocking
- Context-aware validation

## References

- [AWS Bedrock Guardrails Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [AWS Bedrock AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-learning/)

## Implementation Status

✅ **Completed**
- GuardrailConfig dataclass with location-specific settings
- Guardrail validation and testing utilities
- Prompt injection protection with comprehensive patterns
- Integration utilities for model and agent level application
- Comprehensive test suite (33 tests)
- CDK-ready infrastructure configuration
- Monitoring and health check utilities

This implementation provides enterprise-grade security for location weather services while maintaining usability for legitimate queries.