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

# 导入增强工具（如果可用）
try:
    from ..storage.unified_manager import UnifiedDataManager
    from ..tools.agent_automation import AgentAutomationTools
    from ..tools.agent_behavior import AgentBehaviorTools
    from ..tools.collaboration import ToolCollaborationFramework
    from ..tools.context_engine import ContextEngineTools
    from ..tools.context_tools import ContextTools
    from ..tools.enhanced_file_operations import EnhancedFileOperationsTools
    from ..tools.enhanced_network import EnhancedNetworkTools
    from ..tools.enhanced_system import EnhancedSystemTools
    from ..tools.git_integration import GitIntegrationTools
    from ..tools.intelligent_analysis import IntelligentAnalysisTools
    from ..tools.memory_management import MemoryManagementTools
    from ..tools.semantic_engine import SemanticIntelligenceTools
    from ..tools.task_management import create_task_tools
    from ..tools.version_management import VersionManagementTools
    from ..tools.visualization import create_visualization_tools

    ENHANCED_TOOLS_AVAILABLE = True
except ImportError:
    ENHANCED_TOOLS_AVAILABLE = False

logger = get_logger(__name__)


class BasicToolsService(ServiceModule):
    """基础工具服务"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.tools_config = self.config.get("tools", {})
        # 为每个服务实例创建独立的工具注册表
        self.registry = ToolRegistry()
        self._initialized = False
        self.data_manager: Optional[UnifiedDataManager] = None

        # 检查是否启用增强模式
        self.enhanced_mode = self._is_enhanced_mode_enabled()
        if self.enhanced_mode and ENHANCED_TOOLS_AVAILABLE:
            # 初始化 ChromaDB 统一数据管理器
            chromadb_config = self.config.get("chromadb", {})
            persist_directory = chromadb_config.get(
                "persist_directory", "./mcp_unified_db"
            )
            self.data_manager = UnifiedDataManager(persist_directory)
            logger.info("增强模式已启用，ChromaDB 统一数据管理器已初始化")
        else:
            self.data_manager = None

    @property
    def name(self) -> str:
        return "basic_tools"

    def get_name(self) -> str:
        """获取服务名称"""
        return self.name

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        if self.enhanced_mode:
            return "增强工具服务，提供基础工具 + ChromaDB统一存储、语义搜索等增强功能"
        return "基础工具服务，提供文件操作、终端执行、网络请求、搜索等功能"

    def _is_enhanced_mode_enabled(self) -> bool:
        """检查是否启用增强模式"""
        # 检查配置文件路径是否包含 enhanced
        config_file = os.environ.get("MCP_CONFIG_FILE", "")
        if "enhanced" in config_file.lower():
            return True

        # 检查配置中是否明确启用增强模式
        return bool(self.config.get("enhanced_mode", False))

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
                "task_management": {
                    "enabled": True,
                    "settings": {
                        "auto_store_to_chromadb": True,
                        "max_tasks_per_query": 50,
                    },
                },
                "visualization": {
                    "enabled": True,
                    "settings": {
                        "default_theme": "default",
                        "max_nodes": 1000,
                        "enable_auto_generation": True,
                    },
                },
                "memory_management": {
                    "enabled": True,
                    "settings": {
                        "auto_store_to_chromadb": True,
                        "max_memories_per_query": 50,
                        "default_importance_threshold": 0.5,
                        "enable_auto_cleanup": True,
                        "memory_retention_days": 90,
                    },
                },
                "collaboration": {
                    "enabled": True,
                    "settings": {
                        "max_parallel_tasks": 5,
                        "enable_caching": True,
                        "default_timeout": 300,
                        "enable_rollback": False,
                    },
                },
            }
        }

    def _register_tools(self, tools_config: Dict) -> None:
        """注册工具"""
        categories = tools_config.get("categories", {})

        # 注册Echo工具（始终启用，用于测试）
        echo_tools = EchoTools(self.config)
        for tool in echo_tools.create_tools():
            self.registry.register_tool(tool, "基础工具")

        # 注册文件操作工具
        if categories.get("file_operations", {}).get("enabled", True):
            file_config = categories.get("file_operations", {}).get("settings", {})
            file_tools = FileOperationsTools(file_config)
            for tool in file_tools.create_tools():
                self.registry.register_tool(tool, "文件操作")

        # 注册终端工具
        if categories.get("terminal", {}).get("enabled", True):
            terminal_config = categories.get("terminal", {}).get("settings", {})
            terminal_tools = TerminalTools(terminal_config)
            for tool in terminal_tools.create_tools():
                self.registry.register_tool(tool, "终端操作")

        # 注册网络工具
        if categories.get("network", {}).get("enabled", True):
            network_config = categories.get("network", {}).get("settings", {})
            network_tools = NetworkTools(network_config)
            for tool in network_tools.create_tools():
                self.registry.register_tool(tool, "网络操作")

        # 注册搜索工具
        if categories.get("search", {}).get("enabled", True):
            search_config = categories.get("search", {}).get("settings", {})
            search_tools = SearchTools(search_config)
            for tool in search_tools.create_tools():
                self.registry.register_tool(tool, "搜索工具")

        # 注册增强工具（如果启用增强模式）
        if self.enhanced_mode and ENHANCED_TOOLS_AVAILABLE:
            self._register_enhanced_tools(categories)

    async def initialize(self) -> None:
        """初始化服务"""
        try:
            logger.info("初始化基础工具服务...")

            # 加载工具配置
            tools_config = self._load_tools_config()

            # 创建并注册工具
            self._register_tools(tools_config)

            self._initialized = True
            tool_count = len(self.registry.list_tools())
            if self.enhanced_mode:
                logger.info(
                    f"增强工具服务初始化完成，注册了 {tool_count} 个工具（包含增强功能）"
                )
            else:
                logger.info(f"基础工具服务初始化完成，注册了 {tool_count} 个工具")

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

    def _register_enhanced_tools(self, categories: Dict[str, Any]) -> None:
        """注册增强工具"""
        try:
            # 注册增强文件操作工具
            if categories.get("enhanced_file_operations", {}).get("enabled", True):
                enhanced_file_config = categories.get(
                    "enhanced_file_operations", {}
                ).get("settings", {})
                enhanced_file_tools = EnhancedFileOperationsTools(enhanced_file_config)
                for tool in enhanced_file_tools.create_tools():
                    self.registry.register_tool(tool, "增强文件操作")
                logger.info("增强文件操作工具注册完成")

            # 注册增强网络工具
            if categories.get("enhanced_network", {}).get("enabled", True):
                enhanced_network_config = categories.get("enhanced_network", {}).get(
                    "settings", {}
                )
                enhanced_network_tools = EnhancedNetworkTools(enhanced_network_config)
                for tool in enhanced_network_tools.create_tools():
                    self.registry.register_tool(tool, "增强网络操作")
                logger.info("增强网络工具注册完成")

            # 注册增强系统工具
            if categories.get("enhanced_system", {}).get("enabled", True):
                enhanced_system_config = categories.get("enhanced_system", {}).get(
                    "settings", {}
                )
                enhanced_system_tools = EnhancedSystemTools(enhanced_system_config)
                for tool in enhanced_system_tools.create_tools():
                    self.registry.register_tool(tool, "增强系统操作")
                logger.info("增强系统工具注册完成")

            # 注册上下文引擎工具（第二阶段）
            if categories.get("context_tools", {}).get("enabled", True):
                context_tools_config = categories.get("context_tools", {}).get(
                    "settings", {}
                )
                context_tools = ContextTools(context_tools_config)
                for tool in context_tools.create_tools():
                    self.registry.register_tool(tool, "上下文引擎")
                logger.info("上下文引擎工具注册完成")

            # 注册 Git 集成工具（第一阶段增强）
            if categories.get("git_integration", {}).get("enabled", True):
                git_config = categories.get("git_integration", {}).get("settings", {})
                # 合并 ChromaDB 配置
                if self.data_manager:
                    git_config["chromadb_path"] = self.data_manager.persist_directory
                git_tools = GitIntegrationTools(git_config)
                for tool in git_tools.create_tools():
                    self.registry.register_tool(tool, "Git集成")
                logger.info("Git 集成工具注册完成")

            # 注册版本管理工具（第一阶段增强）
            if categories.get("version_management", {}).get("enabled", True):
                version_config = categories.get("version_management", {}).get(
                    "settings", {}
                )
                # 合并 ChromaDB 配置
                if self.data_manager:
                    version_config["chromadb_path"] = (
                        self.data_manager.persist_directory
                    )
                version_tools = VersionManagementTools(version_config)
                for tool in version_tools.create_tools():
                    self.registry.register_tool(tool, "版本管理")
                logger.info("版本管理工具注册完成")

            # 注册 Agent 自动化工具（第一阶段增强）
            if categories.get("agent_automation", {}).get("enabled", True):
                automation_config = categories.get("agent_automation", {}).get(
                    "settings", {}
                )
                # 合并 ChromaDB 配置
                if self.data_manager:
                    automation_config["chromadb_path"] = (
                        self.data_manager.persist_directory
                    )
                automation_tools = AgentAutomationTools(automation_config)
                for tool in automation_tools.create_tools():
                    self.registry.register_tool(tool, "Agent自动化")
                logger.info("Agent 自动化工具注册完成")

            # 注册智能分析工具（第二阶段）
            if categories.get("intelligent_analysis", {}).get("enabled", True):
                analysis_config = categories.get("intelligent_analysis", {}).get(
                    "settings", {}
                )
                # 合并 ChromaDB 配置
                if self.data_manager:
                    analysis_config["chromadb_path"] = (
                        self.data_manager.persist_directory
                    )
                analysis_tools = IntelligentAnalysisTools(analysis_config)
                for tool in analysis_tools.create_tools():
                    self.registry.register_tool(tool, "智能分析")
                logger.info("智能分析工具注册完成")

            # 注册 Agent 行为工具（第二阶段）
            if categories.get("agent_behavior", {}).get("enabled", True):
                behavior_config = categories.get("agent_behavior", {}).get(
                    "settings", {}
                )
                # 合并 ChromaDB 配置
                if self.data_manager:
                    behavior_config["chromadb_path"] = (
                        self.data_manager.persist_directory
                    )
                behavior_tools = AgentBehaviorTools(behavior_config)
                for tool in behavior_tools.create_tools():
                    self.registry.register_tool(tool, "Agent行为")
                logger.info("Agent 行为工具注册完成")

            # 注册上下文引擎工具（第二阶段）
            if categories.get("context_engine", {}).get("enabled", True):
                context_config = categories.get("context_engine", {}).get(
                    "settings", {}
                )
                # 合并 ChromaDB 配置
                if self.data_manager:
                    context_config["chromadb_path"] = (
                        self.data_manager.persist_directory
                    )
                context_engine_tools = ContextEngineTools(context_config)
                for tool in context_engine_tools.create_tools():
                    self.registry.register_tool(tool, "上下文引擎深度")
                logger.info("上下文引擎工具注册完成")

            # 注册语义智能工具（第一阶段增强）
            if categories.get("semantic_intelligence", {}).get("enabled", True):
                semantic_config = categories.get("semantic_intelligence", {}).get(
                    "settings", {}
                )
                # 合并 ChromaDB 配置
                if self.data_manager:
                    semantic_config["chromadb_path"] = (
                        self.data_manager.persist_directory
                    )
                semantic_tools = SemanticIntelligenceTools(semantic_config)
                for tool in semantic_tools.create_tools():
                    self.registry.register_tool(tool, "语义智能")
                logger.info("语义智能工具注册完成")

            # 注册任务管理工具（第三阶段）
            if categories.get("task_management", {}).get("enabled", True):
                if self.data_manager:
                    # 创建所有任务管理相关工具
                    task_tools = create_task_tools(self.data_manager)
                    for tool in task_tools:
                        self.registry.register_tool(tool, "任务管理")
                    logger.info("任务管理工具注册完成")
                else:
                    logger.warning("数据管理器未初始化，跳过任务管理工具注册")

            # 注册可视化工具（第三阶段）
            if categories.get("visualization", {}).get("enabled", True):
                # 注册所有可视化工具（包括新的专门工具）
                visualization_tools = create_visualization_tools()
                for tool in visualization_tools:
                    self.registry.register_tool(tool, "可视化")

                logger.info("可视化工具注册完成")

            # 注册记忆管理工具（第三阶段）
            if categories.get("memory_management", {}).get("enabled", True):
                memory_config = categories.get("memory_management", {}).get(
                    "settings", {}
                )
                memory_tools = MemoryManagementTools(memory_config)

                # 设置数据管理器
                if self.data_manager:
                    memory_tools.set_data_manager(self.data_manager)

                for tool in memory_tools.create_tools():
                    self.registry.register_tool(tool, "记忆管理")
                logger.info("记忆管理工具注册完成")

            # 注册工具协作框架（第三阶段）
            if categories.get("collaboration", {}).get("enabled", True):
                collaboration_config = categories.get("collaboration", {}).get(
                    "settings", {}
                )
                collaboration_framework = ToolCollaborationFramework(
                    collaboration_config
                )

                # 注册所有已创建的工具实例到协作框架
                # 获取所有已注册的工具并注册到协作框架
                for tool_name, tool_instance in self.registry._tools.items():
                    collaboration_framework.register_tool(tool_name, tool_instance)

                for tool in collaboration_framework.create_tools():
                    self.registry.register_tool(tool, "工具协作")
                logger.info("工具协作框架注册完成")

        except Exception as e:
            logger.error(f"注册增强工具失败: {e}")
            # 不抛出异常，允许基础工具继续工作


def create_basic_tools_service(
    config: Optional[ConfigDict] = None,
) -> BasicToolsService:
    """创建基础工具服务实例"""
    return BasicToolsService(config)
