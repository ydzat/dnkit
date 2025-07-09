"""
HTTP transport handler for MCP protocol.

Provides HTTP server functionality with CORS support, request validation,
and integration with JSON-RPC processor.
"""

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional, Set

from aiohttp import hdrs, web
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from .base import ProtocolError, ProtocolHandler
from .jsonrpc import JSONRPCProcessor


class HTTPTransportHandler(ProtocolHandler):
    """HTTP transport handler for MCP protocol."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        allowed_origins: Optional[List[str]] = None,
        max_request_size: int = 1024 * 1024,
    ):  # 1MB default
        self.host = host
        self.port = port
        self.allowed_origins = set(allowed_origins) if allowed_origins else {"*"}
        self.max_request_size = max_request_size

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._is_running = False

        self.jsonrpc_processor = JSONRPCProcessor()
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the HTTP server."""
        if self._is_running:
            return

        self._app = web.Application(client_max_size=self.max_request_size)
        self._setup_routes()
        self._setup_middleware()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        self._is_running = True
        self.logger.info(f"HTTP server started on http://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if not self._is_running:
            return

        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        self._is_running = False
        self.logger.info("HTTP server stopped")

    async def handle_request(self, request_data: bytes) -> bytes:
        """Handle raw request data (used for testing)."""
        # This method is for direct testing without HTTP layer
        response = await self.jsonrpc_processor.process_message(request_data)
        return response.encode("utf-8")

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._is_running

    def register_method(self, method_name: str, handler: Callable) -> None:
        """Register a JSON-RPC method handler."""
        self.jsonrpc_processor.register_method(method_name, handler)

    def unregister_method(self, method_name: str) -> None:
        """Unregister a JSON-RPC method handler."""
        self.jsonrpc_processor.unregister_method(method_name)

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        if self._app is None:
            raise RuntimeError("Application not initialized")
        self._app.router.add_post("/mcp", self._handle_mcp_request)
        self._app.router.add_post("/", self._handle_mcp_request)  # 添加根路径支持
        self._app.router.add_get("/health", self._handle_health_check)
        self._app.router.add_get("/methods", self._handle_methods_list)
        self._app.router.add_options("/mcp", self._handle_preflight)
        self._app.router.add_options("/", self._handle_preflight)  # 添加根路径CORS支持

    def _setup_middleware(self) -> None:
        """Setup middleware chain."""
        if self._app is None:
            raise RuntimeError("Application not initialized")
        self._app.middlewares.append(self._cors_middleware)
        self._app.middlewares.append(self._error_middleware)
        self._app.middlewares.append(self._logging_middleware)

    @web.middleware
    async def _cors_middleware(self, request: Request, handler: Callable) -> Response:
        """Handle CORS headers."""
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)

        # Add CORS headers
        origin = request.headers.get("Origin", "")
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"

        return response

    @web.middleware
    async def _error_middleware(
        self, request: Request, handler: Callable[[Request], Awaitable[StreamResponse]]
    ) -> StreamResponse:
        """Handle errors and convert to appropriate HTTP responses."""
        try:
            response = await handler(request)
            return response
        except web.HTTPException:
            raise
        except ProtocolError as e:
            self.logger.error(f"Protocol error: {e.message}")
            return web.json_response(
                {"error": e.message, "code": e.error_code}, status=400
            )
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return web.json_response({"error": "Internal server error"}, status=500)

    @web.middleware
    async def _logging_middleware(
        self, request: Request, handler: Callable[[Request], Awaitable[StreamResponse]]
    ) -> StreamResponse:
        """Log requests and responses."""
        start_time = asyncio.get_event_loop().time()

        self.logger.debug(f"Request: {request.method} {request.path}")

        response = await handler(request)

        duration = asyncio.get_event_loop().time() - start_time
        self.logger.debug(f"Response: {response.status} in {duration:.3f}s")

        return response

    async def _handle_mcp_request(self, request: Request) -> Response:
        """Handle MCP JSON-RPC requests using Streamable HTTP protocol."""
        try:
            # Check Accept header to determine response type
            accept_header = request.headers.get("Accept", "application/json")
            supports_sse = "text/event-stream" in accept_header

            # Check content type
            content_type = request.headers.get("Content-Type", "")
            if not content_type.startswith("application/json"):
                return web.json_response(
                    {"error": "Content-Type must be application/json"}, status=400
                )

            # Read request body
            body = await request.read()
            if not body:
                return web.json_response({"error": "Empty request body"}, status=400)

            # Process JSON-RPC request
            response_json = await self.jsonrpc_processor.process_message(body)

            # Add CORS headers
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id",
                "Access-Control-Expose-Headers": "Mcp-Session-Id",
            }

            # Return response
            if response_json:
                return web.Response(
                    text=response_json, content_type="application/json", headers=headers
                )
            else:
                # For notification requests, return empty JSON response
                return web.Response(
                    text="{}", content_type="application/json", headers=headers
                )

        except Exception as e:
            self.logger.error(f"Error handling MCP request: {str(e)}")
            return web.json_response(
                {"error": "Failed to process request"},
                status=500,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id",
                },
            )

    async def _handle_health_check(self, request: Request) -> Response:
        """Handle health check requests."""
        health_data = {
            "status": "healthy",
            "server": "mcp-toolkit",
            "version": "0.1.0",
            "registered_methods": self.jsonrpc_processor.get_registered_methods(),
        }
        return web.json_response(health_data)

    async def _handle_methods_list(self, request: Request) -> Response:
        """Handle method listing requests."""
        methods_data = {"methods": self.jsonrpc_processor.get_registered_methods()}
        return web.json_response(methods_data)

    async def _handle_preflight(self, request: Request) -> Response:
        """Handle CORS preflight requests."""
        return web.Response()

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed by CORS policy."""
        if "*" in self.allowed_origins:
            return True

        for allowed_origin in self.allowed_origins:
            if allowed_origin.endswith("*"):
                prefix = allowed_origin[:-1]
                if origin.startswith(prefix):
                    return True
            elif origin == allowed_origin:
                return True

        return False
