"""
Unit tests for JSON-RPC processor.
"""

import json
import pytest
from mcp_toolkit.protocols.jsonrpc import JSONRPCProcessor, JSONRPCRequest, JSONRPCResponse


@pytest.fixture
def processor():
    """Create a JSON-RPC processor for testing."""
    return JSONRPCProcessor()


@pytest.fixture
def processor_with_methods():
    """Create a JSON-RPC processor with sample methods."""
    processor = JSONRPCProcessor()
    
    async def echo_method(params):
        return params
    
    def sync_add(params):
        if not isinstance(params, dict):
            raise ValueError("Params must be a dict")
        return params.get("a", 0) + params.get("b", 0)
    
    processor.register_method("echo", echo_method)
    processor.register_method("add", sync_add)
    
    return processor


@pytest.mark.asyncio
async def test_simple_request(processor_with_methods):
    """Test simple JSON-RPC request processing."""
    request = {
        "jsonrpc": "2.0",
        "method": "add",
        "params": {"a": 5, "b": 3},
        "id": 1
    }
    
    response_json = await processor_with_methods.process_message(json.dumps(request))
    response = json.loads(response_json)
    
    assert response["jsonrpc"] == "2.0"
    assert response["result"] == 8
    assert response["id"] == 1


@pytest.mark.asyncio
async def test_async_request(processor_with_methods):
    """Test async method call."""
    request = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"message": "hello world"},
        "id": "test-123"
    }
    
    response_json = await processor_with_methods.process_message(json.dumps(request))
    response = json.loads(response_json)
    
    assert response["jsonrpc"] == "2.0"
    assert response["result"] == {"message": "hello world"}
    assert response["id"] == "test-123"


@pytest.mark.asyncio
async def test_notification_request(processor_with_methods):
    """Test notification (no id) request."""
    request = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"message": "notification"}
    }
    
    response_json = await processor_with_methods.process_message(json.dumps(request))
    
    # Notifications should not return a response
    assert response_json == ""


@pytest.mark.asyncio
async def test_method_not_found(processor):
    """Test method not found error."""
    request = {
        "jsonrpc": "2.0",
        "method": "nonexistent",
        "params": {},
        "id": 1
    }
    
    response_json = await processor.process_message(json.dumps(request))
    response = json.loads(response_json)
    
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "not found" in response["error"]["message"].lower()
    assert response["id"] == 1


@pytest.mark.asyncio
async def test_invalid_json(processor):
    """Test invalid JSON parsing."""
    invalid_json = '{"jsonrpc": "2.0", "method": "test", "id": 1'  # Missing closing brace
    
    response_json = await processor.process_message(invalid_json)
    response = json.loads(response_json)
    
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32700  # Parse error


@pytest.mark.asyncio
async def test_invalid_request_structure(processor):
    """Test invalid request structure."""
    request = {
        "jsonrpc": "2.0",
        # Missing method
        "id": 1
    }
    
    response_json = await processor.process_message(json.dumps(request))
    response = json.loads(response_json)
    
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32600  # Invalid request


@pytest.mark.asyncio
async def test_batch_request(processor_with_methods):
    """Test batch request processing."""
    batch = [
        {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1},
        {"jsonrpc": "2.0", "method": "add", "params": {"a": 3, "b": 4}, "id": 2},
        {"jsonrpc": "2.0", "method": "echo", "params": {"msg": "test"}}  # Notification
    ]
    
    response_json = await processor_with_methods.process_message(json.dumps(batch))
    responses = json.loads(response_json)
    
    assert len(responses) == 2  # Notification doesn't return response
    assert responses[0]["result"] == 3
    assert responses[1]["result"] == 7


@pytest.mark.asyncio
async def test_method_execution_error(processor):
    """Test method execution error handling."""
    def failing_method(params):
        raise ValueError("Test error")
    
    processor.register_method("fail", failing_method)
    
    request = {
        "jsonrpc": "2.0",
        "method": "fail",
        "params": {},
        "id": 1
    }
    
    response_json = await processor.process_message(json.dumps(request))
    response = json.loads(response_json)
    
    assert response["jsonrpc"] == "2.0"
    assert "error" in response
    assert response["error"]["code"] == -32002  # Tool execution error
    assert "Test error" in response["error"]["message"]


def test_method_registration(processor):
    """Test method registration and listing."""
    def test_method(params):
        return "test"
    
    # Initially no methods
    assert len(processor.get_registered_methods()) == 0
    
    # Register method
    processor.register_method("test", test_method)
    assert "test" in processor.get_registered_methods()
    
    # Unregister method
    processor.unregister_method("test")
    assert "test" not in processor.get_registered_methods()


def test_jsonrpc_models():
    """Test JSON-RPC model validation."""
    # Valid request
    request = JSONRPCRequest(method="test", params={"a": 1}, id=1)
    assert request.method == "test"
    assert request.jsonrpc == "2.0"
    
    # Valid response
    response = JSONRPCResponse(result="success", id=1)
    assert response.result == "success"
    assert response.jsonrpc == "2.0"
    
    # Error response
    error_response = JSONRPCResponse(
        error={"code": -32000, "message": "Custom error"}, 
        id=1
    )
    assert error_response.error["code"] == -32000
