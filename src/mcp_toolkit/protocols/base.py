"""
Base protocol handler interface.

Defines the fundamental interface that all protocol handlers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..core.types import ToolCallRequest, ToolCallResponse


class ProtocolHandler(ABC):
    """Base interface for protocol handlers."""

    @abstractmethod
    async def start(self) -> None:
        """Start the protocol handler."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the protocol handler."""
        pass

    @abstractmethod
    async def handle_request(self, request_data: bytes) -> bytes:
        """Handle incoming request and return response."""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the handler is currently running."""
        pass


class ProtocolError(Exception):
    """Base exception for protocol-related errors."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class ValidationError(ProtocolError):
    """Raised when request validation fails."""

    pass


class ParseError(ProtocolError):
    """Raised when request parsing fails."""

    pass


class RoutingError(ProtocolError):
    """Raised when request routing fails."""

    pass
