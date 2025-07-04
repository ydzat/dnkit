"""MCP Toolkit - A modular MCP (Model Context Protocol) toolkit.

This package provides a comprehensive set of tools and services
for building MCP-compliant applications.
"""

__version__ = "0.1.0"
__author__ = "ydzat"
__email__ = "ydzat@live.com"

# Core exports
from .core.interfaces import ModuleInterface, ServiceModule
from .core.types import ToolCallRequest, ToolCallResponse, ToolDefinition

__all__ = [
    "ModuleInterface",
    "ServiceModule",
    "ToolDefinition",
    "ToolCallRequest",
    "ToolCallResponse",
]
