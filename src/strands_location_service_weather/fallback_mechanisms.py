"""
Graceful degradation and fallback mechanisms with OpenTelemetry trace context.

This module implements fallback strategies for tool invocations across different
deployment modes, ensuring service continuity even when primary systems fail.

Requirements addressed:
- Graceful degradation and fallback mechanisms with proper OpenTelemetry trace context
- Consistent tool behavior across deployment modes with OpenTelemetry spans
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .config import DeploymentMode
from .error_handling import (
    ErrorContext,
)

# Get logger for this module
logger = logging.getLogger(__name__)

# Get tracer for OpenTelemetry spans
tracer = trace.get_tracer(__name__)


class FallbackStrategy(Enum):
    """Fallback strategies for different failure scenarios."""

    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    ALTERNATIVE_TOOL = "alternative_tool"
    CACHED_RESPONSE = "cached_response"
    DEGRADED_SERVICE = "degraded_service"
    FAIL_FAST = "fail_fast"


class FallbackTrigger(Enum):
    """Conditions that trigger fallback mechanisms."""

    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanisms."""

    strategy: FallbackStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    cache_ttl: int = 300
    enable_tracing: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackResult:
    """Result of fallback mechanism execution."""

    success: bool
    result: Any
    strategy_used: FallbackStrategy
    attempts: int
    total_time: float
    error_message: str | None = None
    fallback_triggered: bool = False
    original_error: Exception | None = None
    trace_id: str | None = None
    span_id: str | None = None


class FallbackMechanism(ABC):
    """Abstract base class for fallback mechanisms."""

    def __init__(self, config: FallbackConfig, deployment_mode: DeploymentMode):
        self.config = config
        self.deployment_mode = deployment_mode
        self.strategy = config.strategy

    @abstractmethod
    def execute(
        self, primary_function: Callable, context: ErrorContext, *args, **kwargs
    ) -> FallbackResult:
        """Execute the fallback mechanism."""
        pass

    def _should_trigger_fallback(self, exception: Exception) -> bool:
        """Determine if fallback should be triggered for this exception."""
        # Map exceptions to fallback triggers
        trigger_mapping = {
            TimeoutError: FallbackTrigger.TIMEOUT,
            ConnectionError: FallbackTrigger.NETWORK_ERROR,
            PermissionError: FallbackTrigger.AUTHENTICATION_ERROR,
            ValueError: FallbackTrigger.VALIDATION_ERROR,
        }

        # Check for requests library errors
        try:
            import requests

            if isinstance(exception, requests.RequestException):
                if isinstance(exception, requests.Timeout):
                    return True
                elif isinstance(exception, requests.ConnectionError):
                    return True
                elif isinstance(exception, requests.HTTPError):
                    if hasattr(exception, "response") and exception.response:
                        status_code = exception.response.status_code
                        # Trigger fallback for server errors and rate limits
                        return status_code >= 500 or status_code == 429
                    return True
        except ImportError:
            pass

        # Check if exception type should trigger fallback
        exception_type = type(exception)
        if exception_type in trigger_mapping:
            return True

        # Check error message for common patterns
        error_message = str(exception).lower()
        fallback_patterns = [
            "timeout",
            "connection",
            "service unavailable",
            "rate limit",
            "server error",
            "internal error",
        ]

        return any(pattern in error_message for pattern in fallback_patterns)

    def _record_fallback_telemetry(
        self,
        result: FallbackResult,
        context: ErrorContext,
        primary_function: Callable,
    ):
        """Record fallback execution with OpenTelemetry."""
        with tracer.start_as_current_span(f"fallback_{self.strategy.value}") as span:
            # Add fallback attributes
            span.set_attribute("fallback.strategy", self.strategy.value)
            span.set_attribute("fallback.success", result.success)
            span.set_attribute("fallback.attempts", result.attempts)
            span.set_attribute("fallback.total_time", result.total_time)
            span.set_attribute("fallback.triggered", result.fallback_triggered)
            span.set_attribute("deployment_mode", self.deployment_mode.value)

            # Add function context
            if hasattr(primary_function, "__name__"):
                span.set_attribute("function.name", primary_function.__name__)

            if context.tool_name:
                span.set_attribute("tool.name", context.tool_name)

            if context.request_id:
                span.set_attribute("request.id", context.request_id)

            if context.session_id:
                span.set_attribute("session.id", context.session_id)

            # Record error if fallback failed
            if not result.success and result.original_error:
                span.record_exception(result.original_error)
                span.set_status(
                    Status(StatusCode.ERROR, result.error_message or "Fallback failed")
                )
            else:
                span.set_status(Status(StatusCode.OK))

            # Store trace information in result
            result.trace_id = f"{span.get_span_context().trace_id:032x}"
            result.span_id = f"{span.get_span_context().span_id:016x}"


