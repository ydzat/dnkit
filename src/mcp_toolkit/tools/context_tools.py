"""
上下文引擎工具集

基于 ChromaDB 统一存储的智能上下文工具，提供代码分析、语义搜索、项目概览等功能。
"""

import time
from typing import Any, Dict, List, Optional

from ..context.context_engine import ContextEngine
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


class CodeAnalysisTool(BaseTool):
    """代码分析工具 - 分析代码文件并存储到 ChromaDB"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.context_engine = ContextEngine(
            self.data_manager, self.config.get("context_engine", {})
        )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_code",
            description="分析代码文件，提取函数、类、依赖关系等信息并存储到 ChromaDB",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要分析的代码文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容（可选，如果不提供则从文件路径读取）",
                    },
                    "force_reanalyze": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否强制重新分析（即使已存在）",
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

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行代码分析"""
        params = request.parameters

        # 验证参数
        validation_result = self.validate_parameters(params)
        if not validation_result.is_valid:
            errors = validation_result.errors or []
            error_messages = [error.message for error in errors]
            return self._create_error_result(
                "VALIDATION_ERROR", f"参数验证失败: {'; '.join(error_messages)}"
            )

        file_path = self._resolve_path(params["file_path"], request)
        content = params.get("content")
        force_reanalyze = params.get("force_reanalyze", False)

        try:
            start_time = time.time()

            # 如果没有提供内容，尝试读取文件
            if content is None:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    return self._create_error_result(
                        "FILE_READ_ERROR", f"无法读取文件 {file_path}: {str(e)}"
                    )

            # 检查是否已存在分析结果
            if not force_reanalyze:
                existing_context = self.context_engine.get_file_context(file_path)
                if existing_context.get("found"):
                    return self._create_success_result(
                        {
                            "file_path": file_path,
                            "already_analyzed": True,
                            "existing_context": existing_context,
                            "message": "文件已分析，使用 force_reanalyze=true 强制重新分析",
                        }
                    )

            # 执行分析
            result = self.context_engine.analyze_and_store_file(file_path, content)

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=len(content) / 1024 / 1024,
                cpu_time=execution_time * 0.2,
                io_operations=result.get("total_stored", 0),
            )

            resources = ResourceUsage(
                memory_mb=len(content) / 1024 / 1024,
                cpu_time_ms=execution_time * 0.2,
                io_operations=result.get("total_stored", 0),
            )

            return self._create_success_result(result, metadata, resources)

        except Exception as e:
            self._logger.exception("代码分析时发生异常")
            return self._create_error_result(
                "ANALYSIS_ERROR", f"代码分析失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class CodeSearchTool(BaseTool):
    """代码搜索工具 - 智能代码搜索"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.context_engine = ContextEngine(
            self.data_manager, self.config.get("context_engine", {})
        )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_code",
            description="智能代码搜索，支持自然语言查询和语义搜索",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询（支持自然语言）",
                    },
                    "language": {"type": "string", "description": "过滤特定编程语言"},
                    "file_path": {
                        "type": "string",
                        "description": "限制在特定文件中搜索",
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["all", "functions", "classes", "files"],
                        "default": "all",
                        "description": "搜索类型",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                        "description": "最大返回结果数",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行代码搜索"""
        params = request.parameters

        # 基本参数检查
        if "query" not in params:
            return self._create_error_result("VALIDATION_ERROR", "缺少必需参数: query")

        query = params["query"]
        language = params.get("language")
        file_path = params.get("file_path")
        search_type = params.get("search_type", "all")
        max_results = params.get("max_results", 20)

        try:
            start_time = time.time()

            # 构建搜索上下文
            context = {}
            if file_path:
                context["current_file"] = file_path
            if language:
                context["current_language"] = language

            # 执行搜索
            search_results = self.context_engine.search_code(query, context)

            # 根据搜索类型过滤结果
            if search_type != "all":
                filtered_items = []
                for item in search_results.get("results", {}).get("items", []):
                    content_type = item.get("metadata", {}).get("content_type", "")
                    if search_type == "functions" and "function" in content_type:
                        filtered_items.append(item)
                    elif search_type == "classes" and "class" in content_type:
                        filtered_items.append(item)
                    elif search_type == "files" and content_type == "full_file":
                        filtered_items.append(item)

                search_results["results"]["items"] = filtered_items[:max_results]
                search_results["results"]["summary"]["total_results"] = len(
                    filtered_items
                )

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=0.1,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(search_results, metadata)

        except Exception as e:
            self._logger.exception("代码搜索时发生异常")
            return self._create_error_result("SEARCH_ERROR", f"代码搜索失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class SimilarCodeTool(BaseTool):
    """相似代码搜索工具"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.context_engine = ContextEngine(
            self.data_manager, self.config.get("context_engine", {})
        )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="find_similar_code",
            description="查找与给定代码片段相似的代码",
            parameters={
                "type": "object",
                "properties": {
                    "code_snippet": {
                        "type": "string",
                        "description": "要搜索的代码片段",
                    },
                    "language": {"type": "string", "description": "代码语言（可选）"},
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "最大返回结果数",
                    },
                },
                "required": ["code_snippet"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行相似代码搜索"""
        params = request.parameters

        # 基本参数检查
        if "code_snippet" not in params:
            return self._create_error_result(
                "VALIDATION_ERROR", "缺少必需参数: code_snippet"
            )

        code_snippet = params["code_snippet"]
        language = params.get("language")
        max_results = params.get("max_results", 10)

        try:
            start_time = time.time()

            # 执行相似代码搜索
            results = self.context_engine.search_similar_code(
                code_snippet, language, max_results
            )

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=0.1,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(results, metadata)

        except Exception as e:
            self._logger.exception("相似代码搜索时发生异常")
            return self._create_error_result(
                "SIMILAR_SEARCH_ERROR", f"相似代码搜索失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ProjectOverviewTool(BaseTool):
    """项目概览工具"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.context_engine = ContextEngine(
            self.data_manager, self.config.get("context_engine", {})
        )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_project_overview",
            description="获取项目概览，包括文件统计、语言分布、代码结构等",
            parameters={
                "type": "object",
                "properties": {
                    "include_files": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否包含文件详情",
                    }
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行项目概览获取"""
        params = request.parameters
        include_files = params.get("include_files", True)

        try:
            start_time = time.time()

            # 获取项目概览
            overview = self.context_engine.get_project_overview()

            # 如果不需要文件详情，移除文件列表
            if not include_files and "files" in overview:
                file_count = len(overview["files"])
                overview["files"] = f"包含 {file_count} 个文件（详情已隐藏）"

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=0.1,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(overview, metadata)

        except Exception as e:
            self._logger.exception("获取项目概览时发生异常")
            return self._create_error_result(
                "OVERVIEW_ERROR", f"获取项目概览失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ContextTools:
    """上下文引擎工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.data_manager = UnifiedDataManager()

    def create_tools(self) -> List[BaseTool]:
        """创建所有上下文引擎工具"""
        tools_config = self.config.get("context_tools", {})

        return [
            CodeAnalysisTool(tools_config, self.data_manager),
            CodeSearchTool(tools_config, self.data_manager),
            SimilarCodeTool(tools_config, self.data_manager),
            ProjectOverviewTool(tools_config, self.data_manager),
        ]
