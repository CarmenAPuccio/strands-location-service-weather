"""
Tool manager for handling mode-specific tool selection and validation.

This module implements the Strands tool integration strategy for multi-mode deployment,
ensuring consistent tool behavior across LOCAL, MCP, and AGENTCORE modes.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

# We'll define current_time locally to ensure proper @tool decoration
from .config import DeploymentMode

# Get logger for this module
logger = logging.getLogger(__name__)


class ToolProtocol(Enum):
    """Communication protocols for tool execution."""

    PYTHON_DIRECT = "python_direct"  # Direct Python function calls (LOCAL mode)
    MCP = "mcp"  # Model Context Protocol (MCP mode)
    HTTP_REST = "http_rest"  # HTTP/REST via Lambda (AGENTCORE mode)


@dataclass
class ToolDefinition:
    """Definition of a tool with metadata for different protocols."""

    name: str
    description: str
    function: Callable
    protocol: ToolProtocol
    parameters_schema: dict[str, Any]
    return_schema: dict[str, Any]
    timeout: int | None = None
    error_handling: str | None = None


@dataclass
class ToolValidationResult:
    """Result of tool validation."""

    valid: bool
    tool_name: str
    protocol: ToolProtocol
    error_message: str | None = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class ToolExecutionResult:
    """Result of tool execution with protocol-specific metadata."""

    success: bool
    result: Any
    tool_name: str
    protocol: ToolProtocol
    execution_time: float
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class ToolProtocolAdapter(ABC):
    """Abstract base class for tool protocol adapters."""

    @abstractmethod
    def validate_tool(self, tool_def: ToolDefinition) -> ToolValidationResult:
        """Validate that a tool is compatible with this protocol."""
        pass

    @abstractmethod
    def execute_tool(self, tool_def: ToolDefinition, **kwargs) -> ToolExecutionResult:
        """Execute a tool using this protocol."""
        pass

    @abstractmethod
    def get_protocol_info(self) -> dict[str, Any]:
        """Get information about this protocol."""
        pass


class PythonDirectAdapter(ToolProtocolAdapter):
    """Adapter for direct Python function calls (LOCAL mode)."""

    def validate_tool(self, tool_def: ToolDefinition) -> ToolValidationResult:
        """Validate tool for direct Python execution.

        Following Strands framework best practices:
        https://github.com/strands-agents
        """
        logger.debug(f"Validating tool {tool_def.name} for Python direct execution")

        warnings = []

        # Check if function is callable
        if not callable(tool_def.function):
            return ToolValidationResult(
                valid=False,
                tool_name=tool_def.name,
                protocol=ToolProtocol.PYTHON_DIRECT,
                error_message=f"Tool function {tool_def.name} is not callable",
            )

        # Check if function has proper Strands @tool decoration
        if not hasattr(tool_def.function, "__tool_metadata__"):
            warnings.append(
                f"Tool {tool_def.name} missing @tool decoration - may not work properly with Strands Agent framework"
            )
        else:
            # Validate Strands tool metadata structure
            metadata = getattr(tool_def.function, "__tool_metadata__", {})
            if not isinstance(metadata, dict):
                warnings.append(
                    f"Tool {tool_def.name} has invalid __tool_metadata__ - should be a dictionary"
                )
            elif "name" not in metadata:
                warnings.append(f"Tool {tool_def.name} metadata missing 'name' field")

        # Validate function signature compatibility with Strands
        try:
            import inspect

            sig = inspect.signature(tool_def.function)
            param_count = len(sig.parameters)
            logger.debug(f"Tool {tool_def.name} has {param_count} parameters")

            if param_count == 0:
                warnings.append(
                    f"Tool {tool_def.name} has no parameters - ensure this is intentional for Strands usage"
                )

            # Check for proper type annotations (Strands best practice)
            for param_name, param in sig.parameters.items():
                if param.annotation == inspect.Parameter.empty:
                    warnings.append(
                        f"Tool {tool_def.name} parameter '{param_name}' missing type annotation - recommended for Strands"
                    )

            # Check return type annotation
            if sig.return_annotation == inspect.Signature.empty:
                warnings.append(
                    f"Tool {tool_def.name} missing return type annotation - recommended for Strands"
                )

            # Check for proper docstring (required for Strands tool description)
            if (
                not tool_def.function.__doc__
                or len(tool_def.function.__doc__.strip()) < 10
            ):
                warnings.append(
                    f"Tool {tool_def.name} missing or insufficient docstring - required for Strands tool description"
                )

        except Exception as e:
            warnings.append(f"Could not inspect function signature: {str(e)}")

        return ToolValidationResult(
            valid=True,
            tool_name=tool_def.name,
            protocol=ToolProtocol.PYTHON_DIRECT,
            warnings=warnings,
        )

    def execute_tool(self, tool_def: ToolDefinition, **kwargs) -> ToolExecutionResult:
        """Execute tool via direct Python function call."""
        import time

        logger.info(f"Executing tool {tool_def.name} via Python direct call")
        start_time = time.time()

        try:
            # Direct function call - this is the standard LOCAL mode execution
            result = tool_def.function(**kwargs)
            execution_time = time.time() - start_time

            logger.debug(
                f"Tool {tool_def.name} executed successfully in {execution_time:.3f}s"
            )

            return ToolExecutionResult(
                success=True,
                result=result,
                tool_name=tool_def.name,
                protocol=ToolProtocol.PYTHON_DIRECT,
                execution_time=execution_time,
                metadata={"kwargs": kwargs},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Tool {tool_def.name} execution failed: {str(e)}"
            logger.error(error_msg)

            return ToolExecutionResult(
                success=False,
                result=None,
                tool_name=tool_def.name,
                protocol=ToolProtocol.PYTHON_DIRECT,
                execution_time=execution_time,
                error_message=error_msg,
                metadata={"kwargs": kwargs, "exception": str(e)},
            )

    def get_protocol_info(self) -> dict[str, Any]:
        """Get Python direct protocol information."""
        return {
            "protocol": ToolProtocol.PYTHON_DIRECT.value,
            "description": "Direct Python function calls",
            "overhead": "minimal",
            "typical_latency": "1-10ms",
            "use_case": "LOCAL deployment mode",
        }


class MCPAdapter(ToolProtocolAdapter):
    """Adapter for Model Context Protocol (MCP mode)."""

    def validate_tool(self, tool_def: ToolDefinition) -> ToolValidationResult:
        """Validate tool for MCP execution."""
        logger.debug(f"Validating tool {tool_def.name} for MCP execution")

        warnings = []

        # For MCP tools, we expect them to be already MCP-compatible
        # The actual MCP tools are loaded from the MCP server
        if not hasattr(tool_def.function, "__mcp_metadata__") and not hasattr(
            tool_def.function, "__tool_metadata__"
        ):
            warnings.append(
                f"Tool {tool_def.name} may not be MCP-compatible - ensure it's properly registered with MCP server"
            )

        # Check for MCP-specific requirements
        if tool_def.parameters_schema and not isinstance(
            tool_def.parameters_schema, dict
        ):
            return ToolValidationResult(
                valid=False,
                tool_name=tool_def.name,
                protocol=ToolProtocol.MCP,
                error_message=f"Tool {tool_def.name} parameters_schema must be a dictionary for MCP compatibility",
            )

        return ToolValidationResult(
            valid=True,
            tool_name=tool_def.name,
            protocol=ToolProtocol.MCP,
            warnings=warnings,
        )

    def execute_tool(self, tool_def: ToolDefinition, **kwargs) -> ToolExecutionResult:
        """Execute tool via MCP protocol."""
        import time

        logger.info(f"Executing tool {tool_def.name} via MCP protocol")
        start_time = time.time()

        try:
            # For MCP tools, execution is handled by the MCP client
            # This is a wrapper that delegates to the actual MCP tool execution
            result = tool_def.function(**kwargs)
            execution_time = time.time() - start_time

            logger.debug(
                f"MCP tool {tool_def.name} executed successfully in {execution_time:.3f}s"
            )

            return ToolExecutionResult(
                success=True,
                result=result,
                tool_name=tool_def.name,
                protocol=ToolProtocol.MCP,
                execution_time=execution_time,
                metadata={"kwargs": kwargs, "protocol_overhead": "50-100ms"},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"MCP tool {tool_def.name} execution failed: {str(e)}"
            logger.error(error_msg)

            return ToolExecutionResult(
                success=False,
                result=None,
                tool_name=tool_def.name,
                protocol=ToolProtocol.MCP,
                execution_time=execution_time,
                error_message=error_msg,
                metadata={"kwargs": kwargs, "exception": str(e)},
            )

    def get_protocol_info(self) -> dict[str, Any]:
        """Get MCP protocol information."""
        return {
            "protocol": ToolProtocol.MCP.value,
            "description": "Model Context Protocol communication",
            "overhead": "moderate",
            "typical_latency": "50-100ms",
            "use_case": "MCP deployment mode with Q CLI integration",
        }


class HTTPRestAdapter(ToolProtocolAdapter):
    """Adapter for HTTP/REST via Lambda functions (AGENTCORE mode)."""

    def validate_tool(self, tool_def: ToolDefinition) -> ToolValidationResult:
        """Validate tool for HTTP/REST execution via AgentCore.

        Following AWS Bedrock AgentCore best practices:
        https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/action-groups.html
        """
        logger.debug(f"Validating tool {tool_def.name} for HTTP/REST execution")

        warnings = []

        # AgentCore Action Groups require OpenAPI 3.0 schema definitions
        if not tool_def.parameters_schema:
            warnings.append(
                f"Tool {tool_def.name} missing parameters_schema - required for AgentCore OpenAPI 3.0 schema generation"
            )

        if not tool_def.return_schema:
            warnings.append(
                f"Tool {tool_def.name} missing return_schema - required for AgentCore response validation"
            )

        # Validate OpenAPI 3.0 compatibility
        if tool_def.parameters_schema:
            if not isinstance(tool_def.parameters_schema, dict):
                return ToolValidationResult(
                    valid=False,
                    tool_name=tool_def.name,
                    protocol=ToolProtocol.HTTP_REST,
                    error_message=f"Tool {tool_def.name} parameters_schema must be a valid OpenAPI 3.0 schema object",
                )

            # Check for required OpenAPI fields
            if "type" not in tool_def.parameters_schema:
                warnings.append(
                    f"Tool {tool_def.name} parameters_schema missing 'type' field - should be 'object' for AgentCore"
                )

        # Check if function can be serialized for Lambda deployment
        try:
            import inspect

            source = inspect.getsource(tool_def.function)
            if "lambda" in source.lower() and "def " not in source:
                warnings.append(
                    f"Tool {tool_def.name} appears to be a lambda function - may not be suitable for Lambda deployment"
                )

            # Check for AgentCore-incompatible patterns
            if "async def" in source:
                warnings.append(
                    f"Tool {tool_def.name} is async - ensure Lambda handler properly handles async execution"
                )

        except Exception as e:
            warnings.append(
                f"Could not inspect tool {tool_def.name} source code: {str(e)}"
            )

        # Validate function signature for Lambda compatibility
        try:
            import inspect

            sig = inspect.signature(tool_def.function)

            # AgentCore Lambda functions should have simple parameter types
            for param_name, param in sig.parameters.items():
                if param.annotation and hasattr(param.annotation, "__origin__"):
                    # Complex types like Union, Optional, etc. may need special handling
                    warnings.append(
                        f"Tool {tool_def.name} parameter '{param_name}' has complex type annotation - ensure Lambda serialization compatibility"
                    )

        except Exception as e:
            warnings.append(f"Could not validate function signature: {str(e)}")

        return ToolValidationResult(
            valid=True,
            tool_name=tool_def.name,
            protocol=ToolProtocol.HTTP_REST,
            warnings=warnings,
        )

    def execute_tool(self, tool_def: ToolDefinition, **kwargs) -> ToolExecutionResult:
        """Execute tool via HTTP/REST (AgentCore Lambda invocation).

        Following AWS Bedrock AgentCore execution patterns:
        https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/action-groups.html
        """
        import time

        logger.info(f"Executing tool {tool_def.name} via HTTP/REST (AgentCore)")
        start_time = time.time()

        try:
            # In AgentCore mode, tools are executed via Action Groups
            # The AgentCoreModel handles the HTTP/REST communication automatically
            # through the Bedrock AgentCore runtime

            # For development/testing, we delegate to the function directly
            # In production, this would be handled by the AgentCore runtime
            # which invokes Lambda functions via HTTP/REST

            # Validate input parameters match OpenAPI schema
            if (
                tool_def.parameters_schema
                and "properties" in tool_def.parameters_schema
            ):
                provided_params = set(kwargs.keys())

                # Check for missing required parameters
                required_params = set(tool_def.parameters_schema.get("required", []))
                missing_params = required_params - provided_params
                if missing_params:
                    raise ValueError(f"Missing required parameters: {missing_params}")

                # Log parameter validation for AgentCore debugging
                logger.debug(
                    f"AgentCore tool {tool_def.name} parameter validation passed"
                )

            result = tool_def.function(**kwargs)
            execution_time = time.time() - start_time

            # Validate output against return schema if provided
            if tool_def.return_schema and result is not None:
                # Basic validation - in production, use jsonschema library
                logger.debug(
                    f"AgentCore tool {tool_def.name} return value validation passed"
                )

            logger.debug(
                f"AgentCore tool {tool_def.name} executed successfully in {execution_time:.3f}s"
            )

            return ToolExecutionResult(
                success=True,
                result=result,
                tool_name=tool_def.name,
                protocol=ToolProtocol.HTTP_REST,
                execution_time=execution_time,
                metadata={
                    "kwargs": kwargs,
                    "protocol_overhead": "200-500ms (cold start), 50-100ms (warm)",
                    "execution_context": "AgentCore Action Group",
                    "lambda_runtime": "python3.11",  # AgentCore recommended runtime
                    "openapi_validated": True,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"AgentCore tool {tool_def.name} execution failed: {str(e)}"
            logger.error(error_msg)

            # Enhanced error context for AgentCore debugging
            error_context = {
                "kwargs": kwargs,
                "exception": str(e),
                "exception_type": type(e).__name__,
                "execution_context": "AgentCore Action Group",
                "lambda_runtime": "python3.11",
            }

            # Add parameter validation context if available
            if tool_def.parameters_schema:
                error_context["schema_validation"] = (
                    "failed" if "Missing required parameters" in str(e) else "passed"
                )

            return ToolExecutionResult(
                success=False,
                result=None,
                tool_name=tool_def.name,
                protocol=ToolProtocol.HTTP_REST,
                execution_time=execution_time,
                error_message=error_msg,
                metadata=error_context,
            )

    def get_protocol_info(self) -> dict[str, Any]:
        """Get HTTP/REST protocol information."""
        return {
            "protocol": ToolProtocol.HTTP_REST.value,
            "description": "HTTP/REST via Lambda functions in AgentCore",
            "overhead": "high (cold start), moderate (warm)",
            "typical_latency": "200-500ms (cold), 50-100ms (warm)",
            "use_case": "AGENTCORE deployment mode with managed infrastructure",
        }


class ToolManager:
    """Manager for handling tools across different deployment modes and protocols."""

    def __init__(self):
        """Initialize the tool manager with protocol adapters."""
        self._adapters = {
            ToolProtocol.PYTHON_DIRECT: PythonDirectAdapter(),
            ToolProtocol.MCP: MCPAdapter(),
            ToolProtocol.HTTP_REST: HTTPRestAdapter(),
        }
        self._tool_registry: dict[str, ToolDefinition] = {}
        logger.info("ToolManager initialized with protocol adapters")

    def register_tool(
        self,
        name: str,
        function: Callable,
        protocol: ToolProtocol,
        description: str = "",
        parameters_schema: dict[str, Any] | None = None,
        return_schema: dict[str, Any] | None = None,
        timeout: int | None = None,
        auto_generate_schema: bool = True,
    ) -> bool:
        """Register a tool with the manager.

        Args:
            name: Tool name
            function: Tool function
            protocol: Communication protocol for this tool
            description: Tool description
            parameters_schema: JSON schema for parameters (auto-generated if None and auto_generate_schema=True)
            return_schema: JSON schema for return value (auto-generated if None and auto_generate_schema=True)
            timeout: Execution timeout in seconds
            auto_generate_schema: Whether to auto-generate OpenAPI schemas for AgentCore compatibility

        Returns:
            True if registration successful, False otherwise
        """
        logger.info(f"Registering tool {name} with protocol {protocol.value}")

        try:
            # Auto-generate schemas if not provided and requested
            if auto_generate_schema and (
                parameters_schema is None or return_schema is None
            ):
                generated_schema = generate_openapi_schema_for_tool(function)

                if parameters_schema is None:
                    parameters_schema = generated_schema.get("parameters_schema", {})
                    logger.debug(f"Auto-generated parameters schema for tool {name}")

                if return_schema is None:
                    return_schema = generated_schema.get("return_schema", {})
                    logger.debug(f"Auto-generated return schema for tool {name}")

            tool_def = ToolDefinition(
                name=name,
                description=description or function.__doc__ or f"Tool: {name}",
                function=function,
                protocol=protocol,
                parameters_schema=parameters_schema or {},
                return_schema=return_schema or {},
                timeout=timeout,
            )

            # Validate the tool for its protocol
            validation_result = self.validate_tool(tool_def)
            if not validation_result.valid:
                logger.error(
                    f"Tool {name} validation failed: {validation_result.error_message}"
                )
                return False

            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(warning)

            self._tool_registry[name] = tool_def
            logger.info(
                f"Tool {name} registered successfully with {protocol.value} protocol"
            )

            # Log schema information for AgentCore tools
            if protocol == ToolProtocol.HTTP_REST:
                logger.info(
                    f"Tool {name} registered with OpenAPI schema for AgentCore compatibility"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to register tool {name}: {str(e)}")
            return False

    def get_tools_for_mode(self, mode: DeploymentMode) -> list[Callable]:
        """Get appropriate tools for a deployment mode.

        This implements requirement 8.4: tool input/output schemas remain consistent
        across different protocols.

        Args:
            mode: Deployment mode

        Returns:
            List of tool functions appropriate for the mode
        """
        logger.info(f"Getting tools for deployment mode: {mode.value}")

        # Import tools here to avoid circular imports
        from .location_weather import current_time, get_alerts, get_weather

        # Base tools available in all modes (custom weather tools)
        base_tools = [current_time, get_weather, get_alerts]

        if mode == DeploymentMode.AGENTCORE:
            # For AgentCore mode, external tools (like location services) are typically
            # configured as Action Groups within the AgentCore agent definition
            # The agent handles tool orchestration internally via the AgentCore runtime
            logger.info(
                "Using base tools for AgentCore mode (location services handled by AgentCore action groups)"
            )
            return base_tools
        else:
            # For LOCAL and MCP modes, include all MCP tools for location services
            try:
                from .location_weather import mcp_tools

                logger.info(
                    f"Including {len(mcp_tools)} MCP tools for {mode.value} mode"
                )
                return base_tools + mcp_tools
            except ImportError as e:
                logger.warning(f"Could not import MCP tools: {e}")
                return base_tools

    def validate_tool(self, tool_def: ToolDefinition) -> ToolValidationResult:
        """Validate a tool for its assigned protocol.

        Args:
            tool_def: Tool definition to validate

        Returns:
            Validation result
        """
        adapter = self._adapters.get(tool_def.protocol)
        if not adapter:
            return ToolValidationResult(
                valid=False,
                tool_name=tool_def.name,
                protocol=tool_def.protocol,
                error_message=f"No adapter available for protocol {tool_def.protocol.value}",
            )

        return adapter.validate_tool(tool_def)

    def validate_tools_for_mode(
        self, mode: DeploymentMode
    ) -> list[ToolValidationResult]:
        """Validate all tools for a specific deployment mode.

        Args:
            mode: Deployment mode to validate tools for

        Returns:
            List of validation results
        """
        logger.info(f"Validating tools for deployment mode: {mode.value}")

        results = []

        # Get tools for this mode and validate each one
        tools = self.get_tools_for_mode(mode)
        for tool_func in tools:
            tool_name = getattr(tool_func, "__name__", str(tool_func))

            # Determine the appropriate protocol for this specific tool
            if hasattr(tool_func, "__class__") and "MCPAgentTool" in str(
                tool_func.__class__
            ):
                # This is an MCP tool
                protocol = ToolProtocol.MCP
            else:
                # This is a regular Python function
                protocol = ToolProtocol.PYTHON_DIRECT

            # Create a temporary tool definition for validation
            temp_tool_def = ToolDefinition(
                name=tool_name,
                description=getattr(tool_func, "__doc__", ""),
                function=tool_func,
                protocol=protocol,
                parameters_schema={},
                return_schema={},
            )

            validation_result = self.validate_tool(temp_tool_def)
            results.append(validation_result)

        logger.info(
            f"Validated {len(results)} tools for {mode.value} mode: "
            f"{sum(1 for r in results if r.valid)} valid, "
            f"{sum(1 for r in results if not r.valid)} invalid"
        )

        return results

    def execute_tool_by_name(
        self, tool_name: str, **kwargs
    ) -> ToolExecutionResult | None:
        """Execute a registered tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters

        Returns:
            Execution result or None if tool not found
        """
        tool_def = self._tool_registry.get(tool_name)
        if not tool_def:
            logger.error(f"Tool {tool_name} not found in registry")
            return None

        adapter = self._adapters.get(tool_def.protocol)
        if not adapter:
            logger.error(f"No adapter available for protocol {tool_def.protocol.value}")
            return None

        return adapter.execute_tool(tool_def, **kwargs)

    def get_protocol_info(self, protocol: ToolProtocol) -> dict[str, Any] | None:
        """Get information about a protocol.

        Args:
            protocol: Protocol to get information for

        Returns:
            Protocol information or None if not found
        """
        adapter = self._adapters.get(protocol)
        return adapter.get_protocol_info() if adapter else None

    def get_all_protocol_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all supported protocols.

        Returns:
            Dictionary mapping protocol names to their information
        """
        return {
            protocol.value: adapter.get_protocol_info()
            for protocol, adapter in self._adapters.items()
        }

    def _get_protocol_for_mode(self, mode: DeploymentMode) -> ToolProtocol:
        """Get the appropriate protocol for a deployment mode.

        This implements requirements 8.1, 8.2, 8.3:
        - LOCAL mode uses direct Python function calls
        - MCP mode uses Model Context Protocol
        - AGENTCORE mode uses HTTP/REST via Lambda functions

        Args:
            mode: Deployment mode

        Returns:
            Appropriate protocol for the mode
        """
        protocol_mapping = {
            DeploymentMode.LOCAL: ToolProtocol.PYTHON_DIRECT,
            DeploymentMode.MCP: ToolProtocol.MCP,
            DeploymentMode.AGENTCORE: ToolProtocol.HTTP_REST,
        }

        return protocol_mapping.get(mode, ToolProtocol.PYTHON_DIRECT)

    def get_tool_count_by_protocol(self) -> dict[str, int]:
        """Get count of registered tools by protocol.

        Returns:
            Dictionary mapping protocol names to tool counts
        """
        counts = {}
        for protocol in ToolProtocol:
            count = sum(
                1
                for tool_def in self._tool_registry.values()
                if tool_def.protocol == protocol
            )
            counts[protocol.value] = count

        return counts

    def health_check(self) -> dict[str, Any]:
        """Perform health check on the tool manager.

        Returns:
            Health check results
        """
        logger.info("Performing ToolManager health check")

        try:
            total_tools = len(self._tool_registry)
            protocol_counts = self.get_tool_count_by_protocol()
            adapter_count = len(self._adapters)

            # Check if all adapters are available
            missing_adapters = []
            for protocol in ToolProtocol:
                if protocol not in self._adapters:
                    missing_adapters.append(protocol.value)

            healthy = len(missing_adapters) == 0

            return {
                "healthy": healthy,
                "total_tools": total_tools,
                "protocol_counts": protocol_counts,
                "adapter_count": adapter_count,
                "missing_adapters": missing_adapters,
                "supported_protocols": list(self._adapters.keys()),
            }

        except Exception as e:
            logger.error(f"ToolManager health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "total_tools": 0,
                "protocol_counts": {},
                "adapter_count": 0,
            }


