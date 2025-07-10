"""
记忆管理工具集

基于 ChromaDB 统一存储的记忆系统，支持对话历史、知识积累、经验记录等多种记忆类型。
与上下文引擎、任务管理等组件共享同一个 ChromaDB 实例。
"""

import json
import time
import uuid
from datetime import datetime, timedelta
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
)


class MemoryManagementTools(BaseTool):
    """记忆管理工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager: Optional[UnifiedDataManager] = None
        self.memory_types = {
            "conversation": "对话记忆",
            "knowledge": "知识记忆",
            "experience": "经验记忆",
            "working": "工作记忆",
        }
        self.importance_thresholds = {
            "conversation": 0.5,
            "knowledge": 0.7,
            "experience": 0.6,
            "working": 0.3,
        }

    def set_data_manager(self, data_manager: UnifiedDataManager) -> None:
        """设置数据管理器"""
        self.data_manager = data_manager

    def _ensure_data_manager(self) -> UnifiedDataManager:
        """确保数据管理器已初始化"""
        if not self.data_manager:
            from .base import ToolError

            raise ToolError("DATA_MANAGER_NOT_INITIALIZED", "数据管理器未初始化")
        return self.data_manager

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="manage_memory",
            description="记忆管理工具 - 支持存储、检索、更新和删除各种类型的记忆",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "store",
                            "retrieve",
                            "update",
                            "delete",
                            "search",
                            "list",
                        ],
                        "description": "操作类型",
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": list(self.memory_types.keys()),
                        "description": "记忆类型",
                    },
                    "memory_id": {
                        "type": "string",
                        "description": "记忆ID（用于更新、删除、获取特定记忆）",
                    },
                    "content": {
                        "type": "string",
                        "description": "记忆内容",
                    },
                    "title": {
                        "type": "string",
                        "description": "记忆标题",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "记忆标签",
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "重要性分数（0-1）",
                    },
                    "query": {
                        "type": "string",
                        "description": "搜索查询（用于搜索和检索）",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "返回结果数量限制",
                    },
                    "filters": {
                        "type": "object",
                        "description": "过滤条件（JSON格式）",
                    },
                },
                "required": ["action"],
            },
        )

    def create_tools(self) -> List["BaseTool"]:
        """创建工具实例列表"""
        return [self]

    async def cleanup(self) -> None:
        """清理资源"""
        # 记忆管理工具不需要特殊的清理操作
        pass

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行记忆管理操作"""
        start_time = time.time()
        params = request.parameters

        try:
            if not self.data_manager:
                return self._create_error_result(
                    "NO_DATA_MANAGER", "数据管理器未设置，无法执行记忆操作"
                )

            action = params["action"]

            if action == "store":
                result = await self._store_memory(params)
            elif action == "retrieve":
                result = await self._retrieve_memory(params)
            elif action == "update":
                result = await self._update_memory(params)
            elif action == "delete":
                result = await self._delete_memory(params)
            elif action == "search":
                query = params.get("query", "")
                memory_type = params.get("memory_type")
                limit = params.get("limit", 10)
                result = await self._search_memories(query, memory_type, limit)
            elif action == "list":
                result = await self._list_memories(params)
            else:
                return self._create_error_result(
                    "INVALID_ACTION", f"不支持的操作类型: {action}"
                )

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=len(str(result)) / 1024,  # KB
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(result)) / 1024 / 1024,  # MB
                cpu_time_ms=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(result, metadata, resources)

        except Exception as e:
            self._logger.exception("记忆管理操作时发生异常")
            return self._create_error_result(
                "MEMORY_MANAGEMENT_ERROR", f"记忆管理失败: {str(e)}"
            )

    async def _store_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """存储记忆"""
        memory_type = params.get("memory_type", "working")
        content = params.get("content", "")
        title = params.get("title", "")
        tags = params.get("tags", [])
        importance = params.get("importance")

        if not content:
            raise ValueError("记忆内容不能为空")

        # 生成记忆ID
        memory_id = str(uuid.uuid4())
        current_time = time.time()

        # 如果没有指定重要性，使用默认阈值
        if importance is None:
            importance = self.importance_thresholds.get(memory_type, 0.5)

        # 构建记忆元数据
        memory_metadata = {
            "data_type": "memory",
            "memory_type": memory_type,
            "memory_id": memory_id,
            "memory_title": title,
            "importance_score": importance,
            "access_count": 0,
            "created_time": current_time,
            "last_accessed": current_time,
            "tags": self._tags_to_string(tags),
            "content_type": "memory_record",
        }

        # 构建记忆内容
        memory_content = f"标题: {title}\n\n内容: {content}"
        if tags:
            memory_content += f"\n\n标签: {', '.join(tags)}"

        # 存储记忆
        data_manager = self._ensure_data_manager()
        data_manager.store_data(
            data_type="memory",
            content=memory_content,
            metadata=memory_metadata,
            data_id=memory_id,
        )

        return {
            "memory_id": memory_id,
            "memory_type": memory_type,
            "title": title,
            "content": content,
            "importance": importance,
            "tags": tags,
            "created_time": current_time,
            "message": "记忆存储成功",
        }

    async def _retrieve_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """检索记忆 - 支持通过ID检索特定记忆或通过查询搜索记忆"""
        memory_id = params.get("memory_id")
        query = params.get("query")
        memory_type = params.get("memory_type")
        limit = params.get("limit", 10)

        # 模式1：通过memory_id检索特定记忆
        if memory_id:
            return await self._retrieve_memory_by_id(memory_id)

        # 模式2：通过query搜索记忆
        elif query:
            return await self._search_memories(query, memory_type, limit)

        else:
            raise ValueError("必须提供 memory_id 或 query 参数")

    async def _retrieve_memory_by_id(self, memory_id: str) -> Dict[str, Any]:
        """通过ID检索特定记忆"""
        # 查询记忆
        data_manager = self._ensure_data_manager()
        results = data_manager.query_data(
            query="记忆",
            filters={"memory_id": memory_id},
            n_results=1,
        )

        if not results or not results.get("metadatas"):
            raise ValueError(f"未找到记忆ID为 {memory_id} 的记忆")

        metadata = results["metadatas"][0]
        content = results["documents"][0] if results.get("documents") else ""

        # 更新访问计数和时间
        updated_metadata = metadata.copy()
        updated_metadata["access_count"] = metadata.get("access_count", 0) + 1
        updated_metadata["last_accessed"] = time.time()

        # 更新记忆
        data_manager.update_data(
            data_id=memory_id,
            metadata=updated_metadata,
        )

        return {
            "memory_id": memory_id,
            "memory_type": metadata.get("memory_type", ""),
            "title": metadata.get("memory_title", ""),
            "content": self._extract_content_from_memory(content),
            "importance": metadata.get("importance_score", 0.0),
            "tags": self._tags_from_string(metadata.get("tags", "")),
            "access_count": updated_metadata["access_count"],
            "created_time": metadata.get("created_time", 0),
            "last_accessed": updated_metadata["last_accessed"],
        }

    async def _search_memories(
        self, query: str, memory_type: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """通过查询搜索记忆"""
        # 构建过滤条件
        filters = {}
        if memory_type:
            filters["memory_type"] = memory_type

        # 执行搜索
        data_manager = self._ensure_data_manager()
        results = data_manager.query_data(
            query=query,
            filters=filters,
            n_results=limit,
        )

        if not results or not results.get("metadatas"):
            return {
                "memories": [],
                "total_count": 0,
                "query": query,
                "memory_type": memory_type,
                "message": "未找到匹配的记忆",
            }

        # 处理搜索结果
        memories = []
        metadatas = results["metadatas"]
        documents = results.get("documents", [])
        distances = results.get("distances", [])

        # ChromaDB 返回的是嵌套列表结构
        if metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]
        if documents and isinstance(documents[0], list):
            documents = documents[0]
        if distances and isinstance(distances[0], list):
            distances = distances[0]

        for i, metadata in enumerate(metadatas):
            content = documents[i] if i < len(documents) else ""

            # 处理距离值（可能是嵌套列表）
            distance = 0.0
            if distances and i < len(distances):
                dist_val = distances[i]
                if isinstance(dist_val, list) and dist_val:
                    distance = dist_val[0]  # 取第一个值
                elif isinstance(dist_val, (int, float)):
                    distance = float(dist_val)

            relevance_score = max(0.0, 1.0 - distance)  # 转换为相关性分数

            memory = {
                "memory_id": metadata.get("memory_id", ""),
                "memory_type": metadata.get("memory_type", ""),
                "title": metadata.get("memory_title", ""),
                "content": self._extract_content_from_memory(content),
                "importance": metadata.get("importance_score", 0.0),
                "tags": self._tags_from_string(metadata.get("tags", "")),
                "access_count": metadata.get("access_count", 0),
                "created_time": metadata.get("created_time", 0),
                "last_accessed": metadata.get("last_accessed", 0),
                "relevance_score": relevance_score,
            }
            memories.append(memory)

        return {
            "memories": memories,
            "total_count": len(memories),
            "query": query,
            "memory_type": memory_type,
            "message": f"找到 {len(memories)} 个相关记忆",
        }

    async def _update_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """更新记忆"""
        memory_id = params.get("memory_id")

        if not memory_id:
            raise ValueError("记忆ID不能为空")

        # 先获取现有记忆
        data_manager = self._ensure_data_manager()
        results = data_manager.query_data(
            query="记忆",
            filters={"memory_id": memory_id},
            n_results=1,
        )

        if not results or not results.get("metadatas"):
            raise ValueError(f"未找到记忆ID为 {memory_id} 的记忆")

        existing_metadata = results["metadatas"][0]
        existing_content = results["documents"][0] if results.get("documents") else ""

        # 更新元数据
        updated_metadata = existing_metadata.copy()
        current_time = time.time()
        updated_metadata["last_accessed"] = current_time

        # 更新可修改的字段
        if "title" in params:
            updated_metadata["memory_title"] = params["title"]
        if "importance" in params:
            updated_metadata["importance_score"] = params["importance"]
        if "tags" in params:
            updated_metadata["tags"] = self._tags_to_string(params["tags"])

        # 更新内容
        new_content = existing_content
        if "content" in params:
            title = updated_metadata.get("memory_title", "")
            content = params["content"]
            tags = self._tags_from_string(updated_metadata.get("tags", ""))

            new_content = f"标题: {title}\n\n内容: {content}"
            if tags:
                new_content += f"\n\n标签: {', '.join(tags)}"

        # 更新记忆
        data_manager.update_data(
            data_id=memory_id,
            content=new_content,
            metadata=updated_metadata,
        )

        return {
            "memory_id": memory_id,
            "memory_type": updated_metadata.get("memory_type", ""),
            "title": updated_metadata.get("memory_title", ""),
            "content": self._extract_content_from_memory(new_content),
            "importance": updated_metadata.get("importance_score", 0.0),
            "tags": self._tags_from_string(updated_metadata.get("tags", "")),
            "updated_time": current_time,
            "message": "记忆更新成功",
        }

    async def _delete_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除记忆"""
        memory_id = params.get("memory_id")

        if not memory_id:
            raise ValueError("记忆ID不能为空")

        # 删除记忆
        data_manager = self._ensure_data_manager()
        data_manager.delete_data(data_id=memory_id)

        return {
            "memory_id": memory_id,
            "message": "记忆删除成功",
        }

    async def _list_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出记忆"""
        memory_type = params.get("memory_type")
        limit = params.get("limit", 10)
        filters = params.get("filters", {})

        # 构建查询条件
        where_clause = {"data_type": "memory"}
        if memory_type:
            where_clause["memory_type"] = memory_type

        # 添加其他过滤条件
        where_clause.update(filters)

        # 查询记忆
        data_manager = self._ensure_data_manager()
        results = data_manager.query_data(
            query="记忆",  # 基础查询
            filters=where_clause,
            n_results=limit,
        )

        memories = []
        if results and results.get("metadatas") and results["metadatas"][0]:
            for i, metadata in enumerate(results["metadatas"][0]):
                content = (
                    results["documents"][0][i]
                    if results.get("documents")
                    and results["documents"][0]
                    and i < len(results["documents"][0])
                    else ""
                )

                memory = {
                    "memory_id": metadata.get("memory_id", ""),
                    "memory_type": metadata.get("memory_type", ""),
                    "title": metadata.get("memory_title", ""),
                    "content": self._extract_content_from_memory(content),
                    "importance": metadata.get("importance_score", 0.0),
                    "tags": self._tags_from_string(metadata.get("tags", "")),
                    "access_count": metadata.get("access_count", 0),
                    "created_time": metadata.get("created_time", 0),
                    "last_accessed": metadata.get("last_accessed", 0),
                }
                memories.append(memory)

        return {
            "memories": memories,
            "total_count": len(memories),
            "memory_type": memory_type,
            "filters_applied": where_clause,
            "message": f"找到 {len(memories)} 个记忆",
        }

    def _extract_content_from_memory(self, content: str) -> str:
        """从记忆内容中提取主要内容"""
        if "\n\n内容: " in content:
            parts = content.split("\n\n内容: ")[1].split("\n")
            return parts[0] if parts else ""
        return content

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
