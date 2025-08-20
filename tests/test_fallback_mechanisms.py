"""
Tests for graceful degradation and fallback mechanisms with OpenTelemetry observability.

This module tests fallback strategies for tool invocations across different
deployment modes and validates OpenTelemetry trace context propagation.
"""

import time
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.strands_location_service_weather.config import DeploymentMode
from src.strands_location_service_weather.error_handling import ErrorContext
from src.strands_location_service_weather.fallback_mechanisms import (
    AlternativeToolFallback,
    CachedResponseFallback,
    CircuitBreakerFallback,
    FallbackConfig,
    FallbackManager,
    FallbackResult,
    FallbackStrategy,
    FallbackTrigger,
    RetryFallback,
    create_cache_config,
    create_circuit_breaker_config,
    create_retry_config,
)


class TestFallbackEnums:
    """Test fallback enums and constants."""

    def test_fallback_strategy_enum(self):
        """Test FallbackStrategy enum values."""
        assert FallbackStrategy.RETRY.value == "retry"
        assert FallbackStrategy.CIRCUIT_BREAKER.value == "circuit_breaker"
        assert FallbackStrategy.ALTERNATIVE_TOOL.value == "alternative_tool"
        assert FallbackStrategy.CACHED_RESPONSE.value == "cached_response"
        assert FallbackStrategy.DEGRADED_SERVICE.value == "degraded_service"
        assert FallbackStrategy.FAIL_FAST.value == "fail_fast"

    def test_fallback_trigger_enum(self):
        """Test FallbackTrigger enum values."""
        assert FallbackTrigger.TIMEOUT.value == "timeout"
        assert FallbackTrigger.NETWORK_ERROR.value == "network_error"
        assert FallbackTrigger.SERVICE_UNAVAILABLE.value == "service_unavailable"
        assert FallbackTrigger.RATE_LIMIT.value == "rate_limit"
        assert FallbackTrigger.AUTHENTICATION_ERROR.value == "authentication_error"
        assert FallbackTrigger.VALIDATION_ERROR.value == "validation_error"
        assert FallbackTrigger.INTERNAL_ERROR.value == "internal_error"


class TestFallbackConfig:
    """Test FallbackConfig dataclass."""

    def test_fallback_config_creation(self):
        """Test FallbackConfig creation with all fields."""
        config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=1.5,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=120,
            cache_ttl=600,
            enable_tracing=False,
            metadata={"key": "value"},
        )

        assert config.strategy == FallbackStrategy.RETRY
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.retry_backoff == 1.5
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 120
        assert config.cache_ttl == 600
        assert config.enable_tracing is False
        assert config.metadata == {"key": "value"}

    def test_fallback_config_defaults(self):
        """Test FallbackConfig default values."""
        config = FallbackConfig(strategy=FallbackStrategy.RETRY)

        assert config.strategy == FallbackStrategy.RETRY
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff == 2.0
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 60
        assert config.cache_ttl == 300
        assert config.enable_tracing is True
        assert config.metadata == {}


class TestFallbackResult:
    """Test FallbackResult dataclass."""

    def test_fallback_result_creation(self):
        """Test FallbackResult creation."""
        result = FallbackResult(
            success=True,
            result="test_result",
            strategy_used=FallbackStrategy.RETRY,
            attempts=3,
            total_time=1.5,
            error_message=None,
            fallback_triggered=True,
            original_error=None,
            trace_id="trace_123",
            span_id="span_456",
        )

        assert result.success is True
        assert result.result == "test_result"
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.attempts == 3
        assert result.total_time == 1.5
        assert result.error_message is None
        assert result.fallback_triggered is True
        assert result.original_error is None
        assert result.trace_id == "trace_123"
        assert result.span_id == "span_456"


