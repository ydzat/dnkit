"""
基础工具服务模块

集成所有基础工具，提供统一的服务接口。
"""

import os
from typing import Any, Dict, List, Optional, cast

import yaml

from ..core.interfaces import ModuleInterface, ServiceModule, ToolDefinition
from ..core.logging import get_logger
from ..core.types import ConfigDict, ToolCallRequest, ToolCallResponse
from ..tools.base import BaseTool, ToolRegistry, get_tool_registry
from ..tools.echo import EchoTools
from ..tools.file_operations import FileOperationsTools
from ..tools.network import NetworkTools
from ..tools.search import SearchTools
from ..tools.terminal import TerminalTools

logger = get_logger(__name__)


class BasicToolsService(ServiceModule):
    """基础工具服务"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.tools_config = self.config.get("tools", {})
        # 为每个服务实例创建独立的工具注册表
        self.registry = ToolRegistry()
        self._initialized = False

    @property
    def name(self) -> str:
        return "basic_tools"

    def get_name(self) -> str:
        """获取服务名称"""
        return self.name

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "基础工具服务，提供文件操作、终端执行、网络请求、搜索等功能"

    def _load_tools_config(self) -> Dict[Any, Any]:
        """加载工具配置"""
        # 首先使用传入的配置
        if "tools" in self.config:
            return cast(Dict[Any, Any], self.config["tools"])

        # 尝试从配置文件加载
        config_path = "config/modules/tools.yaml"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    return cast(Dict[Any, Any], config.get("tools", {}))
            except Exception as e:
                logger.error(f"加载工具配置文件失败: {e}")

        # 返回默认配置
        return self._get_default_config()

    def _get_default_config(self) -> Dict[Any, Any]:
        """获取默认配置"""
        return {
            "categories": {
                "file_operations": {
                    "enabled": True,
                    "settings": {
                        "allowed_paths": [],
                        "max_file_size": 10485760,  # 10MB
                    },
                },
                "terminal": {
                    "enabled": True,
                    "settings": {
                        "enable_shell": False,  # 安全默认值
                        "allowed_commands": [],
                        "timeout": 30,
                    },
                },
                "network": {
                    "enabled": True,
                    "settings": {
                        "allowed_hosts": [],
                        "timeout": 30,
                        "max_response_size": 1048576,  # 1MB
                    },
                },
                "search": {
                    "enabled": True,
                    "settings": {"max_results": 100, "max_depth": 10},
                },
            }
        }

    def _register_tools(self, tools_config: Dict) -> None:
        """注册工具"""
        categories = tools_config.get("categories", {})

        # 注册Echo工具（始终启用，用于测试）
        echo_tools = EchoTools(self.config)
        for tool in echo_tools.create_tools():
            self.registry.register_tool(tool)

        # 注册文件操作工具
        if categories.get("file_operations", {}).get("enabled", True):
            file_config = categories.get("file_operations", {}).get("settings", {})
            file_tools = FileOperationsTools(file_config)
            for tool in file_tools.create_tools():
                self.registry.register_tool(tool)

        # 注册终端工具
        if categories.get("terminal", {}).get("enabled", True):
            terminal_config = categories.get("terminal", {}).get("settings", {})
            terminal_tools = TerminalTools(terminal_config)
            for tool in terminal_tools.create_tools():
                self.registry.register_tool(tool)

        # 注册网络工具
        if categories.get("network", {}).get("enabled", True):
            network_config = categories.get("network", {}).get("settings", {})
            network_tools = NetworkTools(network_config)
            for tool in network_tools.create_tools():
                self.registry.register_tool(tool)

        # 注册搜索工具
        if categories.get("search", {}).get("enabled", True):
            search_config = categories.get("search", {}).get("settings", {})
            search_tools = SearchTools(search_config)
            for tool in search_tools.create_tools():
                self.registry.register_tool(tool)

    async def initialize(self) -> None:
        """初始化服务"""
        try:
            logger.info("初始化基础工具服务...")

            # 加载工具配置
            tools_config = self._load_tools_config()

            # 创建并注册工具
            self._register_tools(tools_config)

            self._initialized = True
            logger.info(
                f"基础工具服务初始化完成，注册了 {len(self.registry.list_tools())} 个工具"
            )

        except Exception as e:
            logger.exception("基础工具服务初始化失败")
            raise

    async def cleanup(self) -> None:
        """关闭服务"""
        try:
            logger.info("关闭基础工具服务...")

            # 清理所有工具
            for tool_name in self.registry.list_tools():
                tool = self.registry.get_tool(tool_name)
                if tool:
                    await tool.cleanup()
                self.registry.unregister_tool(tool_name)

            self._initialized = False
            logger.info("基础工具服务已关闭")

        except Exception as e:
            logger.exception("关闭基础工具服务时发生异常")
            raise

    def is_ready(self) -> bool:
        """检查服务是否就绪"""
        return self._initialized

    def get_tools(self) -> List[ToolDefinition]:
        """获取支持的工具定义"""
        definitions = []
        for tool_name in self.registry.list_tools():
            definition = self.registry.get_tool_definition(tool_name)
            if definition:
                definitions.append(definition)
        return definitions

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[Any, Any]]:
        """获取特定工具的JSON模式"""
        tool = self.registry.get_tool(tool_name)
        if tool:
            definition = tool.get_definition()
            return cast(Optional[Dict[Any, Any]], definition.parameters)
        return None

    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """调用工具"""
        from ..tools.base import ExecutionContext, ToolExecutionRequest

        # 创建执行请求
        exec_request = ToolExecutionRequest(
            tool_name=request.tool_name,
            parameters=request.arguments,
            execution_context=ExecutionContext(
                request_id=f"basic_tools_{request.tool_name}_{id(request.arguments)}",
                working_directory=".",
            ),
        )

        # 执行工具
        result = await self.registry.execute_tool(exec_request)

        # 转换结果格式
        if result.success:
            return ToolCallResponse(
                success=True,
                result=result.content,
                error=None,
                request_id=request.request_id,
                execution_time=(
                    result.metadata.execution_time if result.metadata else None
                ),
            )
        else:
            error_message = result.error.message if result.error else "未知错误"
            return ToolCallResponse(
                success=False,
                result=None,
                error=error_message,
                request_id=request.request_id,
                execution_time=(
                    result.metadata.execution_time if result.metadata else None
                ),
            )

    # 兼容性方法 - 保持向后兼容
    def get_supported_tools(self) -> List[ToolDefinition]:
        """获取支持的工具定义（兼容性方法）"""
        return self.get_tools()

    async def shutdown(self) -> bool:
        """关闭服务（兼容性方法）"""
        try:
            await self.cleanup()
            return True
        except Exception:
            return False


def create_basic_tools_service(
    config: Optional[ConfigDict] = None,
) -> BasicToolsService:
    """创建基础工具服务实例"""
    return BasicToolsService(config)
