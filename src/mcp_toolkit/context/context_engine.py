"""
上下文引擎

基于 ChromaDB 统一存储的智能上下文引擎，提供代码分析、语义搜索、上下文聚合等功能。
作为整个系统的核心智能组件，连接所有数据源和查询需求。
"""

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.types import ConfigDict
from ..storage.unified_manager import UnifiedDataManager
from .code_analyzer import CodeAnalyzer
from .query_processor import QueryProcessor


class ContextEngine:
    """上下文引擎 - 系统核心智能组件"""

    def __init__(
        self, data_manager: UnifiedDataManager, config: Optional[ConfigDict] = None
    ):
        self.data_manager = data_manager
        self.config = config or {}

        # 初始化子组件
        self.code_analyzer = CodeAnalyzer(self.config.get("code_analyzer", {}))
        self.query_processor = QueryProcessor(
            self.data_manager, self.config.get("query_processor", {})
        )

        # 配置参数
        self.chunk_size = self.config.get("chunk_size", 1000)
        self.chunk_overlap = self.config.get("chunk_overlap", 100)
        self.max_file_size = self.config.get("max_file_size_mb", 10) * 1024 * 1024

    def analyze_and_store_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """分析文件并存储到 ChromaDB"""
        try:
            # 代码分析
            analysis = self.code_analyzer.analyze_file(file_path, content)

            # 存储结果
            storage_results = []

            # 存储整个文件
            file_id = self._store_file_content(file_path, content, analysis)
            storage_results.append({"type": "file", "id": file_id})

            # 存储代码块
            for chunk in analysis.get("code_chunks", []):
                chunk_id = self._store_code_chunk(file_path, chunk, analysis)
                storage_results.append({"type": "chunk", "id": chunk_id})

            # 存储函数
            for func in analysis.get("functions", []):
                func_id = self._store_function(file_path, func, analysis)
                storage_results.append({"type": "function", "id": func_id})

            # 存储类
            for cls in analysis.get("classes", []):
                class_id = self._store_class(file_path, cls, analysis)
                storage_results.append({"type": "class", "id": class_id})

            return {
                "success": True,
                "file_path": file_path,
                "analysis": analysis,
                "storage_results": storage_results,
                "total_stored": len(storage_results),
            }

        except Exception as e:
            return {"success": False, "file_path": file_path, "error": str(e)}

    def _store_file_content(
        self, file_path: str, content: str, analysis: Dict[str, Any]
    ) -> str:
        """存储完整文件内容"""
        file_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
        data_id = f"file_{file_hash}"

        metadata = {
            "file_path": file_path,
            "language": analysis.get("language", "text"),
            "file_size": len(content),
            "line_count": analysis.get("line_count", 0),
            "function_count": len(analysis.get("functions", [])),
            "class_count": len(analysis.get("classes", [])),
            "complexity_score": analysis.get("complexity_score", 0),
            "content_type": "full_file",
            "content_hash": file_hash,
        }

        return self.data_manager.store_data(
            data_type="file", content=content, metadata=metadata, data_id=data_id
        )

    def _store_code_chunk(
        self, file_path: str, chunk: Dict[str, Any], analysis: Dict[str, Any]
    ) -> str:
        """存储代码块"""
        chunk_content = chunk["content"]
        chunk_hash = hashlib.md5(
            chunk_content.encode(), usedforsecurity=False
        ).hexdigest()
        data_id = f"chunk_{chunk_hash}"

        metadata = {
            "file_path": file_path,
            "language": analysis.get("language", "text"),
            "chunk_type": chunk.get("type", "generic"),
            "content_type": "code_chunk",
            "content_hash": chunk_hash,
        }

        # 添加特定类型的元数据
        if chunk.get("type") == "function":
            metadata.update(
                {
                    "function_name": chunk.get("name", ""),
                    "line_start": chunk.get("line_start", 0),
                    "line_end": chunk.get("line_end", 0),
                }
            )
        elif chunk.get("type") == "class":
            metadata.update(
                {
                    "class_name": chunk.get("name", ""),
                    "line_start": chunk.get("line_start", 0),
                    "line_end": chunk.get("line_end", 0),
                }
            )

        return self.data_manager.store_data(
            data_type="file", content=chunk_content, metadata=metadata, data_id=data_id
        )

    def _store_function(
        self, file_path: str, func: Dict[str, Any], analysis: Dict[str, Any]
    ) -> str:
        """存储函数信息"""
        func_name = func["name"]
        func_id = f"func_{hashlib.md5(f'{file_path}:{func_name}:{func.get('line_start', 0)}'.encode(), usedforsecurity=False).hexdigest()}"

        # 构建函数描述文本
        func_description = f"Function: {func_name}"
        if func.get("docstring"):
            func_description += f"\nDocstring: {func['docstring']}"
        if func.get("args"):
            func_description += f"\nArguments: {', '.join(func['args'])}"

        metadata = {
            "file_path": file_path,
            "language": analysis.get("language", "text"),
            "function_name": func_name,
            "line_start": func.get("line_start", 0),
            "line_end": func.get("line_end", 0),
            "args": ",".join(func.get("args", [])),  # 转换为字符串
            "is_async": func.get("is_async", False),
            "decorators": ",".join(func.get("decorators", [])),  # 转换为字符串
            "content_type": "function_definition",
        }

        return self.data_manager.store_data(
            data_type="file",
            content=func_description,
            metadata=metadata,
            data_id=func_id,
        )

    def _store_class(
        self, file_path: str, cls: Dict[str, Any], analysis: Dict[str, Any]
    ) -> str:
        """存储类信息"""
        class_name = cls["name"]
        class_id = f"class_{hashlib.md5(f'{file_path}:{class_name}:{cls.get('line_start', 0)}'.encode(), usedforsecurity=False).hexdigest()}"

        # 构建类描述文本
        class_description = f"Class: {class_name}"
        if cls.get("docstring"):
            class_description += f"\nDocstring: {cls['docstring']}"
        if cls.get("bases"):
            class_description += f"\nInherits from: {', '.join(cls['bases'])}"
        if cls.get("methods"):
            method_names = [method["name"] for method in cls["methods"]]
            class_description += f"\nMethods: {', '.join(method_names)}"

        metadata = {
            "file_path": file_path,
            "language": analysis.get("language", "text"),
            "class_name": class_name,
            "line_start": cls.get("line_start", 0),
            "line_end": cls.get("line_end", 0),
            "bases": ",".join(cls.get("bases", [])),  # 转换为字符串
            "method_count": len(cls.get("methods", [])),
            "content_type": "class_definition",
        }

        return self.data_manager.store_data(
            data_type="file",
            content=class_description,
            metadata=metadata,
            data_id=class_id,
        )

    def search_code(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """搜索代码"""
        return self.query_processor.process_query(query, context)

    def search_similar_code(
        self, code_snippet: str, language: Optional[str] = None, n_results: int = 10
    ) -> Dict[str, Any]:
        """搜索相似代码片段"""
        return self.query_processor.search_similar_code(
            code_snippet, language, n_results
        )

    def get_file_context(self, file_path: str) -> Dict[str, Any]:
        """获取文件上下文信息"""
        try:
            # 搜索与文件相关的所有数据
            results = self.data_manager.search_by_metadata(
                filters={"file_path": file_path}, limit=100
            )

            if not results["ids"]:
                return {"file_path": file_path, "found": False}

            # 组织结果
            file_context: Dict[str, Any] = {
                "file_path": file_path,
                "found": True,
                "functions": [],
                "classes": [],
                "chunks": [],
                "full_file": None,
            }

            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                content = results["documents"][i]
                content_type = metadata.get("content_type", "")

                if content_type == "full_file":
                    file_context["full_file"] = {
                        "id": doc_id,
                        "language": metadata.get("language", ""),
                        "file_size": metadata.get("file_size", 0),
                        "line_count": metadata.get("line_count", 0),
                        "function_count": metadata.get("function_count", 0),
                        "class_count": metadata.get("class_count", 0),
                    }
                elif content_type == "function_definition":
                    file_context["functions"].append(
                        {
                            "id": doc_id,
                            "name": metadata.get("function_name", ""),
                            "line_start": metadata.get("line_start", 0),
                            "line_end": metadata.get("line_end", 0),
                            "description": content,
                        }
                    )
                elif content_type == "class_definition":
                    file_context["classes"].append(
                        {
                            "id": doc_id,
                            "name": metadata.get("class_name", ""),
                            "line_start": metadata.get("line_start", 0),
                            "line_end": metadata.get("line_end", 0),
                            "description": content,
                        }
                    )
                elif content_type == "code_chunk":
                    file_context["chunks"].append(
                        {
                            "id": doc_id,
                            "type": metadata.get("chunk_type", "generic"),
                            "content_preview": (
                                content[:200] + "..." if len(content) > 200 else content
                            ),
                        }
                    )

            return file_context

        except Exception as e:
            return {"file_path": file_path, "found": False, "error": str(e)}

    def get_project_overview(self) -> Dict[str, Any]:
        """获取项目概览"""
        try:
            # 获取所有文件数据的统计
            stats = self.data_manager.get_stats()

            # 获取语言分布
            language_results = self.data_manager.search_by_metadata(
                filters={"data_type": "file"}, limit=1000
            )

            language_stats: Dict[str, int] = {}
            file_stats: Dict[str, Dict[str, Any]] = {}

            for metadata in language_results.get("metadatas", []):
                language = metadata.get("language", "unknown")
                language_stats[language] = language_stats.get(language, 0) + 1

                if metadata.get("content_type") == "full_file":
                    file_path = metadata.get("file_path", "")
                    file_stats[file_path] = {
                        "language": language,
                        "size": metadata.get("file_size", 0),
                        "functions": metadata.get("function_count", 0),
                        "classes": metadata.get("class_count", 0),
                        "complexity": metadata.get("complexity_score", 0),
                    }

            return {
                "total_data_items": sum(stats.values()),
                "data_type_distribution": stats,
                "language_distribution": language_stats,
                "file_count": len(file_stats),
                "files": file_stats,
                "top_languages": sorted(
                    language_stats.items(), key=lambda x: x[1], reverse=True
                )[:5],
            }

        except Exception as e:
            return {"error": str(e)}

    def cleanup_file_data(self, file_path: str) -> bool:
        """清理文件相关的所有数据"""
        try:
            # 查找所有与文件相关的数据
            results = self.data_manager.search_by_metadata(
                filters={"file_path": file_path}, limit=1000
            )

            # 删除所有相关数据
            for doc_id in results.get("ids", []):
                self.data_manager.delete_data(doc_id)

            return True
        except Exception:
            return False
