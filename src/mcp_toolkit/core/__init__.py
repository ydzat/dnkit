"""
Core module for MCP Toolkit.
"""

# Re-export main interfaces and types
from .interfaces import ModuleInterface, ServiceModule
from .types import ToolDefinition, ToolCallRequest, ToolCallResponse, ToolType

__all__ = [
    "ModuleInterface",
    "ServiceModule",
    "ToolDefinition", 
    "ToolCallRequest",
    "ToolCallResponse",
    "ToolType",
]
