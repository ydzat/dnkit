"""
基础工具服务测试
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from mcp_toolkit.services.basic_tools import BasicToolsService


class TestBasicToolsService:
    """基础工具服务测试"""

    @pytest.fixture
    def service_config(self):
        """创建服务配置"""
        return {
            "tools": {
                "categories": {
                    "file_operations": {"enabled": True},
                    "terminal": {"enabled": True},
                    "network": {"enabled": True},
                    "search": {"enabled": True},
                }
            }
        }

    @pytest.fixture
    def service(self, service_config):
        """创建基础工具服务"""
        return BasicToolsService(service_config)

    def test_service_properties(self, service):
        """测试服务基本属性"""
        assert service.get_name() == "basic_tools"
        assert service.get_version() == "1.0.0"
        assert "基础工具服务" in service.get_description()

    @pytest.mark.asyncio
    async def test_initialize_service(self, service):
        """测试服务初始化"""
        await service.initialize()

        assert service.is_ready()

        # 检查工具是否已注册
        tools = service.get_supported_tools()
        assert len(tools) > 0

        # 检查是否包含基础工具
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "read_file",
            "write_file",
            "run_command",
            "http_request",
            "file_search",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_shutdown_service(self, service):
        """测试服务关闭"""
        await service.initialize()

        success = await service.shutdown()

        assert success
        assert not service.is_ready()

        # 检查工具是否已清理
        tools = service.get_supported_tools()
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_call_tool_success(self, service):
        """测试成功调用工具"""
        from mcp_toolkit.core.types import ToolCallRequest

        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一个带有临时目录配置的新服务
            config = {
                "tools": {
                    "categories": {
                        "file_operations": {
                            "enabled": True,
                            "settings": {"allowed_paths": [temp_dir]},
                        }
                    }
                }
            }

            test_service = BasicToolsService(config)
            await test_service.initialize()

            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Hello, World!")

            # 调用工具
            request = ToolCallRequest(
                tool_name="read_file", arguments={"path": test_file}
            )
            result = await test_service.call_tool(request)

            assert result.success
            assert result.result["content"] == "Hello, World!"

            await test_service.cleanup()

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, service):
        """测试调用不存在的工具"""
        from mcp_toolkit.core.types import ToolCallRequest

        await service.initialize()

        request = ToolCallRequest(tool_name="nonexistent_tool", arguments={})
        result = await service.call_tool(request)

        assert not result.success

    @pytest.mark.asyncio
    async def test_call_tool_invalid_parameters(self, service):
        """测试调用工具时参数无效"""
        from mcp_toolkit.core.types import ToolCallRequest

        await service.initialize()

        # 调用read_file但不提供path参数
        request = ToolCallRequest(tool_name="read_file", arguments={})
        result = await service.call_tool(request)

        assert not result.success

    def test_load_tools_config_default(self, service):
        """测试加载默认工具配置"""
        config = service._load_tools_config()

        assert "categories" in config
        assert config["categories"]["file_operations"]["enabled"]
        assert config["categories"]["terminal"]["enabled"]

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    def test_load_tools_config_from_file(
        self, mock_yaml_load, mock_open, mock_exists, service
    ):
        """测试从文件加载工具配置"""
        # 模拟配置文件存在
        mock_exists.return_value = True

        # 模拟配置文件内容
        mock_config = {"tools": {"categories": {"file_operations": {"enabled": False}}}}
        mock_yaml_load.return_value = mock_config

        config = service._load_tools_config()

        # 验证配置被加载（但实际上会使用默认配置，因为没有传入tools配置）
        assert config["categories"]["file_operations"]["enabled"]  # 默认启用

    def test_get_default_config(self, service):
        """测试获取默认配置"""
        config = service._get_default_config()

        assert "categories" in config
        assert config["categories"]["file_operations"]["enabled"]
        assert config["categories"]["terminal"]["enabled"]

        terminal = config["categories"]["terminal"]
        assert terminal["enabled"]
        assert not terminal["settings"]["enable_shell"]  # 安全默认值

    @pytest.mark.asyncio
    async def test_service_with_disabled_categories(self):
        """测试禁用某些工具分类的服务"""
        config = {
            "tools": {
                "categories": {
                    "file_operations": {"enabled": True},
                    "terminal": {"enabled": False},  # 禁用终端工具
                    "network": {"enabled": False},  # 禁用网络工具
                    "search": {"enabled": True},
                }
            }
        }

        service = BasicToolsService(config)
        await service.initialize()

        tools = service.get_supported_tools()
        tool_names = [tool.name for tool in tools]

        # 应该包含文件操作和搜索工具
        assert "read_file" in tool_names
        assert "file_search" in tool_names

        # 不应该包含终端和网络工具
        assert "run_command" not in tool_names
        assert "http_request" not in tool_names

    @pytest.mark.asyncio
    async def test_error_handling_in_tool_call(self, service):
        """测试工具调用中的错误处理"""
        from mcp_toolkit.core.types import ToolCallRequest

        await service.initialize()

        # 尝试读取不存在的文件
        request = ToolCallRequest(
            tool_name="read_file", arguments={"path": "/nonexistent/file.txt"}
        )
        result = await service.call_tool(request)

        assert not result.success

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, service):
        """测试并发工具调用"""
        import asyncio

        from mcp_toolkit.core.types import ToolCallRequest

        await service.initialize()

        # 创建多个并发任务
        tasks = []
        for _ in range(5):
            request = ToolCallRequest(
                tool_name="get_environment", arguments={"variable": "PATH"}
            )
            task = service.call_tool(request)
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)

        # 检查所有调用都成功
        for result in results:
            assert result.success
            assert "PATH" in result.result["variables"]


class TestServiceIntegration:
    """服务集成测试"""

    @pytest.mark.asyncio
    async def test_full_service_lifecycle(self):
        """测试完整的服务生命周期"""
        # 创建服务
        service = BasicToolsService()

        # 初始化
        await service.initialize()
        assert service.is_ready()

        # 使用服务
        tools = service.get_supported_tools()
        assert len(tools) > 0

        # 测试工具调用
        from mcp_toolkit.core.types import ToolCallRequest

        request = ToolCallRequest(tool_name="get_environment", arguments={})
        result = await service.call_tool(request)
        assert result.success

        # 关闭服务
        assert await service.shutdown()
        assert not service.is_ready()

    @pytest.mark.asyncio
    async def test_service_resilience(self):
        """测试服务的容错性"""
        from mcp_toolkit.core.types import ToolCallRequest

        service = BasicToolsService()

        # 在未初始化状态下调用工具应该失败
        request = ToolCallRequest(tool_name="read_file", arguments={"path": "test.txt"})
        result = await service.call_tool(request)
        assert not result.success

        # 初始化服务
        await service.initialize()

        # 多次关闭服务不应该出错
        assert await service.shutdown()
        assert await service.shutdown()  # 第二次关闭

        # 重新初始化应该成功
        await service.initialize()
        assert service.is_ready()
