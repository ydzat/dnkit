#!/usr/bin/env python3
"""
MCP协议合规性测试脚本
检查MCP工具集是否符合MCP协议规范
"""

import sys
import json
import asyncio
from pathlib import Path

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_toolkit.protocols.jsonrpc import JSONRPCProcessor, JSONRPCRequest, JSONRPCResponse
from mcp_toolkit.protocols.http_handler import HTTPTransportHandler
from mcp_toolkit.protocols.router import RequestRouter
from mcp_toolkit.protocols.middleware import MiddlewareChain
from mcp_toolkit.core.types import ToolCallRequest, ToolCallResponse


async def test_jsonrpc_basic_compliance():
    """测试JSON-RPC 2.0基本合规性"""
    print("🔍 测试JSON-RPC 2.0基本合规性...")
    
    processor = JSONRPCProcessor()
    
    # 注册一个测试方法
    async def test_handler(params):
        return {"status": "success", "received": params}
    
    processor.register_method("test_method", test_handler)
    
    # 测试有效的JSON-RPC请求
    valid_request = {
        "jsonrpc": "2.0",
        "method": "test_method",
        "params": {"test": "value"},
        "id": 1
    }
    
    request_json = json.dumps(valid_request)
    
    try:
        # 测试JSON-RPC请求处理
        response_json = await processor.process_message(request_json)
        response_data = json.loads(response_json)
        
        assert response_data["jsonrpc"] == "2.0"
        assert response_data["result"]["status"] == "success"
        assert response_data["result"]["received"]["test"] == "value"
        assert response_data["id"] == 1
        print("  ✅ JSON-RPC请求处理正确")
        
        # 测试响应对象创建
        response = JSONRPCResponse(
            jsonrpc="2.0",
            result={"status": "success"},
            id=1
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result["status"] == "success"
        assert response.id == 1
        print("  ✅ JSON-RPC响应对象正确")
        
        # 测试方法注册
        assert "test_method" in processor.get_registered_methods()
        print("  ✅ 方法注册功能正确")
        
    except Exception as e:
        print(f"  ❌ JSON-RPC合规性测试失败: {e}")
        return False
    
    return True


async def test_mcp_protocol_structure():
    """测试MCP协议结构"""
    print("🔍 测试MCP协议结构...")
    
    try:
        # 测试工具调用请求结构
        request = ToolCallRequest(
            tool_name="test_tool",
            arguments={"param1": "value1"},
            request_id="test-123"
        )
        
        assert request.tool_name == "test_tool"
        assert request.arguments["param1"] == "value1"
        assert request.request_id == "test-123"
        print("  ✅ ToolCallRequest结构正确")
        
        # 测试工具调用响应结构
        response = ToolCallResponse(
            success=True,
            result={"output": "test output"},
            request_id="test-123"
        )
        
        assert response.success is True
        assert response.result["output"] == "test output"
        assert response.request_id == "test-123"
        print("  ✅ ToolCallResponse结构正确")
        
    except Exception as e:
        print(f"  ❌ MCP协议结构测试失败: {e}")
        return False
    
    return True


async def test_transport_layer():
    """测试传输层"""
    print("🔍 测试传输层...")
    
    try:
        # 测试HTTP传输处理器初始化
        handler = HTTPTransportHandler(host="127.0.0.1", port=8081)
        
        assert handler.host == "127.0.0.1"
        assert handler.port == 8081
        assert handler.jsonrpc_processor is not None
        print("  ✅ HTTP传输处理器初始化正确")
        
        # 测试JSON-RPC处理器
        processor = handler.jsonrpc_processor
        assert len(processor.get_registered_methods()) == 0
        print("  ✅ JSON-RPC处理器初始化正确")
        
        # 测试路由器初始化
        router = RequestRouter()
        assert len(router._services) == 0
        assert len(router._tool_registry) == 0
        print("  ✅ 请求路由器初始化正确")
        
        # 测试中间件链初始化
        middleware = MiddlewareChain()
        assert len(middleware.middlewares) == 0
        print("  ✅ 中间件链初始化正确")
        
    except Exception as e:
        print(f"  ❌ 传输层测试失败: {e}")
        return False
    
    return True


async def main():
    """主测试函数"""
    print("🚀 MCP工具集协议合规性测试")
    print("=" * 50)
    
    tests = [
        test_jsonrpc_basic_compliance,
        test_mcp_protocol_structure,
        test_transport_layer
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
    
    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有MCP协议合规性测试通过！")
        return 0
    else:
        print("❌ 部分测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
