"""
ChromaDB 统一数据管理器

所有组件（文件系统、任务管理、上下文引擎、记忆系统、配置管理）共享同一个 ChromaDB 实例和集合，
通过元数据字段区分数据类型，实现真正的统一数据管理。
"""

import json
import os
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

        # 使用现有的目录创建工具确保目录存在
        self._ensure_directory_exists(persist_directory)

        try:
            # 清理可能的锁文件（复用现有逻辑）
            self._cleanup_lock_files(persist_directory)

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
            except Exception:
                # 如果模型下载失败，使用默认嵌入函数
                self.collection = self.client.get_or_create_collection(
                    name="mcp_unified_storage"
                )

        except Exception as init_error:
            # 尝试清理并重新初始化（复用现有逻辑）
            try:
                self._reset_chromadb_data(persist_directory)

                # 重新初始化
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )

                self.collection = self.client.get_or_create_collection(
                    name="mcp_unified_storage"
                )

            except Exception:
                raise Exception(f"ChromaDB初始化失败: {init_error}")

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
        current_time = time.time()
        enhanced_metadata = {
            "data_type": data_type,
            "created_time": current_time,
            "updated_time": current_time,
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
            except Exception:
                raise Exception(f"存储数据失败: {str(e)}")

        return data_id

    def _reinitialize_database(self) -> None:
        """重新初始化数据库（简化版）"""
        try:
            # 重置客户端
            if hasattr(self, "client"):
                try:
                    self.client.reset()
                except Exception:
                    pass  # nosec B110

            # 清理锁文件
            self._cleanup_lock_files(self.persist_directory)

            # 重新创建客户端和集合
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            self.collection = self.client.get_or_create_collection(
                name="mcp_unified_storage"
            )

        except Exception as e:
            raise Exception(f"ChromaDB重新初始化失败: {e}")

    def _ensure_directory_exists(self, directory: str) -> None:
        """确保目录存在并有正确权限（复用现有逻辑）"""
        try:
            # 创建目录
            os.makedirs(directory, exist_ok=True)

            # 设置基本权限
            os.chmod(directory, 0o755)  # nosec B103

            # 简单的写权限测试
            test_file = os.path.join(directory, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception:
                # 如果写入失败，尝试更宽松的权限
                os.chmod(directory, 0o777)  # nosec B103

        except Exception as e:
            raise Exception(f"无法创建或访问ChromaDB目录 {directory}: {e}")

    def _cleanup_lock_files(self, directory: str) -> None:
        """清理ChromaDB锁文件"""
        lock_files = [
            os.path.join(directory, "chroma.sqlite3-wal"),
            os.path.join(directory, "chroma.sqlite3-shm"),
            os.path.join(directory, ".lock"),
        ]

        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass  # 忽略清理失败 # nosec B110

    def _reset_chromadb_data(self, directory: str) -> None:
        """重置ChromaDB数据目录"""
        import shutil

        if os.path.exists(directory):
            shutil.rmtree(directory)
        self._ensure_directory_exists(directory)

    def query_data(
        self,
        query: str,
        data_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 10,
    ) -> Any:
        """统一数据查询接口

        Args:
            query: 查询文本
            data_type: 可选的数据类型过滤
            filters: 可选的元数据过滤条件
            n_results: 返回结果数量

        Returns:
            Dict: 查询结果
        """
        # 构建 ChromaDB 兼容的过滤器
        conditions: List[Dict[str, Any]] = []

        if data_type:
            conditions.append({"data_type": data_type})

        if filters:
            conditions.extend([{k: v} for k, v in filters.items()])

        # 根据条件数量构建 where 子句
        where_clause: Optional[Dict[str, Any]] = None
        if conditions:
            if len(conditions) == 1:
                where_clause = conditions[0]
            else:
                where_clause = {"$and": conditions}

        try:
            return self.collection.query(
                query_texts=[query],
                where=where_clause,
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

    def search_data(
        self,
        query: str,
        data_types: Optional[List[str]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """搜索数据（兼容性方法）

        Args:
            query: 查询文本
            data_types: 数据类型列表
            limit: 返回结果数量限制
            filters: 额外的过滤条件

        Returns:
            List[Dict]: 搜索结果列表
        """
        # 构建过滤条件
        conditions = []

        if data_types:
            if len(data_types) == 1:
                conditions.append({"data_type": data_types[0]})
            else:
                # ChromaDB doesn't support $in operator, we'll handle this differently
                conditions.append(
                    {"data_type": data_types[0]}
                )  # Use first type for now

        if filters:
            conditions.extend([{k: v} for k, v in filters.items()])

        where_clause = None
        if conditions:
            # For ChromaDB, we need to use proper where clause format
            if len(conditions) == 1:
                where_clause = conditions[0]
            else:
                # For multiple conditions, merge them into a single dict
                # This is a simplified approach for ChromaDB compatibility
                merged_conditions = {}
                for condition in conditions:
                    if isinstance(condition, dict):
                        merged_conditions.update(condition)
                where_clause = merged_conditions

        try:
            # Use direct method call instead of **kwargs to avoid type issues
            if where_clause:
                result = self.collection.query(
                    query_texts=[query],
                    where=where_clause,  # type: ignore[arg-type]
                    n_results=limit,
                )
            else:
                result = self.collection.query(
                    query_texts=[query],
                    n_results=limit,
                )

            # 转换为列表格式
            search_results: List[Dict[str, Any]] = []
            if result["documents"] and result["documents"][0]:
                for i in range(len(result["documents"][0])):
                    # 安全访问可能为空的字段
                    id_val = (
                        result["ids"][0][i]
                        if result["ids"] and result["ids"][0]
                        else None
                    )
                    doc_val = (
                        result["documents"][0][i]
                        if result["documents"] and result["documents"][0]
                        else None
                    )
                    meta_val = (
                        result["metadatas"][0][i]
                        if result["metadatas"] and result["metadatas"][0]
                        else None
                    )
                    dist_val = (
                        result["distances"][0][i]
                        if result["distances"] and result["distances"][0]
                        else 0.0
                    )

                    search_results.append(
                        {
                            "id": id_val,
                            "document": doc_val,
                            "metadata": meta_val,
                            "distance": dist_val,
                        }
                    )

            return search_results

        except Exception as e:
            print(f"搜索数据失败: {e}")
            return []

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
