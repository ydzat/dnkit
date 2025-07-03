"""
Core module for MCP Toolkit.
"""

# Re-export main interfaces and types
from .interfaces import ModuleInterface, ServiceModule
from .types import ToolDefinition, ToolCallRequest, ToolCallResponse, ToolType, ConfigDict
from .logging import get_logger, configure_logging, LogConfig, ModuleLogger
from .i18n import get_text, set_locale, _, configure_i18n, I18nConfig

__all__ = [
    "ModuleInterface",
    "ServiceModule",
    "ToolDefinition", 
    "ToolCallRequest",
    "ToolCallResponse",
    "ToolType",
    "ConfigDict",
    "get_logger",
    "configure_logging", 
    "LogConfig",
    "ModuleLogger",
    "get_text",
    "set_locale",
    "_",
    "configure_i18n",
    "I18nConfig",
]
