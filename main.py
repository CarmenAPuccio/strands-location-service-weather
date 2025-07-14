#!/usr/bin/env python3
"""
Main initialization script for the location service weather project.
"""

import json
import logging
import os
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Determine if we're in development mode
is_development = os.environ.get("DEVELOPMENT", "false").lower() == "true"

# Configure OpenTelemetry FIRST
resource = Resource.create({"service.name": "strands-location-service-weather"})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Configure exporters based on environment
if is_development:
    # In development: Use SimpleSpanProcessor for immediate console output
    console_exporter = ConsoleSpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(console_exporter))
else:
    # Production exporter setup would go here
    pass

# Get a tracer for this module
tracer = trace.get_tracer(__name__)

# Configure logging - use INFO in production, DEBUG in development
log_level = logging.DEBUG if is_development else logging.INFO

# Configure the root logger with a single handler
handler = logging.StreamHandler()
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove existing handlers
root_logger.addHandler(handler)
root_logger.setLevel(log_level)

# Instrument logging with OpenTelemetry using the default format
LoggingInstrumentor().instrument(
    log_level=log_level,
    set_logging_format=True  # Use the default OpenTelemetry format
)

# Instrument requests to propagate trace context to external HTTP requests
RequestsInstrumentor().instrument()

# Configure logging based on environment
if is_development:
    # In development: More verbose logging
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('strands').setLevel(logging.INFO)  # Show INFO level Strands logs
else:
    # In production: Minimal logging except for Strands requests/responses
    logging.getLogger('botocore').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    logging.getLogger('strands').setLevel(logging.INFO)  # Keep Strands requests/responses
    logging.getLogger('location_service').setLevel(logging.INFO)  # Only important operational logs

# Get logger for this module
logger = logging.getLogger(__name__)

# Import application modules after telemetry is configured

# Import application modules after telemetry is configured
from location_weather import LocationWeatherClient

def main():
    """
    Main entry point for the strands-location-service-weather sample
    """
    # Only show welcome messages in development mode
    if is_development:
        logger.info("PlaceFinder & Weather")
        logger.info("Ask about locations, routes, nearby places, or weather conditions.")
        logger.info("Examples: 'Weather in Seattle', 'Find coffee shops open now in Boston', 'Route from Trenton to Philadelphia'")
        logger.info("          'Places near 47.6062,-122.3321', 'Optimize route with stops at Central Park, Times Square, and Brooklyn Bridge'")
        logger.info("Type 'exit' to quit.")

    client = LocationWeatherClient()
    
    while True:
        # Print a newline before the prompt to separate from any previous output
        print("")
        user_input = input("How can I help you? ")
        
        if user_input.lower() in ['exit', 'quit']:
            logger.info("Exiting the application. Goodbye!")
            break

        try:
            # Create a span for each user interaction
            with tracer.start_as_current_span("user_interaction") as span:
                response = client.chat(user_input)
                # Add attributes to the span
                span.set_attribute("user.input", user_input)
                span.set_attribute("response.length", len(str(response)))
                logger.info(f"Response: {response}\n")
        except Exception as e:
            logger.error("An error occurred. Please try again.")
            logger.error(f"Error processing input: {e}")
    
    # Shutdown telemetry when exiting
    tracer_provider.shutdown()

if __name__ == "__main__":
    main()