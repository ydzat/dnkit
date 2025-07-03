"""
JSON-RPC 2.0 protocol processor for MCP.

Handles parsing, validation, and formatting of JSON-RPC 2.0 messages
according to the Model Context Protocol specification.
"""

import json
import uuid
import asyncio
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from .base import ParseError, ValidationError


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message."""
    
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="Method parameters")
    id: Optional[Union[str, int]] = Field(None, description="Request ID")
    
    class Config:
        extra = "forbid"


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message."""
    
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Any] = Field(None, description="Method result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")
    id: Optional[Union[str, int]] = Field(None, description="Request ID")
    
    class Config:
        extra = "forbid"


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""
    
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")


class JSONRPCProcessor:
    """JSON-RPC 2.0 message processor."""
    
    # Standard JSON-RPC error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes (from -32000 to -32099)
    MCP_ERROR_BASE = -32000
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    PERMISSION_DENIED = -32003
    
    def __init__(self):
        self._method_handlers: Dict[str, callable] = {}
    
    def register_method(self, method_name: str, handler: callable) -> None:
        """Register a method handler."""
        self._method_handlers[method_name] = handler
    
    def unregister_method(self, method_name: str) -> None:
        """Unregister a method handler."""
        self._method_handlers.pop(method_name, None)
    
    async def process_message(self, message_data: Union[str, bytes]) -> str:
        """Process a JSON-RPC message and return response."""
        try:
            # Parse JSON
            if isinstance(message_data, bytes):
                message_data = message_data.decode('utf-8')
            
            try:
                parsed_data = json.loads(message_data)
            except json.JSONDecodeError as e:
                return self._create_error_response(
                    None, self.PARSE_ERROR, f"Parse error: {str(e)}"
                )
            
            # Handle batch requests
            if isinstance(parsed_data, list):
                return await self._process_batch(parsed_data)
            else:
                return await self._process_single_request(parsed_data)
                
        except Exception as e:
            return self._create_error_response(
                None, self.INTERNAL_ERROR, f"Internal error: {str(e)}"
            )
    
    async def _process_batch(self, requests: List[Dict[str, Any]]) -> str:
        """Process a batch of JSON-RPC requests."""
        if not requests:
            return self._create_error_response(
                None, self.INVALID_REQUEST, "Invalid request: empty batch"
            )
        
        responses = []
        for request_data in requests:
            response = await self._process_single_request(request_data)
            if response:  # Don't include responses for notifications
                try:
                    response_obj = json.loads(response)
                    responses.append(response_obj)
                except json.JSONDecodeError:
                    # If response parsing fails, include error response
                    responses.append(json.loads(self._create_error_response(
                        None, self.INTERNAL_ERROR, "Failed to process response"
                    )))
        
        return json.dumps(responses) if responses else ""
    
    async def _process_single_request(self, request_data: Dict[str, Any]) -> str:
        """Process a single JSON-RPC request."""
        request_id = request_data.get('id')
        
        try:
            # Validate request structure
            try:
                request = JSONRPCRequest(**request_data)
            except PydanticValidationError as e:
                return self._create_error_response(
                    request_id, self.INVALID_REQUEST, f"Invalid request: {str(e)}"
                )
            
            # Check if method exists
            if request.method not in self._method_handlers:
                # For notifications (no id), don't return error response
                if request.id is None:
                    return ""
                return self._create_error_response(
                    request.id, self.METHOD_NOT_FOUND, f"Method not found: {request.method}"
                )
            
            # Execute method
            handler = self._method_handlers[request.method]
            try:
                # Check if handler is async
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(request.params)
                else:
                    # Call sync function
                    result = handler(request.params)
                
                # For notifications (no id), don't return response
                if request.id is None:
                    return ""
                
                return self._create_success_response(request.id, result)
                
            except Exception as e:
                if request.id is None:
                    return ""
                return self._create_error_response(
                    request.id, self.TOOL_EXECUTION_ERROR, f"Execution error: {str(e)}"
                )
                
        except Exception as e:
            return self._create_error_response(
                request_id, self.INTERNAL_ERROR, f"Internal error: {str(e)}"
            )
    
    def _create_success_response(self, request_id: Union[str, int], result: Any) -> str:
        """Create a successful JSON-RPC response."""
        response = JSONRPCResponse(
            result=result,
            id=request_id
        )
        return response.model_dump_json()
    
    def _create_error_response(self, request_id: Optional[Union[str, int]], 
                             error_code: int, error_message: str, 
                             error_data: Optional[Any] = None) -> str:
        """Create an error JSON-RPC response."""
        error_obj = JSONRPCError(
            code=error_code,
            message=error_message,
            data=error_data
        )
        
        response = JSONRPCResponse(
            error=error_obj.model_dump(),
            id=request_id
        )
        return response.model_dump_json()
    
    def get_registered_methods(self) -> List[str]:
        """Get list of registered method names."""
        return list(self._method_handlers.keys())
