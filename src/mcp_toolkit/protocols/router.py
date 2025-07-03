"""
Request router for MCP toolkit.

Handles routing of tool calls to appropriate service modules and
manages tool discovery and registration.
"""

import asyncio
from typing import Any, Dict, List, Optional, Set

from ..core.interfaces import ServiceModule
from ..core.types import ToolCallRequest, ToolCallResponse, ToolDefinition
from .base import RoutingError


class RequestRouter:
    """Routes requests to appropriate service modules."""

    def __init__(self) -> None:
        self._services: Dict[str, ServiceModule] = {}
        self._tool_registry: Dict[str, str] = {}  # tool_name -> service_name
        self._service_tools: Dict[str, Set[str]] = {}  # service_name -> tool_names
        self._lock = asyncio.Lock()

    async def register_service(self, service: ServiceModule) -> None:
        """Register a service module."""
        async with self._lock:
            service_name = service.name

            # Remove old service if exists
            if service_name in self._services:
                await self.unregister_service(service_name)

            # Register new service
            self._services[service_name] = service
            self._service_tools[service_name] = set()

            # Register tools
            tools = service.get_tools()
            for tool in tools:
                tool_name = tool.name

                # Check for tool name conflicts
                if tool_name in self._tool_registry:
                    existing_service = self._tool_registry[tool_name]
                    raise RoutingError(
                        f"Tool '{tool_name}' already registered by service '{existing_service}'"
                    )

                self._tool_registry[tool_name] = service_name
                self._service_tools[service_name].add(tool_name)

    async def unregister_service(self, service_name: str) -> None:
        """Unregister a service module."""
        async with self._lock:
            if service_name not in self._services:
                return

            # Remove tool registrations
            if service_name in self._service_tools:
                for tool_name in self._service_tools[service_name]:
                    self._tool_registry.pop(tool_name, None)
                del self._service_tools[service_name]

            # Remove service
            del self._services[service_name]

    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """Route a tool call to the appropriate service."""
        tool_name = request.tool_name

        # Find service for tool
        service_name = self._tool_registry.get(tool_name)
        if not service_name:
            return ToolCallResponse(
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not found",
                request_id=request.request_id,
                execution_time=0.0,
            )

        # Get service
        service = self._services.get(service_name)
        if not service:
            return ToolCallResponse(
                success=False,
                result=None,
                error=f"Service '{service_name}' not found",
                request_id=request.request_id,
                execution_time=0.0,
            )

        # Execute tool call
        try:
            start_time = asyncio.get_event_loop().time()
            response = await service.call_tool(request)
            execution_time = asyncio.get_event_loop().time() - start_time

            # Add execution time if not already set
            if response.execution_time is None:
                response.execution_time = execution_time

            return response

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolCallResponse(
                success=False,
                result=None,
                error=f"Tool execution failed: {str(e)}",
                request_id=request.request_id,
                execution_time=execution_time,
            )

    def get_available_tools(self) -> List[ToolDefinition]:
        """Get all available tools from registered services."""
        tools = []
        for service in self._services.values():
            tools.extend(service.get_tools())
        return tools

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool."""
        service_name = self._tool_registry.get(tool_name)
        if not service_name:
            return None

        service = self._services.get(service_name)
        if not service:
            return None

        return service.get_tool_schema(tool_name)

    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific service."""
        service = self._services.get(service_name)
        if not service:
            return None

        tools = []
        if service_name in self._service_tools:
            tool_names = self._service_tools[service_name]
            service_tools = service.get_tools()
            tools = [tool for tool in service_tools if tool.name in tool_names]

        return {
            "name": service.name,
            "tools": [tool.model_dump() for tool in tools],
            "tool_count": len(tools),
        }

    def get_registered_services(self) -> List[str]:
        """Get list of registered service names."""
        return list(self._services.keys())

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tool_registry.keys())

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services."""
        health_info: Dict[str, Any] = {
            "router_status": "healthy",
            "registered_services": len(self._services),
            "registered_tools": len(self._tool_registry),
            "services": {},
        }

        services_info: Dict[str, Any] = health_info["services"]
        for service_name, service in self._services.items():
            try:
                # Basic health check - check if service has tools
                tools = service.get_tools()
                services_info[service_name] = {
                    "status": "healthy",
                    "tool_count": len(tools),
                }
            except Exception as e:
                services_info[service_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        return health_info
