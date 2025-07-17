"""
MCP工具集基础工具模块

提供文件操作、终端执行、网络请求、搜索等基础工具功能。
所有工具都遵循MCP协议规范，支持标准化的参数验证、错误处理和性能监控。

第一阶段增强功能：
- 基于 ChromaDB 的统一数据存储
- 增强的文件系统工具（支持语义搜索）
- 增强的网络工具（支持网页内容存储）
- 增强的系统工具（支持系统信息管理）
"""

# Agent 自动化工具
from .agent_automation import AgentAutomationTools

# Agent 行为工具
from .agent_behavior import AgentBehaviorTools
from .base import BaseTool, ToolRegistry

# 上下文引擎工具
from .context_engine import ContextEngineTools

# 第二阶段上下文引擎工具
from .context_tools import ContextTools
from .echo import EchoTools

# 第一阶段增强工具
from .enhanced_file_operations import EnhancedFileOperationsTools
from .enhanced_network import EnhancedNetworkTools
from .enhanced_system import EnhancedSystemTools
from .file_operations import FileOperationsTools

# Git 集成工具
from .git_integration import GitIntegrationTools

# 智能分析工具
from .intelligent_analysis import IntelligentAnalysisTools
from .network import NetworkTools
from .search import SearchTools
from .terminal import TerminalTools

# 版本管理工具
from .version_management import VersionManagementTools

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "EchoTools",
    "FileOperationsTools",
    "TerminalTools",
    "NetworkTools",
    "SearchTools",
    # 第一阶段增强工具
    "EnhancedFileOperationsTools",
    "EnhancedNetworkTools",
    "EnhancedSystemTools",
    # 第二阶段上下文引擎工具
    "ContextTools",
    # Git 集成工具
    "GitIntegrationTools",
    # 版本管理工具
    "VersionManagementTools",
    # Agent 自动化工具
    "AgentAutomationTools",
    # 智能分析工具
    "IntelligentAnalysisTools",
    # Agent 行为工具
    "AgentBehaviorTools",
    # 上下文引擎工具
    "ContextEngineTools",
]