class RetryFallback(FallbackMechanism):
    """Retry fallback mechanism with exponential backoff."""

    def execute(
        self, primary_function: Callable, context: ErrorContext, *args, **kwargs
    ) -> FallbackResult:
        """Execute retry fallback with exponential backoff."""
        start_time = time.time()
        attempts = 0
        last_exception = None

        logger.info(
            f"Starting retry fallback for {getattr(primary_function, '__name__', 'unknown_function')}"
        )

        for attempt in range(self.config.max_retries + 1):
            attempts += 1

            try:
                with tracer.start_as_current_span(f"retry_attempt_{attempt}") as span:
                    span.set_attribute("retry.attempt", attempt)
                    span.set_attribute("retry.max_attempts", self.config.max_retries)

                    # Execute primary function
                    result = primary_function(*args, **kwargs)

                    total_time = time.time() - start_time

                    fallback_result = FallbackResult(
                        success=True,
                        result=result,
                        strategy_used=FallbackStrategy.RETRY,
                        attempts=attempts,
                        total_time=total_time,
                        fallback_triggered=attempt > 0,
                    )

                    if self.config.enable_tracing:
                        self._record_fallback_telemetry(
                            fallback_result, context, primary_function
                        )

                    if attempt > 0:
                        logger.info(f"Retry successful on attempt {attempt + 1}")

                    return fallback_result

            except Exception as e:
                last_exception = e

                # Check if we should trigger fallback for this exception
                if not self._should_trigger_fallback(e):
                    logger.warning(
                        f"Exception {type(e).__name__} does not trigger retry fallback"
                    )
                    break

                logger.warning(f"Retry attempt {attempt + 1} failed: {str(e)}")

                # If this is not the last attempt, wait before retrying
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (
                        self.config.retry_backoff**attempt
                    )
                    logger.info(
                        f"Waiting {delay:.2f}s before retry attempt {attempt + 2}"
                    )
                    time.sleep(delay)

        # All retries failed
        total_time = time.time() - start_time

        fallback_result = FallbackResult(
            success=False,
            result=None,
            strategy_used=FallbackStrategy.RETRY,
            attempts=attempts,
            total_time=total_time,
            error_message=f"All {self.config.max_retries + 1} retry attempts failed: {str(last_exception)}",
            fallback_triggered=True,
            original_error=last_exception,
        )

        if self.config.enable_tracing:
            self._record_fallback_telemetry(fallback_result, context, primary_function)

        logger.error(f"Retry fallback failed after {attempts} attempts")
        return fallback_result


class CircuitBreakerFallback(FallbackMechanism):
    """Circuit breaker fallback mechanism."""

    def __init__(self, config: FallbackConfig, deployment_mode: DeploymentMode):
        super().__init__(config, deployment_mode)
        self._failure_count = 0
        self._last_failure_time = 0
        self._state = "closed"  # closed, open, half-open

    def execute(
        self, primary_function: Callable, context: ErrorContext, *args, **kwargs
    ) -> FallbackResult:
        """Execute circuit breaker fallback."""
        start_time = time.time()

        logger.info(
            f"Circuit breaker state: {self._state}, failures: {self._failure_count}"
        )

        # Check circuit breaker state
        if self._state == "open":
            if (
                time.time() - self._last_failure_time
                < self.config.circuit_breaker_timeout
            ):
                # Circuit is open, fail fast
                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=False,
                    result=None,
                    strategy_used=FallbackStrategy.CIRCUIT_BREAKER,
                    attempts=0,
                    total_time=total_time,
                    error_message="Circuit breaker is open - failing fast",
                    fallback_triggered=True,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                logger.warning("Circuit breaker is open - failing fast")
                return fallback_result
            else:
                # Timeout expired, move to half-open
                self._state = "half-open"
                logger.info("Circuit breaker moving to half-open state")

        try:
            with tracer.start_as_current_span("circuit_breaker_execution") as span:
                span.set_attribute("circuit_breaker.state", self._state)
                span.set_attribute("circuit_breaker.failure_count", self._failure_count)

                # Execute primary function
                result = primary_function(*args, **kwargs)

                # Success - reset circuit breaker
                self._failure_count = 0
                self._state = "closed"

                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=True,
                    result=result,
                    strategy_used=FallbackStrategy.CIRCUIT_BREAKER,
                    attempts=1,
                    total_time=total_time,
                    fallback_triggered=False,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                logger.info("Circuit breaker execution successful - circuit closed")
                return fallback_result

        except Exception as e:
            # Check if we should trigger fallback for this exception
            if self._should_trigger_fallback(e):
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self.config.circuit_breaker_threshold:
                    self._state = "open"
                    logger.warning(
                        f"Circuit breaker opened after {self._failure_count} failures"
                    )

                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=False,
                    result=None,
                    strategy_used=FallbackStrategy.CIRCUIT_BREAKER,
                    attempts=1,
                    total_time=total_time,
                    error_message=f"Circuit breaker execution failed: {str(e)}",
                    fallback_triggered=True,
                    original_error=e,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                return fallback_result
            else:
                # Exception doesn't trigger circuit breaker
                raise e


