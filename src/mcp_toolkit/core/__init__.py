"""
Core module for MCP Toolkit.
"""

from .i18n import I18nConfig, _, configure_i18n, get_text, set_locale

# Re-export main interfaces and types
from .interfaces import ModuleInterface, ServiceModule
from .logging import LogConfig, ModuleLogger, configure_logging, get_logger
from .types import (
    ConfigDict,
    ToolCallRequest,
    ToolCallResponse,
    ToolDefinition,
    ToolType,
)

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