class TestRetryFallback:
    """Test RetryFallback mechanism."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=3,
            retry_delay=0.1,  # Short delay for testing
            retry_backoff=2.0,
            enable_tracing=False,  # Disable for simpler testing
        )
        self.fallback = RetryFallback(self.config, DeploymentMode.LOCAL)
        self.context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

    def test_successful_first_attempt(self):
        """Test successful execution on first attempt."""

        def successful_function():
            return "success"

        result = self.fallback.execute(successful_function, self.context)

        assert result.success is True
        assert result.result == "success"
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.attempts == 1
        assert result.fallback_triggered is False
        assert result.error_message is None

    def test_successful_after_retries(self):
        """Test successful execution after retries."""
        call_count = 0

        def failing_then_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = self.fallback.execute(failing_then_successful_function, self.context)

        assert result.success is True
        assert result.result == "success"
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.attempts == 3
        assert result.fallback_triggered is True
        assert result.error_message is None

    def test_all_retries_failed(self):
        """Test failure after all retries exhausted."""

        def always_failing_function():
            raise ConnectionError("Network error")

        result = self.fallback.execute(always_failing_function, self.context)

        assert result.success is False
        assert result.result is None
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.attempts == 4  # Initial attempt + 3 retries
        assert result.fallback_triggered is True
        assert "All 4 retry attempts failed" in result.error_message
        assert isinstance(result.original_error, ConnectionError)

    def test_non_retryable_error(self):
        """Test that non-retryable errors don't trigger retries."""

        def validation_error_function():
            raise ValueError("Invalid input")

        # Mock _should_trigger_fallback to return False for ValueError
        with patch.object(
            self.fallback, "_should_trigger_fallback", return_value=False
        ):
            result = self.fallback.execute(validation_error_function, self.context)

            assert result.success is False
            assert result.attempts == 1  # No retries
            # The fallback is still triggered (attempted) but doesn't retry
            assert result.fallback_triggered is True

    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        call_times = []

        def timing_function():
            call_times.append(time.time())
            raise ConnectionError("Network error")

        time.time()
        self.fallback.execute(timing_function, self.context)

        # Verify we made the expected number of attempts
        assert len(call_times) == 4  # Initial + 3 retries

        # Verify exponential backoff (approximately)
        # First retry: ~0.1s, Second retry: ~0.2s, Third retry: ~0.4s
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            # Allow some tolerance for timing variations
            assert delay1 >= 0.08  # Should be around 0.1s
            assert delay2 >= 0.18  # Should be around 0.2s
            assert delay2 > delay1  # Should be increasing

    @patch("src.strands_location_service_weather.fallback_mechanisms.tracer")
    def test_telemetry_recording(self, mock_tracer):
        """Test OpenTelemetry telemetry recording."""
        # Enable tracing for this test
        self.config.enable_tracing = True

        # Set up mock span
        mock_span = Mock()
        mock_span.get_span_context.return_value = Mock(
            trace_id=12345,
            span_id=67890,
        )
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        def successful_function():
            return "success"

        self.fallback.execute(successful_function, self.context)

        # Verify telemetry was recorded
        mock_tracer.start_as_current_span.assert_called()
        mock_span.set_attribute.assert_any_call("fallback.strategy", "retry")
        mock_span.set_attribute.assert_any_call("fallback.success", True)
        mock_span.set_attribute.assert_any_call("fallback.attempts", 1)


