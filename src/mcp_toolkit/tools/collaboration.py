"""
工具协作框架

实现工具间的链式调用、并行执行和数据流优化，支持复杂的工具组合操作。
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
)


class ToolChain:
    """工具链，支持顺序执行和数据传递"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []
        self.variables: Dict[str, Any] = {}

    def add_step(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        output_mapping: Optional[Dict[str, str]] = None,
        condition: Optional[str] = None,
    ) -> "ToolChain":
        """添加执行步骤"""
        step = {
            "tool_name": tool_name,
            "parameters": parameters,
            "output_mapping": output_mapping or {},
            "condition": condition,
            "step_id": str(uuid.uuid4()),
        }
        self.steps.append(step)
        return self

    def set_variable(self, name: str, value: Any) -> "ToolChain":
        """设置变量"""
        self.variables[name] = value
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolChain":
        """从字典创建工具链"""
        chain = cls(data["name"], data.get("description", ""))
        chain.steps = data.get("steps", [])
        chain.variables = data.get("variables", {})
        return chain


class ToolCollaborationFramework(BaseTool):
    """工具协作框架"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.tool_registry: Dict[str, BaseTool] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.max_parallel_tasks = config.get("max_parallel_tasks", 5) if config else 5
        self.enable_caching = config.get("enable_caching", True) if config else True
        self.cache: Dict[str, Any] = {}

    def register_tool(self, tool_name: str, tool_instance: BaseTool) -> None:
        """注册工具实例"""
        self.tool_registry[tool_name] = tool_instance

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="execute_tool_chain",
            description="执行工具链 - 支持顺序执行、并行执行和复杂的工具组合操作",
            parameters={
                "type": "object",
                "properties": {
                    "execution_mode": {
                        "type": "string",
                        "enum": ["sequential", "parallel", "conditional", "chain"],
                        "default": "sequential",
                        "description": "执行模式",
                    },
                    "tools": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool_name": {"type": "string"},
                                "parameters": {"type": "object"},
                                "output_mapping": {"type": "object"},
                                "condition": {"type": "string"},
                                "depends_on": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["tool_name", "parameters"],
                        },
                        "description": "要执行的工具列表",
                    },
                    "chain_definition": {
                        "type": "string",
                        "description": "工具链定义（JSON格式）",
                    },
                    "global_variables": {
                        "type": "object",
                        "description": "全局变量",
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 300,
                        "description": "执行超时时间（秒）",
                    },
                    "enable_rollback": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否启用回滚机制",
                    },
                },
                "required": ["execution_mode"],
            },
        )

    def create_tools(self) -> List["BaseTool"]:
        """创建工具实例列表"""
        return [self]

    async def cleanup(self) -> None:
        """清理资源"""
        # 清理缓存和历史记录
        self.cache.clear()
        self.execution_history.clear()

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行工具协作操作"""
        start_time = time.time()
        params = request.parameters

        try:
            execution_mode = params.get("execution_mode", "sequential")
            timeout = params.get("timeout", 300)
            enable_rollback = params.get("enable_rollback", False)
            global_variables = params.get("global_variables", {})

            if execution_mode == "chain" and "chain_definition" in params:
                # 执行预定义的工具链
                chain_data = json.loads(params["chain_definition"])
                chain = ToolChain.from_dict(chain_data)
                result = await self._execute_tool_chain(
                    chain, global_variables, timeout
                )
            else:
                # 执行工具列表
                tools = params.get("tools", [])
                if not tools:
                    raise ValueError("工具列表不能为空")

                if execution_mode == "sequential":
                    result = await self._execute_sequential(
                        tools, global_variables, timeout
                    )
                elif execution_mode == "parallel":
                    result = await self._execute_parallel(
                        tools, global_variables, timeout
                    )
                elif execution_mode == "conditional":
                    result = await self._execute_conditional(
                        tools, global_variables, timeout
                    )
                else:
                    raise ValueError(f"不支持的执行模式: {execution_mode}")

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=len(str(result)) / 1024,  # KB
                cpu_time=execution_time * 0.1,
                io_operations=len(tools) if "tools" in params else 1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(result)) / 1024 / 1024,  # MB
                cpu_time_ms=execution_time * 0.1,
                io_operations=len(tools) if "tools" in params else 1,
            )

            return self._create_success_result(result, metadata, resources)

        except Exception as e:
            self._logger.exception("工具协作执行时发生异常")
            return self._create_error_result(
                "COLLABORATION_ERROR", f"工具协作执行失败: {str(e)}"
            )

    async def _execute_sequential(
        self,
        tools: List[Dict[str, Any]],
        global_variables: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """顺序执行工具"""
        results = []
        variables = global_variables.copy()

        for i, tool_config in enumerate(tools):
            tool_name = tool_config["tool_name"]
            parameters = tool_config["parameters"]
            output_mapping = tool_config.get("output_mapping", {})

            # 替换参数中的变量引用
            resolved_params = self._resolve_variables(parameters, variables)

            # 执行工具
            tool_result = await self._execute_single_tool(tool_name, resolved_params)

            # 更新变量
            if output_mapping and tool_result.success:
                for var_name, result_path in output_mapping.items():
                    value = self._extract_value_from_result(
                        tool_result.content, result_path
                    )
                    variables[var_name] = value

            results.append(
                {
                    "step": i + 1,
                    "tool_name": tool_name,
                    "success": tool_result.success,
                    "result": tool_result.content if tool_result.success else None,
                    "error": (
                        tool_result.error.message
                        if not tool_result.success and tool_result.error
                        else None
                    ),
                }
            )

            # 如果某个步骤失败，停止执行
            if not tool_result.success:
                break

        return {
            "execution_mode": "sequential",
            "total_steps": len(tools),
            "completed_steps": len(results),
            "results": results,
            "final_variables": variables,
            "success": all(r["success"] for r in results),
        }

    async def _execute_parallel(
        self,
        tools: List[Dict[str, Any]],
        global_variables: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """并行执行工具"""
        variables = global_variables.copy()

        # 创建并行任务
        tasks = []
        for i, tool_config in enumerate(tools):
            tool_name = tool_config["tool_name"]
            parameters = tool_config["parameters"]

            # 替换参数中的变量引用
            resolved_params = self._resolve_variables(parameters, variables)

            # 创建异步任务
            task = asyncio.create_task(
                self._execute_single_tool(tool_name, resolved_params),
                name=f"tool_{i}_{tool_name}",
            )
            tasks.append((i, tool_name, task))

        # 等待所有任务完成
        results = []
        try:
            completed_tasks = await asyncio.wait_for(
                asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True),
                timeout=timeout,
            )

            for (i, tool_name, _), result in zip(tasks, completed_tasks):
                if isinstance(result, Exception):
                    results.append(
                        {
                            "step": i + 1,
                            "tool_name": tool_name,
                            "success": False,
                            "result": None,
                            "error": str(result),
                        }
                    )
                elif isinstance(result, ToolExecutionResult):
                    # result 是 ToolExecutionResult 类型
                    results.append(
                        {
                            "step": i + 1,
                            "tool_name": tool_name,
                            "success": result.success,
                            "result": result.content if result.success else None,
                            "error": (
                                result.error.message
                                if not result.success and result.error
                                else None
                            ),
                        }
                    )
                else:
                    # 未知类型，作为错误处理
                    results.append(
                        {
                            "step": i + 1,
                            "tool_name": tool_name,
                            "success": False,
                            "result": None,
                            "error": f"未知结果类型: {type(result)}",
                        }
                    )

        except asyncio.TimeoutError:
            # 取消未完成的任务
            for _, _, task in tasks:
                if not task.done():
                    task.cancel()

            raise TimeoutError(f"并行执行超时（{timeout}秒）")

        return {
            "execution_mode": "parallel",
            "total_tools": len(tools),
            "results": results,
            "success": all(r["success"] for r in results),
            "execution_time": time.time(),
        }

    async def _execute_conditional(
        self,
        tools: List[Dict[str, Any]],
        global_variables: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """条件执行工具"""
        results = []
        variables = global_variables.copy()

        for i, tool_config in enumerate(tools):
            tool_name = tool_config["tool_name"]
            parameters = tool_config["parameters"]
            condition = tool_config.get("condition")
            output_mapping = tool_config.get("output_mapping", {})

            # 检查执行条件
            should_execute = True
            if condition:
                should_execute = self._evaluate_condition(condition, variables)

            if should_execute:
                # 替换参数中的变量引用
                resolved_params = self._resolve_variables(parameters, variables)

                # 执行工具
                tool_result = await self._execute_single_tool(
                    tool_name, resolved_params
                )

                # 更新变量
                if output_mapping and tool_result.success:
                    for var_name, result_path in output_mapping.items():
                        value = self._extract_value_from_result(
                            tool_result.content, result_path
                        )
                        variables[var_name] = value

                results.append(
                    {
                        "step": i + 1,
                        "tool_name": tool_name,
                        "executed": True,
                        "success": tool_result.success,
                        "result": tool_result.content if tool_result.success else None,
                        "error": (
                            tool_result.error.message
                            if not tool_result.success and tool_result.error
                            else None
                        ),
                    }
                )
            else:
                results.append(
                    {
                        "step": i + 1,
                        "tool_name": tool_name,
                        "executed": False,
                        "success": True,  # 跳过的步骤视为成功
                        "result": None,
                        "error": None,
                        "skip_reason": f"条件不满足: {condition}",
                    }
                )

        return {
            "execution_mode": "conditional",
            "total_steps": len(tools),
            "executed_steps": len([r for r in results if r["executed"]]),
            "results": results,
            "final_variables": variables,
            "success": all(r["success"] for r in results),
        }

    async def _execute_tool_chain(
        self, chain: ToolChain, global_variables: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """执行工具链"""
        results = []
        variables = {**chain.variables, **global_variables}

        for i, step in enumerate(chain.steps):
            tool_name = step["tool_name"]
            parameters = step["parameters"]
            condition = step.get("condition")
            output_mapping = step.get("output_mapping", {})

            # 检查执行条件
            should_execute = True
            if condition:
                should_execute = self._evaluate_condition(condition, variables)

            if should_execute:
                # 替换参数中的变量引用
                resolved_params = self._resolve_variables(parameters, variables)

                # 执行工具
                tool_result = await self._execute_single_tool(
                    tool_name, resolved_params
                )

                # 更新变量
                if output_mapping and tool_result.success:
                    for var_name, result_path in output_mapping.items():
                        value = self._extract_value_from_result(
                            tool_result.content, result_path
                        )
                        variables[var_name] = value

                results.append(
                    {
                        "step_id": step["step_id"],
                        "step": i + 1,
                        "tool_name": tool_name,
                        "executed": True,
                        "success": tool_result.success,
                        "result": tool_result.content if tool_result.success else None,
                        "error": (
                            tool_result.error.message
                            if not tool_result.success and tool_result.error
                            else None
                        ),
                    }
                )

                # 如果某个步骤失败，停止执行
                if not tool_result.success:
                    break
            else:
                results.append(
                    {
                        "step_id": step["step_id"],
                        "step": i + 1,
                        "tool_name": tool_name,
                        "executed": False,
                        "success": True,
                        "result": None,
                        "error": None,
                        "skip_reason": f"条件不满足: {condition}",
                    }
                )

        return {
            "execution_mode": "chain",
            "chain_name": chain.name,
            "chain_description": chain.description,
            "total_steps": len(chain.steps),
            "executed_steps": len([r for r in results if r["executed"]]),
            "results": results,
            "final_variables": variables,
            "success": all(r["success"] for r in results),
        }

    async def _execute_single_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> ToolExecutionResult:
        """执行单个工具"""
        if tool_name not in self.tool_registry:
            # 创建错误结果
            from .base import ToolError

            error = ToolError("TOOL_NOT_FOUND", f"工具 {tool_name} 未注册")
            return ToolExecutionResult(
                success=False,
                content={},
                error=error,
                metadata=ExecutionMetadata(
                    execution_time=0, memory_used=0, cpu_time=0, io_operations=0
                ),
                resources_used=ResourceUsage(
                    memory_mb=0, cpu_time_ms=0, io_operations=0
                ),
            )

        tool_instance = self.tool_registry[tool_name]

        # 创建执行请求
        from .base import ExecutionContext

        request = ToolExecutionRequest(
            tool_name=tool_name,
            parameters=parameters,
            execution_context=ExecutionContext(
                request_id=str(uuid.uuid4()),
                working_directory=".",
            ),
        )

        # 执行工具
        return await tool_instance.execute(request)

    def _resolve_variables(
        self, parameters: Dict[str, Any], variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析参数中的变量引用"""
        resolved = {}

        for key, value in parameters.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                # 变量引用格式: ${variable_name}
                var_name = value[2:-1]
                resolved[key] = variables.get(var_name, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_variables(value, variables)
            elif isinstance(value, list):
                resolved[key] = [
                    (
                        self._resolve_variables(item, variables)
                        if isinstance(item, dict)
                        else (
                            variables.get(item[2:-1], item)
                            if isinstance(item, str)
                            and item.startswith("${")
                            and item.endswith("}")
                            else item
                        )
                    )
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _extract_value_from_result(self, result: Any, path: str) -> Any:
        """从结果中提取值"""
        keys = path.split(".")
        current = result

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 简单的条件评估，支持基本的比较操作
            # 格式: variable_name operator value
            # 例如: "status == 'success'" 或 "count > 0"

            # 替换变量引用
            for var_name, var_value in variables.items():
                condition = condition.replace(f"${{{var_name}}}", str(var_value))
                condition = condition.replace(var_name, str(var_value))

            # 安全的条件评估（仅支持基本操作）
            allowed_operators = [
                ">=",
                "<=",
                "==",
                "!=",
                ">",
                "<",
                "not in",
                "in",
            ]  # 长操作符在前

            for op in allowed_operators:
                if op in condition:
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        left_str = parts[0].strip().strip("'\"")
                        right_str = parts[1].strip().strip("'\"")

                        # 尝试转换为数字
                        try:
                            left: Union[str, float] = float(left_str)
                            right: Union[str, float] = float(right_str)
                        except ValueError:
                            left = left_str
                            right = right_str

                        if op == "==":
                            return left == right
                        elif op == "!=":
                            return left != right
                        elif op == ">":
                            try:
                                return left > right  # type: ignore
                            except TypeError:
                                return False
                        elif op == "<":
                            try:
                                return left < right  # type: ignore
                            except TypeError:
                                return False
                        elif op == ">=":
                            try:
                                return left >= right  # type: ignore
                            except TypeError:
                                return False
                        elif op == "<=":
                            try:
                                return left <= right  # type: ignore
                            except TypeError:
                                return False
                        elif op == "in":
                            return str(left) in str(right)
                        elif op == "not in":
                            return str(left) not in str(right)

            # 如果没有操作符，检查布尔值
            return bool(condition.lower() in ["true", "1", "yes", "on"])

        except Exception:
            # 条件评估失败，默认返回 False
            return False
