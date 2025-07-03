"""
Core data types for MCP Toolkit.

This module defines the fundamental data structures used throughout
the MCP Toolkit.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# Type aliases
ConfigDict = Dict[str, Any]


class ToolType(str, Enum):
    """Tool type enumeration."""
    FUNCTION = "function"
    RESOURCE = "resource"
    PROMPT = "prompt"


class ToolDefinition(BaseModel):
    """Definition of a tool that can be called via MCP."""
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    tool_type: ToolType = Field(default=ToolType.FUNCTION, description="Tool type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters schema")
    required_permissions: List[str] = Field(default_factory=list, description="Required permissions")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolCallRequest(BaseModel):
    """Request to call a tool."""
    
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    session_id: Optional[str] = Field(None, description="Session ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolCallResponse(BaseModel):
    """Response from a tool call."""
    
    success: bool = Field(..., description="Whether the call was successful")
    result: Optional[Any] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
