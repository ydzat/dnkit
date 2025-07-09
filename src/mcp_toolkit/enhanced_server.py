"""
MCP 工具集增强服务器

集成第一阶段的增强功能：
- ChromaDB 统一数据存储
- 增强的文件系统工具
- 增强的网络工具
- 增强的系统工具
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .core.interfaces import ToolDefinition
from .core.types import ConfigDict
from .storage.unified_manager import UnifiedDataManager
from .tools import (
    BaseTool,
    EchoTools,
    EnhancedFileOperationsTools,
    EnhancedNetworkTools,
    EnhancedSystemTools,
    FileOperationsTools,
    NetworkTools,
    SearchTools,
    TerminalTools,
    ToolRegistry,
)


class EnhancedMCPServer:
    """增强的 MCP 服务器，集成 ChromaDB 统一存储"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化增强的 MCP 服务器

        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)

        # 初始化工具注册中心
        self.tool_registry = ToolRegistry()

        # 初始化 ChromaDB 统一数据管理器
        chromadb_config = self.config.get("chromadb", {})
        persist_directory = chromadb_config.get("persist_directory", "./mcp_unified_db")
        self.data_manager = UnifiedDataManager(persist_directory)

        # 设置日志
        self._setup_logging()

        # 注册增强工具
        self._register_enhanced_tools()

        self.logger.info("增强的 MCP 服务器初始化完成")

    def _load_config(self, config_path: Optional[str]) -> ConfigDict:
        """加载配置文件"""
        if config_path is None:
            # 尝试默认配置文件路径
            default_paths = [
                "config/enhanced_tools_config.yaml",
                "enhanced_tools_config.yaml",
                "config.yaml",
            ]

            for path in default_paths:
                if Path(path).exists():
                    config_path = path
                    break

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    return config or {}
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return {}
        else:
            print("未找到配置文件，使用默认配置")
            return {}

    def _setup_logging(self) -> None:
        """设置日志"""
        log_config = self.config.get("logging", {})
        log_level = log_config.get("level", "INFO")

        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        self.logger = logging.getLogger("EnhancedMCPServer")

    def _register_enhanced_tools(self) -> None:
        """注册增强工具"""
        try:
            # 注册原有工具
            self._register_basic_tools()

            # 注册增强工具
            self._register_enhanced_file_tools()
            self._register_enhanced_network_tools()
            self._register_enhanced_system_tools()

            self.logger.info("所有增强工具注册完成")

        except Exception as e:
            self.logger.error(f"注册增强工具失败: {e}")
            raise

    def _register_basic_tools(self) -> None:
        """注册基础工具"""
        # Echo 工具
        echo_tools = EchoTools(self.config)
        for tool in echo_tools.create_tools():
            self.tool_registry.register_tool(tool)

        # 基础文件操作工具
        file_tools = FileOperationsTools(self.config)
        for tool in file_tools.create_tools():
            self.tool_registry.register_tool(tool)

        # 基础网络工具
        network_tools = NetworkTools(self.config)
        for tool in network_tools.create_tools():
            self.tool_registry.register_tool(tool)

        # 搜索工具
        search_tools = SearchTools(self.config)
        for tool in search_tools.create_tools():
            self.tool_registry.register_tool(tool)

        # 终端工具
        terminal_tools = TerminalTools(self.config)
        for tool in terminal_tools.create_tools():
            self.tool_registry.register_tool(tool)

        self.logger.info("基础工具注册完成")

    def _register_enhanced_file_tools(self) -> None:
        """注册增强文件工具"""
        enhanced_file_tools = EnhancedFileOperationsTools(self.config)
        for tool in enhanced_file_tools.create_tools():
            self.tool_registry.register_tool(tool)

        self.logger.info("增强文件工具注册完成")

    def _register_enhanced_network_tools(self) -> None:
        """注册增强网络工具"""
        enhanced_network_tools = EnhancedNetworkTools(self.config)
        for tool in enhanced_network_tools.create_tools():
            self.tool_registry.register_tool(tool)

        self.logger.info("增强网络工具注册完成")

    def _register_enhanced_system_tools(self) -> None:
        """注册增强系统工具"""
        enhanced_system_tools = EnhancedSystemTools(self.config)
        for tool in enhanced_system_tools.create_tools():
            self.tool_registry.register_tool(tool)

        self.logger.info("增强系统工具注册完成")

    async def get_data_stats(self) -> Dict[str, int]:
        """获取 ChromaDB 数据统计"""
        try:
            return self.data_manager.get_stats()
        except Exception as e:
            self.logger.error(f"获取数据统计失败: {e}")
            return {}

    async def search_unified_data(
        self, query: str, data_type: Optional[str] = None, max_results: int = 10
    ) -> Dict:
        """搜索统一数据存储"""
        try:
            return self.data_manager.query_data(
                query=query, data_type=data_type, n_results=max_results
            )
        except Exception as e:
            self.logger.error(f"搜索统一数据失败: {e}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]]}

    async def cleanup_data_type(self, data_type: str) -> bool:
        """清理指定类型的数据"""
        try:
            return self.data_manager.clear_data_type(data_type)
        except Exception as e:
            self.logger.error(f"清理数据类型 {data_type} 失败: {e}")
            return False

    def get_enhanced_tool_definitions(self) -> List[ToolDefinition]:
        """获取所有增强工具的定义"""
        definitions = []
        for tool_name in self.tool_registry.list_tools():
            tool = self.tool_registry.get_tool(tool_name)
            if tool and hasattr(tool, "get_definition"):
                definitions.append(tool.get_definition())
        return definitions

    async def start_enhanced_server(
        self, host: str = "localhost", port: int = 8000
    ) -> None:
        """启动增强服务器"""
        self.logger.info(f"启动增强 MCP 服务器: {host}:{port}")

        # 显示注册的工具
        tools = self.tool_registry.list_tools()
        self.logger.info(f"已注册 {len(tools)} 个工具: {', '.join(tools)}")

        # 显示 ChromaDB 统计
        stats = await self.get_data_stats()
        if stats:
            self.logger.info(f"ChromaDB 数据统计: {stats}")

        # 简单的服务器循环（实际项目中应该使用真正的 HTTP 服务器）
        self.logger.info("增强 MCP 服务器已启动，按 Ctrl+C 停止")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("服务器正在停止...")
            return


async def main() -> None:
    """主函数 - 启动增强的 MCP 服务器"""
    try:
        # 创建增强服务器
        server = EnhancedMCPServer()

        # 启动服务器
        await server.start_enhanced_server()

    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
