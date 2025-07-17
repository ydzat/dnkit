"""
增强的文件系统工具集

基于 ChromaDB 统一存储的文件操作工具，支持文件内容存储、语义搜索等功能。
扩展现有的文件操作工具，添加 ChromaDB 集成。
"""

import hashlib
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from ..storage.unified_manager import UnifiedDataManager
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
    ValidationError,
    ValidationResult,
)


class EnhancedFileReader(BaseTool):
    """增强的文件读取工具 - 支持 ChromaDB 存储"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.max_file_size = self.config.get("max_file_size_mb", 10) * 1024 * 1024
        self.auto_store = self.config.get("auto_store_to_chromadb", True)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="enhanced_read_file",
            description="读取文件内容并可选择存储到 ChromaDB 进行语义搜索",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "要读取的文件路径"},
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "文件编码",
                    },
                    "store_to_chromadb": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否将文件内容存储到 ChromaDB",
                    },
                    "extract_metadata": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否提取文件元数据",
                    },
                },
                "required": ["file_path"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        errors: List[ValidationError] = []

        file_path = params.get("file_path", "")
        if not file_path:
            errors.append(
                ValidationError(
                    field="file_path",
                    message="文件路径不能为空",
                    code="EMPTY_FILE_PATH",
                )
            )
        elif not os.path.exists(file_path):
            errors.append(
                ValidationError(
                    field="file_path",
                    message=f"文件不存在: {file_path}",
                    code="FILE_NOT_FOUND",
                )
            )
        elif not os.path.isfile(file_path):
            errors.append(
                ValidationError(
                    field="file_path",
                    message=f"路径不是文件: {file_path}",
                    code="NOT_A_FILE",
                )
            )
        elif os.path.getsize(file_path) > self.max_file_size:
            errors.append(
                ValidationError(
                    field="file_path",
                    message=f"文件过大，超过 {self.max_file_size / 1024 / 1024}MB 限制",
                    code="FILE_TOO_LARGE",
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行文件读取"""
        params = request.parameters
        file_path = self._resolve_path(params["file_path"], request)
        encoding = params.get("encoding", "utf-8")
        store_to_chromadb = params.get("store_to_chromadb", True)
        extract_metadata = params.get("extract_metadata", True)

        try:
            start_time = time.time()

            # 读取文件内容
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()

            # 提取文件元数据
            file_stat = os.stat(file_path)
            file_info = {
                "path": os.path.abspath(file_path),
                "size": file_stat.st_size,
                "modified_time": file_stat.st_mtime,
                "created_time": file_stat.st_ctime,
                "extension": Path(file_path).suffix,
                "mime_type": mimetypes.guess_type(file_path)[0] or "text/plain",
            }

            # 检测编程语言
            language = self._detect_language(file_path)
            if language:
                file_info["language"] = language

            result_content = {
                "content": content,
                "file_info": file_info,
                "content_length": len(content),
                "line_count": content.count("\n") + 1 if content else 0,
            }

            # 存储到 ChromaDB
            if store_to_chromadb and self.auto_store:
                try:
                    file_hash = hashlib.md5(
                        content.encode(), usedforsecurity=False
                    ).hexdigest()
                    data_id = f"file_{file_hash}"

                    metadata = {
                        "file_path": file_info["path"],
                        "file_size": file_info["size"],
                        "language": language or "text",
                        "file_extension": file_info["extension"],
                        "mime_type": file_info["mime_type"],
                        "modified_time": file_info["modified_time"],
                        "content_hash": file_hash,
                    }

                    stored_id = self.data_manager.store_data(
                        data_type="file",
                        content=content,
                        metadata=metadata,
                        data_id=data_id,
                    )

                    result_content["chromadb_id"] = stored_id
                    result_content["stored_to_chromadb"] = True

                except Exception as e:
                    result_content["chromadb_error"] = str(e)
                    result_content["stored_to_chromadb"] = False

            execution_time = (time.time() - start_time) * 1000

            exec_metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=len(content) / 1024 / 1024,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(content) / 1024 / 1024,
                cpu_time_ms=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(result_content, exec_metadata, resources)

        except UnicodeDecodeError as e:
            return self._create_error_result(
                "ENCODING_ERROR", f"文件编码错误，尝试使用不同的编码: {str(e)}"
            )
        except PermissionError:
            return self._create_error_result(
                "PERMISSION_DENIED", f"没有权限读取文件: {file_path}"
            )
        except Exception as e:
            self._logger.exception("读取文件时发生异常")
            return self._create_error_result("READ_ERROR", f"读取文件失败: {str(e)}")

    def _detect_language(self, file_path: str) -> Optional[str]:
        """检测编程语言"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
            ".ps1": "powershell",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".md": "markdown",
            ".txt": "text",
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext)

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class FileSearchTool(BaseTool):
    """基于 ChromaDB 的文件内容搜索工具"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_files",
            description="在 ChromaDB 中搜索文件内容",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询文本"},
                    "language": {"type": "string", "description": "过滤特定编程语言"},
                    "file_extension": {
                        "type": "string",
                        "description": "过滤特定文件扩展名",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "最大返回结果数",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行文件搜索"""
        params = request.parameters
        query = params["query"]
        language = params.get("language")
        file_extension = params.get("file_extension")
        max_results = params.get("max_results", 10)

        try:
            start_time = time.time()

            # 构建过滤条件
            filters = {}
            if language:
                filters["language"] = language
            if file_extension:
                filters["file_extension"] = file_extension

            # 执行搜索
            results = self.data_manager.query_data(
                query=query,
                data_type="file",
                filters=filters if filters else None,
                n_results=max_results,
            )

            # 处理搜索结果
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    result_item = {
                        "id": doc_id,
                        "file_path": results["metadatas"][0][i].get("file_path", ""),
                        "language": results["metadatas"][0][i].get("language", ""),
                        "file_size": results["metadatas"][0][i].get("file_size", 0),
                        "similarity_score": (
                            1 - results["distances"][0][i]
                            if results["distances"][0]
                            else 0
                        ),
                        "content_preview": (
                            results["documents"][0][i][:200] + "..."
                            if len(results["documents"][0][i]) > 200
                            else results["documents"][0][i]
                        ),
                    }
                    search_results.append(result_item)

            execution_time = (time.time() - start_time) * 1000

            result_content = {
                "query": query,
                "results": search_results,
                "total_found": len(search_results),
                "filters_applied": filters,
            }

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=0.1,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(result_content, metadata)

        except Exception as e:
            self._logger.exception("搜索文件时发生异常")
            return self._create_error_result("SEARCH_ERROR", f"搜索失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class EnhancedFileOperationsTools:
    """增强的文件操作工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.data_manager = UnifiedDataManager()

    def create_tools(self) -> List[BaseTool]:
        """创建所有增强的文件操作工具"""
        tools_config = self.config.get("enhanced_file_operations", {})

        return [
            EnhancedFileReader(tools_config, self.data_manager),
            FileSearchTool(tools_config, self.data_manager),
        ]
