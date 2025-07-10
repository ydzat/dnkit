"""
查询处理器

处理用户查询，解析查询意图，构建搜索条件，聚合搜索结果。
支持自然语言查询和结构化查询。
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ..core.types import ConfigDict
from ..storage.unified_manager import UnifiedDataManager


class QueryProcessor:
    """查询处理器 - 智能查询解析和结果聚合"""

    def __init__(
        self, data_manager: UnifiedDataManager, config: Optional[ConfigDict] = None
    ):
        self.data_manager = data_manager
        self.config = config or {}

        # 查询类型关键词
        self.query_patterns = {
            "function": [
                r"function\s+(\w+)",
                r"def\s+(\w+)",
                r"(\w+)\s*\(",
                r"method\s+(\w+)",
                r"函数\s*(\w+)",
                r"方法\s*(\w+)",
            ],
            "class": [r"class\s+(\w+)", r"类\s*(\w+)", r"对象\s*(\w+)"],
            "variable": [r"variable\s+(\w+)", r"var\s+(\w+)", r"变量\s*(\w+)"],
            "file": [r"file\s+([^\s]+)", r"文件\s*([^\s]+)", r"\.(\w+)$"],
            "language": [
                r"python",
                r"javascript",
                r"typescript",
                r"java",
                r"cpp",
                r"go",
                r"rust",
            ],
        }

    def process_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理用户查询，返回搜索结果"""
        # 解析查询意图
        query_intent = self._parse_query_intent(query)

        # 构建搜索条件
        search_conditions = self._build_search_conditions(query, query_intent, context)

        # 执行搜索
        search_results = self._execute_search(search_conditions)

        # 聚合和排序结果
        aggregated_results = self._aggregate_results(search_results, query_intent)

        return {
            "query": query,
            "intent": query_intent,
            "conditions": search_conditions,
            "results": aggregated_results,
            "total_found": len(aggregated_results.get("items", [])),
            "processing_time": 0,  # 可以添加计时
        }

    def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """解析查询意图"""
        intent: Dict[str, Any] = {
            "type": "general",
            "entities": {},
            "filters": {},
            "scope": "all",
        }

        query_lower = query.lower()

        # 检测查询类型
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    if query_type not in intent["entities"]:
                        intent["entities"][query_type] = []
                    entity_list = intent["entities"][query_type]
                    if isinstance(entity_list, list):
                        entity_list.extend(matches)

        # 检测数据类型过滤
        if any(word in query_lower for word in ["file", "code", "源码", "代码"]):
            intent["filters"]["data_type"] = "file"
        elif any(word in query_lower for word in ["task", "任务", "todo"]):
            intent["filters"]["data_type"] = "task"
        elif any(word in query_lower for word in ["config", "配置", "设置"]):
            intent["filters"]["data_type"] = "config"
        elif any(word in query_lower for word in ["web", "网页", "页面"]):
            intent["filters"]["data_type"] = "web_content"
        elif any(word in query_lower for word in ["system", "系统", "进程"]):
            intent["filters"]["data_type"] = "system_info"

        # 检测编程语言
        for lang in self.query_patterns["language"]:
            if lang in query_lower:
                intent["filters"]["language"] = lang
                break

        # 确定主要查询类型
        if intent["entities"]:
            if "function" in intent["entities"]:
                intent["type"] = "function_search"
            elif "class" in intent["entities"]:
                intent["type"] = "class_search"
            elif "file" in intent["entities"]:
                intent["type"] = "file_search"
            else:
                intent["type"] = "entity_search"
        elif intent["filters"]:
            intent["type"] = "filtered_search"

        return intent

    def _build_search_conditions(
        self, query: str, intent: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建搜索条件"""
        conditions = {
            "query_text": query,
            "filters": intent.get("filters", {}),
            "n_results": self.config.get("max_results", 20),
        }

        # 添加上下文过滤
        if context:
            if "current_file" in context:
                conditions["filters"]["file_path"] = context["current_file"]
            if "current_language" in context:
                conditions["filters"]["language"] = context["current_language"]

        # 根据查询类型调整搜索策略
        if intent["type"] == "function_search":
            conditions["boost_fields"] = ["function_name", "content"]
        elif intent["type"] == "class_search":
            conditions["boost_fields"] = ["class_name", "content"]
        elif intent["type"] == "file_search":
            conditions["boost_fields"] = ["file_path", "content"]

        return conditions

    def _execute_search(self, conditions: Dict[str, Any]) -> Any:
        """执行搜索"""
        query_text = conditions["query_text"]
        filters = conditions.get("filters", {})
        n_results = conditions.get("n_results", 20)

        # 从过滤条件中提取 data_type
        data_type = filters.pop("data_type", None)

        try:
            # 使用统一数据管理器进行搜索
            results = self.data_manager.query_data(
                query=query_text,
                data_type=data_type,
                filters=filters if filters else None,
                n_results=n_results,
            )
            return results
        except Exception as e:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
                "error": str(e),
            }

    def _aggregate_results(
        self, search_results: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """聚合和排序结果"""
        if "error" in search_results:
            return {"items": [], "error": search_results["error"]}

        items = []

        if search_results["ids"] and search_results["ids"][0]:
            for i, doc_id in enumerate(search_results["ids"][0]):
                metadata = (
                    search_results["metadatas"][0][i]
                    if search_results["metadatas"][0]
                    else {}
                )
                document = (
                    search_results["documents"][0][i]
                    if search_results["documents"][0]
                    else ""
                )
                distance = (
                    search_results["distances"][0][i]
                    if search_results["distances"][0]
                    else 1.0
                )

                item = {
                    "id": doc_id,
                    "content": document,
                    "metadata": metadata,
                    "similarity_score": 1 - distance,
                    "data_type": metadata.get("data_type", "unknown"),
                    "relevance_score": self._calculate_relevance(
                        document, metadata, intent
                    ),
                }

                # 添加特定类型的字段
                if metadata.get("data_type") == "file":
                    item.update(
                        {
                            "file_path": metadata.get("file_path", ""),
                            "language": metadata.get("language", ""),
                            "function_name": metadata.get("function_name", ""),
                            "class_name": metadata.get("class_name", ""),
                            "line_start": metadata.get("line_start", 0),
                            "line_end": metadata.get("line_end", 0),
                        }
                    )
                elif metadata.get("data_type") == "web_content":
                    item.update(
                        {
                            "url": metadata.get("url", ""),
                            "title": metadata.get("title", ""),
                            "domain": metadata.get("domain", ""),
                        }
                    )
                elif metadata.get("data_type") == "system_info":
                    item.update(
                        {
                            "hostname": metadata.get("hostname", ""),
                            "os_system": metadata.get("os_system", ""),
                        }
                    )

                items.append(item)

        # 按相关性排序
        items.sort(key=lambda x: x["relevance_score"], reverse=True)

        # 按数据类型分组
        grouped_results = self._group_by_type(items)

        return {
            "items": items,
            "grouped": grouped_results,
            "summary": self._generate_summary(items, intent),
        }

    def _calculate_relevance(
        self, document: str, metadata: Dict[str, Any], intent: Dict[str, Any]
    ) -> float:
        """计算相关性分数"""
        base_score = 0.5

        # 基于查询意图调整分数
        if intent["type"] == "function_search" and metadata.get("function_name"):
            base_score += 0.3
        elif intent["type"] == "class_search" and metadata.get("class_name"):
            base_score += 0.3
        elif intent["type"] == "file_search" and metadata.get("file_path"):
            base_score += 0.3

        # 基于数据类型调整分数
        data_type = metadata.get("data_type", "")
        if data_type in intent.get("filters", {}):
            base_score += 0.2

        # 基于语言匹配调整分数
        if metadata.get("language") == intent.get("filters", {}).get("language"):
            base_score += 0.1

        return min(base_score, 1.0)

    def _group_by_type(
        self, items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按数据类型分组结果"""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            data_type = item["data_type"]
            if data_type not in grouped:
                grouped[data_type] = []
            grouped[data_type].append(item)
        return grouped

    def _generate_summary(
        self, items: List[Dict[str, Any]], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成搜索结果摘要"""
        summary = {
            "total_results": len(items),
            "data_types": {},
            "languages": {},
            "top_matches": [],
        }

        # 统计数据类型分布
        for item in items:
            data_type = item["data_type"]
            data_types_dict = summary["data_types"]
            if isinstance(data_types_dict, dict):
                data_types_dict[data_type] = data_types_dict.get(data_type, 0) + 1

        # 统计语言分布
        for item in items:
            language = item["metadata"].get("language", "unknown")
            languages_dict = summary["languages"]
            if isinstance(languages_dict, dict):
                languages_dict[language] = languages_dict.get(language, 0) + 1

        # 获取前5个最佳匹配
        summary["top_matches"] = items[:5]

        return summary

    def search_similar_code(
        self, code_snippet: str, language: Optional[str] = None, n_results: int = 10
    ) -> Dict[str, Any]:
        """搜索相似代码片段"""
        filters = {"data_type": "file"}
        if language:
            filters["language"] = language

        results = self.data_manager.query_data(
            query=code_snippet, data_type="file", filters=filters, n_results=n_results
        )

        return self._format_code_search_results(results)

    def _format_code_search_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """格式化代码搜索结果"""
        formatted_results = []

        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                document = results["documents"][0][i]
                distance = (
                    results["distances"][0][i] if results["distances"][0] else 1.0
                )

                formatted_results.append(
                    {
                        "id": doc_id,
                        "file_path": metadata.get("file_path", ""),
                        "language": metadata.get("language", ""),
                        "function_name": metadata.get("function_name", ""),
                        "class_name": metadata.get("class_name", ""),
                        "code_snippet": (
                            document[:500] + "..." if len(document) > 500 else document
                        ),
                        "similarity_score": 1 - distance,
                        "line_start": metadata.get("line_start", 0),
                        "line_end": metadata.get("line_end", 0),
                    }
                )

        return {"results": formatted_results, "total_found": len(formatted_results)}