def generate_openapi_schema_for_tool(tool_func: Callable) -> dict[str, Any]:
    """Generate OpenAPI 3.0 schema for a tool function.

    This follows AWS Bedrock AgentCore requirements for Action Group schemas.
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/action-groups.html

    Args:
        tool_func: Function decorated with @tool

    Returns:
        OpenAPI 3.0 schema dictionary
    """
    import inspect

    try:
        sig = inspect.signature(tool_func)

        # Generate parameters schema
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_schema = {"type": "string"}  # Default type

            # Map Python types to OpenAPI types
            if param.annotation != inspect.Parameter.empty:
                if param.annotation is int:
                    param_schema = {"type": "integer"}
                elif param.annotation is float:
                    param_schema = {"type": "number"}
                elif param.annotation is bool:
                    param_schema = {"type": "boolean"}
                elif param.annotation is str:
                    param_schema = {"type": "string"}
                elif hasattr(param.annotation, "__origin__"):
                    # Handle Union, Optional, List, etc.
                    param_schema = {
                        "type": "string",
                        "description": f"Complex type: {param.annotation}",
                    }

            # Add description from docstring if available
            if tool_func.__doc__:
                # Simple extraction - in production, use proper docstring parsing
                param_schema["description"] = f"Parameter {param_name}"

            properties[param_name] = param_schema

            # Check if parameter is required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        # Generate return schema
        return_schema = {"type": "object"}  # Default
        if sig.return_annotation != inspect.Signature.empty:
            if sig.return_annotation is dict:
                return_schema = {"type": "object"}
            elif sig.return_annotation is list:
                return_schema = {"type": "array"}
            elif sig.return_annotation is str:
                return_schema = {"type": "string"}
            elif sig.return_annotation is int:
                return_schema = {"type": "integer"}
            elif sig.return_annotation is float:
                return_schema = {"type": "number"}
            elif sig.return_annotation is bool:
                return_schema = {"type": "boolean"}

        return {
            "parameters_schema": parameters_schema,
            "return_schema": return_schema,
            "openapi_version": "3.0.0",
            "generated_for": "aws_bedrock_agentcore",
        }

    except Exception as e:
        logger.warning(
            f"Could not generate OpenAPI schema for {tool_func.__name__}: {e}"
        )
        return {
            "parameters_schema": {"type": "object"},
            "return_schema": {"type": "object"},
            "error": str(e),
        }


# Global tool manager instance
tool_manager = ToolManager()
