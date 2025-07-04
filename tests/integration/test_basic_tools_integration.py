"""
基础工具模块集成测试
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from mcp_toolkit.core.types import ToolCallRequest
from mcp_toolkit.services.basic_tools import create_basic_tools_service


class TestBasicToolsIntegration:
    """基础工具模块集成测试"""

    @pytest.mark.asyncio
    async def test_file_operations_workflow(self):
        """测试完整的文件操作工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建基础工具服务
            config = {
                "tools": {
                    "categories": {
                        "file_operations": {
                            "enabled": True,
                            "settings": {"allowed_paths": [temp_dir]},
                        },
                        "search": {"enabled": True},
                    }
                }
            }

            service = create_basic_tools_service(config)
            await service.initialize()

            try:
                # 创建文件
                test_file = os.path.join(temp_dir, "test.txt")
                request = ToolCallRequest(
                    tool_name="write_file",
                    arguments={"path": test_file, "content": "Hello World!"},
                )
                result = await service.call_tool(request)
                assert result.success

                # 读取文件
                request = ToolCallRequest(
                    tool_name="read_file", arguments={"path": test_file}
                )
                result = await service.call_tool(request)
                assert result.success
                assert "Hello World!" in result.result["content"]

            finally:
                await service.cleanup()

    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """测试服务生命周期"""
        service = create_basic_tools_service()

        # 初始化
        await service.initialize()
        assert service.is_ready()

        # 获取工具列表
        tools = service.get_tools()
        assert len(tools) > 0

        # 关闭
        await service.cleanup()
        assert not service.is_ready()
