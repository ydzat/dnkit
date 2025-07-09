"""
文件操作工具集

提供读取、写入、列出文件和创建目录等基础文件操作功能。
所有操作都包含安全检查和权限控制。
"""

import fnmatch
import glob
import os
import shutil
import stat
import time
from datetime import datetime
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


class BaseFileOperationTool(BaseTool):
    """文件操作工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)

        self.allowed_paths = self.config.get(
            "allowed_paths", ["/workspace", "/tmp/mcp-toolkit"]  # nosec B108
        )
        self.forbidden_paths = self.config.get(
            "forbidden_paths", ["/etc", "/bin", "/usr/bin", "/sys", "/proc", "/root"]
        )
        self.max_file_size = self.config.get("max_file_size_bytes", 104857600)  # 100MB
        self.allowed_extensions = self.config.get("allowed_extensions", [])
        self.forbidden_extensions = self.config.get(
            "forbidden_extensions", [".exe", ".dll", ".so"]
        )

    def _is_path_safe(self, normalized_path: str) -> bool:
        """
        智能路径安全验证
        使用安全策略而非硬编码白名单，更适合多用户环境
        """
        import pwd

        # 获取当前用户信息
        try:
            current_user = pwd.getpwuid(os.getuid())
            user_home = current_user.pw_dir
        except (KeyError, AttributeError):
            user_home = os.path.expanduser("~")

        # 获取当前工作目录
        current_dir = os.getcwd()

        # 安全路径策略：
        # 1. 允许用户家目录及其子目录
        if normalized_path.startswith(user_home):
            return True

        # 2. 允许当前工作目录及其子目录
        if normalized_path.startswith(current_dir):
            return True

        # 3. 允许临时目录
        import tempfile

        temp_dirs = [tempfile.gettempdir()]  # 使用系统临时目录
        for temp_dir in temp_dirs:
            if normalized_path.startswith(temp_dir):
                return True

        # 4. 如果配置了allowed_paths，也检查这些路径（向后兼容）
        if self.allowed_paths:
            for allowed_path in self.allowed_paths:
                expanded_allowed = os.path.abspath(os.path.expanduser(allowed_path))
                if normalized_path.startswith(expanded_allowed):
                    return True

        # 5. 其他路径默认不允许
        return False

    def _validate_path(self, path: str) -> ValidationResult:
        """验证路径安全性"""
        errors = []

        try:
            # 规范化路径
            normalized_path = os.path.abspath(os.path.expanduser(path))

            # 检查是否在禁止路径中
            for forbidden in self.forbidden_paths:
                if normalized_path.startswith(os.path.abspath(forbidden)):
                    errors.append(
                        ValidationError(
                            field="path",
                            message=f"路径 {path} 在禁止访问的目录中",
                            code="FORBIDDEN_PATH",
                        )
                    )

            # 智能路径验证：使用安全策略而非硬编码白名单
            if not self._is_path_safe(normalized_path):
                errors.append(
                    ValidationError(
                        field="path",
                        message=f"路径 {path} (规范化为: {normalized_path}) 访问被拒绝：安全策略不允许访问此路径",
                        code="PATH_NOT_ALLOWED",
                    )
                )

            # 检查文件扩展名
            if self.forbidden_extensions:
                ext = os.path.splitext(normalized_path)[1].lower()
                if ext in self.forbidden_extensions:
                    errors.append(
                        ValidationError(
                            field="path",
                            message=f"文件扩展名 {ext} 被禁止",
                            code="FORBIDDEN_EXTENSION",
                        )
                    )

            if self.allowed_extensions:
                ext = os.path.splitext(normalized_path)[1].lower()
                if ext and ext not in self.allowed_extensions:
                    errors.append(
                        ValidationError(
                            field="path",
                            message=f"文件扩展名 {ext} 不被允许",
                            code="EXTENSION_NOT_ALLOWED",
                        )
                    )

        except Exception as e:
            errors.append(
                ValidationError(
                    field="path",
                    message=f"路径验证失败: {str(e)}",
                    code="PATH_VALIDATION_ERROR",
                )
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params={"path": normalized_path} if len(errors) == 0 else None,
        )


class ReadFileTool(BaseFileOperationTool):
    """读取文件工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="读取指定文件的内容，支持文本和二进制文件",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径（绝对或相对路径）",
                    },
                    "encoding": {
                        "type": "string",
                        "enum": ["utf-8", "gbk", "ascii", "binary"],
                        "default": "utf-8",
                        "description": "文件编码格式",
                    },
                    "max_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 104857600,
                        "default": 10485760,
                        "description": "最大读取字节数",
                    },
                    "start_line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "起始行号（可选）",
                    },
                    "end_line": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "结束行号（可选）",
                    },
                },
                "required": ["path"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        # 验证路径
        path_validation = self._validate_path(params.get("path", ""))
        if not path_validation.is_valid:
            return path_validation

        errors = []
        sanitized = (
            path_validation.sanitized_params.copy()
            if path_validation.sanitized_params
            else {}
        )

        # 验证编码
        encoding = params.get("encoding", "utf-8")
        if encoding not in ["utf-8", "gbk", "ascii", "binary"]:
            errors.append(
                ValidationError(
                    field="encoding",
                    message=f"不支持的编码格式: {encoding}",
                    code="INVALID_ENCODING",
                )
            )
        sanitized["encoding"] = encoding

        # 验证文件大小限制
        max_size = params.get("max_size", 10485760)
        if (
            not isinstance(max_size, int)
            or max_size <= 0
            or max_size > self.max_file_size
        ):
            errors.append(
                ValidationError(
                    field="max_size",
                    message=f"max_size 必须在 1 到 {self.max_file_size} 之间",
                    code="INVALID_MAX_SIZE",
                )
            )
        sanitized["max_size"] = max_size

        # 验证行号范围
        start_line = params.get("start_line")
        end_line = params.get("end_line")

        if start_line is not None:
            if not isinstance(start_line, int) or start_line < 1:
                errors.append(
                    ValidationError(
                        field="start_line",
                        message="start_line 必须是大于0的整数",
                        code="INVALID_START_LINE",
                    )
                )
            else:
                sanitized["start_line"] = start_line

        if end_line is not None:
            if not isinstance(end_line, int) or end_line < 1:
                errors.append(
                    ValidationError(
                        field="end_line",
                        message="end_line 必须是大于0的整数",
                        code="INVALID_END_LINE",
                    )
                )
            else:
                sanitized["end_line"] = end_line

        if start_line is not None and end_line is not None and start_line > end_line:
            errors.append(
                ValidationError(
                    field="end_line",
                    message="end_line 必须大于等于 start_line",
                    code="INVALID_LINE_RANGE",
                )
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized if len(errors) == 0 else None,
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行文件读取"""
        params = request.parameters
        file_path = params["path"]
        encoding = params.get("encoding", "utf-8")
        max_size = params.get("max_size", 10485760)
        start_line = params.get("start_line")
        end_line = params.get("end_line")

        try:
            # 检查文件存在性
            if not os.path.exists(file_path):
                return self._create_error_result(
                    "FILE_NOT_FOUND", f"文件不存在: {file_path}"
                )

            # 检查是否为文件
            if not os.path.isfile(file_path):
                return self._create_error_result(
                    "NOT_A_FILE", f"路径不是文件: {file_path}"
                )

            # 获取文件信息
            stat_info = os.stat(file_path)
            file_size = stat_info.st_size
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)

            # 检查文件大小
            if file_size > max_size:
                return self._create_error_result(
                    "FILE_TOO_LARGE",
                    f"文件过大 ({file_size} bytes), 超过限制 ({max_size} bytes)",
                )

            # 读取文件内容
            if encoding == "binary":
                with open(file_path, "rb") as f:
                    content = f.read().hex()
                is_binary = True
            else:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        if start_line is not None or end_line is not None:
                            lines = f.readlines()
                            start_idx = (start_line - 1) if start_line else 0
                            end_idx = end_line if end_line else len(lines)
                            content = "".join(lines[start_idx:end_idx])
                            lines_count = len(lines)
                        else:
                            content = f.read()
                            lines_count = content.count("\n") + 1 if content else 0
                    is_binary = False
                except UnicodeDecodeError:
                    return self._create_error_result(
                        "ENCODING_ERROR", f"无法使用编码 {encoding} 读取文件"
                    )

            # 构建响应
            result_content = {
                "content": content,
                "metadata": {
                    "size": file_size,
                    "modified_time": modified_time.isoformat(),
                    "encoding": encoding,
                    "lines_count": lines_count if not is_binary else None,
                    "is_binary": is_binary,
                },
            }

            metadata = ExecutionMetadata(
                execution_time=0,  # 会被注册中心填充
                memory_used=file_size / 1024 / 1024,  # MB
                cpu_time=0,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=file_size / 1024 / 1024, cpu_time_ms=0, io_operations=1
            )

            return self._create_success_result(result_content, metadata, resources)

        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限读取文件: {file_path}"
            )
        except Exception as e:
            self._logger.exception("读取文件时发生异常")
            return self._create_error_result("READ_ERROR", f"读取文件失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class WriteFileTool(BaseFileOperationTool):
    """写入文件工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="写入内容到指定文件，支持创建新文件和覆盖现有文件",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"},
                    "encoding": {
                        "type": "string",
                        "enum": ["utf-8", "gbk", "ascii"],
                        "default": "utf-8",
                        "description": "文件编码格式",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["create", "overwrite", "append"],
                        "default": "create",
                        "description": "写入模式",
                    },
                    "backup": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否创建备份",
                    },
                    "permissions": {
                        "type": "string",
                        "pattern": "^[0-7]{3}$",
                        "default": "644",
                        "description": "文件权限（Unix格式）",
                    },
                },
                "required": ["path", "content"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        # 验证路径
        path_validation = self._validate_path(params.get("path", ""))
        if not path_validation.is_valid:
            return path_validation

        errors = []
        sanitized = (
            path_validation.sanitized_params.copy()
            if path_validation.sanitized_params
            else {}
        )

        # 验证内容
        content = params.get("content", "")
        if not isinstance(content, str):
            errors.append(
                ValidationError(
                    field="content",
                    message="content 必须是字符串",
                    code="INVALID_CONTENT_TYPE",
                )
            )
        sanitized["content"] = content

        # 验证编码
        encoding = params.get("encoding", "utf-8")
        if encoding not in ["utf-8", "gbk", "ascii"]:
            errors.append(
                ValidationError(
                    field="encoding",
                    message=f"不支持的编码格式: {encoding}",
                    code="INVALID_ENCODING",
                )
            )
        sanitized["encoding"] = encoding

        # 验证模式
        mode = params.get("mode", "create")
        if mode not in ["create", "overwrite", "append"]:
            errors.append(
                ValidationError(
                    field="mode",
                    message=f"不支持的写入模式: {mode}",
                    code="INVALID_MODE",
                )
            )
        sanitized["mode"] = mode

        # 验证权限
        permissions = params.get("permissions", "644")
        if not isinstance(permissions, str) or len(permissions) != 3:
            errors.append(
                ValidationError(
                    field="permissions",
                    message="permissions 必须是3位数字字符串",
                    code="INVALID_PERMISSIONS_FORMAT",
                )
            )
        else:
            try:
                int(permissions, 8)  # 验证是否为有效八进制数
                sanitized["permissions"] = permissions
            except ValueError:
                errors.append(
                    ValidationError(
                        field="permissions",
                        message="permissions 必须是有效的八进制数",
                        code="INVALID_PERMISSIONS_VALUE",
                    )
                )

        # 验证备份选项
        backup = params.get("backup", False)
        if not isinstance(backup, bool):
            errors.append(
                ValidationError(
                    field="backup",
                    message="backup 必须是布尔值",
                    code="INVALID_BACKUP_TYPE",
                )
            )
        sanitized["backup"] = backup

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized if len(errors) == 0 else None,
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行文件写入"""
        params = request.parameters
        file_path = params["path"]
        content = params["content"]
        encoding = params.get("encoding", "utf-8")
        mode = params.get("mode", "create")
        backup = params.get("backup", False)
        permissions = params.get("permissions", "644")

        try:
            # 检查文件是否存在
            file_exists = os.path.exists(file_path)

            # 根据模式检查是否可以写入
            if mode == "create" and file_exists:
                return self._create_error_result(
                    "FILE_EXISTS", f"文件已存在，使用 create 模式无法覆盖: {file_path}"
                )

            # 创建目录（如果不存在）
            directory = os.path.dirname(file_path)
            created_directories = []
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                created_directories.append(directory)

            # 创建备份
            backup_path = None
            if backup and file_exists:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{file_path}.backup_{timestamp}"
                shutil.copy2(file_path, backup_path)

            # 写入文件
            write_mode = {"create": "w", "overwrite": "w", "append": "a"}[mode]

            with open(file_path, write_mode, encoding=encoding) as f:
                f.write(content)

            # 设置权限
            if os.name != "nt":  # 非Windows系统
                os.chmod(file_path, int(permissions, 8))

            # 获取写入的字节数
            bytes_written = len(content.encode(encoding))

            # 构建响应
            result_content = {
                "bytes_written": bytes_written,
                "backup_path": backup_path,
                "created_directories": created_directories,
            }

            metadata = ExecutionMetadata(
                execution_time=0,
                memory_used=bytes_written / 1024 / 1024,
                cpu_time=0,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=bytes_written / 1024 / 1024, cpu_time_ms=0, io_operations=1
            )

            return self._create_success_result(result_content, metadata, resources)

        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限写入文件: {file_path}"
            )
        except Exception as e:
            self._logger.exception("写入文件时发生异常")
            return self._create_error_result("WRITE_ERROR", f"写入文件失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ListFilesTool(BaseFileOperationTool):
    """列出文件工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_files",
            description="列出目录中的文件和子目录",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "default": ".",
                        "description": "目录路径",
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否递归列出子目录",
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否包含隐藏文件",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件名匹配模式（glob）",
                    },
                    "file_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["file", "directory", "symlink"],
                        },
                        "default": ["file", "directory"],
                        "description": "文件类型过滤",
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": "最大递归深度",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["name", "size", "modified_time", "created_time"],
                        "default": "name",
                        "description": "排序字段",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "default": "asc",
                        "description": "排序顺序",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行文件列表"""
        params = request.parameters
        directory = params.get("path", ".")
        recursive = params.get("recursive", False)
        include_hidden = params.get("include_hidden", False)
        pattern = params.get("pattern")
        file_types = params.get("file_types", ["file", "directory"])
        max_depth = params.get("max_depth", 5)
        sort_by = params.get("sort_by", "name")
        sort_order = params.get("sort_order", "asc")

        try:
            # 验证目录
            if not os.path.exists(directory):
                return self._create_error_result(
                    "DIRECTORY_NOT_FOUND", f"目录不存在: {directory}"
                )

            if not os.path.isdir(directory):
                return self._create_error_result(
                    "NOT_A_DIRECTORY", f"路径不是目录: {directory}"
                )

            files = []

            def collect_files(current_dir: str, current_depth: int = 0) -> None:
                """递归收集文件"""
                if current_depth > max_depth:
                    return

                try:
                    for entry in os.listdir(current_dir):
                        # 跳过隐藏文件（如果未启用）
                        if not include_hidden and entry.startswith("."):
                            continue

                        entry_path = os.path.join(current_dir, entry)

                        # 模式匹配
                        if pattern and not fnmatch.fnmatch(entry, pattern):
                            continue

                        # 获取文件信息
                        try:
                            stat_info = os.lstat(entry_path)  # 使用lstat以支持符号链接

                            # 确定文件类型
                            if stat.S_ISDIR(stat_info.st_mode):
                                file_type = "directory"
                            elif stat.S_ISLNK(stat_info.st_mode):
                                file_type = "symlink"
                            else:
                                file_type = "file"

                            # 类型过滤
                            if file_type not in file_types:
                                # 如果是目录且开启递归，仍需要进入
                                if file_type == "directory" and recursive:
                                    collect_files(entry_path, current_depth + 1)
                                continue

                            # 构建文件信息
                            file_info = {
                                "name": entry,
                                "path": entry_path,
                                "relative_path": os.path.relpath(entry_path, directory),
                                "type": file_type,
                                "size": stat_info.st_size,
                                "modified_time": datetime.fromtimestamp(
                                    stat_info.st_mtime
                                ).isoformat(),
                                "permissions": oct(stat_info.st_mode)[-3:],
                                "is_hidden": entry.startswith("."),
                            }

                            files.append(file_info)

                            # 递归处理子目录
                            if file_type == "directory" and recursive:
                                collect_files(entry_path, current_depth + 1)

                        except OSError:
                            # 跳过无法访问的文件
                            continue

                except OSError:
                    # 跳过无法访问的目录
                    pass

            # 收集文件
            collect_files(directory)

            # 排序
            if sort_by == "name":
                files.sort(key=lambda x: str(x["name"]), reverse=(sort_order == "desc"))
            elif sort_by == "size":
                files.sort(
                    key=lambda x: (
                        int(x["size"]) if isinstance(x["size"], (str, int)) else 0
                    ),
                    reverse=(sort_order == "desc"),
                )
            elif sort_by == "modified_time":
                files.sort(
                    key=lambda x: str(x["modified_time"]),
                    reverse=(sort_order == "desc"),
                )

            # 统计信息
            total_count = len(files)
            directory_count = sum(1 for f in files if f["type"] == "directory")
            file_count = sum(1 for f in files if f["type"] == "file")

            result_content = {
                "files": files,
                "total_count": total_count,
                "directory_count": directory_count,
                "file_count": file_count,
            }

            metadata = ExecutionMetadata(
                execution_time=0,
                memory_used=total_count * 0.01,  # 每个文件信息约10KB
                cpu_time=0,
                io_operations=total_count,
            )

            resources = ResourceUsage(
                memory_mb=total_count * 0.01, cpu_time_ms=0, io_operations=total_count
            )

            return self._create_success_result(result_content, metadata, resources)

        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限访问目录: {directory}"
            )
        except Exception as e:
            self._logger.exception("列出文件时发生异常")
            return self._create_error_result("LIST_ERROR", f"列出文件失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class CreateDirectoryTool(BaseFileOperationTool):
    """创建目录工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_directory",
            description="创建目录，支持递归创建父目录",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径"},
                    "recursive": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否递归创建父目录",
                    },
                    "permissions": {
                        "type": "string",
                        "pattern": "^[0-7]{3}$",
                        "default": "755",
                        "description": "目录权限（Unix格式）",
                    },
                    "exist_ok": {
                        "type": "boolean",
                        "default": True,
                        "description": "目录已存在时是否报错",
                    },
                },
                "required": ["path"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行创建目录"""
        params = request.parameters
        directory = params["path"]
        recursive = params.get("recursive", True)
        permissions = params.get("permissions", "755")
        exist_ok = params.get("exist_ok", True)

        try:
            created_directories = []

            # 检查目录是否已存在
            if os.path.exists(directory):
                if not exist_ok:
                    return self._create_error_result(
                        "DIRECTORY_EXISTS", f"目录已存在: {directory}"
                    )
                if not os.path.isdir(directory):
                    return self._create_error_result(
                        "PATH_IS_FILE", f"路径已存在但不是目录: {directory}"
                    )
            else:
                # 创建目录
                if recursive:
                    # 找出需要创建的所有父目录
                    path_parts = Path(directory).parts
                    for i in range(1, len(path_parts) + 1):
                        partial_path = os.path.join(*path_parts[:i])
                        if not os.path.exists(partial_path):
                            created_directories.append(partial_path)

                    os.makedirs(directory, exist_ok=exist_ok)
                else:
                    parent_dir = os.path.dirname(directory)
                    if parent_dir and not os.path.exists(parent_dir):
                        return self._create_error_result(
                            "PARENT_NOT_EXISTS", f"父目录不存在: {parent_dir}"
                        )
                    os.mkdir(directory)
                    created_directories.append(directory)

                # 设置权限
                if os.name != "nt":  # 非Windows系统
                    os.chmod(directory, int(permissions, 8))

            result_content = {
                "created": not os.path.exists(directory)
                or len(created_directories) > 0,
                "path": directory,
                "created_directories": created_directories,
            }

            metadata = ExecutionMetadata(
                execution_time=0,
                memory_used=0.1,
                cpu_time=0,
                io_operations=len(created_directories),
            )

            resources = ResourceUsage(
                memory_mb=0.1, cpu_time_ms=0, io_operations=len(created_directories)
            )

            return self._create_success_result(result_content, metadata, resources)

        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限创建目录: {directory}"
            )
        except Exception as e:
            self._logger.exception("创建目录时发生异常")
            return self._create_error_result("CREATE_ERROR", f"创建目录失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class FileOperationsTools:
    """文件操作工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有文件操作工具"""
        # 直接使用传递的配置，如果没有则使用默认配置
        tools_config = self.config

        return [
            ReadFileTool(tools_config),
            WriteFileTool(tools_config),
            ListFilesTool(tools_config),
            CreateDirectoryTool(tools_config),
        ]
