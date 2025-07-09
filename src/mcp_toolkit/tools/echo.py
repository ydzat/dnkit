"""
Echo工具模块

提供简单的回显功能，用于测试和演示MCP工具注册。
"""

import time
from typing import Any, Dict, List, Optional

from ..core.logging import get_logger
from ..core.types import ConfigDict, ToolDefinition
from .base import BaseTool, ToolExecutionRequest, ToolExecutionResult

logger = get_logger(__name__)


class EchoTool(BaseTool):
    """回显工具 - 简单地返回输入的内容"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def get_name(self) -> str:
        return "echo"

    def get_description(self) -> str:
        return "回显输入的文本内容，用于测试MCP工具功能"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "要回显的消息内容"}
            },
            "required": ["message"],
        }

    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        return ToolDefinition(
            name=self.get_name(),
            description=self.get_description(),
            parameters=self.get_parameters(),
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行回显操作"""
        try:
            message = request.parameters.get("message", "")

            if not message:
                return self._create_error_result(
                    "MISSING_MESSAGE", "缺少必需的message参数"
                )

            # 简单回显消息
            result = f"Echo: {message}"

            self._logger.info(f"回显消息: {message}")

            return self._create_success_result(result)

        except Exception as e:
            self._logger.exception("回显工具执行异常")
            return self._create_error_result("ECHO_ERROR", f"回显操作失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class EchoTools:
    """回显工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有回显工具"""
        return [EchoTool(self.config)]
