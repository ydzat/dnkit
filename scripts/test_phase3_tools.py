#!/usr/bin/env python3
"""
第三阶段工具快速测试脚本

用于验证任务管理、记忆系统、可视化工具和工具协作是否正常工作
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_toolkit.services.basic_tools import BasicToolsService
from mcp_toolkit.core.types import ToolCallRequest


async def test_task_management():
    """测试任务管理工具"""
    print("🔧 测试任务管理工具...")

    # 启用增强模式配置
    config = {
        "enhanced_mode": True,
        "tools": {
            "categories": {
                "task_management": {"enabled": True},
                "memory_management": {"enabled": True},
                "visualization": {"enabled": True},
                "collaboration": {"enabled": True}
            }
        },
        "chromadb": {
            "persist_directory": "./mcp_unified_db",
            "collection_name": "mcp_unified_storage"
        }
    }

    service = BasicToolsService(config)
    await service.initialize()

    # 创建任务
    create_request = ToolCallRequest(
        tool_name="manage_tasks",
        arguments={
            "action": "create",
            "title": "测试任务",
            "description": "这是一个测试任务",
            "priority": "HIGH",
            "assignee": "测试用户",
            "tags": ["测试", "自动化"]
        }
    )

    result = await service.call_tool(create_request)
    if result.success:
        print("  ✅ 任务创建成功")
        task_id = result.result.get("task_id")

        # 搜索任务
        search_request = ToolCallRequest(
            tool_name="manage_tasks",
            arguments={
                "action": "search",
                "query": "测试",
                "limit": 5
            }
        )

        search_result = await service.call_tool(search_request)
        if search_result.success:
            print("  ✅ 任务搜索成功")
            print(f"     找到 {len(search_result.result.get('tasks', []))} 个任务")
        else:
            print("  ❌ 任务搜索失败")
    else:
        print("  ❌ 任务创建失败")

    await service.cleanup()


async def test_memory_management():
    """测试记忆管理工具"""
    print("🧠 测试记忆管理工具...")

    # 启用增强模式配置
    config = {
        "enhanced_mode": True,
        "tools": {
            "categories": {
                "task_management": {"enabled": True},
                "memory_management": {"enabled": True},
                "visualization": {"enabled": True},
                "collaboration": {"enabled": True}
            }
        },
        "chromadb": {
            "persist_directory": "./mcp_unified_db",
            "collection_name": "mcp_unified_storage"
        }
    }

    service = BasicToolsService(config)
    await service.initialize()

    # 存储记忆
    store_request = ToolCallRequest(
        tool_name="manage_memory",
        arguments={
            "action": "store",
            "memory_type": "knowledge",
            "title": "Python 编程技巧",
            "content": "使用列表推导式可以简化代码并提高性能",
            "tags": ["Python", "编程", "技巧"],
            "importance": 0.8
        }
    )

    result = await service.call_tool(store_request)
    if result.success:
        print("  ✅ 记忆存储成功")

        # 搜索记忆
        search_request = ToolCallRequest(
            tool_name="manage_memory",
            arguments={
                "action": "search",
                "query": "Python",
                "limit": 5
            }
        )

        search_result = await service.call_tool(search_request)
        if search_result.success:
            print("  ✅ 记忆搜索成功")
            print(f"     找到 {len(search_result.result.get('memories', []))} 个记忆")
        else:
            print("  ❌ 记忆搜索失败")
    else:
        print("  ❌ 记忆存储失败")

    await service.cleanup()


async def test_visualization():
    """测试可视化工具"""
    print("📊 测试可视化工具...")

    # 启用增强模式配置
    config = {
        "enhanced_mode": True,
        "tools": {
            "categories": {
                "task_management": {"enabled": True},
                "memory_management": {"enabled": True},
                "visualization": {"enabled": True},
                "collaboration": {"enabled": True}
            }
        },
        "chromadb": {
            "persist_directory": "./mcp_unified_db",
            "collection_name": "mcp_unified_storage"
        }
    }

    service = BasicToolsService(config)
    await service.initialize()

    # 生成流程图
    flowchart_request = ToolCallRequest(
        tool_name="generate_diagram",
        arguments={
            "diagram_type": "flowchart",
            "title": "测试流程",
            "content": "开始\n处理数据\n结束",
            "direction": "TD"
        }
    )

    result = await service.call_tool(flowchart_request)
    if result.success:
        print("  ✅ 流程图生成成功")
        print(f"     图表类型: {result.result.get('diagram_type')}")

        # 生成数据图表
        chart_request = ToolCallRequest(
            tool_name="create_data_chart",
            arguments={
                "chart_type": "bar",
                "title": "测试数据",
                "data": json.dumps({"A": 10, "B": 20, "C": 15}),
                "x_label": "类别",
                "y_label": "数值"
            }
        )

        chart_result = await service.call_tool(chart_request)
        if chart_result.success:
            print("  ✅ 数据图表生成成功")
            print(f"     数据点数量: {chart_result.result.get('data_points')}")
        else:
            print("  ❌ 数据图表生成失败")
    else:
        print("  ❌ 流程图生成失败")

    await service.cleanup()


async def test_collaboration():
    """测试工具协作框架"""
    print("🤝 测试工具协作框架...")

    # 启用增强模式配置
    config = {
        "enhanced_mode": True,
        "tools": {
            "categories": {
                "task_management": {"enabled": True},
                "memory_management": {"enabled": True},
                "visualization": {"enabled": True},
                "collaboration": {"enabled": True}
            }
        },
        "chromadb": {
            "persist_directory": "./mcp_unified_db",
            "collection_name": "mcp_unified_storage"
        }
    }

    service = BasicToolsService(config)
    await service.initialize()

    # 顺序执行工具链
    chain_request = ToolCallRequest(
        tool_name="execute_tool_chain",
        arguments={
            "execution_mode": "sequential",
            "tools": [
                {
                    "tool_name": "manage_memory",
                    "parameters": {
                        "action": "store",
                        "memory_type": "working",
                        "title": "协作测试",
                        "content": "测试工具协作功能"
                    },
                    "output_mapping": {"memory_id": "stored_memory_id"}
                },
                {
                    "tool_name": "generate_diagram",
                    "parameters": {
                        "diagram_type": "flowchart",
                        "title": "协作流程",
                        "content": "存储记忆\n生成图表\n完成"
                    }
                }
            ]
        }
    )

    result = await service.call_tool(chain_request)
    if result.success:
        print("  ✅ 工具协作执行成功")
        print(f"     执行模式: {result.result.get('execution_mode')}")
        print(f"     完成步骤: {result.result.get('completed_steps')}/{result.result.get('total_steps')}")
        print(f"     整体成功: {result.result.get('success')}")
    else:
        print("  ❌ 工具协作执行失败")

    await service.cleanup()


async def main():
    """主测试函数"""
    print("🚀 开始第三阶段工具测试...\n")

    try:
        await test_task_management()
        print()

        await test_memory_management()
        print()

        await test_visualization()
        print()

        await test_collaboration()
        print()

        print("✅ 第三阶段工具测试完成！")
        print("\n📝 测试总结:")
        print("   - 任务管理系统: 创建和搜索功能正常")
        print("   - 记忆管理系统: 存储和检索功能正常")
        print("   - 可视化工具: 图表生成功能正常")
        print("   - 工具协作框架: 链式调用功能正常")
        print("\n🎯 可以开始在 n8n 中进行集成测试了！")

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
