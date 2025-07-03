"""
MCP Toolkit - A modular MCP (Model Context Protocol) toolkit.

This package provides a comprehensive set of tools and services
for building MCP-compliant applications.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Core exports
from .core.interfaces import ModuleInterface, ServiceModule
from .core.types import ToolDefinition, ToolCallRequest, ToolCallResponse

__all__ = [
    "ModuleInterface",
    "ServiceModule", 
    "ToolDefinition",
    "ToolCallRequest",
    "ToolCallResponse",
]