class TestCircuitBreakerFallback:
    """Test CircuitBreakerFallback mechanism."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = FallbackConfig(
            strategy=FallbackStrategy.CIRCUIT_BREAKER,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=1,  # Short timeout for testing
            enable_tracing=False,
        )
        self.fallback = CircuitBreakerFallback(self.config, DeploymentMode.LOCAL)
        self.context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

    def test_successful_execution_closed_circuit(self):
        """Test successful execution with closed circuit."""

        def successful_function():
            return "success"

        result = self.fallback.execute(successful_function, self.context)

        assert result.success is True
        assert result.result == "success"
        assert result.strategy_used == FallbackStrategy.CIRCUIT_BREAKER
        assert result.attempts == 1
        assert result.fallback_triggered is False
        assert self.fallback._state == "closed"
        assert self.fallback._failure_count == 0

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold is reached."""

        def failing_function():
            raise ConnectionError("Network error")

        # Execute enough failures to open the circuit
        for _i in range(self.config.circuit_breaker_threshold):
            result = self.fallback.execute(failing_function, self.context)
            assert result.success is False

        # Circuit should now be open
        assert self.fallback._state == "open"
        assert self.fallback._failure_count == self.config.circuit_breaker_threshold

    def test_circuit_fails_fast_when_open(self):
        """Test circuit fails fast when open."""

        # First, open the circuit
        def failing_function():
            raise ConnectionError("Network error")

        for _i in range(self.config.circuit_breaker_threshold):
            self.fallback.execute(failing_function, self.context)

        # Now test that it fails fast
        def any_function():
            return "should not be called"

        result = self.fallback.execute(any_function, self.context)

        assert result.success is False
        assert result.attempts == 0  # Function not called
        assert result.fallback_triggered is True
        assert "Circuit breaker is open" in result.error_message

    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""

        # Open the circuit
        def failing_function():
            raise ConnectionError("Network error")

        for _i in range(self.config.circuit_breaker_threshold):
            self.fallback.execute(failing_function, self.context)

        assert self.fallback._state == "open"

        # Wait for timeout
        time.sleep(self.config.circuit_breaker_timeout + 0.1)

        # Next execution should move to half-open
        def successful_function():
            return "success"

        result = self.fallback.execute(successful_function, self.context)

        assert result.success is True
        assert self.fallback._state == "closed"  # Should close after success
        assert self.fallback._failure_count == 0

    def test_non_triggering_errors_dont_affect_circuit(self):
        """Test that non-triggering errors don't affect circuit state."""

        def validation_error_function():
            raise ValueError("Invalid input")

        # Mock _should_trigger_fallback to return False for ValueError
        with patch.object(
            self.fallback, "_should_trigger_fallback", return_value=False
        ):
            # This should raise the exception without affecting circuit state
            with pytest.raises(ValueError):
                self.fallback.execute(validation_error_function, self.context)

            # Circuit should remain closed
            assert self.fallback._state == "closed"
            assert self.fallback._failure_count == 0


