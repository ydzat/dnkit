"""
ChromaDB 统一数据管理器

所有组件（文件系统、任务管理、上下文引擎、记忆系统、配置管理）共享同一个 ChromaDB 实例和集合，
通过元数据字段区分数据类型，实现真正的统一数据管理。
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings


class UnifiedDataManager:
    """ChromaDB 统一数据管理器 - 所有组件的数据访问层"""

    def __init__(self, persist_directory: str = "./mcp_unified_db"):
        """初始化统一数据管理器

        Args:
            persist_directory: ChromaDB 持久化目录
        """
        self.persist_directory = persist_directory

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # 创建或获取统一集合
        try:
            self.collection = self.client.get_or_create_collection(
                name="mcp_unified_storage",
                embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(  # type: ignore
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                ),
            )
        except Exception as e:
            # 如果模型下载失败，使用默认嵌入函数
            self.collection = self.client.get_or_create_collection(
                name="mcp_unified_storage"
            )

    def store_data(
        self,
        data_type: str,
        content: str,
        metadata: Dict[str, Any],
        data_id: Optional[str] = None,
    ) -> str:
        """统一数据存储接口

        Args:
            data_type: 数据类型 (file, task, config, memory, knowledge)
            content: 文档内容
            metadata: 元数据字典
            data_id: 可选的数据ID，如果不提供则自动生成

        Returns:
            str: 数据ID
        """
        if data_id is None:
            data_id = f"{data_type}_{uuid.uuid4()}"

        # 添加通用元数据
        enhanced_metadata = {
            "data_type": data_type,
            "created_time": time.time(),
            "updated_time": time.time(),
            **metadata,
        }

        try:
            self.collection.add(
                documents=[content], metadatas=[enhanced_metadata], ids=[data_id]
            )
        except Exception as e:
            # 如果ID已存在，先删除再添加
            try:
                self.collection.delete(ids=[data_id])
                self.collection.add(
                    documents=[content], metadatas=[enhanced_metadata], ids=[data_id]
                )
            except Exception as inner_e:
                raise Exception(f"存储数据失败: {str(inner_e)}")

        return data_id

    def query_data(
        self,
        query: str,
        data_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 10,
    ) -> Dict[str, Any]:
        """统一数据查询接口

        Args:
            query: 查询文本
            data_type: 可选的数据类型过滤
            filters: 可选的元数据过滤条件
            n_results: 返回结果数量

        Returns:
            Dict: 查询结果
        """
        where_clause = {}

        if data_type:
            where_clause["data_type"] = data_type

        if filters:
            where_clause.update(filters)

        try:
            return self.collection.query(  # type: ignore
                query_texts=[query],
                where=where_clause if where_clause else None,  # type: ignore
                n_results=n_results,
            )
        except Exception as e:
            # 如果查询失败，返回空结果
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

    def get_by_id(self, data_id: str) -> Dict[str, Any]:
        """根据ID获取数据

        Args:
            data_id: 数据ID

        Returns:
            Dict: 数据内容
        """
        try:
            return self.collection.get(  # type: ignore
                ids=[data_id], include=["documents", "metadatas"]
            )
        except Exception:
            return {"ids": [], "documents": [], "metadatas": []}

    def update_data(
        self,
        data_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新数据

        Args:
            data_id: 数据ID
            content: 可选的新内容
            metadata: 可选的新元数据

        Returns:
            bool: 是否更新成功
        """
        try:
            current_data = self.get_by_id(data_id)
            if not current_data["ids"]:
                return False

            new_content = (
                content if content is not None else current_data["documents"][0]
            )

            if metadata:
                current_metadata = current_data["metadatas"][0]
                current_metadata.update(metadata)
                current_metadata["updated_time"] = time.time()
                new_metadata = current_metadata
            else:
                new_metadata = current_data["metadatas"][0]
                new_metadata["updated_time"] = time.time()

            # ChromaDB 需要先删除再添加来更新
            self.collection.delete(ids=[data_id])
            self.collection.add(
                documents=[new_content], metadatas=[new_metadata], ids=[data_id]
            )
            return True
        except Exception:
            return False

    def delete_data(self, data_id: str) -> bool:
        """删除数据

        Args:
            data_id: 数据ID

        Returns:
            bool: 是否删除成功
        """
        try:
            self.collection.delete(ids=[data_id])
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, int]:
        """获取数据统计

        Returns:
            Dict: 各数据类型的统计信息
        """
        try:
            all_data = self.collection.get(include=["metadatas"])
            stats: Dict[str, int] = {}

            metadatas = all_data["metadatas"]
            if metadatas:  # 检查不为 None
                for metadata in metadatas:
                    data_type = metadata.get("data_type", "unknown")
                    if isinstance(data_type, str):
                        stats[data_type] = stats.get(data_type, 0) + 1

            return stats
        except Exception:
            return {}

    def search_by_metadata(
        self, filters: Dict[str, Any], limit: int = 100
    ) -> Dict[str, Any]:
        """根据元数据搜索

        Args:
            filters: 元数据过滤条件
            limit: 结果限制

        Returns:
            Dict: 搜索结果
        """
        try:
            return self.collection.get(  # type: ignore
                where=filters, limit=limit, include=["documents", "metadatas"]
            )
        except Exception:
            return {"ids": [], "documents": [], "metadatas": []}

    def clear_data_type(self, data_type: str) -> bool:
        """清除指定类型的所有数据

        Args:
            data_type: 要清除的数据类型

        Returns:
            bool: 是否清除成功
        """
        try:
            # 获取指定类型的所有数据
            data = self.search_by_metadata({"data_type": data_type})
            if data["ids"]:
                self.collection.delete(ids=data["ids"])
            return True
        except Exception:
            return False

    def reset_database(self) -> bool:
        """重置整个数据库（谨慎使用）

        Returns:
            bool: 是否重置成功
        """
        try:
            self.client.delete_collection("mcp_unified_storage")
            self.collection = self.client.get_or_create_collection(
                name="mcp_unified_storage",
                embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(  # type: ignore
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                ),
            )
            return True
        except Exception:
            return False
