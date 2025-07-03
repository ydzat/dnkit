"""
Middleware chain for request processing.

Provides extensible middleware system for logging, validation,
authentication, and other cross-cutting concerns.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod

from ..core.types import ToolCallRequest, ToolCallResponse


class Middleware(ABC):
    """Base middleware interface."""
    
    @abstractmethod
    async def process_request(self, request: ToolCallRequest, 
                            next_handler: Callable) -> ToolCallResponse:
        """Process request and call next handler in chain."""
        pass


class LoggingMiddleware(Middleware):
    """Middleware for request/response logging."""
    
    def __init__(self, logger=None):
        import logging
        self.logger = logger or logging.getLogger(__name__)
    
    async def process_request(self, request: ToolCallRequest, 
                            next_handler: Callable) -> ToolCallResponse:
        """Log request and response."""
        start_time = time.time()
        
        self.logger.debug(
            f"Tool call started: {request.tool_name} "
            f"(request_id: {request.request_id})"
        )
        
        try:
            response = await next_handler(request)
            
            duration = time.time() - start_time
            status = "success" if response.success else "error"
            
            self.logger.info(
                f"Tool call completed: {request.tool_name} "
                f"status={status} duration={duration:.3f}s "
                f"(request_id: {request.request_id})"
            )
            
            if not response.success:
                self.logger.warning(f"Tool call error: {response.error}")
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Tool call failed: {request.tool_name} "
                f"error={str(e)} duration={duration:.3f}s "
                f"(request_id: {request.request_id})"
            )
            raise


class ValidationMiddleware(Middleware):
    """Middleware for request validation."""
    
    def __init__(self, required_fields: Optional[List[str]] = None):
        self.required_fields = required_fields or ["tool_name"]
    
    async def process_request(self, request: ToolCallRequest, 
                            next_handler: Callable) -> ToolCallResponse:
        """Validate request before processing."""
        # Check required fields
        for field in self.required_fields:
            if not hasattr(request, field) or getattr(request, field) is None:
                return ToolCallResponse(
                    success=False,
                    error=f"Missing required field: {field}",
                    request_id=request.request_id
                )
        
        # Validate tool name format
        tool_name = request.tool_name
        if not tool_name or not isinstance(tool_name, str):
            return ToolCallResponse(
                success=False,
                error="Tool name must be a non-empty string",
                request_id=request.request_id
            )
        
        # Check for invalid characters
        if any(char in tool_name for char in [" ", "/", "\\", ":", "*", "?", "<", ">", "|"]):
            return ToolCallResponse(
                success=False,
                error="Tool name contains invalid characters",
                request_id=request.request_id
            )
        
        return await next_handler(request)


class RateLimitingMiddleware(Middleware):
    """Middleware for rate limiting."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.request_timestamps: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def process_request(self, request: ToolCallRequest, 
                            next_handler: Callable) -> ToolCallResponse:
        """Apply rate limiting based on session ID."""
        session_id = request.session_id or "default"
        current_time = time.time()
        
        async with self._lock:
            # Initialize session if not exists
            if session_id not in self.request_timestamps:
                self.request_timestamps[session_id] = []
            
            # Clean old timestamps (older than 1 minute)
            minute_ago = current_time - 60
            self.request_timestamps[session_id] = [
                ts for ts in self.request_timestamps[session_id] 
                if ts > minute_ago
            ]
            
            # Check rate limit
            if len(self.request_timestamps[session_id]) >= self.max_requests:
                return ToolCallResponse(
                    success=False,
                    error="Rate limit exceeded. Too many requests per minute.",
                    request_id=request.request_id
                )
            
            # Record current request
            self.request_timestamps[session_id].append(current_time)
        
        return await next_handler(request)


class PermissionMiddleware(Middleware):
    """Middleware for permission checking."""
    
    def __init__(self, permission_checker: Optional[Callable] = None):
        self.permission_checker = permission_checker
    
    async def process_request(self, request: ToolCallRequest, 
                            next_handler: Callable) -> ToolCallResponse:
        """Check permissions before tool execution."""
        if self.permission_checker:
            try:
                allowed = await self.permission_checker(request)
                if not allowed:
                    return ToolCallResponse(
                        success=False,
                        error="Permission denied for this tool",
                        request_id=request.request_id
                    )
            except Exception as e:
                return ToolCallResponse(
                    success=False,
                    error=f"Permission check failed: {str(e)}",
                    request_id=request.request_id
                )
        
        return await next_handler(request)


class MiddlewareChain:
    """Manages and executes middleware chain."""
    
    def __init__(self):
        self.middlewares: List[Middleware] = []
    
    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to the chain."""
        self.middlewares.append(middleware)
    
    def remove_middleware(self, middleware_type: type) -> None:
        """Remove middleware of specific type from chain."""
        self.middlewares = [
            mw for mw in self.middlewares 
            if not isinstance(mw, middleware_type)
        ]
    
    async def process(self, request: ToolCallRequest, 
                     final_handler: Callable) -> ToolCallResponse:
        """Process request through middleware chain."""
        if not self.middlewares:
            return await final_handler(request)
        
        # Create middleware chain
        async def create_handler(index: int) -> Callable:
            if index >= len(self.middlewares):
                return final_handler
            
            middleware = self.middlewares[index]
            next_handler = await create_handler(index + 1)
            
            async def handler(req: ToolCallRequest) -> ToolCallResponse:
                return await middleware.process_request(req, next_handler)
            
            return handler
        
        # Execute chain
        handler = await create_handler(0)
        return await handler(request)
    
    def get_middleware_types(self) -> List[str]:
        """Get list of middleware types in chain."""
        return [type(mw).__name__ for mw in self.middlewares]
