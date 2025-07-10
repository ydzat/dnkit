"""
任务管理工具集

基于 ChromaDB 统一存储的任务管理工具，支持任务的创建、更新、删除、查询和语义搜索。
与其他工具共享同一个 ChromaDB 实例，通过元数据字段区分任务数据。
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..core.types import ConfigDict, ToolCallRequest, ToolCallResponse, ToolDefinition
from ..storage.unified_manager import UnifiedDataManager
from .base import BaseTool, ToolExecutionRequest, ToolExecutionResult


class TaskManagementTools(BaseTool):
    """任务管理工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager: Optional[UnifiedDataManager] = None
        self.auto_store = self.config.get("auto_store_to_chromadb", True)

    def set_data_manager(self, data_manager: UnifiedDataManager) -> None:
        """设置数据管理器"""
        self.data_manager = data_manager

    def _ensure_data_manager(self) -> UnifiedDataManager:
        """确保数据管理器已初始化"""
        if not self.data_manager:
            from .base import ToolError

            raise ToolError("DATA_MANAGER_NOT_INITIALIZED", "数据管理器未初始化")
        return self.data_manager

    def create_tools(self) -> List["BaseTool"]:
        """创建工具实例列表"""
        return [self]

    async def cleanup(self) -> None:
        """清理资源"""
        # 任务管理工具不需要特殊的清理操作
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="manage_tasks",
            description="任务管理工具 - 创建、更新、删除、查询和搜索任务",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete", "get", "list", "search"],
                        "description": "要执行的操作",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "任务ID（用于 update、delete、get 操作）",
                    },
                    "title": {
                        "type": "string",
                        "description": "任务标题（用于 create、update 操作）",
                    },
                    "description": {
                        "type": "string",
                        "description": "任务描述（用于 create、update 操作）",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "NOT_STARTED",
                            "IN_PROGRESS",
                            "COMPLETED",
                            "CANCELLED",
                            "ON_HOLD",
                        ],
                        "default": "NOT_STARTED",
                        "description": "任务状态",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                        "default": "MEDIUM",
                        "description": "任务优先级",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "任务负责人",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "截止日期 (YYYY-MM-DD 格式)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "任务标签",
                    },
                    "query": {
                        "type": "string",
                        "description": "搜索查询（用于 search 操作）",
                    },
                    "filters": {
                        "type": "object",
                        "description": "过滤条件（用于 list、search 操作）",
                        "properties": {
                            "status": {"type": "string"},
                            "priority": {"type": "string"},
                            "assignee": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "返回结果数量限制",
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行任务管理操作"""
        if not self.data_manager:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError("DATA_MANAGER_NOT_INITIALIZED", "数据管理器未初始化"),
            )

        start_time = time.time()
        params = request.parameters

        try:
            action = params["action"]

            if action == "create":
                result = await self._create_task(params)
            elif action == "update":
                result = await self._update_task(params)
            elif action == "delete":
                result = await self._delete_task(params)
            elif action == "get":
                result = await self._get_task(params)
            elif action == "list":
                result = await self._list_tasks(params)
            elif action == "search":
                result = await self._search_tasks(params)
            else:
                return self._create_error_result(
                    "INVALID_ACTION", f"不支持的操作: {action}"
                )

            return ToolExecutionResult(success=True, content=result)

        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError("TASK_MANAGEMENT_ERROR", f"任务管理失败: {str(e)}"),
            )

    async def _create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建新任务"""
        title = params.get("title", "")
        description = params.get("description", "")

        if not title:
            raise ValueError("任务标题不能为空")

        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        current_time = time.time()

        # 构建任务元数据（ChromaDB 只支持基本类型，将标签转换为字符串）
        tags = params.get("tags", [])
        tags_str = ",".join(tags) if tags else ""

        task_metadata = {
            "data_type": "task",
            "task_id": task_id,
            "task_title": title,
            "task_status": params.get("status", "NOT_STARTED"),
            "task_priority": params.get("priority", "MEDIUM"),
            "task_assignee": params.get("assignee", ""),
            "task_due_date": params.get("due_date", ""),
            "task_tags": tags_str,
            "created_time": current_time,
            "updated_time": current_time,
            "content_type": "task_definition",
        }

        # 构建任务内容（用于语义搜索）
        content = f"任务: {title}\n\n描述: {description}"
        if params.get("assignee"):
            content += f"\n负责人: {params['assignee']}"
        if params.get("tags"):
            content += f"\n标签: {', '.join(params['tags'])}"

        # 存储到 ChromaDB
        data_manager = self._ensure_data_manager()
        data_manager.store_data(
            data_type="task",
            content=content,
            metadata=task_metadata,
            data_id=task_id,
        )

        return {
            "task_id": task_id,
            "title": title,
            "description": description,
            "status": task_metadata["task_status"],
            "priority": task_metadata["task_priority"],
            "assignee": task_metadata["task_assignee"],
            "due_date": task_metadata["task_due_date"],
            "tags": tags,  # 返回原始的标签列表
            "created_time": current_time,
            "message": "任务创建成功",
        }

    async def _update_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("任务ID不能为空")

        # 获取现有任务
        data_manager = self._ensure_data_manager()
        existing_data = data_manager.get_by_id(task_id)
        if not existing_data or not existing_data.get("documents"):
            raise ValueError(f"任务不存在: {task_id}")

        # 获取现有元数据
        existing_metadata = existing_data["metadatas"][0]

        # 更新元数据
        updated_metadata = existing_metadata.copy()
        current_time = time.time()
        updated_metadata["updated_time"] = current_time

        # 更新字段
        if "title" in params:
            updated_metadata["task_title"] = params["title"]
        if "status" in params:
            updated_metadata["task_status"] = params["status"]
        if "priority" in params:
            updated_metadata["task_priority"] = params["priority"]
        if "assignee" in params:
            updated_metadata["task_assignee"] = params["assignee"]
        if "due_date" in params:
            updated_metadata["task_due_date"] = params["due_date"]
        if "tags" in params:
            updated_metadata["task_tags"] = self._tags_to_string(params["tags"])

        # 重新构建内容
        title = updated_metadata["task_title"]
        description = params.get(
            "description",
            (
                existing_data["documents"][0].split("\n\n描述: ")[1].split("\n")[0]
                if "\n\n描述: " in existing_data["documents"][0]
                else ""
            ),
        )

        content = f"任务: {title}\n\n描述: {description}"
        if updated_metadata.get("task_assignee"):
            content += f"\n负责人: {updated_metadata['task_assignee']}"
        if updated_metadata.get("task_tags"):
            content += f"\n标签: {', '.join(updated_metadata['task_tags'])}"

        # 更新存储
        data_manager.store_data(
            data_type="task",
            content=content,
            metadata=updated_metadata,
            data_id=task_id,
        )

        return {
            "task_id": task_id,
            "title": updated_metadata["task_title"],
            "status": updated_metadata["task_status"],
            "priority": updated_metadata["task_priority"],
            "assignee": updated_metadata["task_assignee"],
            "due_date": updated_metadata["task_due_date"],
            "tags": self._tags_from_string(updated_metadata["task_tags"]),
            "updated_time": current_time,
            "message": "任务更新成功",
        }

    async def _delete_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("任务ID不能为空")

        # 检查任务是否存在
        data_manager = self._ensure_data_manager()
        existing_data = data_manager.get_by_id(task_id)
        if not existing_data or not existing_data.get("documents"):
            raise ValueError(f"任务不存在: {task_id}")

        # 删除任务
        success = data_manager.delete_data(task_id)
        if not success:
            raise ValueError(f"删除任务失败: {task_id}")

        return {
            "task_id": task_id,
            "message": "任务删除成功",
        }

    async def _get_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取单个任务"""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("任务ID不能为空")

        # 获取任务数据
        data_manager = self._ensure_data_manager()
        task_data = data_manager.get_by_id(task_id)
        if not task_data or not task_data.get("documents"):
            raise ValueError(f"任务不存在: {task_id}")

        metadata = task_data["metadatas"][0]
        content = task_data["documents"][0]

        return {
            "task_id": task_id,
            "title": metadata.get("task_title", ""),
            "description": self._extract_description_from_content(content),
            "status": metadata.get("task_status", "NOT_STARTED"),
            "priority": metadata.get("task_priority", "MEDIUM"),
            "assignee": metadata.get("task_assignee", ""),
            "due_date": metadata.get("task_due_date", ""),
            "tags": self._tags_from_string(metadata.get("task_tags", "")),
            "created_time": metadata.get("created_time", 0),
            "updated_time": metadata.get("updated_time", 0),
        }

    def _extract_description_from_content(self, content: str) -> str:
        """从内容中提取描述"""
        if "\n\n描述: " in content:
            parts = content.split("\n\n描述: ")[1].split("\n")
            return parts[0] if parts else ""
        return ""

    def _tags_to_string(self, tags: list) -> str:
        """将标签列表转换为字符串"""
        return ",".join(tags) if tags else ""

    def _tags_from_string(self, tags_str: str) -> list:
        """将标签字符串转换为列表"""
        return (
            [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            if tags_str
            else []
        )

    async def _list_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出任务"""
        filters = params.get("filters", {})
        limit = params.get("limit", 20)

        # 从参数中直接获取过滤条件（兼容 n8n 的调用方式）
        status = params.get("status")
        priority = params.get("priority")
        assignee = params.get("assignee")
        tags = params.get("tags")

        # 构建 ChromaDB 查询过滤器
        where_clause = {"data_type": "task"}

        # 添加 filters 对象中的过滤条件
        if filters.get("status"):
            where_clause["task_status"] = filters["status"]
        if filters.get("priority"):
            where_clause["task_priority"] = filters["priority"]
        if filters.get("assignee"):
            where_clause["task_assignee"] = filters["assignee"]

        # 添加直接参数的过滤条件（优先级更高）
        if status:
            where_clause["task_status"] = status
        if priority:
            where_clause["task_priority"] = priority
        if assignee:
            where_clause["task_assignee"] = assignee

        # 查询任务
        data_manager = self._ensure_data_manager()
        results = data_manager.query_data(
            query="任务",  # 基础查询
            filters=where_clause,
            n_results=limit,
        )

        tasks = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            for i, metadata in enumerate(results["metadatas"][0]):
                content = (
                    results["documents"][0][i]
                    if results.get("documents")
                    and results["documents"][0]
                    and i < len(results["documents"][0])
                    else ""
                )

                # 标签过滤（需要在应用层处理，因为 ChromaDB 不支持数组查询）
                filter_tags = filters.get("tags") or tags
                if filter_tags:
                    task_tags_str = metadata.get("task_tags", "")
                    task_tags = self._tags_from_string(task_tags_str)
                    if not any(tag in task_tags for tag in filter_tags):
                        continue

                task = {
                    "task_id": metadata.get("task_id", ""),
                    "title": metadata.get("task_title", ""),
                    "description": self._extract_description_from_content(content),
                    "status": metadata.get("task_status", "NOT_STARTED"),
                    "priority": metadata.get("task_priority", "MEDIUM"),
                    "assignee": metadata.get("task_assignee", ""),
                    "due_date": metadata.get("task_due_date", ""),
                    "tags": self._tags_from_string(metadata.get("task_tags", "")),
                    "created_time": metadata.get("created_time", 0),
                    "updated_time": metadata.get("updated_time", 0),
                }
                tasks.append(task)

        # 构建应用的过滤器信息（用于返回结果）
        applied_filters = {}
        if status:
            applied_filters["status"] = status
        if priority:
            applied_filters["priority"] = priority
        if assignee:
            applied_filters["assignee"] = assignee
        if tags:
            applied_filters["tags"] = tags
        if filters:
            applied_filters.update(filters)

        return {
            "tasks": tasks,
            "total_count": len(tasks),
            "filters_applied": applied_filters,
            "message": f"找到 {len(tasks)} 个任务",
        }

    async def _search_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索任务 - 支持语义搜索和过滤查询"""
        query = params.get("query", "")
        filters = params.get("filters", {})
        limit = params.get("limit", 20)

        # 从参数中直接获取过滤条件（兼容 n8n 的调用方式）
        status = params.get("status")
        priority = params.get("priority")
        assignee = params.get("assignee")
        tags = params.get("tags")

        # 智能搜索逻辑：分析查询意图
        is_general_search = not query or query.strip() == ""
        has_explicit_filters = bool(filters) or bool(assignee) or bool(tags)

        # 从参数中获取搜索模式
        search_mode = params.get(
            "search_mode", "default"
        )  # default, recent, oldest, relevant
        sort_by = params.get(
            "sort_by", "relevance"
        )  # relevance, created_time, updated_time, priority
        sort_order = params.get("sort_order", "desc")  # asc, desc

        # 根据搜索模式调整行为
        if search_mode == "recent":
            sort_by = "created_time"
            sort_order = "desc"
            limit = min(limit, 5)  # 最近搜索限制结果数量
        elif search_mode == "oldest":
            sort_by = "created_time"
            sort_order = "asc"
            limit = min(limit, 5)

        # 构建 ChromaDB 查询过滤器
        where_clause = {"data_type": "task"}

        # 只有在明确指定过滤条件或非通用搜索时才应用过滤器
        # 但时间相关搜索模式除外（时间搜索忽略默认过滤器）
        if (not is_general_search or has_explicit_filters) and search_mode == "default":
            # 添加 filters 对象中的过滤条件
            if filters.get("status"):
                where_clause["task_status"] = filters["status"]
            if filters.get("priority"):
                where_clause["task_priority"] = filters["priority"]
            if filters.get("assignee"):
                where_clause["task_assignee"] = filters["assignee"]

            # 添加直接参数的过滤条件（优先级更高）
            if status:
                where_clause["task_status"] = status
            if priority:
                where_clause["task_priority"] = priority
            if assignee:
                where_clause["task_assignee"] = assignee

        # 如果没有查询文本，使用通用查询进行过滤
        if not query:
            query = "任务"  # 使用通用查询词

        # 构建应用的过滤器信息（用于返回结果）
        applied_filters = {}
        applied_filters["search_mode"] = search_mode
        applied_filters["sort_by"] = sort_by
        applied_filters["sort_order"] = sort_order

        if search_mode in ["recent", "oldest"]:
            applied_filters["note"] = f"{search_mode} 搜索模式，忽略默认过滤器"
        elif not is_general_search or has_explicit_filters:
            if status:
                applied_filters["status"] = status
            if priority:
                applied_filters["priority"] = priority
            if assignee:
                applied_filters["assignee"] = assignee
            if tags:
                applied_filters["tags"] = tags
            if filters:
                applied_filters.update(filters)
        else:
            applied_filters["note"] = "通用搜索，忽略默认过滤器"

        # 执行搜索
        data_manager = self._ensure_data_manager()
        results = data_manager.query_data(
            query=query,
            filters=where_clause,
            n_results=limit,
        )

        tasks = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            for i, metadata in enumerate(results["metadatas"][0]):
                content = (
                    results["documents"][0][i]
                    if results.get("documents")
                    and results["documents"][0]
                    and i < len(results["documents"][0])
                    else ""
                )
                distance = (
                    results["distances"][0][i]
                    if results.get("distances")
                    and results["distances"][0]
                    and i < len(results["distances"][0])
                    else 0.0
                )

                # 标签过滤
                if filters.get("tags"):
                    task_tags_str = metadata.get("task_tags", "")
                    task_tags = self._tags_from_string(task_tags_str)
                    if not any(tag in task_tags for tag in filters["tags"]):
                        continue

                task = {
                    "task_id": metadata.get("task_id", ""),
                    "title": metadata.get("task_title", ""),
                    "description": self._extract_description_from_content(content),
                    "status": metadata.get("task_status", "NOT_STARTED"),
                    "priority": metadata.get("task_priority", "MEDIUM"),
                    "assignee": metadata.get("task_assignee", ""),
                    "due_date": metadata.get("task_due_date", ""),
                    "tags": self._tags_from_string(metadata.get("task_tags", "")),
                    "created_time": metadata.get("created_time", 0),
                    "updated_time": metadata.get("updated_time", 0),
                    "relevance_score": 1.0 - distance,  # 转换为相关性分数
                }
                tasks.append(task)

        # 如果是时间相关查询，按创建时间排序（最新的在前）
        is_time_based_query = search_mode in ["recent", "oldest"]
        if is_time_based_query and tasks:
            tasks.sort(key=lambda x: x.get("created_time", 0), reverse=True)
            applied_filters["note"] = f"时间相关搜索，按创建时间排序，限制{limit}个结果"

        return {
            "tasks": tasks,
            "total_count": len(tasks),
            "query": query,
            "filters_applied": applied_filters,
            "message": f"搜索到 {len(tasks)} 个相关任务",
        }


class SearchRecentTasksTool(BaseTool):
    """搜索最近创建的任务工具"""

    def __init__(self, data_manager: UnifiedDataManager):
        super().__init__()
        self.data_manager = data_manager

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_recent_tasks",
            description="搜索最近创建的任务 - 按创建时间排序，返回最新的任务",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                        "description": "返回结果数量限制",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "NOT_STARTED",
                            "IN_PROGRESS",
                            "COMPLETED",
                            "CANCELLED",
                            "ON_HOLD",
                        ],
                        "description": "任务状态过滤（可选）",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                        "description": "任务优先级过滤（可选）",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "任务负责人过滤（可选）",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行搜索最近任务"""
        try:
            params = request.parameters
            limit = params.get("limit", 5)
            status = params.get("status")
            priority = params.get("priority")
            assignee = params.get("assignee")

            # 构建过滤器
            where_clause = {"data_type": "task"}
            if status:
                where_clause["task_status"] = status
            if priority:
                where_clause["task_priority"] = priority
            if assignee:
                where_clause["task_assignee"] = assignee

            # 搜索所有任务
            results = self.data_manager.query_data(
                query="任务",
                filters=where_clause,
                n_results=100,  # 先获取更多结果用于排序
            )

            tasks = []
            if results and results.get("metadatas") and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    content = (
                        results["documents"][0][i]
                        if results.get("documents")
                        and results["documents"][0]
                        and i < len(results["documents"][0])
                        else ""
                    )

                    task = {
                        "task_id": metadata.get("task_id", ""),
                        "title": metadata.get("task_title", ""),
                        "description": content.split("\n")[0] if content else "",
                        "status": metadata.get("task_status", "NOT_STARTED"),
                        "priority": metadata.get("task_priority", "MEDIUM"),
                        "assignee": metadata.get("task_assignee", ""),
                        "due_date": metadata.get("task_due_date", ""),
                        "tags": (
                            metadata.get("task_tags", "").split(",")
                            if metadata.get("task_tags")
                            else []
                        ),
                        "created_time": metadata.get("created_time", 0),
                        "updated_time": metadata.get("updated_time", 0),
                    }
                    tasks.append(task)

            # 按创建时间排序（最新的在前）
            tasks.sort(key=lambda x: x.get("created_time", 0), reverse=True)

            # 限制结果数量
            tasks = tasks[:limit]

            applied_filters = {
                "search_type": "recent",
                "sort_by": "created_time",
                "sort_order": "desc",
            }
            if status:
                applied_filters["status"] = status
            if priority:
                applied_filters["priority"] = priority
            if assignee:
                applied_filters["assignee"] = assignee

            return ToolExecutionResult(
                success=True,
                content={
                    "tasks": tasks,
                    "total_count": len(tasks),
                    "filters_applied": applied_filters,
                    "message": f"找到 {len(tasks)} 个最近创建的任务",
                },
            )

        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    "SEARCH_RECENT_TASKS_ERROR", f"搜索最近任务失败: {str(e)}"
                ),
            )


