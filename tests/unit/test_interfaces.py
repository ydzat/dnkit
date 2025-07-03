"""
Unit tests for core interfaces.
"""

import pytest
from mcp_toolkit.core.interfaces import ModuleInterface, ServiceModule
from mcp_toolkit.core.types import ToolDefinition, ToolCallRequest, ToolCallResponse


class MockModule(ModuleInterface):
    """Mock implementation for testing."""
    
    def __init__(self, name: str = "test_module"):
        self._name = name
        self._initialized = False
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def cleanup(self) -> None:
        self._initialized = False
    
    @property
    def name(self) -> str:
        return self._name


@pytest.mark.asyncio
async def test_module_interface():
    """Test basic module interface functionality."""
    module = MockModule("test")
    
    assert module.name == "test"
    assert not module._initialized
    
    await module.initialize()
    assert module._initialized
    
    await module.cleanup()
    assert not module._initialized


def test_tool_definition():
    """Test tool definition creation."""
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters={"param1": {"type": "string"}}
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert "param1" in tool.parameters


def test_tool_call_request():
    """Test tool call request creation."""
    request = ToolCallRequest(
        tool_name="test_tool",
        arguments={"param1": "value1"},
        request_id="req_123"
    )
    
    assert request.tool_name == "test_tool"
    assert request.arguments["param1"] == "value1"
    assert request.request_id == "req_123"


def test_tool_call_response():
    """Test tool call response creation."""
    response = ToolCallResponse(
        success=True,
        result={"output": "test result"},
        request_id="req_123",
        execution_time=0.1
    )
    
    assert response.success is True
    assert response.result["output"] == "test result"
    assert response.request_id == "req_123"
    assert response.execution_time == 0.1
