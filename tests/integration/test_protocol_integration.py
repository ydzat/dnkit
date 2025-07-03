"""
Integration test for MCP protocol processing.

Tests the full protocol stack from HTTP request to JSON-RPC processing.
"""

import json
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from mcp_toolkit.protocols.http_handler import HTTPTransportHandler
from mcp_toolkit.protocols.router import RequestRouter
from mcp_toolkit.protocols.middleware import MiddlewareChain, LoggingMiddleware, ValidationMiddleware
from mcp_toolkit.core.interfaces import ServiceModule
from mcp_toolkit.core.types import ToolDefinition, ToolCallRequest, ToolCallResponse


class MockEchoService(ServiceModule):
    """Mock service for testing."""
    
    @property
    def name(self) -> str:
        return "echo_service"
    
    async def initialize(self) -> None:
        pass
    
    async def cleanup(self) -> None:
        pass
    
    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="echo",
                description="Echo the input message",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to echo"}
                    },
                    "required": ["message"]
                }
            )
        ]
    
    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        if request.tool_name == "echo":
            message = request.arguments.get("message", "")
            return ToolCallResponse(
                success=True,
                result={"echoed": message},
                request_id=request.request_id
            )
        else:
            return ToolCallResponse(
                success=False,
                error=f"Unknown tool: {request.tool_name}",
                request_id=request.request_id
            )
    
    def get_tool_schema(self, tool_name: str) -> dict:
        if tool_name == "echo":
            return {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        return {}


class TestProtocolIntegration(AioHTTPTestCase):
    """Test full protocol integration."""
    
    async def get_application(self):
        """Create integrated test application."""
        # Create components
        self.router = RequestRouter()
        self.handler = HTTPTransportHandler(
            host="127.0.0.1",
            port=8080,
            allowed_origins=["*"]
        )
        
        # Setup middleware
        middleware_chain = MiddlewareChain()
        middleware_chain.add_middleware(ValidationMiddleware())
        middleware_chain.add_middleware(LoggingMiddleware())
        
        # Register service
        self.echo_service = MockEchoService()
        await self.router.register_service(self.echo_service)
        
        # Register MCP methods with router
        async def list_tools(params):
            tools = self.router.get_available_tools()
            return [tool.model_dump() for tool in tools]
        
        async def call_tool(params):
            if not isinstance(params, dict):
                raise ValueError("Params must be an object")
            
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                raise ValueError("Tool name is required")
            
            request = ToolCallRequest(
                tool_name=tool_name,
                arguments=arguments,
                request_id=params.get("request_id")
            )
            
            # Process through middleware chain
            response = await middleware_chain.process(request, self.router.call_tool)
            return response.model_dump()
        
        self.handler.register_method("tools/list", list_tools)
        self.handler.register_method("tools/call", call_tool)
        
        # Setup app
        app = web.Application()
        self.handler._app = app
        self.handler._setup_routes()
        self.handler._setup_middleware()
        
        return app
    
    async def test_tool_discovery(self):
        """Test tool discovery via MCP."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }
        
        resp = await self.client.request(
            "POST", "/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertIsInstance(data["result"], list)
        self.assertEqual(len(data["result"]), 1)
        self.assertEqual(data["result"][0]["name"], "echo")
    
    async def test_tool_execution(self):
        """Test tool execution via MCP."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Hello, MCP!"},
                "request_id": "test-123"
            },
            "id": 2
        }
        
        resp = await self.client.request(
            "POST", "/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertTrue(data["result"]["success"])
        self.assertEqual(data["result"]["result"]["echoed"], "Hello, MCP!")
        self.assertEqual(data["result"]["request_id"], "test-123")
    
    async def test_tool_call_validation_error(self):
        """Test tool call with validation error."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                # Missing tool name
                "arguments": {"message": "test"}
            },
            "id": 3
        }
        
        resp = await self.client.request(
            "POST", "/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertIn("error", data)
        self.assertIn("Tool name is required", data["error"]["message"])
    
    async def test_unknown_tool_error(self):
        """Test calling unknown tool."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "nonexistent",
                "arguments": {}
            },
            "id": 4
        }
        
        resp = await self.client.request(
            "POST", "/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(resp.status, 200)
        
        data = await resp.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertFalse(data["result"]["success"])
        self.assertIn("not found", data["result"]["error"].lower())


@pytest.mark.asyncio
async def test_router_service_lifecycle():
    """Test router service lifecycle management."""
    router = RequestRouter()
    service = MockEchoService()
    
    # Initially no tools
    assert len(router.get_available_tools()) == 0
    assert len(router.get_registered_services()) == 0
    
    # Register service
    await router.register_service(service)
    assert len(router.get_available_tools()) == 1
    assert len(router.get_registered_services()) == 1
    assert "echo_service" in router.get_registered_services()
    
    # Test health check
    health = await router.health_check()
    assert health["router_status"] == "healthy"
    assert health["registered_services"] == 1
    assert health["registered_tools"] == 1
    
    # Unregister service
    await router.unregister_service("echo_service")
    assert len(router.get_available_tools()) == 0
    assert len(router.get_registered_services()) == 0
