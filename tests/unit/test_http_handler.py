"""
Unit tests for HTTP transport handler.
"""

import json

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from mcp_toolkit.protocols.http_handler import HTTPTransportHandler


class TestHTTPTransportHandler(AioHTTPTestCase):
    """Test HTTP transport handler functionality."""

    async def get_application(self):
        """Create test application."""
        self.handler = HTTPTransportHandler(
            host="127.0.0.1",
            port=8080,
            allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
        )

        # Register test methods
        def echo_method(params):
            return params

        def add_method(params):
            if not isinstance(params, dict):
                raise ValueError("Params must be a dict")
            return params.get("a", 0) + params.get("b", 0)

        self.handler.register_method("echo", echo_method)
        self.handler.register_method("add", add_method)

        # Setup app manually since we're using test framework
        app = web.Application()
        self.handler._app = app
        self.handler._setup_routes()
        self.handler._setup_middleware()

        return app

    @unittest_run_loop
    async def test_health_check(self):
        """Test health check endpoint."""
        resp = await self.client.request("GET", "/health")
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("registered_methods", data)
        self.assertIn("echo", data["registered_methods"])
        self.assertIn("add", data["registered_methods"])

    @unittest_run_loop
    async def test_methods_list(self):
        """Test methods listing endpoint."""
        resp = await self.client.request("GET", "/methods")
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertIn("methods", data)
        self.assertIn("echo", data["methods"])
        self.assertIn("add", data["methods"])

    @unittest_run_loop
    async def test_simple_mcp_request(self):
        """Test simple MCP JSON-RPC request."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "add",
            "params": {"a": 5, "b": 3},
            "id": 1,
        }

        resp = await self.client.request(
            "POST",
            "/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["result"], 8)
        self.assertEqual(data["id"], 1)

    @unittest_run_loop
    async def test_notification_request(self):
        """Test notification request (no response expected)."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "echo",
            "params": {"message": "test notification"},
        }

        resp = await self.client.request(
            "POST",
            "/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        # Notification should return 204 No Content
        self.assertEqual(resp.status, 204)

    @unittest_run_loop
    async def test_cors_headers(self):
        """Test CORS headers are properly set."""
        resp = await self.client.request(
            "GET", "/health", headers={"Origin": "http://localhost:3000"}
        )

        self.assertEqual(resp.status, 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)

    @unittest_run_loop
    async def test_cors_preflight(self):
        """Test CORS preflight handling."""
        resp = await self.client.request(
            "OPTIONS",
            "/mcp",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        self.assertEqual(resp.status, 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)
        self.assertIn("Access-Control-Allow-Methods", resp.headers)

    @unittest_run_loop
    async def test_invalid_content_type(self):
        """Test rejection of invalid content type."""
        resp = await self.client.request(
            "POST", "/mcp", data="test data", headers={"Content-Type": "text/plain"}
        )

        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("Content-Type", data["error"])

    @unittest_run_loop
    async def test_empty_request_body(self):
        """Test rejection of empty request body."""
        resp = await self.client.request(
            "POST", "/mcp", headers={"Content-Type": "application/json"}
        )

        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("Empty request body", data["error"])

    @unittest_run_loop
    async def test_batch_request(self):
        """Test batch JSON-RPC request."""
        batch_data = [
            {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1},
            {"jsonrpc": "2.0", "method": "echo", "params": {"msg": "test"}, "id": 2},
        ]

        resp = await self.client.request(
            "POST",
            "/mcp",
            json=batch_data,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["result"], 3)
        self.assertEqual(data[1]["result"], {"msg": "test"})


@pytest.mark.asyncio
async def test_handler_lifecycle():
    """Test handler start/stop lifecycle."""
    handler = HTTPTransportHandler(host="127.0.0.1", port=0)  # Random port

    assert not handler.is_running

    await handler.start()
    assert handler.is_running

    await handler.stop()
    assert not handler.is_running


@pytest.mark.asyncio
async def test_direct_request_handling():
    """Test direct request handling (without HTTP layer)."""
    handler = HTTPTransportHandler()

    def test_method(params):
        return {"echo": params}

    handler.register_method("test", test_method)

    request_data = json.dumps(
        {"jsonrpc": "2.0", "method": "test", "params": {"input": "hello"}, "id": 1}
    ).encode("utf-8")

    response_data = await handler.handle_request(request_data)
    response = json.loads(response_data.decode("utf-8"))

    assert response["jsonrpc"] == "2.0"
    assert response["result"]["echo"]["input"] == "hello"
    assert response["id"] == 1
