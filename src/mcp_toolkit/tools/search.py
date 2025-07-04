"""
搜索工具集

提供文件搜索、内容搜索等功能，支持多种搜索模式和过滤选项。
"""

import fnmatch
import glob
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Union

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


class BaseSearchTool(BaseTool):
    """搜索工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.max_results = self.config.get("max_results", 10000)
        self.max_file_size = self.config.get("max_file_size_bytes", 10485760)  # 10MB
        self.allowed_paths = self.config.get("allowed_paths", [])
        self.forbidden_paths = self.config.get("forbidden_paths", [])
        self.max_search_depth = self.config.get("max_search_depth", 20)

    def _validate_search_path(self, path: str) -> ValidationResult:
        """验证搜索路径安全性"""
        errors = []

        try:
            # 规范化路径
            normalized_path = os.path.abspath(os.path.expanduser(path))

            # 检查路径是否存在
            if not os.path.exists(normalized_path):
                errors.append(
                    ValidationError(
                        field="search_path",
                        message=f"搜索路径不存在: {path}",
                        code="PATH_NOT_FOUND",
                    )
                )
                return ValidationResult(is_valid=False, errors=errors)

            # 检查是否为目录
            if not os.path.isdir(normalized_path):
                errors.append(
                    ValidationError(
                        field="search_path",
                        message=f"搜索路径不是目录: {path}",
                        code="NOT_A_DIRECTORY",
                    )
                )
                return ValidationResult(is_valid=False, errors=errors)

            # 检查禁止路径
            for forbidden in self.forbidden_paths:
                if normalized_path.startswith(os.path.abspath(forbidden)):
                    errors.append(
                        ValidationError(
                            field="search_path",
                            message=f"搜索路径在禁止目录中: {path}",
                            code="FORBIDDEN_PATH",
                        )
                    )

            # 检查允许路径
            if self.allowed_paths:
                allowed = False
                for allowed_path in self.allowed_paths:
                    if normalized_path.startswith(
                        os.path.abspath(os.path.expanduser(allowed_path))
                    ):
                        allowed = True
                        break
                if not allowed:
                    errors.append(
                        ValidationError(
                            field="search_path",
                            message=f"搜索路径不在允许目录中: {path}",
                            code="PATH_NOT_ALLOWED",
                        )
                    )

        except Exception as e:
            errors.append(
                ValidationError(
                    field="search_path",
                    message=f"路径验证失败: {str(e)}",
                    code="PATH_VALIDATION_ERROR",
                )
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=(
                {"search_path": normalized_path} if len(errors) == 0 else None
            ),
        )


class FileSearchTool(BaseSearchTool):
    """文件搜索工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_search",
            description="在指定目录中搜索文件",
            parameters={
                "type": "object",
                "properties": {
                    "search_path": {
                        "type": "string",
                        "default": ".",
                        "description": "搜索根目录",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件名匹配模式（支持glob和正则）",
                    },
                    "pattern_type": {
                        "type": "string",
                        "enum": ["glob", "regex", "exact"],
                        "default": "glob",
                        "description": "模式类型",
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否递归搜索子目录",
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 10,
                        "description": "最大搜索深度",
                    },
                    "file_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["file", "directory", "symlink"],
                        },
                        "default": ["file"],
                        "description": "文件类型过滤",
                    },
                    "size_filter": {
                        "type": "object",
                        "properties": {
                            "min_size": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "最小文件大小（字节）",
                            },
                            "max_size": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "最大文件大小（字节）",
                            },
                        },
                        "description": "文件大小过滤",
                    },
                    "date_filter": {
                        "type": "object",
                        "properties": {
                            "modified_after": {
                                "type": "string",
                                "format": "date-time",
                                "description": "修改时间晚于",
                            },
                            "modified_before": {
                                "type": "string",
                                "format": "date-time",
                                "description": "修改时间早于",
                            },
                        },
                        "description": "日期过滤",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10000,
                        "default": 1000,
                        "description": "最大结果数量",
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否包含隐藏文件",
                    },
                },
                "required": ["pattern"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        errors: List[ValidationError] = []
        sanitized: Dict[str, Any] = {}

        # 验证搜索路径
        search_path = params.get("search_path", ".")
        path_validation = self._validate_search_path(search_path)
        if not path_validation.is_valid:
            errors.extend(path_validation.errors or [])
        else:
            if path_validation.sanitized_params:
                sanitized.update(path_validation.sanitized_params)

        # 验证模式
        pattern = params.get("pattern", "")
        if not pattern:
            errors.append(
                ValidationError(
                    field="pattern", message="搜索模式不能为空", code="EMPTY_PATTERN"
                )
            )
        sanitized["pattern"] = pattern

        # 验证模式类型
        pattern_type = params.get("pattern_type", "glob")
        if pattern_type not in ["glob", "regex", "exact"]:
            errors.append(
                ValidationError(
                    field="pattern_type",
                    message=f"不支持的模式类型: {pattern_type}",
                    code="INVALID_PATTERN_TYPE",
                )
            )
        sanitized["pattern_type"] = pattern_type

        # 验证正则表达式
        if pattern_type == "regex":
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(
                    ValidationError(
                        field="pattern",
                        message=f"无效的正则表达式: {str(e)}",
                        code="INVALID_REGEX",
                    )
                )

        # 验证其他参数
        sanitized["recursive"] = params.get("recursive", True)
        sanitized["max_depth"] = min(params.get("max_depth", 10), self.max_search_depth)
        sanitized["file_types"] = params.get("file_types", ["file"])
        sanitized["max_results"] = min(
            params.get("max_results", 1000), self.max_results
        )
        sanitized["include_hidden"] = params.get("include_hidden", False)
        sanitized["size_filter"] = params.get("size_filter", {})
        sanitized["date_filter"] = params.get("date_filter", {})

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized if len(errors) == 0 else None,
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行文件搜索"""
        params = request.parameters
        search_path = params["search_path"]
        pattern = params["pattern"]
        pattern_type = params.get("pattern_type", "glob")
        recursive = params.get("recursive", True)
        max_depth = params.get("max_depth", 10)
        file_types = params.get("file_types", ["file"])
        size_filter = params.get("size_filter", {})
        date_filter = params.get("date_filter", {})
        max_results = params.get("max_results", 1000)
        include_hidden = params.get("include_hidden", False)

        start_time = time.time()
        results: List[Dict[str, Any]] = []
        total_searched = 0

        try:
            # 编译模式
            if pattern_type == "regex":
                pattern_obj = re.compile(pattern)
            else:
                pattern_obj = None

            # 解析日期过滤器
            modified_after = None
            modified_before = None
            if date_filter.get("modified_after"):
                modified_after = datetime.fromisoformat(
                    date_filter["modified_after"].replace("Z", "+00:00")
                )
            if date_filter.get("modified_before"):
                modified_before = datetime.fromisoformat(
                    date_filter["modified_before"].replace("Z", "+00:00")
                )

            def search_directory(current_path: str, current_depth: int = 0) -> None:
                """递归搜索目录"""
                nonlocal total_searched

                if current_depth > max_depth or len(results) >= max_results:
                    return

                try:
                    for entry in os.listdir(current_path):
                        if len(results) >= max_results:
                            break

                        # 跳过隐藏文件
                        if not include_hidden and entry.startswith("."):
                            continue

                        entry_path = os.path.join(current_path, entry)
                        total_searched += 1

                        try:
                            stat_info = os.lstat(entry_path)

                            # 确定文件类型
                            if os.path.isdir(entry_path):
                                file_type = "directory"
                            elif os.path.islink(entry_path):
                                file_type = "symlink"
                            else:
                                file_type = "file"

                            # 类型过滤
                            if file_type not in file_types:
                                if file_type == "directory" and recursive:
                                    search_directory(entry_path, current_depth + 1)
                                continue

                            # 名称模式匹配
                            name_match = False
                            if pattern_type == "exact":
                                name_match = entry == pattern
                            elif pattern_type == "glob":
                                name_match = fnmatch.fnmatch(entry, pattern)
                            elif pattern_type == "regex":
                                name_match = (
                                    bool(pattern_obj.search(entry))
                                    if pattern_obj
                                    else False
                                )

                            if not name_match:
                                if file_type == "directory" and recursive:
                                    search_directory(entry_path, current_depth + 1)
                                continue

                            # 大小过滤
                            file_size = stat_info.st_size
                            if (
                                size_filter.get("min_size") is not None
                                and file_size < size_filter["min_size"]
                            ):
                                continue
                            if (
                                size_filter.get("max_size") is not None
                                and file_size > size_filter["max_size"]
                            ):
                                continue

                            # 日期过滤
                            modified_time = datetime.fromtimestamp(stat_info.st_mtime)
                            if modified_after and modified_time < modified_after:
                                continue
                            if modified_before and modified_time > modified_before:
                                continue

                            # 添加到结果
                            result_item = {
                                "path": entry_path,
                                "name": entry,
                                "relative_path": os.path.relpath(
                                    entry_path, search_path
                                ),
                                "type": file_type,
                                "size": file_size,
                                "modified_time": modified_time.isoformat(),
                                "permissions": oct(stat_info.st_mode)[-3:],
                                "is_hidden": entry.startswith("."),
                            }

                            results.append(result_item)

                            # 递归搜索子目录
                            if file_type == "directory" and recursive:
                                search_directory(entry_path, current_depth + 1)

                        except OSError:
                            # 跳过无法访问的文件
                            continue

                except OSError:
                    # 跳过无法访问的目录
                    pass

            # 开始搜索
            search_directory(search_path)

            search_time = (time.time() - start_time) * 1000  # 转换为毫秒

            result_content = {
                "results": results,
                "total_found": len(results),
                "total_searched": total_searched,
                "search_time": search_time / 1000,  # 转换回秒
                "truncated": len(results) >= max_results,
                "search_path": search_path,
                "pattern": pattern,
                "pattern_type": pattern_type,
            }

            metadata = ExecutionMetadata(
                execution_time=search_time,
                memory_used=len(results) * 0.01,  # 每个结果约10KB
                cpu_time=search_time,
                io_operations=total_searched,
            )

            resources = ResourceUsage(
                memory_mb=len(results) * 0.01,
                cpu_time_ms=search_time,
                io_operations=total_searched,
            )

            return self._create_success_result(result_content, metadata, resources)

        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限访问搜索路径: {search_path}"
            )
        except Exception as e:
            self._logger.exception("文件搜索时发生异常")
            return self._create_error_result("SEARCH_ERROR", f"文件搜索失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ContentSearchTool(BaseSearchTool):
    """内容搜索工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="content_search",
            description="在文件内容中搜索指定文本",
            parameters={
                "type": "object",
                "properties": {
                    "search_path": {
                        "type": "string",
                        "default": ".",
                        "description": "搜索根目录",
                    },
                    "query": {"type": "string", "description": "搜索查询文本"},
                    "query_type": {
                        "type": "string",
                        "enum": ["text", "regex"],
                        "default": "text",
                        "description": "查询类型",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否区分大小写",
                    },
                    "whole_word": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否全词匹配",
                    },
                    "file_pattern": {
                        "type": "string",
                        "default": "*",
                        "description": "文件名过滤模式",
                    },
                    "exclude_pattern": {
                        "type": "string",
                        "description": "排除文件模式",
                    },
                    "max_line_length": {
                        "type": "integer",
                        "minimum": 50,
                        "maximum": 1000,
                        "default": 200,
                        "description": "结果行最大长度",
                    },
                    "context_lines": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                        "default": 2,
                        "description": "上下文行数",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10000,
                        "default": 1000,
                        "description": "最大结果数量",
                    },
                    "max_matches_per_file": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 100,
                        "description": "每个文件最大匹配数",
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否递归搜索",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行内容搜索"""
        params = request.parameters
        search_path = params.get("search_path", ".")
        query = params["query"]
        query_type = params.get("query_type", "text")
        case_sensitive = params.get("case_sensitive", False)
        whole_word = params.get("whole_word", False)
        file_pattern = params.get("file_pattern", "*")
        exclude_pattern = params.get("exclude_pattern")
        max_line_length = params.get("max_line_length", 200)
        context_lines = params.get("context_lines", 2)
        max_results = params.get("max_results", 1000)
        max_matches_per_file = params.get("max_matches_per_file", 100)
        recursive = params.get("recursive", True)

        start_time = time.time()
        results: List[Dict[str, Any]] = []
        files_searched = 0
        total_matches = 0

        try:
            # 构建搜索模式
            if query_type == "regex":
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    search_pattern = re.compile(query, flags)
                except re.error as e:
                    return self._create_error_result(
                        "INVALID_REGEX", f"无效的正则表达式: {str(e)}"
                    )
            else:
                # 文本搜索
                if whole_word:
                    # 全词匹配
                    escaped_query = re.escape(query)
                    pattern_str = r"\b" + escaped_query + r"\b"
                    flags = 0 if case_sensitive else re.IGNORECASE
                    search_pattern = re.compile(pattern_str, flags)
                else:
                    # 普通文本搜索
                    if case_sensitive:
                        # fmt: off
                        def search_func(text: str) -> bool:
                            return query in text
                        # fmt: on
                    else:
                        query_lower = query.lower()
                        # fmt: off

                        def search_func(text: str) -> bool:
                            return query_lower in text.lower()
                        # fmt: on

                    search_pattern = None

            def search_in_file(file_path: str) -> List[Dict[str, Any]]:
                """在单个文件中搜索"""
                nonlocal total_matches

                try:
                    # 检查文件大小
                    if os.path.getsize(file_path) > self.max_file_size:
                        return []

                    matches: List[Dict[str, Any]] = []

                    # 尝试多种编码
                    encodings = ["utf-8", "gbk", "latin1"]
                    content = None

                    for encoding in encodings:
                        try:
                            with open(file_path, "r", encoding=encoding) as f:
                                content = f.read()
                            break
                        except UnicodeDecodeError:
                            continue

                    if content is None:
                        return []  # 无法读取文件

                    lines = content.splitlines()

                    for line_num, line in enumerate(lines, 1):
                        if len(matches) >= max_matches_per_file:
                            break

                        # 搜索匹配
                        if search_pattern:
                            # 正则表达式或全词匹配
                            line_matches = list(search_pattern.finditer(line))
                        else:
                            # 简单文本搜索
                            if search_func(line):
                                # 创建虚拟匹配对象
                                class SimpleMatch:
                                    def __init__(self, text: str, start: int, end: int):
                                        self._text = text
                                        self._start = start
                                        self._end = end

                                    def group(self) -> str:
                                        return self._text[self._start : self._end]

                                    def start(self) -> int:
                                        return self._start

                                    def end(self) -> int:
                                        return self._end

                                start_pos = (
                                    line.find(query)
                                    if case_sensitive
                                    else line.lower().find(query.lower())
                                )
                                if start_pos >= 0:
                                    end_pos = start_pos + len(query)
                                    # 使用 Any 来避免类型检查问题
                                    simple_matches: List[Any] = [
                                        SimpleMatch(line, start_pos, end_pos)
                                    ]
                                    line_matches = simple_matches
                                else:
                                    line_matches = []
                            else:
                                line_matches = []

                        if line_matches:
                            # 获取上下文
                            context_start = max(0, line_num - context_lines - 1)
                            context_end = min(len(lines), line_num + context_lines)

                            context_before = lines[context_start : line_num - 1]
                            context_after = lines[line_num:context_end]

                            # 截断长行
                            display_line = line
                            if len(display_line) > max_line_length:
                                display_line = display_line[:max_line_length] + "..."

                            match_info = {
                                "line_number": line_num,
                                "line_content": display_line,
                                "context_before": (
                                    context_before[-context_lines:]
                                    if context_before
                                    else []
                                ),
                                "context_after": (
                                    context_after[:context_lines]
                                    if context_after
                                    else []
                                ),
                                "match_count": (
                                    len(line_matches) if search_pattern else 1
                                ),
                            }

                            # 如果是正则匹配，添加匹配位置
                            if search_pattern and line_matches[0] is not None:
                                match_info["matches"] = [
                                    {
                                        "start": match.start(),
                                        "end": match.end(),
                                        "text": match.group(),
                                    }
                                    for match in line_matches
                                ]

                            matches.append(match_info)
                            total_matches += 1

                    return matches

                except OSError:
                    return []

            def search_directory(current_path: str) -> None:
                """递归搜索目录"""
                nonlocal files_searched

                if len(results) >= max_results:
                    return

                try:
                    for entry in os.listdir(current_path):
                        if len(results) >= max_results:
                            break

                        entry_path = os.path.join(current_path, entry)

                        if os.path.isfile(entry_path):
                            # 检查文件名模式
                            if not fnmatch.fnmatch(entry, file_pattern):
                                continue

                            # 检查排除模式
                            if exclude_pattern and fnmatch.fnmatch(
                                entry, exclude_pattern
                            ):
                                continue

                            files_searched += 1
                            matches = search_in_file(entry_path)

                            if matches:
                                result_item = {
                                    "file_path": entry_path,
                                    "relative_path": os.path.relpath(
                                        entry_path, search_path
                                    ),
                                    "matches": matches,
                                    "match_count": len(matches),
                                }
                                results.append(result_item)

                        elif os.path.isdir(entry_path) and recursive:
                            # 递归搜索子目录
                            search_directory(entry_path)

                except OSError:
                    pass

            # 开始搜索
            search_directory(search_path)

            search_time = (time.time() - start_time) * 1000  # 转换为毫秒

            result_content = {
                "results": results,
                "total_files_found": len(results),
                "total_files_searched": files_searched,
                "total_matches": total_matches,
                "search_time": search_time / 1000,  # 转换回秒
                "truncated": len(results) >= max_results,
                "query": query,
                "query_type": query_type,
                "search_path": search_path,
            }

            metadata = ExecutionMetadata(
                execution_time=search_time,
                memory_used=total_matches * 0.005,  # 每个匹配约5KB
                cpu_time=search_time,
                io_operations=files_searched,
            )

            resources = ResourceUsage(
                memory_mb=total_matches * 0.005,
                cpu_time_ms=search_time,
                io_operations=files_searched,
            )

            return self._create_success_result(result_content, metadata, resources)

        except Exception as e:
            self._logger.exception("内容搜索时发生异常")
            return self._create_error_result(
                "CONTENT_SEARCH_ERROR", f"内容搜索失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class SearchTools:
    """搜索工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有搜索工具"""
        tools_config = self.config.get("search", {})

        return [FileSearchTool(tools_config), ContentSearchTool(tools_config)]