class SearchTasksByTimeTool(BaseTool):
    """按时间范围搜索任务工具"""

    def __init__(self, data_manager: UnifiedDataManager):
        super().__init__()
        self.data_manager = data_manager

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_tasks_by_time",
            description="按时间范围搜索任务 - 支持指定时间范围和排序方式",
            parameters={
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "enum": [
                            "last_hour",
                            "last_day",
                            "last_week",
                            "last_month",
                            "custom",
                        ],
                        "default": "last_day",
                        "description": "时间范围",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "自定义开始时间 (ISO格式，仅当 time_range=custom 时使用)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "自定义结束时间 (ISO格式，仅当 time_range=custom 时使用)",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["newest_first", "oldest_first"],
                        "default": "newest_first",
                        "description": "排序方式",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "返回结果数量限制",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行按时间范围搜索"""
        try:
            params = request.parameters
            time_range = params.get("time_range", "last_day")
            sort_order = params.get("sort_order", "newest_first")
            limit = params.get("limit", 10)

            # 计算时间范围
            now = time.time()
            if time_range == "last_hour":
                start_time = now - 3600
            elif time_range == "last_day":
                start_time = now - 86400
            elif time_range == "last_week":
                start_time = now - 604800
            elif time_range == "last_month":
                start_time = now - 2592000
            elif time_range == "custom":
                start_time_str = params.get("start_time")
                end_time_str = params.get("end_time")
                if start_time_str:
                    start_time = datetime.fromisoformat(
                        start_time_str.replace("Z", "+00:00")
                    ).timestamp()
                else:
                    start_time = 0
                if end_time_str:
                    end_time = datetime.fromisoformat(
                        end_time_str.replace("Z", "+00:00")
                    ).timestamp()
                else:
                    end_time = now
            else:
                start_time = 0
                end_time = now

            # 搜索所有任务
            results = self.data_manager.query_data(
                query="任务",
                filters={"data_type": "task"},
                n_results=200,  # 获取更多结果用于时间过滤
            )

            tasks = []
            if results and results.get("metadatas") and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    created_time = metadata.get("created_time", 0)

                    # 时间范围过滤
                    if time_range == "custom":
                        if not (start_time <= created_time <= end_time):
                            continue
                    else:
                        if created_time < start_time:
                            continue

                    content = (
                        results["documents"][0][i]
                        if results.get("documents")
                        and results["documents"][0]
                        and i < len(results["documents"][0])
                        else ""
                    )

                    task = {
                        "task_id": metadata.get("task_id", ""),
                        "title": metadata.get("task_title", ""),
                        "description": content.split("\n")[0] if content else "",
                        "status": metadata.get("task_status", "NOT_STARTED"),
                        "priority": metadata.get("task_priority", "MEDIUM"),
                        "assignee": metadata.get("task_assignee", ""),
                        "due_date": metadata.get("task_due_date", ""),
                        "tags": (
                            metadata.get("task_tags", "").split(",")
                            if metadata.get("task_tags")
                            else []
                        ),
                        "created_time": created_time,
                        "updated_time": metadata.get("updated_time", 0),
                    }
                    tasks.append(task)

            # 排序
            reverse_order = sort_order == "newest_first"
            tasks.sort(key=lambda x: x.get("created_time", 0), reverse=reverse_order)

            # 限制结果数量
            tasks = tasks[:limit]

            return ToolExecutionResult(
                success=True,
                content={
                    "tasks": tasks,
                    "total_count": len(tasks),
                    "time_range": time_range,
                    "sort_order": sort_order,
                    "message": f"在 {time_range} 时间范围内找到 {len(tasks)} 个任务",
                },
            )

        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    "SEARCH_TASKS_BY_TIME_ERROR", f"按时间搜索任务失败: {str(e)}"
                ),
            )


class SearchTasksSemanticTool(BaseTool):
    """语义搜索任务工具"""

    def __init__(self, data_manager: UnifiedDataManager):
        super().__init__()
        self.data_manager = data_manager

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_tasks_semantic",
            description="语义搜索任务 - 基于内容相似性搜索，支持自然语言查询",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询文本（支持自然语言）",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "NOT_STARTED",
                            "IN_PROGRESS",
                            "COMPLETED",
                            "CANCELLED",
                            "ON_HOLD",
                        ],
                        "description": "任务状态过滤（可选）",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                        "description": "任务优先级过滤（可选）",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "任务负责人过滤（可选）",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "任务标签过滤（可选）",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                        "description": "返回结果数量限制",
                    },
                    "min_relevance": {
                        "type": "number",
                        "default": 0.0,
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "最小相关性分数阈值",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行语义搜索"""
        try:
            params = request.parameters
            query = params.get("query", "")
            status = params.get("status")
            priority = params.get("priority")
            assignee = params.get("assignee")
            tags = params.get("tags", [])
            limit = params.get("limit", 10)
            min_relevance = params.get("min_relevance", 0.0)

            if not query:
                from .base import ToolError

                return ToolExecutionResult(
                    success=False, error=ToolError("EMPTY_QUERY", "搜索查询不能为空")
                )

            # 构建过滤器
            where_clause = {"data_type": "task"}
            if status:
                where_clause["task_status"] = status
            if priority:
                where_clause["task_priority"] = priority
            if assignee:
                where_clause["task_assignee"] = assignee

            # 执行语义搜索
            results = self.data_manager.query_data(
                query=query,
                filters=where_clause,
                n_results=limit * 2,  # 获取更多结果用于过滤
            )

            tasks = []
            if results and results.get("metadatas") and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    distance = (
                        results["distances"][0][i]
                        if results.get("distances")
                        and results["distances"][0]
                        and i < len(results["distances"][0])
                        else 0.0
                    )
                    relevance_score = 1.0 - distance

                    # 相关性过滤
                    if relevance_score < min_relevance:
                        continue

                    # 标签过滤
                    if tags:
                        task_tags_str = metadata.get("task_tags", "")
                        task_tags = (
                            [
                                tag.strip()
                                for tag in task_tags_str.split(",")
                                if tag.strip()
                            ]
                            if task_tags_str
                            else []
                        )
                        if not any(tag in task_tags for tag in tags):
                            continue

                    content = (
                        results["documents"][0][i]
                        if results.get("documents")
                        and results["documents"][0]
                        and i < len(results["documents"][0])
                        else ""
                    )

                    task = {
                        "task_id": metadata.get("task_id", ""),
                        "title": metadata.get("task_title", ""),
                        "description": content.split("\n")[0] if content else "",
                        "status": metadata.get("task_status", "NOT_STARTED"),
                        "priority": metadata.get("task_priority", "MEDIUM"),
                        "assignee": metadata.get("task_assignee", ""),
                        "due_date": metadata.get("task_due_date", ""),
                        "tags": [
                            tag.strip()
                            for tag in metadata.get("task_tags", "").split(",")
                            if tag.strip()
                        ],
                        "created_time": metadata.get("created_time", 0),
                        "updated_time": metadata.get("updated_time", 0),
                        "relevance_score": relevance_score,
                    }
                    tasks.append(task)

            # 限制结果数量
            tasks = tasks[:limit]

            applied_filters = {"search_type": "semantic", "query": query}
            if status:
                applied_filters["status"] = status
            if priority:
                applied_filters["priority"] = priority
            if assignee:
                applied_filters["assignee"] = assignee
            if tags:
                applied_filters["tags"] = tags
            if min_relevance > 0:
                applied_filters["min_relevance"] = min_relevance

            return ToolExecutionResult(
                success=True,
                content={
                    "tasks": tasks,
                    "total_count": len(tasks),
                    "query": query,
                    "filters_applied": applied_filters,
                    "message": f"语义搜索找到 {len(tasks)} 个相关任务",
                },
            )

        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    "SEMANTIC_SEARCH_TASKS_ERROR", f"语义搜索任务失败: {str(e)}"
                ),
            )


def create_task_tools(data_manager: UnifiedDataManager) -> List[BaseTool]:
    """创建任务管理相关的所有工具"""
    # 创建主任务管理工具
    task_management_tool = TaskManagementTools()
    task_management_tool.set_data_manager(data_manager)

    return [
        task_management_tool,
        SearchRecentTasksTool(data_manager),
        SearchTasksByTimeTool(data_manager),
        SearchTasksSemanticTool(data_manager),
    ]