class AlternativeToolFallback(FallbackMechanism):
    """Fallback to alternative tool implementation."""

    def __init__(
        self,
        config: FallbackConfig,
        deployment_mode: DeploymentMode,
        alternative_function: Callable | None = None,
    ):
        super().__init__(config, deployment_mode)
        self.alternative_function = alternative_function

    def execute(
        self, primary_function: Callable, context: ErrorContext, *args, **kwargs
    ) -> FallbackResult:
        """Execute alternative tool fallback."""
        start_time = time.time()

        try:
            with tracer.start_as_current_span("primary_tool_execution") as span:
                span.set_attribute("tool.type", "primary")
                if context.tool_name:
                    span.set_attribute("tool.name", context.tool_name)

                # Try primary function first
                result = primary_function(*args, **kwargs)

                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=True,
                    result=result,
                    strategy_used=FallbackStrategy.ALTERNATIVE_TOOL,
                    attempts=1,
                    total_time=total_time,
                    fallback_triggered=False,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                return fallback_result

        except Exception as e:
            logger.warning(f"Primary tool failed: {str(e)}, trying alternative")

            # Check if we should trigger fallback
            if not self._should_trigger_fallback(e) or not self.alternative_function:
                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=False,
                    result=None,
                    strategy_used=FallbackStrategy.ALTERNATIVE_TOOL,
                    attempts=1,
                    total_time=total_time,
                    error_message=f"Primary tool failed and no alternative available: {str(e)}",
                    fallback_triggered=False,
                    original_error=e,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                return fallback_result

            # Try alternative function
            try:
                with tracer.start_as_current_span("alternative_tool_execution") as span:
                    span.set_attribute("tool.type", "alternative")
                    span.set_attribute(
                        "tool.name",
                        getattr(self.alternative_function, "__name__", "unknown"),
                    )

                    result = self.alternative_function(*args, **kwargs)

                    total_time = time.time() - start_time

                    fallback_result = FallbackResult(
                        success=True,
                        result=result,
                        strategy_used=FallbackStrategy.ALTERNATIVE_TOOL,
                        attempts=2,
                        total_time=total_time,
                        fallback_triggered=True,
                    )

                    if self.config.enable_tracing:
                        self._record_fallback_telemetry(
                            fallback_result, context, primary_function
                        )

                    logger.info("Alternative tool execution successful")
                    return fallback_result

            except Exception as alt_e:
                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=False,
                    result=None,
                    strategy_used=FallbackStrategy.ALTERNATIVE_TOOL,
                    attempts=2,
                    total_time=total_time,
                    error_message=f"Both primary and alternative tools failed. Primary: {str(e)}, Alternative: {str(alt_e)}",
                    fallback_triggered=True,
                    original_error=e,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                logger.error("Both primary and alternative tools failed")
                return fallback_result


