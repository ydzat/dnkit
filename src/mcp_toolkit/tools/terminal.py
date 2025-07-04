"""
终端操作工具集

提供命令执行、环境变量管理、工作目录操作等终端相关功能。
包含安全限制和执行控制机制。
"""

import asyncio
import os
import shlex
import subprocess  # nosec B404
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceEstimate,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
    ValidationError,
    ValidationResult,
)


class BaseTerminalTool(BaseTool):
    """终端操作工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.allowed_commands = self.config.get("allowed_commands", [])
        self.forbidden_commands = self.config.get(
            "forbidden_commands",
            [
                "rm",
                "rmdir",
                "del",
                "format",
                "fdisk",
                "shutdown",
                "reboot",
                "sudo",
                "su",
                "passwd",
                "useradd",
                "userdel",
                "chmod",
                "chown",
            ],
        )
        self.max_execution_time = self.config.get(
            "max_execution_time_seconds", 300
        )  # 5分钟
        self.sandbox_enabled = self.config.get("sandbox_enabled", True)
        self.log_commands = self.config.get("log_all_commands", True)

    def _validate_command(self, command: str) -> ValidationResult:
        """验证命令安全性"""
        errors = []

        try:
            # 解析命令
            parts = shlex.split(command) if command else []
            if not parts:
                errors.append(
                    ValidationError(
                        field="command", message="命令不能为空", code="EMPTY_COMMAND"
                    )
                )
                return ValidationResult(is_valid=False, errors=errors)

            base_command = parts[0].split("/")[-1]  # 获取命令基本名称

            # 检查禁止命令
            if self.forbidden_commands:
                for forbidden in self.forbidden_commands:
                    if base_command == forbidden or command.startswith(forbidden + " "):
                        errors.append(
                            ValidationError(
                                field="command",
                                message=f"命令 {forbidden} 被禁止执行",
                                code="FORBIDDEN_COMMAND",
                            )
                        )

            # 检查允许命令（如果配置了白名单）
            if self.allowed_commands:
                allowed = False
                for allowed_cmd in self.allowed_commands:
                    if base_command == allowed_cmd or command.startswith(
                        allowed_cmd + " "
                    ):
                        allowed = True
                        break
                if not allowed:
                    errors.append(
                        ValidationError(
                            field="command",
                            message=f"命令 {base_command} 不在允许列表中",
                            code="COMMAND_NOT_ALLOWED",
                        )
                    )

            # 检查危险字符和模式
            dangerous_patterns = [
                "&&",
                "||",
                ";",
                "|",
                ">",
                ">>",
                "<",
                "$(",
                "`",
                "eval",
                "exec",
            ]

            for pattern in dangerous_patterns:
                if pattern in command:
                    errors.append(
                        ValidationError(
                            field="command",
                            message=f"命令包含危险模式: {pattern}",
                            code="DANGEROUS_PATTERN",
                        )
                    )

        except Exception as e:
            errors.append(
                ValidationError(
                    field="command",
                    message=f"命令解析失败: {str(e)}",
                    code="COMMAND_PARSE_ERROR",
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


class RunCommandTool(BaseTerminalTool):
    """执行命令工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="run_command",
            description="在终端中执行命令并返回结果",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令",
                        "maxLength": 4096,
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "命令参数",
                    },
                    "working_directory": {"type": "string", "description": "工作目录"},
                    "environment": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "环境变量",
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3600,
                        "default": 30,
                        "description": "超时时间（秒）",
                    },
                    "capture_output": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否捕获输出",
                    },
                    "shell": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否使用shell执行",
                    },
                    "input": {"type": "string", "description": "标准输入内容"},
                },
                "required": ["command"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        errors: List[ValidationError] = []
        sanitized = {}

        # 验证命令
        command = params.get("command", "")
        command_validation = self._validate_command(command)
        if not command_validation.is_valid:
            errors.extend(command_validation.errors or [])
        sanitized["command"] = command

        # 验证参数列表
        args = params.get("args", [])
        if not isinstance(args, list):
            errors.append(
                ValidationError(
                    field="args",
                    message="args 必须是字符串数组",
                    code="INVALID_ARGS_TYPE",
                )
            )
        else:
            for i, arg in enumerate(args):
                if not isinstance(arg, str):
                    errors.append(
                        ValidationError(
                            field=f"args[{i}]",
                            message=f"参数 {i} 必须是字符串",
                            code="INVALID_ARG_TYPE",
                        )
                    )
        sanitized["args"] = args

        # 验证工作目录
        working_directory = params.get("working_directory")
        if working_directory is not None:
            if not isinstance(working_directory, str):
                errors.append(
                    ValidationError(
                        field="working_directory",
                        message="working_directory 必须是字符串",
                        code="INVALID_WORKDIR_TYPE",
                    )
                )
            elif not os.path.exists(working_directory):
                errors.append(
                    ValidationError(
                        field="working_directory",
                        message=f"工作目录不存在: {working_directory}",
                        code="WORKDIR_NOT_FOUND",
                    )
                )
            elif not os.path.isdir(working_directory):
                errors.append(
                    ValidationError(
                        field="working_directory",
                        message=f"工作目录路径不是目录: {working_directory}",
                        code="WORKDIR_NOT_DIRECTORY",
                    )
                )
        sanitized["working_directory"] = working_directory

        # 验证环境变量
        environment = params.get("environment", {})
        if not isinstance(environment, dict):
            errors.append(
                ValidationError(
                    field="environment",
                    message="environment 必须是对象",
                    code="INVALID_ENV_TYPE",
                )
            )
        else:
            for key, value in environment.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    errors.append(
                        ValidationError(
                            field="environment",
                            message="环境变量的键和值都必须是字符串",
                            code="INVALID_ENV_VALUE_TYPE",
                        )
                    )
        sanitized["environment"] = environment

        # 验证超时时间
        timeout = params.get("timeout", 30)
        if (
            not isinstance(timeout, int)
            or timeout < 1
            or timeout > self.max_execution_time
        ):
            errors.append(
                ValidationError(
                    field="timeout",
                    message=f"timeout 必须在 1 到 {self.max_execution_time} 之间",
                    code="INVALID_TIMEOUT",
                )
            )
        sanitized["timeout"] = timeout

        # 验证其他布尔参数
        for field in ["capture_output", "shell"]:
            value = params.get(field)
            if value is not None and not isinstance(value, bool):
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"{field} 必须是布尔值",
                        code=f"INVALID_{field.upper()}_TYPE",
                    )
                )
            sanitized[field] = value

        # 验证输入
        input_data = params.get("input")
        if input_data is not None and not isinstance(input_data, str):
            errors.append(
                ValidationError(
                    field="input",
                    message="input 必须是字符串",
                    code="INVALID_INPUT_TYPE",
                )
            )
        sanitized["input"] = input_data

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized if len(errors) == 0 else None,
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行命令"""
        params = request.parameters
        command = params["command"]
        args = params.get("args", [])
        working_directory = params.get("working_directory")
        environment = params.get("environment", {})
        timeout = params.get("timeout", 30)
        capture_output = params.get("capture_output", True)
        shell = params.get("shell", False)
        input_data = params.get("input")

        if self.log_commands:
            self._logger.info(f"执行命令: {command} {' '.join(args)}")

        try:
            # 准备执行环境
            env = os.environ.copy()
            env.update(environment)

            # 构建完整命令
            if args:
                full_command = [command] + args
            else:
                full_command = command if shell else [command]

            # 执行命令
            start_time = time.time()

            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdin=subprocess.PIPE if input_data else None,
                    stdout=subprocess.PIPE if capture_output else None,
                    stderr=subprocess.PIPE if capture_output else None,
                    cwd=working_directory,
                    env=env,
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *full_command,
                    stdin=subprocess.PIPE if input_data else None,
                    stdout=subprocess.PIPE if capture_output else None,
                    stderr=subprocess.PIPE if capture_output else None,
                    cwd=working_directory,
                    env=env,
                )

            # 等待执行完成
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input_data.encode() if input_data else None),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return self._create_error_result(
                    "EXECUTION_TIMEOUT", f"命令执行超时 (>{timeout}秒)"
                )

            execution_time = (time.time() - start_time) * 1000  # 转换为毫秒

            # 处理输出
            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            result_content = {
                "exit_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "execution_time": execution_time / 1000,  # 转换回秒
                "pid": process.pid,
                "signal": None,  # 在Windows上可能不可用
            }

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=len(stdout_text + stderr_text) / 1024 / 1024,
                cpu_time=execution_time,  # 简化估算
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(stdout_text + stderr_text) / 1024 / 1024,
                cpu_time_ms=execution_time,
                io_operations=1,
            )

            return self._create_success_result(result_content, metadata, resources)

        except FileNotFoundError:
            return self._create_error_result(
                "COMMAND_NOT_FOUND", f"命令不存在: {command}"
            )
        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限执行命令: {command}"
            )
        except Exception as e:
            self._logger.exception("执行命令时发生异常")
            return self._create_error_result(
                "EXECUTION_ERROR", f"命令执行失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class GetEnvironmentTool(BaseTerminalTool):
    """获取环境变量工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_environment",
            description="获取当前环境变量信息",
            input_schema={
                "type": "object",
                "properties": {
                    "variable": {
                        "type": "string",
                        "description": "特定环境变量名（可选）",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "环境变量名匹配模式（可选）",
                    },
                    "include_system": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否包含系统环境变量",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """获取环境变量"""
        params = request.parameters
        variable = params.get("variable")
        pattern = params.get("pattern")
        include_system = params.get("include_system", True)

        try:
            env_vars = {}

            if variable:
                # 获取特定环境变量
                value = os.environ.get(variable)
                if value is not None:
                    env_vars[variable] = value
            else:
                # 获取所有环境变量
                if include_system:
                    env_vars = dict(os.environ)
                else:
                    # 过滤系统变量（简化实现）
                    system_vars = {"PATH", "HOME", "USER", "USERNAME", "SHELL", "TERM"}
                    env_vars = {
                        k: v for k, v in os.environ.items() if k not in system_vars
                    }

                # 应用模式过滤
                if pattern:
                    import re

                    pattern_regex = re.compile(pattern)
                    env_vars = {
                        k: v for k, v in env_vars.items() if pattern_regex.search(k)
                    }

            result_content = {"variables": env_vars, "count": len(env_vars)}

            metadata = ExecutionMetadata(
                execution_time=0,
                memory_used=len(str(env_vars)) / 1024 / 1024,
                cpu_time=0,
                io_operations=0,
            )

            return self._create_success_result(result_content, metadata)

        except Exception as e:
            self._logger.exception("获取环境变量时发生异常")
            return self._create_error_result("ENV_ERROR", f"获取环境变量失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class SetWorkingDirectoryTool(BaseTerminalTool):
    """设置工作目录工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="set_working_directory",
            description="设置当前工作目录",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径"},
                    "create_if_missing": {
                        "type": "boolean",
                        "default": False,
                        "description": "目录不存在时是否创建",
                    },
                },
                "required": ["path"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """设置工作目录"""
        params = request.parameters
        directory = params["path"]
        create_if_missing = params.get("create_if_missing", False)

        try:
            # 规范化路径
            directory = os.path.abspath(os.path.expanduser(directory))

            # 检查目录是否存在
            if not os.path.exists(directory):
                if create_if_missing:
                    os.makedirs(directory, exist_ok=True)
                else:
                    return self._create_error_result(
                        "DIRECTORY_NOT_FOUND", f"目录不存在: {directory}"
                    )

            # 检查是否为目录
            if not os.path.isdir(directory):
                return self._create_error_result(
                    "NOT_A_DIRECTORY", f"路径不是目录: {directory}"
                )

            # 获取原工作目录
            old_directory = os.getcwd()

            # 设置新工作目录
            os.chdir(directory)

            result_content = {
                "old_directory": old_directory,
                "new_directory": directory,
                "created": create_if_missing and not os.path.exists(directory),
            }

            metadata = ExecutionMetadata(
                execution_time=0, memory_used=0.01, cpu_time=0, io_operations=1
            )

            return self._create_success_result(result_content, metadata)

        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限访问目录: {directory}"
            )
        except Exception as e:
            self._logger.exception("设置工作目录时发生异常")
            return self._create_error_result(
                "WORKDIR_ERROR", f"设置工作目录失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class TerminalTools:
    """终端操作工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有终端工具"""
        tools_config = self.config.get("terminal", {})

        return [
            RunCommandTool(tools_config),
            GetEnvironmentTool(tools_config),
            SetWorkingDirectoryTool(tools_config),
        ]
