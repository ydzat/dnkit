"""Core interfaces for MCP Toolkit.

This module defines the fundamental interfaces that all modules
and services must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .types import ToolCallRequest, ToolCallResponse, ToolDefinition


class ModuleInterface(ABC):
    """Base interface for all MCP Toolkit modules."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the module."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up module resources."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the module name."""
        pass


class ServiceModule(ModuleInterface):
    """Interface for service modules that provide tools."""

    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """Get the list of tools provided by this service."""
        pass

    @abstractmethod
    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """Execute a tool call."""
        pass

    @abstractmethod
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the JSON schema for a specific tool."""
        pass
