"""
WebSocket transport handler for MCP protocol.

Provides WebSocket server functionality with MCP protocol support,
connection management, and integration with JSON-RPC processor.
"""

import asyncio
import json
import logging
import weakref
from typing import Dict, Optional, Set

from aiohttp import WSMsgType, web
from aiohttp.web_request import Request
from aiohttp.web_ws import WebSocketResponse

from .base import ProtocolError, ProtocolHandler
from .jsonrpc import JSONRPCProcessor


class WebSocketConnection:
    """Represents a WebSocket connection."""

    def __init__(self, ws: WebSocketResponse, connection_id: str):
        self.ws = ws
        self.connection_id = connection_id
        self.is_active = True
        self.last_ping = asyncio.get_event_loop().time()

    async def send_message(self, message: str) -> bool:
        """Send a message to the client."""
        if not self.is_active or self.ws.closed:
            return False

        try:
            await self.ws.send_str(message)
            return True
        except Exception:
            self.is_active = False
            return False

    async def close(self) -> None:
        """Close the connection."""
        self.is_active = False
        if not self.ws.closed:
            await self.ws.close()


class WebSocketTransportHandler(ProtocolHandler):
    """WebSocket transport handler for MCP protocol."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8081,
        max_connections: int = 500,
        ping_interval: int = 30,
        max_message_size: int = 1024 * 1024,  # 1MB
    ):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.ping_interval = ping_interval
        self.max_message_size = max_message_size

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._is_running = False

        # Connection management
        self._connections: Dict[str, WebSocketConnection] = {}
        self._connection_counter = 0
        self._ping_task: Optional[asyncio.Task] = None

        self.jsonrpc_processor = JSONRPCProcessor()
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the WebSocket server."""
        if self._is_running:
            return

        self._app = web.Application()
        self._setup_routes()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        # Start ping task
        self._ping_task = asyncio.create_task(self._ping_connections())

        self._is_running = True
        self.logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
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
            await connection.close()
        self._connections.clear()

        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        self._is_running = False
        self.logger.info("WebSocket server stopped")

    @property
    def is_running(self) -> bool:
        """Check if the handler is currently running."""
        return self._is_running

    async def handle_request(self, request_data: bytes) -> bytes:
        """Handle incoming request and return response."""
        # For WebSocket, this method is not used directly
        # Messages are handled through WebSocket connections
        response_json = await self.jsonrpc_processor.process_message(request_data)
        return response_json.encode("utf-8") if response_json else b""

    def _setup_routes(self) -> None:
        """Setup WebSocket routes."""
        if self._app is None:
            raise RuntimeError("Application not initialized")
        self._app.router.add_get("/", self._handle_websocket)
        self._app.router.add_get("/mcp", self._handle_websocket)
        self._app.router.add_get("/ws", self._handle_websocket)

    async def _handle_websocket(self, request: Request) -> WebSocketResponse:
        """Handle WebSocket connection."""
        ws = WebSocketResponse(max_msg_size=self.max_message_size)
        await ws.prepare(request)

        # Check connection limit
        if len(self._connections) >= self.max_connections:
            await ws.close(code=1013, message=b"Server overloaded")
            return ws

        # Create connection
        self._connection_counter += 1
        connection_id = f"ws_{self._connection_counter}"
        connection = WebSocketConnection(ws, connection_id)
        self._connections[connection_id] = connection

        self.logger.info(f"WebSocket connection established: {connection_id}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(connection, msg.data)
                elif msg.type == WSMsgType.BINARY:
                    await self._handle_message(connection, msg.data.decode("utf-8"))
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
                    break
                elif msg.type == WSMsgType.CLOSE:
                    break

        except Exception as e:
            self.logger.error(
                f"Error handling WebSocket connection {connection_id}: {e}"
            )
        finally:
            # Clean up connection
            self._connections.pop(connection_id, None)
            connection.is_active = False
            self.logger.info(f"WebSocket connection closed: {connection_id}")

        return ws

    async def _handle_message(
        self, connection: WebSocketConnection, message: str
    ) -> None:
        """Handle incoming WebSocket message."""
        try:
            # Process JSON-RPC message
            response_json = await self.jsonrpc_processor.process_message(message)

            # Send response if not a notification
            if response_json:
                await connection.send_message(response_json)

        except Exception as e:
            self.logger.error(
                f"Error processing message from {connection.connection_id}: {e}"
            )

            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error", "data": str(e)},
                "id": None,
            }
            await connection.send_message(json.dumps(error_response))

    async def _ping_connections(self) -> None:
        """Periodically ping all connections."""
        while self._is_running:
            try:
                await asyncio.sleep(self.ping_interval)

                current_time = asyncio.get_event_loop().time()
                dead_connections = []

                for connection_id, connection in self._connections.items():
                    if not connection.is_active or connection.ws.closed:
                        dead_connections.append(connection_id)
                        continue

                    # Send ping
                    try:
                        await connection.ws.ping()
                        connection.last_ping = current_time
                    except Exception:
                        dead_connections.append(connection_id)

                # Remove dead connections
                for connection_id in dead_connections:
                    if connection_id in self._connections:
                        connection = self._connections.pop(connection_id)
                        await connection.close()
                        self.logger.info(f"Removed dead connection: {connection_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in ping task: {e}")

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def get_connection_ids(self) -> Set[str]:
        """Get all active connection IDs."""
        return set(self._connections.keys())

    async def broadcast_message(self, message: str) -> int:
        """Broadcast a message to all connections."""
        sent_count = 0
        dead_connections = []

        for connection_id, connection in self._connections.items():
            if await connection.send_message(message):
                sent_count += 1
            else:
                dead_connections.append(connection_id)

        # Clean up dead connections
        for connection_id in dead_connections:
            self._connections.pop(connection_id, None)

        return sent_count
