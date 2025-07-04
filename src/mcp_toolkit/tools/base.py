"""
基础工具抽象类和工具注册中心

定义了所有工具的基础接口和统一的执行框架。
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from ..core.interfaces import ToolDefinition
from ..core.logging import get_logger
from ..core.types import ConfigDict

logger = get_logger(__name__)


class ToolStatus(Enum):
    """工具状态枚举"""

    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class Priority(Enum):
    """执行优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ResourceEstimate:
    """资源使用估算"""

    memory_mb: float
    cpu_time_ms: float
    io_operations: int
    network_requests: int = 0


@dataclass
class ResourceUsage:
    """实际资源使用"""

    memory_mb: float
    cpu_time_ms: float
    io_operations: int
    network_requests: int = 0


@dataclass
class UserInfo:
    """用户信息"""

    user_id: str
    permissions: List[str]
    session_id: Optional[str] = None


@dataclass
class ExecutionContext:
    """执行上下文"""

    request_id: str
    session_id: Optional[str] = None
    user_info: Optional[UserInfo] = None
    working_directory: str = "."
    environment_variables: Optional[Dict[str, str]] = None
    permissions: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.environment_variables is None:
            self.environment_variables = {}
        if self.permissions is None:
            self.permissions = []


@dataclass
class ExecutionMetadata:
    """执行元数据"""

    execution_time: float  # milliseconds
    memory_used: float  # MB
    cpu_time: float  # milliseconds
    io_operations: int
    cache_hit: bool = False


@dataclass
class ToolExecutionRequest:
    """工具执行请求"""

    tool_name: str
    parameters: Dict[str, Any]
    execution_context: ExecutionContext
    timeout: Optional[float] = None
    priority: Priority = Priority.NORMAL


@dataclass
class ToolError:
    """工具执行错误"""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ToolExecutionResult:
    """工具执行结果"""

    success: bool
    content: Optional[Any] = None
    error: Optional[ToolError] = None
    metadata: Optional[ExecutionMetadata] = None
    resources_used: Optional[ResourceUsage] = None


@dataclass
class ValidationError:
    """参数验证错误"""

    field: str
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: Optional[List[ValidationError]] = None
    warnings: Optional[List[str]] = None
    sanitized_params: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseTool(ABC):
    """基础工具抽象类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self._status = ToolStatus.AVAILABLE
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        pass

    @abstractmethod
    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行工具"""
        pass

    def get_name(self) -> str:
        """获取工具名称"""
        return self.get_definition().name

    def get_version(self) -> str:
        """获取工具版本"""
        return getattr(self.get_definition(), "version", "1.0.0")

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        # 基础验证实现，子类可以重写
        return ValidationResult(is_valid=True, sanitized_params=params)

    def get_status(self) -> ToolStatus:
        """获取工具状态"""
        return self._status

    def is_available(self) -> bool:
        """检查工具是否可用"""
        return self._status == ToolStatus.AVAILABLE

    def estimate_resources(self, params: Dict[str, Any]) -> ResourceEstimate:
        """估算资源使用"""
        # 默认估算，子类可以重写
        return ResourceEstimate(memory_mb=10.0, cpu_time_ms=100.0, io_operations=1)

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def _create_error_result(
        self, code: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """创建错误结果"""
        return ToolExecutionResult(
            success=False, error=ToolError(code=code, message=message, details=details)
        )

    def _create_success_result(
        self,
        content: Any,
        metadata: Optional[ExecutionMetadata] = None,
        resources_used: Optional[ResourceUsage] = None,
    ) -> ToolExecutionResult:
        """创建成功结果"""
        return ToolExecutionResult(
            success=True,
            content=content,
            metadata=metadata,
            resources_used=resources_used,
        )


class ToolRegistry:
    """工具注册中心"""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
        self._logger = get_logger(__name__)

    def register_tool(self, tool: BaseTool, category: Optional[str] = None) -> None:
        """注册工具"""
        tool_name = tool.get_name()

        if tool_name in self._tools:
            self._logger.warning(f"工具 {tool_name} 已存在，将被覆盖")

        self._tools[tool_name] = tool

        if category:
            if category not in self._categories:
                self._categories[category] = []
            if tool_name not in self._categories[category]:
                self._categories[category].append(tool_name)

        self._logger.info(f"工具 {tool_name} 注册成功 (分类: {category or 'None'})")

    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        if tool_name not in self._tools:
            return False

        del self._tools[tool_name]

        # 从分类中移除
        for category_tools in self._categories.values():
            if tool_name in category_tools:
                category_tools.remove(tool_name)

        self._logger.info(f"工具 {tool_name} 注销成功")
        return True

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self._tools.get(tool_name)

    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """列出工具"""
        if category is None:
            return list(self._tools.keys())
        return self._categories.get(category, [])

    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return list(self._categories.keys())

    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        tool = self.get_tool(tool_name)
        return tool.get_definition() if tool else None

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行工具"""
        tool = self.get_tool(request.tool_name)
        if not tool:
            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    code="TOOL_NOT_FOUND", message=f"工具 {request.tool_name} 不存在"
                ),
            )

        if not tool.is_available():
            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    code="TOOL_UNAVAILABLE",
                    message=f"工具 {request.tool_name} 当前不可用",
                ),
            )

        # 验证参数
        validation_result = tool.validate_parameters(request.parameters)
        if not validation_result.is_valid:
            error_details = {
                "validation_errors": [
                    {"field": err.field, "message": err.message, "code": err.code}
                    for err in (validation_result.errors or [])
                ]
            }
            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    code="INVALID_PARAMETERS",
                    message="参数验证失败",
                    details=error_details,
                ),
            )

        # 使用验证后的参数
        if validation_result.sanitized_params:
            request.parameters = validation_result.sanitized_params

        try:
            # 设置超时
            timeout = request.timeout or self._get_default_timeout(tool)

            # 执行工具
            start_time = time.time()
            result = await asyncio.wait_for(tool.execute(request), timeout=timeout)
            execution_time = (time.time() - start_time) * 1000  # 转换为毫秒

            # 添加执行时间到元数据
            if result.metadata:
                result.metadata.execution_time = execution_time
            else:
                result.metadata = ExecutionMetadata(
                    execution_time=execution_time,
                    memory_used=0,
                    cpu_time=0,
                    io_operations=0,
                )

            return result

        except asyncio.TimeoutError:
            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    code="EXECUTION_TIMEOUT", message=f"工具执行超时 (>{timeout}秒)"
                ),
            )
        except Exception as e:
            self._logger.exception(f"工具 {request.tool_name} 执行异常")
            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    code="EXECUTION_ERROR", message=f"工具执行异常: {str(e)}"
                ),
            )

    def _get_default_timeout(self, tool: BaseTool) -> float:
        """获取默认超时时间"""
        return float(tool.config.get("timeout", 30.0))


# 全局工具注册中心实例
_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册中心"""
    return _global_registry


def register_tool(tool: BaseTool, category: Optional[str] = None) -> None:
    """注册工具到全局注册中心"""
    _global_registry.register_tool(tool, category)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """从全局注册中心获取工具"""
    return _global_registry.get_tool(tool_name)
