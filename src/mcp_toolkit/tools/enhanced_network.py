"""
增强的网络工具集

基于 ChromaDB 统一存储的网络工具，支持网页内容存储、语义搜索等功能。
扩展现有的网络工具，添加 ChromaDB 集成。
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

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


class EnhancedWebFetcher(BaseTool):
    """增强的网页获取工具 - 支持 ChromaDB 存储"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.timeout = self.config.get("timeout", 30)
        self.max_content_size = self.config.get("max_content_size_mb", 5) * 1024 * 1024
        self.auto_store = self.config.get("auto_store_to_chromadb", True)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="enhanced_fetch_web",
            description="获取网页内容并可选择存储到 ChromaDB 进行语义搜索",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要获取的网页URL"},
                    "extract_text": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否提取纯文本内容",
                    },
                    "store_to_chromadb": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否将内容存储到 ChromaDB",
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否包含页面元数据",
                    },
                    "user_agent": {
                        "type": "string",
                        "default": "MCP-Toolkit/1.0",
                        "description": "HTTP User-Agent",
                    },
                },
                "required": ["url"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        errors: List[ValidationError] = []

        url = params.get("url", "")
        if not url:
            errors.append(
                ValidationError(field="url", message="URL不能为空", code="EMPTY_URL")
            )
        else:
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append(
                        ValidationError(
                            field="url", message="无效的URL格式", code="INVALID_URL"
                        )
                    )
            except Exception:
                errors.append(
                    ValidationError(
                        field="url", message="URL解析失败", code="URL_PARSE_ERROR"
                    )
                )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行网页获取"""
        params = request.parameters
        url = params["url"]
        extract_text = params.get("extract_text", True)
        store_to_chromadb = params.get("store_to_chromadb", True)
        include_metadata = params.get("include_metadata", True)
        user_agent = params.get("user_agent", "MCP-Toolkit/1.0")

        try:
            start_time = time.time()

            # 设置请求头
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            # 发送HTTP请求
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return self._create_error_result(
                            "HTTP_ERROR", f"HTTP请求失败，状态码: {response.status}"
                        )

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_content_size:
                        return self._create_error_result(
                            "CONTENT_TOO_LARGE",
                            f"内容过大，超过 {self.max_content_size / 1024 / 1024}MB 限制",
                        )

                    html_content = await response.text()

            # 解析HTML内容
            soup = BeautifulSoup(html_content, "html.parser")

            # 提取页面信息
            page_info = {
                "url": url,
                "title": (
                    soup.title.string.strip()
                    if soup.title and soup.title.string
                    else ""
                ),
                "content_length": len(html_content),
                "status_code": response.status,
                "content_type": response.headers.get("content-type", ""),
                "fetch_time": time.time(),
            }

            # 提取元数据
            if include_metadata:
                meta_tags = {}
                for meta in soup.find_all("meta"):
                    if hasattr(meta, "get"):  # 确保是 Tag 对象
                        name = meta.get("name") or meta.get("property")
                        content = meta.get("content")
                        if name and content:
                            meta_tags[name] = content
                page_info["meta_tags"] = meta_tags

            # 提取纯文本内容
            text_content = ""
            if extract_text:
                # 移除脚本和样式标签
                for script in soup(["script", "style"]):
                    script.decompose()
                text_content = soup.get_text()
                # 清理文本
                lines = (line.strip() for line in text_content.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                text_content = " ".join(chunk for chunk in chunks if chunk)

            result_content = {
                "url": url,
                "title": page_info["title"],
                "html_content": html_content,
                "text_content": text_content,
                "page_info": page_info,
                "text_length": len(text_content),
            }

            # 存储到 ChromaDB
            if store_to_chromadb and self.auto_store:
                try:
                    # 使用文本内容生成哈希
                    content_hash = hashlib.md5(
                        text_content.encode(), usedforsecurity=False
                    ).hexdigest()
                    data_id = f"web_{content_hash}"

                    # 准备存储的内容（优先使用文本内容）
                    storage_content = text_content if text_content else html_content

                    metadata = {
                        "url": url,
                        "title": page_info["title"],
                        "content_type": "web_page",
                        "fetch_time": page_info["fetch_time"],
                        "content_length": len(storage_content),
                        "domain": urlparse(url).netloc,
                        "content_hash": content_hash,
                    }

                    # 添加元数据标签
                    if include_metadata and "meta_tags" in page_info:
                        description = page_info["meta_tags"].get("description", "")
                        keywords = page_info["meta_tags"].get("keywords", "")
                        if description:
                            metadata["description"] = description
                        if keywords:
                            metadata["keywords"] = keywords

                    stored_id = self.data_manager.store_data(
                        data_type="web_content",
                        content=storage_content,
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
                memory_used=len(html_content) / 1024 / 1024,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(html_content) / 1024 / 1024,
                cpu_time_ms=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(result_content, exec_metadata, resources)

        except asyncio.TimeoutError:
            return self._create_error_result(
                "TIMEOUT_ERROR", f"请求超时，超过 {self.timeout} 秒"
            )
        except aiohttp.ClientError as e:
            return self._create_error_result("CLIENT_ERROR", f"网络请求错误: {str(e)}")
        except Exception as e:
            self._logger.exception("获取网页时发生异常")
            return self._create_error_result("FETCH_ERROR", f"获取网页失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class WebContentSearchTool(BaseTool):
    """基于 ChromaDB 的网页内容搜索工具"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_web_content",
            description="在 ChromaDB 中搜索已存储的网页内容",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询文本"},
                    "domain": {"type": "string", "description": "过滤特定域名"},
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
        """执行网页内容搜索"""
        params = request.parameters
        query = params["query"]
        domain = params.get("domain")
        max_results = params.get("max_results", 10)

        try:
            start_time = time.time()

            # 构建过滤条件
            filters = {}
            if domain:
                filters["domain"] = domain

            # 执行搜索
            results = self.data_manager.query_data(
                query=query,
                data_type="web_content",
                filters=filters if filters else None,
                n_results=max_results,
            )

            # 处理搜索结果
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    result_item = {
                        "id": doc_id,
                        "url": results["metadatas"][0][i].get("url", ""),
                        "title": results["metadatas"][0][i].get("title", ""),
                        "domain": results["metadatas"][0][i].get("domain", ""),
                        "similarity_score": (
                            1 - results["distances"][0][i]
                            if results["distances"][0]
                            else 0
                        ),
                        "content_preview": (
                            results["documents"][0][i][:300] + "..."
                            if len(results["documents"][0][i]) > 300
                            else results["documents"][0][i]
                        ),
                        "fetch_time": results["metadatas"][0][i].get("fetch_time", 0),
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
            self._logger.exception("搜索网页内容时发生异常")
            return self._create_error_result("SEARCH_ERROR", f"搜索失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class EnhancedNetworkTools:
    """增强的网络工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.data_manager = UnifiedDataManager()

    def create_tools(self) -> List[BaseTool]:
        """创建所有增强的网络工具"""
        tools_config = self.config.get("enhanced_network", {})

        return [
            EnhancedWebFetcher(tools_config, self.data_manager),
            WebContentSearchTool(tools_config, self.data_manager),
        ]
