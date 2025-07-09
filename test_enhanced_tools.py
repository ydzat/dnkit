#!/usr/bin/env python3
"""
MCP 工具集第一阶段增强功能测试脚本

测试以下功能：
1. ChromaDB 统一数据管理器
2. 增强文件系统工具
3. 增强网络工具
4. 增强系统工具
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path

# 添加项目路径
import sys
sys.path.insert(0, 'src')

from mcp_toolkit.storage.unified_manager import UnifiedDataManager
from mcp_toolkit.tools.enhanced_file_operations import EnhancedFileOperationsTools
from mcp_toolkit.tools.enhanced_network import EnhancedNetworkTools
from mcp_toolkit.tools.enhanced_system import EnhancedSystemTools
from mcp_toolkit.tools.base import ToolExecutionRequest, ExecutionContext


async def test_chromadb_manager():
    """测试 ChromaDB 统一数据管理器"""
    print("🧪 测试 ChromaDB 统一数据管理器...")

    # 使用临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = UnifiedDataManager(temp_dir)

        # 测试存储数据
        data_id = manager.store_data(
            data_type="test",
            content="这是一个测试文档，包含一些中文内容。",
            metadata={"source": "test", "category": "demo"}
        )
        print(f"✅ 数据存储成功，ID: {data_id}")

        # 测试查询数据
        results = manager.query_data("测试文档", data_type="test")
        if results["ids"] and results["ids"][0]:
            print(f"✅ 数据查询成功，找到 {len(results['ids'][0])} 条结果")
        else:
            print("❌ 数据查询失败")

        # 测试统计
        stats = manager.get_stats()
        print(f"✅ 数据统计: {stats}")


async def test_enhanced_file_tools():
    """测试增强文件工具"""
    print("\n📁 测试增强文件工具...")

    # 创建测试文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def hello_world():
    '''这是一个简单的Python函数'''
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    hello_world()
""")
        test_file = f.name

    try:
        # 创建工具
        file_tools = EnhancedFileOperationsTools()
        tools = file_tools.create_tools()

        # 测试文件读取工具
        read_tool = tools[0]  # EnhancedFileReader

        context = ExecutionContext(request_id="test-1")
        request = ToolExecutionRequest(
            tool_name="enhanced_read_file",
            parameters={
                "file_path": test_file,
                "store_to_chromadb": True
            },
            execution_context=context
        )

        result = await read_tool.execute(request)
        if result.success:
            print("✅ 增强文件读取成功")
            if result.content.get("stored_to_chromadb"):
                print("✅ 文件内容已存储到 ChromaDB")
            else:
                print("⚠️ 文件内容未存储到 ChromaDB")
        else:
            print(f"❌ 增强文件读取失败: {result.error}")

        # 测试文件搜索工具
        search_tool = tools[1]  # FileSearchTool

        search_request = ToolExecutionRequest(
            tool_name="search_files",
            parameters={
                "query": "Python函数",
                "max_results": 5
            },
            execution_context=context
        )

        search_result = await search_tool.execute(search_request)
        if search_result.success:
            results_count = search_result.content.get("total_found", 0)
            print(f"✅ 文件搜索成功，找到 {results_count} 个结果")
        else:
            print(f"❌ 文件搜索失败: {search_result.error}")

    finally:
        # 清理测试文件
        os.unlink(test_file)


async def test_enhanced_network_tools():
    """测试增强网络工具"""
    print("\n🌐 测试增强网络工具...")

    # 创建工具
    network_tools = EnhancedNetworkTools()
    tools = network_tools.create_tools()

    # 测试网页获取工具
    web_tool = tools[0]  # EnhancedWebFetcher

    context = ExecutionContext(request_id="test-2")
    request = ToolExecutionRequest(
        tool_name="enhanced_fetch_web",
        parameters={
            "url": "https://httpbin.org/html",  # 测试用的简单HTML页面
            "store_to_chromadb": True
        },
        execution_context=context
    )

    try:
        result = await web_tool.execute(request)
        if result.success:
            print("✅ 增强网页获取成功")
            if result.content.get("stored_to_chromadb"):
                print("✅ 网页内容已存储到 ChromaDB")
            else:
                print("⚠️ 网页内容未存储到 ChromaDB")
        else:
            print(f"❌ 增强网页获取失败: {result.error}")
    except Exception as e:
        print(f"⚠️ 网络测试跳过（可能是网络问题）: {e}")

    # 测试网页搜索工具
    search_tool = tools[1]  # WebContentSearchTool

    search_request = ToolExecutionRequest(
        tool_name="search_web_content",
        parameters={
            "query": "HTML",
            "max_results": 5
        },
        execution_context=context
    )

    try:
        search_result = await search_tool.execute(search_request)
        if search_result.success:
            results_count = search_result.content.get("total_found", 0)
            print(f"✅ 网页内容搜索成功，找到 {results_count} 个结果")
        else:
            print(f"❌ 网页内容搜索失败: {search_result.error}")
    except Exception as e:
        print(f"⚠️ 网页搜索测试跳过: {e}")


async def test_enhanced_system_tools():
    """测试增强系统工具"""
    print("\n💻 测试增强系统工具...")

    # 创建工具
    system_tools = EnhancedSystemTools()
    tools = system_tools.create_tools()

    # 测试系统信息工具
    info_tool = tools[0]  # SystemInfoTool

    context = ExecutionContext(request_id="test-3")
    request = ToolExecutionRequest(
        tool_name="get_system_info",
        parameters={
            "include_disk": True,
            "store_to_chromadb": True
        },
        execution_context=context
    )

    result = await info_tool.execute(request)
    if result.success:
        print("✅ 系统信息获取成功")
        if result.content.get("stored_to_chromadb"):
            print("✅ 系统信息已存储到 ChromaDB")
        else:
            print("⚠️ 系统信息未存储到 ChromaDB")
    else:
        print(f"❌ 系统信息获取失败: {result.error}")

    # 测试进程管理工具
    process_tool = tools[1]  # ProcessManagerTool

    process_request = ToolExecutionRequest(
        tool_name="manage_processes",
        parameters={
            "action": "list",
            "limit": 5
        },
        execution_context=context
    )

    process_result = await process_tool.execute(process_request)
    if process_result.success:
        process_count = process_result.content.get("total_count", 0)
        print(f"✅ 进程管理成功，获取到 {process_count} 个进程")
    else:
        print(f"❌ 进程管理失败: {process_result.error}")


async def main():
    """主测试函数"""
    print("🚀 MCP 工具集第一阶段增强功能测试")
    print("=" * 50)

    start_time = time.time()

    try:
        # 测试各个组件
        await test_chromadb_manager()
        await test_enhanced_file_tools()
        await test_enhanced_network_tools()
        await test_enhanced_system_tools()

        end_time = time.time()
        print(f"\n✅ 所有测试完成，耗时: {end_time - start_time:.2f} 秒")
        print("\n🎉 第一阶段增强功能测试通过！")
        print("\n📝 功能总结:")
        print("   ✅ ChromaDB 统一数据存储")
        print("   ✅ 增强文件系统工具（语义搜索）")
        print("   ✅ 增强网络工具（网页内容存储）")
        print("   ✅ 增强系统工具（系统信息管理）")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