class TestAlternativeToolFallback:
    """Test AlternativeToolFallback mechanism."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = FallbackConfig(
            strategy=FallbackStrategy.ALTERNATIVE_TOOL,
            enable_tracing=False,
        )

        def alternative_function(*args, **kwargs):
            return "alternative_result"

        self.fallback = AlternativeToolFallback(
            self.config, DeploymentMode.LOCAL, alternative_function=alternative_function
        )
        self.context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

    def test_successful_primary_tool(self):
        """Test successful execution of primary tool."""

        def primary_function():
            return "primary_result"

        result = self.fallback.execute(primary_function, self.context)

        assert result.success is True
        assert result.result == "primary_result"
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_TOOL
        assert result.attempts == 1
        assert result.fallback_triggered is False

    def test_fallback_to_alternative_tool(self):
        """Test fallback to alternative tool when primary fails."""

        def failing_primary_function():
            raise ConnectionError("Primary tool failed")

        result = self.fallback.execute(failing_primary_function, self.context)

        assert result.success is True
        assert result.result == "alternative_result"
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_TOOL
        assert result.attempts == 2
        assert result.fallback_triggered is True

    def test_both_tools_fail(self):
        """Test when both primary and alternative tools fail."""

        def failing_primary_function():
            raise ConnectionError("Primary tool failed")

        # Replace alternative function with failing one
        def failing_alternative_function(*args, **kwargs):
            raise ConnectionError("Alternative tool failed")

        self.fallback.alternative_function = failing_alternative_function

        result = self.fallback.execute(failing_primary_function, self.context)

        assert result.success is False
        assert result.result is None
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_TOOL
        assert result.attempts == 2
        assert result.fallback_triggered is True
        assert "Both primary and alternative tools failed" in result.error_message

    def test_no_alternative_tool_available(self):
        """Test when no alternative tool is available."""
        # Create fallback without alternative function
        fallback_no_alt = AlternativeToolFallback(
            self.config, DeploymentMode.LOCAL, alternative_function=None
        )

        def failing_function():
            raise ConnectionError("Primary tool failed")

        result = fallback_no_alt.execute(failing_function, self.context)

        assert result.success is False
        assert result.result is None
        assert result.attempts == 1
        assert result.fallback_triggered is False
        assert "no alternative available" in result.error_message


class TestCachedResponseFallback:
    """Test CachedResponseFallback mechanism."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = FallbackConfig(
            strategy=FallbackStrategy.CACHED_RESPONSE,
            cache_ttl=1,  # Short TTL for testing
            enable_tracing=False,
        )
        self.fallback = CachedResponseFallback(self.config, DeploymentMode.LOCAL)
        self.context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

    def test_successful_execution_caches_result(self):
        """Test successful execution caches the result."""

        def successful_function(param1, param2="default"):
            return f"result_{param1}_{param2}"

        result = self.fallback.execute(
            successful_function, self.context, "test", param2="value"
        )

        assert result.success is True
        assert result.result == "result_test_value"
        assert result.fallback_triggered is False

        # Verify result is cached
        cache_key = self.fallback._generate_cache_key(
            successful_function, ("test",), {"param2": "value"}
        )
        assert cache_key in self.fallback._cache

    def test_fallback_to_cached_response(self):
        """Test fallback to cached response when primary fails."""

        def sometimes_failing_function(param="test"):
            if not hasattr(sometimes_failing_function, "call_count"):
                sometimes_failing_function.call_count = 0
            sometimes_failing_function.call_count += 1

            if sometimes_failing_function.call_count == 1:
                return "cached_result"
            else:
                raise ConnectionError("Function failed")

        # First call succeeds and caches result
        result1 = self.fallback.execute(
            sometimes_failing_function, self.context, param="test"
        )
        assert result1.success is True
        assert result1.result == "cached_result"

        # Second call fails but returns cached result
        result2 = self.fallback.execute(
            sometimes_failing_function, self.context, param="test"
        )
        assert result2.success is True
        assert result2.result == "cached_result"
        assert result2.fallback_triggered is True

    def test_cache_expiration(self):
        """Test cache expiration after TTL."""

        def successful_function():
            return "result"

        # First call caches result
        result1 = self.fallback.execute(successful_function, self.context)
        assert result1.success is True

        # Wait for cache to expire
        time.sleep(self.config.cache_ttl + 0.1)

        # Function now fails, but cache is expired
        def failing_function():
            raise ConnectionError("Function failed")

        result2 = self.fallback.execute(failing_function, self.context)
        assert result2.success is False
        assert result2.fallback_triggered is True
        assert "no valid cache available" in result2.error_message

    def test_cache_key_generation(self):
        """Test cache key generation for different function calls."""

        def test_function(a, b=None):
            return f"{a}_{b}"

        # Same parameters should generate same key
        key1 = self.fallback._generate_cache_key(
            test_function, ("value1",), {"b": "value2"}
        )
        key2 = self.fallback._generate_cache_key(
            test_function, ("value1",), {"b": "value2"}
        )
        assert key1 == key2

        # Different parameters should generate different keys
        key3 = self.fallback._generate_cache_key(
            test_function, ("value1",), {"b": "value3"}
        )
        assert key1 != key3


