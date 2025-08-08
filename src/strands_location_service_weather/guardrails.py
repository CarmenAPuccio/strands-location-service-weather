"""Bedrock Guardrails utilities for location weather service.

This module implements AWS Bedrock Guardrails best practices for location services:
- Content filtering with appropriate strength levels
- PII detection with location-specific exceptions
- Prompt injection protection with pattern matching
- Integration with both Bedrock models and AgentCore agents

Best Practices Implemented:
- Layered security (model + agent level guardrails)
- Location-appropriate PII handling (allow ADDRESS, block sensitive data)
- Comprehensive prompt injection detection
- Proper error handling and logging
- Configuration validation and testing

References:
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

from .config import GuardrailConfig

logger = logging.getLogger(__name__)


@dataclass
class GuardrailValidationResult:
    """Result of guardrail validation."""

    is_valid: bool
    blocked_content: list[str]
    pii_detected: list[str]
    toxicity_detected: bool
    error_message: str | None = None


class GuardrailValidator:
    """Validates content against Bedrock Guardrails."""

    def __init__(self, config: GuardrailConfig, region_name: str = "us-east-1"):
        """Initialize the guardrail validator.

        Args:
            config: Guardrail configuration
            region_name: AWS region name
        """
        self.config = config
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=region_name)

    def validate_content(self, content: str) -> GuardrailValidationResult:
        """Validate content against configured guardrails.

        Args:
            content: Text content to validate

        Returns:
            GuardrailValidationResult with validation details
        """
        if not self.config.guardrail_id:
            logger.warning("No guardrail ID configured, skipping validation")
            return GuardrailValidationResult(
                is_valid=True,
                blocked_content=[],
                pii_detected=[],
                toxicity_detected=False,
            )

        try:
            response = self.bedrock_runtime.apply_guardrail(
                guardrailIdentifier=self.config.guardrail_id,
                guardrailVersion=self.config.guardrail_version,
                source="INPUT",
                content=[{"text": {"text": content}}],
            )

            # Parse response
            action = response.get("action", "NONE")
            is_valid = action != "GUARDRAIL_INTERVENED"

            blocked_content = []
            pii_detected = []
            toxicity_detected = False

            # Extract details from outputs if available
            outputs = response.get("outputs", [])
            for output in outputs:
                if "text" in output:
                    # Check for content filtering
                    if "contentPolicy" in response:
                        for filter_result in response["contentPolicy"].get(
                            "filters", []
                        ):
                            if filter_result.get("action") == "BLOCKED":
                                blocked_content.append(
                                    filter_result.get("type", "UNKNOWN")
                                )

                    # Check for PII detection
                    if "sensitiveInformationPolicy" in response:
                        for pii_result in response["sensitiveInformationPolicy"].get(
                            "piiEntities", []
                        ):
                            if pii_result.get("action") == "BLOCKED":
                                pii_detected.append(pii_result.get("type", "UNKNOWN"))

                    # Check for toxicity
                    if "toxicity" in response:
                        toxicity_detected = response["toxicity"].get("score", 0) > 0.5

            return GuardrailValidationResult(
                is_valid=is_valid,
                blocked_content=blocked_content,
                pii_detected=pii_detected,
                toxicity_detected=toxicity_detected,
            )

        except ClientError as e:
            error_msg = f"Guardrail validation failed: {e}"
            logger.error(error_msg)
            return GuardrailValidationResult(
                is_valid=False,
                blocked_content=[],
                pii_detected=[],
                toxicity_detected=False,
                error_message=error_msg,
            )

    def is_location_query_safe(self, query: str) -> bool:
        """Check if a location query is safe for processing.

        This method performs basic validation for location queries,
        allowing address-related content while blocking other sensitive information.

        Args:
            query: User query to validate

        Returns:
            True if query is safe to process
        """
        # First check with guardrails
        result = self.validate_content(query)

        # If guardrails blocked it, check if it's only due to address content
        if not result.is_valid:
            # If content was blocked for reasons other than PII, it's not safe
            if result.blocked_content or result.toxicity_detected:
                logger.warning(
                    f"Query blocked due to content policy or toxicity: {query}"
                )
                return False

            # If only PII was detected, check if it's address-related
            if result.pii_detected:
                address_related_pii = {
                    "ADDRESS",
                    "US_STATE",
                    "CITY",
                    "ZIP_CODE",
                    "COUNTRY",
                }
                detected_pii = set(result.pii_detected)

                # If all detected PII is address-related, consider it safe
                if detected_pii.issubset(address_related_pii):
                    logger.info(
                        f"Allowing location query with address PII: {detected_pii}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Query blocked due to non-address PII: {detected_pii}"
                    )
                    return False

            # If blocked for unknown reasons, err on the side of caution
            logger.warning(f"Query blocked for unknown reasons: {query}")
            return False

        return result.is_valid


class PromptInjectionDetector:
    """Detects potential prompt injection attempts."""

    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction attempts
        r"(?i)(ignore|forget|disregard).*(previous|above|earlier).*(instruction|prompt|rule)",
        r"(?i)(ignore|forget|disregard).*(instruction|prompt|rule)",
        r"(?i)(system|assistant|ai).*(prompt|instruction|rule)",
        r"(?i)act\s+as\s+(if\s+you\s+are\s+)?(?!.*weather|.*location)",
        # Role manipulation - more specific patterns
        r"(?i)you\s+are\s+(now\s+)?(a\s+|an\s+)?(?!.*weather|.*location|.*assistant|.*service|.*helpful)(pirate|hacker|criminal|different|evil)",
        r"(?i)you\s+are\s+now\s+a\s+",
        r"(?i)pretend\s+(to\s+be|you\s+are)",
        r"(?i)roleplay\s+as",
        # Instruction injection
        r"(?i)new\s+(instruction|rule|prompt)",
        r"(?i)override\s+(previous|system|default)",
        r"(?i)instead\s+of.*do",
        # Code injection attempts
        r"```\s*(?:python|javascript|sql|bash|sh|cmd)",
        r"<script[^>]*>",
        r"(?i)execute\s+(this\s+)?(code|command|script)",
        r"(?i)execute\s+this\s*:",
        r"(?i)print\s*\(\s*['\"].*['\"]",
        r"(?i)(run|execute)\s+(this|the\s+following)\s*:",
        # Data extraction attempts
        r"(?i)(show|display|print|output).*(system|internal|hidden|secret)",
        r"(?i)(reveal|expose|leak).*(prompt|instruction|rule)",
        r"(?i)(tell|show)\s+me.*(secret|hidden|internal)",
        # Jailbreak attempts
        r"(?i)jailbreak",
        r"(?i)dan\s+mode",
        r"(?i)developer\s+mode",
        # Additional common patterns
        r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions",
        r"(?i)forget\s+(everything|all)",
        r"(?i)forget\s+(the\s+)?(weather|location)",
        r"(?i)system\s*:\s*override",
    ]

    def __init__(self):
        """Initialize the prompt injection detector."""
        self.compiled_patterns = [
            re.compile(pattern) for pattern in self.INJECTION_PATTERNS
        ]

    def detect_injection(self, text: str) -> dict[str, Any]:
        """Detect potential prompt injection in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with detection results
        """
        detected_patterns = []

        for i, pattern in enumerate(self.compiled_patterns):
            matches = pattern.findall(text)
            if matches:
                detected_patterns.append(
                    {
                        "pattern_index": i,
                        "pattern": self.INJECTION_PATTERNS[i],
                        "matches": matches,
                    }
                )

        is_injection = len(detected_patterns) > 0

        # Calculate risk score based on number of patterns matched
        risk_score = min(len(detected_patterns) / len(self.INJECTION_PATTERNS), 1.0)

        return {
            "is_injection": is_injection,
            "risk_score": risk_score,
            "detected_patterns": detected_patterns,
            "recommendation": "BLOCK" if is_injection else "ALLOW",
        }

    def is_safe_location_query(self, query: str) -> bool:
        """Check if query is a safe location/weather query.

        Args:
            query: User query to check

        Returns:
            True if query appears to be a legitimate location/weather query
        """
        detection_result = self.detect_injection(query)

        # If no injection detected, it's safe
        if not detection_result["is_injection"]:
            return True

        # If injection detected, be very strict about allowing it
        # Only allow very specific false positive cases with very low risk
        location_keywords = [
            "weather",
            "temperature",
            "forecast",
            "rain",
            "snow",
            "storm",
            "location",
            "address",
            "place",
            "city",
            "state",
            "country",
            "route",
            "directions",
            "nearby",
            "find",
            "search",
        ]

        query_lower = query.lower()
        has_location_keywords = any(
            keyword in query_lower for keyword in location_keywords
        )

        # Check for high-risk injection patterns that should never be allowed
        high_risk_patterns = [
            "ignore",
            "forget",
            "disregard",
            "act as",
            "you are now",
            "pretend",
            "roleplay",
            "execute",
            "system",
            "override",
            "jailbreak",
            "developer mode",
            "dan mode",
        ]

        has_high_risk = any(pattern in query_lower for pattern in high_risk_patterns)

        # If it has high-risk patterns, never allow it regardless of location keywords
        if has_high_risk:
            return False

        # Only allow if it has location keywords, very low risk score, and no high-risk patterns
        if has_location_keywords and detection_result["risk_score"] < 0.1:
            logger.warning(f"Potential false positive for location query: {query}")
            return True

        return False


def create_guardrail_cdk_config(config: GuardrailConfig) -> dict[str, Any]:
    """Create CDK configuration for Bedrock Guardrail.

    Args:
        config: Guardrail configuration

    Returns:
        Dictionary suitable for CDK CfnGuardrail construct
    """
    cdk_config = {
        "name": "location-weather-guardrail",
        "description": "Guardrail for location weather service with address PII allowed",
    }

    # Add content policy if enabled
    if config.enable_content_filtering:
        cdk_config["contentPolicyConfig"] = {
            "filtersConfig": config.get_content_filters_config()
        }

    # Add sensitive information policy if enabled
    if config.enable_pii_detection:
        cdk_config["sensitiveInformationPolicyConfig"] = {
            "piiEntitiesConfig": config.get_pii_entities_config()
        }

    # Add word policy for additional protection
    cdk_config["wordPolicyConfig"] = {
        "wordsConfig": [
            {"text": "IGNORE PREVIOUS INSTRUCTIONS"},
            {"text": "SYSTEM PROMPT"},
            {"text": "JAILBREAK"},
        ],
        "managedWordListsConfig": [{"type": "PROFANITY"}],
    }

    return cdk_config


def validate_guardrail_config(config: GuardrailConfig) -> list[str]:
    """Validate guardrail configuration.

    Args:
        config: Guardrail configuration to validate

    Returns:
        List of validation errors (empty if valid)
    """
    return config.validate()


class GuardrailIntegration:
    """Integration utilities for Bedrock Guardrails following AWS best practices."""

    @staticmethod
    def apply_model_level_guardrails(
        model_params: dict[str, Any], config: GuardrailConfig
    ) -> dict[str, Any]:
        """Apply guardrails at the model level (Bedrock models).

        This follows AWS best practice of applying guardrails at the model level
        for direct Bedrock model invocations.

        Args:
            model_params: Model parameters dictionary
            config: Guardrail configuration

        Returns:
            Updated model parameters with guardrail configuration
        """
        if config.guardrail_id:
            model_params["guardrail_id"] = config.guardrail_id
            model_params["guardrail_version"] = config.guardrail_version

            # Add guardrail configuration for content filtering
            if config.enable_content_filtering:
                model_params["guardrail_content_filtering"] = True

            if config.enable_pii_detection:
                model_params["guardrail_pii_detection"] = True

            if config.enable_toxicity_detection:
                model_params["guardrail_toxicity_detection"] = True

            logging.info(f"Applied model-level guardrails: {config.guardrail_id}")

        return model_params

    @staticmethod
    def apply_agent_level_guardrails(
        agent_params: dict[str, Any], config: GuardrailConfig
    ) -> dict[str, Any]:
        """Apply guardrails at the agent level (AgentCore agents).

        This follows AWS best practice of applying guardrails at the agent level
        for AgentCore invocations, providing additional safety controls.

        Args:
            agent_params: Agent parameters dictionary
            config: Guardrail configuration

        Returns:
            Updated agent parameters with guardrail configuration
        """
        if config.guardrail_id:
            agent_params["guardrail_id"] = config.guardrail_id
            agent_params["guardrail_version"] = config.guardrail_version

            # AgentCore supports additional guardrail configurations
            agent_params["guardrail_config"] = {
                "content_filtering": config.enable_content_filtering,
                "pii_detection": config.enable_pii_detection,
                "toxicity_detection": config.enable_toxicity_detection,
                "content_filter_strength": config.content_filter_strength,
                "pii_filter_strength": config.pii_filter_strength,
                "toxicity_filter_strength": config.toxicity_filter_strength,
            }

            logging.info(f"Applied agent-level guardrails: {config.guardrail_id}")

        return agent_params

    @staticmethod
    def validate_guardrail_deployment(
        guardrail_id: str, region_name: str = "us-east-1"
    ) -> bool:
        """Validate that a guardrail is properly deployed and accessible.

        This follows AWS best practice of validating guardrail availability
        before using it in production.

        Args:
            guardrail_id: Guardrail identifier
            region_name: AWS region name

        Returns:
            True if guardrail is accessible, False otherwise
        """
        try:
            bedrock_client = boto3.client("bedrock", region_name=region_name)

            response = bedrock_client.get_guardrail(guardrailIdentifier=guardrail_id)

            status = response.get("status", "UNKNOWN")
            if status == "READY":
                logging.info(f"Guardrail {guardrail_id} is ready for use")
                return True
            else:
                logging.warning(f"Guardrail {guardrail_id} status: {status}")
                return False

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                logging.error(f"Guardrail {guardrail_id} not found")
            else:
                logging.error(f"Error validating guardrail {guardrail_id}: {e}")
            return False

    @staticmethod
    def get_guardrail_metrics(
        guardrail_id: str, region_name: str = "us-east-1"
    ) -> dict[str, Any]:
        """Get guardrail usage metrics for monitoring.

        This follows AWS best practice of monitoring guardrail effectiveness
        and usage patterns.

        Args:
            guardrail_id: Guardrail identifier
            region_name: AWS region name

        Returns:
            Dictionary with guardrail metrics
        """
        try:
            cloudwatch = boto3.client("cloudwatch", region_name=region_name)

            # Get guardrail invocation metrics
            response = cloudwatch.get_metric_statistics(
                Namespace="AWS/Bedrock",
                MetricName="GuardrailInvocations",
                Dimensions=[{"Name": "GuardrailId", "Value": guardrail_id}],
                StartTime=boto3.Session().region_name,  # Last 24 hours
                EndTime=boto3.Session().region_name,
                Period=3600,  # 1 hour periods
                Statistics=["Sum"],
            )

            return {
                "guardrail_id": guardrail_id,
                "invocations": response.get("Datapoints", []),
                "status": "active" if response.get("Datapoints") else "inactive",
            }

        except Exception as e:
            logging.error(f"Error getting guardrail metrics: {e}")
            return {"guardrail_id": guardrail_id, "error": str(e), "status": "error"}


def create_location_service_guardrail_policy() -> dict[str, Any]:
    """Create a guardrail policy optimized for location services.

    This follows AWS best practices for location service guardrails:
    - Allow location-related PII (addresses, cities, states)
    - Block sensitive personal information
    - Filter inappropriate content while allowing location queries

    Returns:
        Dictionary with guardrail policy configuration
    """
    return {
        "name": "LocationServiceGuardrail",
        "description": "Guardrail optimized for weather and location services",
        "contentPolicyConfig": {
            "filtersConfig": [
                {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {
                    "type": "INSULTS",
                    "inputStrength": "MEDIUM",  # Less strict for location queries
                    "outputStrength": "MEDIUM",
                },
                {
                    "type": "MISCONDUCT",
                    "inputStrength": "HIGH",
                    "outputStrength": "HIGH",
                },
            ]
        },
        "sensitiveInformationPolicyConfig": {
            "piiEntitiesConfig": [
                # Block sensitive financial/identity PII
                {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
                {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
                {"type": "US_BANK_ACCOUNT_NUMBER", "action": "BLOCK"},
                {"type": "US_BANK_ROUTING_NUMBER", "action": "BLOCK"},
                {"type": "US_PASSPORT_NUMBER", "action": "BLOCK"},
                {"type": "DRIVER_ID", "action": "BLOCK"},
                {"type": "LICENSE_PLATE", "action": "BLOCK"},
                {"type": "PASSWORD", "action": "BLOCK"},
                # Removed VEHICLE_VIN and PIN as they may not be supported in all regions
                # Block contact info (not needed for weather/location service)
                {"type": "PHONE", "action": "BLOCK"},
                {"type": "EMAIL", "action": "BLOCK"},
                {"type": "USERNAME", "action": "BLOCK"},
                {"type": "NAME", "action": "BLOCK"},
                # Note: ADDRESS, US_STATE, CITY, ZIP_CODE, COUNTRY are NOT blocked
                # These are essential for location service functionality
            ]
        },
        "wordPolicyConfig": {
            "wordsConfig": [
                {"text": "IGNORE PREVIOUS INSTRUCTIONS"},
                {"text": "SYSTEM PROMPT"},
                {"text": "JAILBREAK"},
                {"text": "FORGET EVERYTHING"},
                {"text": "ACT AS"},
                {"text": "PRETEND TO BE"},
                {"text": "ROLEPLAY AS"},
            ],
            "managedWordListsConfig": [{"type": "PROFANITY"}],
        },
        "topicPolicyConfig": {
            "topicsConfig": [
                {
                    "name": "FinancialAdvice",
                    "definition": "Content providing financial advice or investment recommendations",
                    "examples": [
                        "You should invest in stocks",
                        "Buy cryptocurrency now",
                        "This is financial advice",
                    ],
                    "type": "DENY",
                },
                {
                    "name": "MedicalAdvice",
                    "definition": "Content providing medical diagnosis or treatment recommendations",
                    "examples": [
                        "You have a medical condition",
                        "Take this medication",
                        "This is medical advice",
                    ],
                    "type": "DENY",
                },
            ]
        },
    }


def validate_location_query_safety(
    query: str, config: GuardrailConfig
) -> dict[str, Any]:
    """Comprehensive safety validation for location queries.

    This combines multiple validation approaches following AWS best practices:
    - Bedrock Guardrails validation
    - Prompt injection detection
    - Location context analysis

    Args:
        query: User query to validate
        config: Guardrail configuration

    Returns:
        Dictionary with comprehensive validation results
    """
    results = {
        "query": query,
        "is_safe": True,
        "validation_results": {},
        "recommendations": [],
    }

    # 1. Bedrock Guardrails validation
    if config.guardrail_id:
        validator = GuardrailValidator(config)
        guardrail_result = validator.validate_content(query)
        results["validation_results"]["guardrails"] = {
            "is_valid": guardrail_result.is_valid,
            "blocked_content": guardrail_result.blocked_content,
            "pii_detected": guardrail_result.pii_detected,
            "toxicity_detected": guardrail_result.toxicity_detected,
        }

        # Check if it's safe for location queries specifically
        location_safe = validator.is_location_query_safe(query)
        results["validation_results"]["location_safe"] = location_safe

        if not location_safe:
            results["is_safe"] = False
            results["recommendations"].append("Query blocked by Bedrock Guardrails")

    # 2. Prompt injection detection
    detector = PromptInjectionDetector()
    injection_result = detector.detect_injection(query)
    results["validation_results"]["prompt_injection"] = injection_result

    if injection_result["is_injection"]:
        injection_safe = detector.is_safe_location_query(query)
        results["validation_results"]["injection_safe"] = injection_safe

        if not injection_safe:
            results["is_safe"] = False
            results["recommendations"].append(
                "Query contains prompt injection patterns"
            )

    # 3. Location context analysis
    location_keywords = [
        "weather",
        "temperature",
        "forecast",
        "rain",
        "snow",
        "storm",
        "location",
        "address",
        "place",
        "city",
        "state",
        "country",
        "route",
        "directions",
        "nearby",
        "find",
        "search",
    ]

    has_location_context = any(
        keyword in query.lower() for keyword in location_keywords
    )
    results["validation_results"]["has_location_context"] = has_location_context

    if not has_location_context:
        results["recommendations"].append("Query may not be location-related")

    # Final safety determination
    if not results["is_safe"]:
        results["recommendations"].append(
            "Query should be blocked or require additional review"
        )
    else:
        results["recommendations"].append(
            "Query appears safe for location service processing"
        )

    return results
