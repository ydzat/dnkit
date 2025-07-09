"""
Server-Sent Events (SSE) transport handler for MCP protocol.

Provides SSE server functionality with MCP protocol support,
specifically designed for n8n MCP client compatibility.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional, Set, Union, cast

from aiohttp import hdrs, web
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

from .base import ProtocolError, ProtocolHandler
from .jsonrpc import JSONRPCProcessor


class SSEConnection:
    """Represents a single SSE connection."""

    def __init__(self, connection_id: str, response: StreamResponse):
        self.connection_id = connection_id
        self.response = response
        self.is_active = True
        self.last_ping = asyncio.get_event_loop().time()

    async def send_event(
        self, event_type: str, data: str, event_id: Optional[str] = None
    ) -> None:
        """Send an SSE event to the client."""
        if not self.is_active:
            return

        try:
            # Format SSE message
            message = f"event: {event_type}\n"
            if event_id:
                message += f"id: {event_id}\n"
            message += f"data: {data}\n\n"

            await self.response.write(message.encode("utf-8"))
            await self.response.drain()

        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending SSE event: {e}")
            self.is_active = False

    async def send_message(self, data: str) -> None:
        """Send a message event."""
        await self.send_event("message", data)

    async def ping(self) -> None:
        """Send a ping event to keep connection alive."""
        await self.send_event("ping", "")
        self.last_ping = asyncio.get_event_loop().time()

    def close(self) -> None:
        """Mark connection as closed."""
        self.is_active = False


class SSETransportHandler(ProtocolHandler):
    """
    Server-Sent Events transport handler for MCP protocol.

    Provides SSE server functionality specifically designed for n8n MCP client compatibility.
    Supports both SSE and streamable HTTP transports as required by n8n.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8082,
        max_connections: int = 100,
        ping_interval: int = 30,
        connection_timeout: int = 300,  # 5 minutes
    ):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.ping_interval = ping_interval
        self.connection_timeout = connection_timeout

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._is_running = False

        # Connection management
        self._connections: Dict[str, SSEConnection] = {}
        self._ping_task: Optional[asyncio.Task] = None

        self.jsonrpc_processor = JSONRPCProcessor()
        self.logger = logging.getLogger(__name__)

    @property
    def is_running(self) -> bool:
        """Check if the handler is currently running."""
        return self._is_running

    async def start(self) -> None:
        """Start the SSE server."""
        if self._is_running:
            return

        self._app = web.Application()
        self._setup_routes()
        self._setup_middleware()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        # Start ping task
        self._ping_task = asyncio.create_task(self._ping_connections())

        self._is_running = True
        self.logger.info(f"SSE server started on http://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the SSE server."""
        if not self._is_running:
            return

        # Stop ping task
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for connection in list(self._connections.values()):
            connection.close()
        self._connections.clear()

        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        self._is_running = False
        self.logger.info("SSE server stopped")

    async def handle_request(self, request_data: bytes) -> bytes:
        """Handle incoming request and return response."""
        # For SSE, this method is not used directly
        # Messages are handled through SSE connections
        response_json = await self.jsonrpc_processor.process_message(request_data)
        return response_json.encode("utf-8") if response_json else b""

    def _setup_routes(self) -> None:
        """Setup SSE routes."""
        if self._app is None:
            raise RuntimeError("Application not initialized")

        # Streamable HTTP endpoints as per MCP specification
        # GET requests establish SSE streams
        self._app.router.add_get("/", self._handle_streamable_http_get)
        self._app.router.add_get("/mcp", self._handle_streamable_http_get)
        self._app.router.add_get("/{path:.*}", self._handle_streamable_http_get)

        # POST requests handle JSON-RPC messages
        self._app.router.add_post("/", self._handle_streamable_http_post)
        self._app.router.add_post("/mcp", self._handle_streamable_http_post)
        self._app.router.add_post("/{path:.*}", self._handle_streamable_http_post)

        # Health check endpoint
        self._app.router.add_get("/health", self._handle_health)

        # Handle OPTIONS for CORS
        self._app.router.add_options("/{path:.*}", self._handle_options)

    def _setup_middleware(self) -> None:
        """Setup middleware for CORS and error handling."""
        if self._app is None:
            raise RuntimeError("Application not initialized")

        @web.middleware
        async def cors_middleware(request: Request, handler: Any) -> web.Response:
            # Handle preflight requests
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                response = await handler(request)

            # Add CORS headers
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = "*"
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = "GET, POST, OPTIONS"
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = (
                "Content-Type, Authorization, Accept, Cache-Control"
            )
            response.headers[hdrs.ACCESS_CONTROL_EXPOSE_HEADERS] = "Content-Type"

            return response

        @web.middleware
        async def error_handling_middleware(
            request: Request, handler: Any
        ) -> web.Response:
            """Handle unknown methods and malformed requests."""
            try:
                # Log the request for debugging
                self.logger.debug(
                    f"Request: {request.method} {request.path} from {request.remote}"
                )

                # Handle unknown methods
                if request.method not in ["GET", "POST", "OPTIONS"]:
                    self.logger.warning(
                        f"Unknown method '{request.method}' from {request.remote}, returning method not allowed"
                    )
                    return web.Response(
                        status=405,
                        text="Method Not Allowed",
                        headers={
                            "Allow": "GET, POST, OPTIONS",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                            "Content-Type": "text/plain",
                        },
                    )

                response = await handler(request)
                return cast(web.Response, response)

            except Exception as e:
                self.logger.error(f"Error handling request from {request.remote}: {e}")
                return web.Response(
                    status=500,
                    text=f"Internal Server Error: {str(e)}",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Content-Type": "text/plain",
                    },
                )

        self._app.middlewares.append(error_handling_middleware)
        self._app.middlewares.append(cors_middleware)

    async def _handle_streamable_http_get(self, request: Request) -> StreamResponse:
        """Handle GET requests - establish SSE stream for Streamable HTTP."""
        # This is for GET requests to establish SSE streams as per MCP Streamable HTTP spec
        accept_header = request.headers.get("Accept", "")

        # Check if client accepts text/event-stream
        if "text/event-stream" in accept_header:
            return await self._establish_sse_stream(request)
        else:
            # Return information about the MCP endpoint
            return web.Response(
                text="MCP Server Streamable HTTP Endpoint\n"
                "POST with Accept: application/json, text/event-stream for MCP requests\n"
                "GET with Accept: text/event-stream for SSE connection",
                content_type="text/plain",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                },
            )

    async def _handle_options(self, request: Request) -> web.Response:
        """Handle CORS preflight requests."""
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Cache-Control",
                "Access-Control-Max-Age": "86400",
            }
        )

    async def _establish_sse_stream(self, request: Request) -> StreamResponse:
        """Handle SSE connection requests - support both traditional SSE and Streamable HTTP."""
        # 检查会话ID - 如果没有会话ID，创建一个新的（兼容传统SSE）
        session_id = request.headers.get("Mcp-Session-Id")
        if not session_id:
            # 为传统SSE客户端（如n8n）创建新会话
            session_id = str(uuid.uuid4())
            self.logger.info(
                f"Creating new SSE session for client {request.remote}: {session_id}"
            )
        else:
            self.logger.info(f"Using existing session for SSE stream: {session_id}")

        self.logger.info(
            f"SSE stream request from {request.remote} for session {session_id}"
        )

        # Check connection limit
        if len(self._connections) >= self.max_connections:
            self.logger.warning(f"Connection limit reached, rejecting {request.remote}")
            return web.Response(status=503, text="Too many connections")

        try:
            # Create SSE response with session ID
            response = StreamResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream; charset=utf-8",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Mcp-Session-Id": session_id,
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

            await response.prepare(request)

            # Create connection with session ID
            connection = SSEConnection(session_id, response)
            self._connections[session_id] = connection

            self.logger.info(f"SSE stream established for session: {session_id}")

            # 根据MCP官方文档，对于旧版SSE协议，需要发送endpoint事件
            # 告诉客户端POST消息的端点 - 应该直接发送URI字符串，不是JSON
            await connection.send_event("endpoint", "/")

            self.logger.info(f"Sent endpoint event to session: {session_id}")

            # Keep connection alive and handle messages
            while connection.is_active:
                try:
                    # Wait for client disconnect or timeout
                    await asyncio.sleep(1)

                    # Check for timeout
                    current_time = asyncio.get_event_loop().time()
                    if current_time - connection.last_ping > self.connection_timeout:
                        self.logger.info(f"Session {session_id} timed out")
                        break

                except asyncio.CancelledError:
                    self.logger.info(f"Session {session_id} cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Error in SSE session {session_id}: {e}")
                    break

            return response

        except Exception as e:
            self.logger.error(
                f"Error setting up SSE connection from {request.remote}: {e}"
            )
            return web.Response(
                status=500,
                text=f"Internal Server Error: {str(e)}",
                headers={"Access-Control-Allow-Origin": "*"},
            )
        finally:
            # Clean up connection
            if session_id and session_id in self._connections:
                connection = self._connections[session_id]
                connection.close()
                self._connections.pop(session_id, None)
                self.logger.info(f"SSE connection closed: {session_id}")

    async def _handle_streamable_http_post(self, request: Request) -> web.Response:
        """Handle HTTP POST requests for MCP Streamable HTTP transport."""
        self.logger.info(f"MCP POST request from {request.remote} to {request.path}")

        try:
            # Read request body
            body = await request.read()
            body_str = body.decode("utf-8", errors="ignore")
            self.logger.info(f"POST request body: {body_str}")  # 改为INFO级别以便查看

            # Parse JSON
            try:
                parsed_body = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in request body: {e}")
                return web.Response(
                    status=400,
                    text=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": "Parse error",
                                "data": str(e),
                            },
                            "id": None,
                        }
                    ),
                    content_type="application/json",
                    headers=self._get_cors_headers(),
                )

            # 检查会话ID
            session_id = request.headers.get("Mcp-Session-Id")

            # 检查请求类型
            is_initialize = self._is_initialize_request(parsed_body)
            is_notification = self._is_notification_request(parsed_body)
            is_mcp_request = self._is_mcp_request(parsed_body)

            if (is_initialize or is_notification or is_mcp_request) and not session_id:
                # 旧版SSE协议 - 查找活跃的SSE连接
                active_connections = [
                    conn for conn in self._connections.values() if conn.is_active
                ]

                if active_connections:
                    # 使用最新的SSE连接
                    connection = active_connections[-1]
                    session_id = connection.connection_id
                    if is_initialize:
                        request_type = "initialize"
                    elif is_notification:
                        request_type = "notification"
                    elif is_mcp_request:
                        request_type = "MCP request"
                    else:
                        request_type = "unknown request"
                    self.logger.info(
                        f"Using existing SSE session for {request_type}: {session_id}"
                    )

                    # 处理请求
                    response_json = await self.jsonrpc_processor.process_message(body)

                    # 通过SSE连接发送响应
                    if response_json:
                        try:
                            response_data = (
                                json.loads(response_json)
                                if isinstance(response_json, str)
                                else response_json
                            )
                            self.logger.info(
                                f"Initialize response data: {response_data}"
                            )  # 添加响应内容日志
                            await connection.send_event(
                                "message", json.dumps(response_data)
                            )
                            self.logger.info(
                                f"Sent initialize response via SSE: {session_id}"
                            )
                        except Exception as e:
                            self.logger.error(f"Failed to send SSE response: {e}")
                    else:
                        self.logger.warning("No response data to send for request")

                    # 返回202 Accepted（响应已通过SSE发送）
                    return web.Response(status=202, headers=self._get_cors_headers())
                else:
                    # 没有活跃的SSE连接，返回错误
                    return web.Response(
                        status=400,
                        text="No active SSE connection found",
                        headers=self._get_cors_headers(),
                    )

            elif session_id:
                # 现有会话 - 处理请求
                self.logger.debug(f"Processing request for session: {session_id}")

                # 处理JSON-RPC请求
                response_json = await self.jsonrpc_processor.process_message(body)

                # 检查是否有对应的SSE连接
                if session_id in self._connections:
                    connection = self._connections[session_id]
                    if connection.is_active and response_json:
                        # 通过SSE发送响应
                        try:
                            response_data = (
                                json.loads(response_json)
                                if isinstance(response_json, str)
                                else response_json
                            )
                            await connection.send_event(
                                "message", json.dumps(response_data)
                            )
                            self.logger.debug(
                                f"Sent response via SSE for session: {session_id}"
                            )
                        except Exception as e:
                            self.logger.error(f"Failed to send SSE response: {e}")

                # 返回202 Accepted（响应已通过SSE发送或将发送）
                return web.Response(
                    status=202,
                    headers={**self._get_cors_headers(), "Mcp-Session-Id": session_id},
                )

            else:
                # 无会话ID且非初始化请求
                return web.Response(
                    status=400,
                    text="Bad Request: Mcp-Session-Id header required or initialize request expected",
                    headers=self._get_cors_headers(),
                )

        except Exception as e:
            self.logger.error(
                f"Error processing MCP POST request from {request.remote}: {e}"
            )
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error", "data": str(e)},
                "id": None,
            }
            return web.Response(
                status=500,
                text=json.dumps(error_response),
                content_type="application/json",
                headers=self._get_cors_headers(),
            )

    async def _handle_health(self, request: Request) -> web.Response:
        """Handle health check requests."""
        return web.Response(
            text=json.dumps(
                {
                    "status": "healthy",
                    "connections": len(self._connections),
                    "max_connections": self.max_connections,
                }
            ),
            content_type="application/json",
        )

    async def _ping_connections(self) -> None:
        """Periodically ping all connections to keep them alive."""
        while self._is_running:
            try:
                await asyncio.sleep(self.ping_interval)

                # Ping all active connections
                for connection in list(self._connections.values()):
                    if connection.is_active:
                        try:
                            await connection.ping()
                        except Exception as e:
                            self.logger.error(
                                f"Error pinging connection {connection.connection_id}: {e}"
                            )
                            connection.close()

                # Clean up closed connections
                closed_connections = [
                    conn_id
                    for conn_id, conn in self._connections.items()
                    if not conn.is_active
                ]
                for conn_id in closed_connections:
                    self._connections.pop(conn_id, None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in ping task: {e}")

    async def broadcast_message(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        for connection in list(self._connections.values()):
            if connection.is_active:
                try:
                    await connection.send_message(message)
                except Exception as e:
                    self.logger.error(
                        f"Error broadcasting to {connection.connection_id}: {e}"
                    )
                    connection.close()

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len([conn for conn in self._connections.values() if conn.is_active])

    def _is_initialize_request(self, body: Any) -> bool:
        """检查请求是否为初始化请求"""
        if isinstance(body, dict):
            return bool(body.get("method") == "initialize")
        elif isinstance(body, list):
            return any(
                item.get("method") == "initialize"
                for item in body
                if isinstance(item, dict)
            )
        return False

    def _is_notification_request(self, body: Any) -> bool:
        """检查请求是否为通知请求（如notifications/initialized）"""
        if isinstance(body, dict):
            method = body.get("method", "")
            return method.startswith("notifications/") or method in [
                "notifications/initialized"
            ]
        elif isinstance(body, list):
            return any(
                item.get("method", "").startswith("notifications/")
                or item.get("method") in ["notifications/initialized"]
                for item in body
                if isinstance(item, dict)
            )
        return False

    def _is_mcp_request(self, body: Any) -> bool:
        """检查请求是否为MCP请求（tools/list, tools/call等）"""
        if isinstance(body, dict):
            method = body.get("method", "")
            return method.startswith("tools/") or method in ["tools/list", "tools/call"]
        elif isinstance(body, list):
            return any(
                item.get("method", "").startswith("tools/")
                or item.get("method") in ["tools/list", "tools/call"]
                for item in body
                if isinstance(item, dict)
            )
        return False

    async def _send_mcp_capabilities(self, connection: SSEConnection) -> None:
        """向新连接发送MCP服务器能力信息"""
        try:
            # 发送MCP服务器信息
            server_info = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": True}, "logging": {}},
                    "serverInfo": {
                        "name": "dnkit-mcp-toolkit",
                        "title": "DNKit MCP Toolkit Server",
                        "version": "1.0.0",
                    },
                    "instructions": "DNKit MCP工具集服务器，提供文件操作、终端执行、网络请求等工具功能",
                },
            }

            await connection.send_event("message", json.dumps(server_info))
            self.logger.info(
                f"已向连接 {connection.connection_id} 发送MCP服务器能力信息"
            )

        except Exception as e:
            self.logger.error(f"发送MCP能力信息失败: {e}")

    def _get_cors_headers(self) -> Dict[str, str]:
        """Get standard CORS headers."""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Mcp-Session-Id",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        }

    def _contains_requests(self, parsed_body: Any) -> bool:
        """Check if the parsed JSON body contains any requests."""
        if isinstance(parsed_body, list):
            # Batch - check each item
            for item in parsed_body:
                if isinstance(item, dict) and "method" in item and "id" in item:
                    return True
        elif isinstance(parsed_body, dict):
            # Single message - check if it's a request
            if "method" in parsed_body and "id" in parsed_body:
                return True
        return False

    async def _handle_post_with_sse(
        self, request: Request, body: bytes
    ) -> StreamResponse:
        """Handle POST request that should return an SSE stream."""
        self.logger.info(f"Creating SSE stream for POST request from {request.remote}")

        try:
            # Create SSE response
            response = StreamResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream; charset=utf-8",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive",
                    **self._get_cors_headers(),
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

            await response.prepare(request)

            # Process the JSON-RPC message and stream the response
            response_json = await self.jsonrpc_processor.process_message(body)

            if response_json:
                # Send the response as SSE event
                event_data = f"data: {response_json}\n\n"
                await response.write(event_data.encode("utf-8"))
                await response.drain()

            # Close the stream
            await response.write_eof()

            return response

        except Exception as e:
            self.logger.error(f"Error creating SSE stream for POST: {e}")
            # Fall back to regular error response
            raise