class CachedResponseFallback(FallbackMechanism):
    """Fallback to cached response."""

    def __init__(self, config: FallbackConfig, deployment_mode: DeploymentMode):
        super().__init__(config, deployment_mode)
        self._cache: dict[str, tuple[Any, float]] = {}

    def execute(
        self, primary_function: Callable, context: ErrorContext, *args, **kwargs
    ) -> FallbackResult:
        """Execute cached response fallback."""
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(primary_function, args, kwargs)

        try:
            with tracer.start_as_current_span("primary_function_with_cache") as span:
                span.set_attribute("cache.key", cache_key)

                # Try primary function first
                result = primary_function(*args, **kwargs)

                # Cache the successful result
                self._cache[cache_key] = (result, time.time())
                span.set_attribute("cache.stored", True)

                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=True,
                    result=result,
                    strategy_used=FallbackStrategy.CACHED_RESPONSE,
                    attempts=1,
                    total_time=total_time,
                    fallback_triggered=False,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                return fallback_result

        except Exception as e:
            logger.warning(f"Primary function failed: {str(e)}, checking cache")

            # Check if we should trigger fallback
            if not self._should_trigger_fallback(e):
                total_time = time.time() - start_time

                fallback_result = FallbackResult(
                    success=False,
                    result=None,
                    strategy_used=FallbackStrategy.CACHED_RESPONSE,
                    attempts=1,
                    total_time=total_time,
                    error_message=f"Primary function failed and fallback not triggered: {str(e)}",
                    fallback_triggered=False,
                    original_error=e,
                )

                if self.config.enable_tracing:
                    self._record_fallback_telemetry(
                        fallback_result, context, primary_function
                    )

                return fallback_result

            # Try to get cached response
            cached_data = self._cache.get(cache_key)
            if cached_data:
                cached_result, cached_time = cached_data

                # Check if cache is still valid
                if time.time() - cached_time <= self.config.cache_ttl:
                    total_time = time.time() - start_time

                    fallback_result = FallbackResult(
                        success=True,
                        result=cached_result,
                        strategy_used=FallbackStrategy.CACHED_RESPONSE,
                        attempts=1,
                        total_time=total_time,
                        fallback_triggered=True,
                    )

                    if self.config.enable_tracing:
                        self._record_fallback_telemetry(
                            fallback_result, context, primary_function
                        )

                    logger.info("Using cached response as fallback")
                    return fallback_result
                else:
                    # Cache expired, remove it
                    del self._cache[cache_key]
                    logger.info("Cached response expired")

            # No valid cache available
            total_time = time.time() - start_time

            fallback_result = FallbackResult(
                success=False,
                result=None,
                strategy_used=FallbackStrategy.CACHED_RESPONSE,
                attempts=1,
                total_time=total_time,
                error_message=f"Primary function failed and no valid cache available: {str(e)}",
                fallback_triggered=True,
                original_error=e,
            )

            if self.config.enable_tracing:
                self._record_fallback_telemetry(
                    fallback_result, context, primary_function
                )

            logger.warning("No valid cached response available")
            return fallback_result

    def _generate_cache_key(self, function: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call."""
        import hashlib

        # Create a string representation of the function call
        func_name = getattr(function, "__name__", str(function))
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))

        # Create hash of the combined string
        combined = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(combined.encode()).hexdigest()


class FallbackManager:
    """Manager for coordinating multiple fallback mechanisms."""

    def __init__(self, deployment_mode: DeploymentMode):
        self.deployment_mode = deployment_mode
        self._mechanisms: list[FallbackMechanism] = []

    def add_mechanism(self, mechanism: FallbackMechanism):
        """Add a fallback mechanism to the manager."""
        self._mechanisms.append(mechanism)
        logger.info(f"Added {mechanism.strategy.value} fallback mechanism")

    def execute_with_fallback(
        self, primary_function: Callable, context: ErrorContext, *args, **kwargs
    ) -> FallbackResult:
        """Execute function with all configured fallback mechanisms."""
        if not self._mechanisms:
            # No fallback mechanisms configured, execute directly
            start_time = time.time()
            try:
                result = primary_function(*args, **kwargs)
                return FallbackResult(
                    success=True,
                    result=result,
                    strategy_used=FallbackStrategy.FAIL_FAST,
                    attempts=1,
                    total_time=time.time() - start_time,
                    fallback_triggered=False,
                )
            except Exception as e:
                return FallbackResult(
                    success=False,
                    result=None,
                    strategy_used=FallbackStrategy.FAIL_FAST,
                    attempts=1,
                    total_time=time.time() - start_time,
                    error_message=str(e),
                    fallback_triggered=False,
                    original_error=e,
                )

        # Try each fallback mechanism in order
        last_result = None
        for mechanism in self._mechanisms:
            logger.info(f"Trying fallback mechanism: {mechanism.strategy.value}")

            result = mechanism.execute(primary_function, context, *args, **kwargs)
            last_result = result

            if result.success:
                logger.info(f"Fallback mechanism {mechanism.strategy.value} succeeded")
                return result
            else:
                logger.warning(
                    f"Fallback mechanism {mechanism.strategy.value} failed: {result.error_message}"
                )

        # All fallback mechanisms failed
        logger.error("All fallback mechanisms failed")
        return last_result or FallbackResult(
            success=False,
            result=None,
            strategy_used=FallbackStrategy.FAIL_FAST,
            attempts=0,
            total_time=0,
            error_message="No fallback mechanisms available",
            fallback_triggered=False,
        )


# Convenience functions for creating common fallback configurations
def create_retry_config(
    max_retries: int = 3, retry_delay: float = 1.0
) -> FallbackConfig:
    """Create retry fallback configuration."""
    return FallbackConfig(
        strategy=FallbackStrategy.RETRY,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )


def create_circuit_breaker_config(
    threshold: int = 5, timeout: int = 60
) -> FallbackConfig:
    """Create circuit breaker fallback configuration."""
    return FallbackConfig(
        strategy=FallbackStrategy.CIRCUIT_BREAKER,
        circuit_breaker_threshold=threshold,
        circuit_breaker_timeout=timeout,
    )


def create_cache_config(cache_ttl: int = 300) -> FallbackConfig:
    """Create cached response fallback configuration."""
    return FallbackConfig(
        strategy=FallbackStrategy.CACHED_RESPONSE,
        cache_ttl=cache_ttl,
    )