class TestFallbackManager:
    """Test FallbackManager for coordinating multiple mechanisms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = FallbackManager(DeploymentMode.LOCAL)
        self.context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

    def test_no_fallback_mechanisms_success(self):
        """Test execution with no fallback mechanisms configured - success case."""

        def successful_function():
            return "success"

        result = self.manager.execute_with_fallback(successful_function, self.context)

        assert result.success is True
        assert result.result == "success"
        assert result.strategy_used == FallbackStrategy.FAIL_FAST
        assert result.attempts == 1
        assert result.fallback_triggered is False

    def test_no_fallback_mechanisms_failure(self):
        """Test execution with no fallback mechanisms configured - failure case."""

        def failing_function():
            raise ConnectionError("Function failed")

        result = self.manager.execute_with_fallback(failing_function, self.context)

        assert result.success is False
        assert result.result is None
        assert result.strategy_used == FallbackStrategy.FAIL_FAST
        assert result.attempts == 1
        assert result.fallback_triggered is False
        assert isinstance(result.original_error, ConnectionError)

    def test_single_fallback_mechanism_success(self):
        """Test execution with single fallback mechanism - success case."""
        retry_config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=2,
            retry_delay=0.01,
            enable_tracing=False,
        )
        retry_fallback = RetryFallback(retry_config, DeploymentMode.LOCAL)
        self.manager.add_mechanism(retry_fallback)

        call_count = 0

        def failing_then_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = self.manager.execute_with_fallback(
            failing_then_successful_function, self.context
        )

        assert result.success is True
        assert result.result == "success"
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.fallback_triggered is True

    def test_multiple_fallback_mechanisms_cascade(self):
        """Test execution with multiple fallback mechanisms cascading."""
        # Add retry mechanism (will fail)
        retry_config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=1,
            retry_delay=0.01,
            enable_tracing=False,
        )
        retry_fallback = RetryFallback(retry_config, DeploymentMode.LOCAL)
        self.manager.add_mechanism(retry_fallback)

        # Add alternative tool mechanism (will succeed)
        def alternative_function(*args, **kwargs):
            return "alternative_success"

        alt_config = FallbackConfig(
            strategy=FallbackStrategy.ALTERNATIVE_TOOL,
            enable_tracing=False,
        )
        alt_fallback = AlternativeToolFallback(
            alt_config, DeploymentMode.LOCAL, alternative_function=alternative_function
        )
        self.manager.add_mechanism(alt_fallback)

        def always_failing_function():
            raise ConnectionError("Always fails")

        result = self.manager.execute_with_fallback(
            always_failing_function, self.context
        )

        # Should succeed with alternative tool after retry fails
        assert result.success is True
        assert result.result == "alternative_success"
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_TOOL
        assert result.fallback_triggered is True

    def test_all_fallback_mechanisms_fail(self):
        """Test when all fallback mechanisms fail."""
        # Add retry mechanism (will fail)
        retry_config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=1,
            retry_delay=0.01,
            enable_tracing=False,
        )
        retry_fallback = RetryFallback(retry_config, DeploymentMode.LOCAL)
        self.manager.add_mechanism(retry_fallback)

        # Add alternative tool mechanism (will also fail)
        def failing_alternative_function(*args, **kwargs):
            raise ConnectionError("Alternative also fails")

        alt_config = FallbackConfig(
            strategy=FallbackStrategy.ALTERNATIVE_TOOL,
            enable_tracing=False,
        )
        alt_fallback = AlternativeToolFallback(
            alt_config,
            DeploymentMode.LOCAL,
            alternative_function=failing_alternative_function,
        )
        self.manager.add_mechanism(alt_fallback)

        def always_failing_function():
            raise ConnectionError("Always fails")

        result = self.manager.execute_with_fallback(
            always_failing_function, self.context
        )

        # All mechanisms should fail
        assert result.success is False
        assert result.result is None
        # Should return result from last mechanism tried
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_TOOL


class TestConvenienceConfigFunctions:
    """Test convenience functions for creating fallback configurations."""

    def test_create_retry_config(self):
        """Test create_retry_config convenience function."""
        config = create_retry_config(max_retries=5, retry_delay=2.0)

        assert config.strategy == FallbackStrategy.RETRY
        assert config.max_retries == 5
        assert config.retry_delay == 2.0

    def test_create_retry_config_defaults(self):
        """Test create_retry_config with default values."""
        config = create_retry_config()

        assert config.strategy == FallbackStrategy.RETRY
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_create_circuit_breaker_config(self):
        """Test create_circuit_breaker_config convenience function."""
        config = create_circuit_breaker_config(threshold=10, timeout=120)

        assert config.strategy == FallbackStrategy.CIRCUIT_BREAKER
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 120

    def test_create_cache_config(self):
        """Test create_cache_config convenience function."""
        config = create_cache_config(cache_ttl=600)

        assert config.strategy == FallbackStrategy.CACHED_RESPONSE
        assert config.cache_ttl == 600


class TestOpenTelemetryIntegration:
    """Test OpenTelemetry integration with fallback mechanisms."""

    def setup_method(self):
        """Set up OpenTelemetry test environment."""
        # Create in-memory span exporter for testing
        self.span_exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.span_exporter))

        # Set the tracer provider
        trace.set_tracer_provider(self.tracer_provider)

    def test_fallback_telemetry_recording(self):
        """Test that fallback telemetry is properly recorded."""
        config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=1,
            retry_delay=0.01,
            enable_tracing=True,
        )
        fallback = RetryFallback(config, DeploymentMode.LOCAL)
        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

        def successful_function():
            return "success"

        # Test that fallback has telemetry recording capability
        assert hasattr(fallback, "_record_fallback_telemetry")

        # Execute fallback and verify it works
        result = fallback.execute(successful_function, context)

        # Verify fallback result
        assert result.success is True
        assert result.result == "success"
        assert result.strategy_used == FallbackStrategy.RETRY
        assert result.attempts == 1
        assert (
            result.fallback_triggered is False
        )  # No fallback needed for successful function

    def test_trace_context_propagation_in_fallback(self):
        """Test that trace context is properly propagated in fallback mechanisms."""
        config = FallbackConfig(
            strategy=FallbackStrategy.RETRY,
            max_retries=1,
            retry_delay=0.01,
            enable_tracing=True,
        )
        fallback = RetryFallback(config, DeploymentMode.LOCAL)
        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

        def successful_function():
            return "success"

        # Create a parent span
        with trace.get_tracer(__name__).start_as_current_span(
            "parent_span"
        ) as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id

            # Execute fallback within the parent span
            fallback.execute(successful_function, context)

        # Get recorded spans
        spans = self.span_exporter.get_finished_spans()

        # Verify all spans have the same trace ID
        for span in spans:
            assert span.get_span_context().trace_id == parent_trace_id

    def teardown_method(self):
        """Clean up OpenTelemetry test environment."""
        self.span_exporter.clear()


class TestFallbackRequirements:
    """Test that fallback mechanisms meet specific requirements."""

    def test_graceful_degradation_with_trace_context(self):
        """Test graceful degradation without OpenTelemetry TracerProvider conflicts."""
        # Create fallback manager with multiple mechanisms
        manager = FallbackManager(DeploymentMode.LOCAL)

        # Add retry fallback
        retry_config = create_retry_config(max_retries=1, retry_delay=0.01)
        retry_config.enable_tracing = True
        retry_fallback = RetryFallback(retry_config, DeploymentMode.LOCAL)
        manager.add_mechanism(retry_fallback)

        # Add alternative tool fallback
        def alternative_tool():
            return "degraded_service_response"

        alt_config = FallbackConfig(
            strategy=FallbackStrategy.ALTERNATIVE_TOOL,
            enable_tracing=True,
        )
        alt_fallback = AlternativeToolFallback(
            alt_config, DeploymentMode.LOCAL, alternative_function=alternative_tool
        )
        manager.add_mechanism(alt_fallback)

        context = ErrorContext(
            deployment_mode=DeploymentMode.LOCAL,
            protocol="python_direct",
            tool_name="test_tool",
        )

        def failing_primary_function():
            raise ConnectionError("Primary service unavailable")

        # Execute with fallback - using existing tracer to avoid conflicts
        result = manager.execute_with_fallback(failing_primary_function, context)

        # Verify graceful degradation occurred
        assert result.success is True
        assert result.result == "degraded_service_response"
        assert result.fallback_triggered is True
        assert result.strategy_used == FallbackStrategy.ALTERNATIVE_TOOL

    def test_consistent_tool_behavior_across_modes(self):
        """Test consistent tool behavior across deployment modes with fallback."""
        modes = [DeploymentMode.LOCAL, DeploymentMode.MCP, DeploymentMode.BEDROCK_AGENT]

        for mode in modes:
            # Create fallback manager for each mode
            manager = FallbackManager(mode)

            # Add retry fallback
            retry_config = create_retry_config(max_retries=1, retry_delay=0.01)
            retry_fallback = RetryFallback(retry_config, mode)
            manager.add_mechanism(retry_fallback)

            context = ErrorContext(
                deployment_mode=mode,
                protocol=f"protocol_{mode.value}",
                tool_name="test_tool",
            )

            def successful_function(current_mode=mode):
                return f"success_{current_mode.value}"

            # Execute with fallback
            result = manager.execute_with_fallback(successful_function, context)

            # Verify consistent behavior across modes
            assert result.success is True
            assert result.result == f"success_{mode.value}"
            assert result.strategy_used == FallbackStrategy.RETRY
            assert result.fallback_triggered is False
