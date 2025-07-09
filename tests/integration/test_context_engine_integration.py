"""
上下文引擎集成测试

测试上下文引擎与其他组件的集成，包括与 BasicToolsService 的集成、
与 ChromaDB 的集成、以及完整的工作流测试。
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from mcp_toolkit.core.types import ToolCallRequest
from mcp_toolkit.services.basic_tools import BasicToolsService
from mcp_toolkit.storage.unified_manager import UnifiedDataManager


class TestContextEngineIntegration:
    """上下文引擎集成测试"""

    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def enhanced_service_config(self, temp_db_dir):
        """创建增强服务配置"""
        return {
            "enhanced_mode": True,
            "chromadb": {
                "persist_directory": temp_db_dir,
                "collection_name": "test_collection",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            },
            "tools": {
                "categories": {
                    "file_operations": {"enabled": True},
                    "enhanced_file_operations": {"enabled": True},
                    "enhanced_network": {"enabled": True},
                    "enhanced_system": {"enabled": True},
                    "context_tools": {"enabled": True},
                }
            },
        }

    @pytest_asyncio.fixture
    async def enhanced_service(self, enhanced_service_config):
        """创建增强服务"""
        service = BasicToolsService(enhanced_service_config)
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_service_initialization_with_context_tools(self, enhanced_service):
        """测试服务初始化包含上下文工具"""
        tools = enhanced_service.get_tools()
        tool_names = [tool.name for tool in tools]

        # 检查上下文工具是否已注册
        context_tool_names = [
            "analyze_code",
            "search_code",
            "find_similar_code",
            "get_project_overview",
        ]
        for tool_name in context_tool_names:
            assert (
                tool_name in tool_names
            ), f"Context tool {tool_name} not found in registered tools"

    @pytest.mark.asyncio
    async def test_analyze_code_tool_integration(self, enhanced_service):
        """测试代码分析工具集成"""
        python_code = '''
import os
import sys
from typing import List, Dict

def process_data(data: List[Dict]) -> Dict:
    """处理数据列表"""
    result = {"processed": 0, "errors": 0}

    for item in data:
        try:
            # 处理逻辑
            if validate_item(item):
                process_item(item)
                result["processed"] += 1
            else:
                result["errors"] += 1
        except Exception as e:
            print(f"Error processing item: {e}")
            result["errors"] += 1

    return result

def validate_item(item: Dict) -> bool:
    """验证数据项"""
    required_fields = ["id", "name", "type"]
    return all(field in item for field in required_fields)

def process_item(item: Dict) -> None:
    """处理单个数据项"""
    print(f"Processing {item['name']}")

class DataProcessor:
    """数据处理器类"""

    def __init__(self, config: Dict):
        self.config = config
        self.stats = {"total": 0, "success": 0, "failed": 0}

    def process_batch(self, batch: List[Dict]) -> Dict:
        """批量处理数据"""
        self.stats["total"] += len(batch)

        for item in batch:
            try:
                if self.validate_and_process(item):
                    self.stats["success"] += 1
                else:
                    self.stats["failed"] += 1
            except Exception:
                self.stats["failed"] += 1

        return self.stats.copy()

    def validate_and_process(self, item: Dict) -> bool:
        """验证并处理数据项"""
        if not validate_item(item):
            return False

        process_item(item)
        return True

    def get_statistics(self) -> Dict:
        """获取处理统计"""
        return self.stats.copy()
'''

        # 调用代码分析工具
        request = ToolCallRequest(
            tool_name="analyze_code",
            arguments={"file_path": "data_processor.py", "content": python_code},
        )

        result = await enhanced_service.call_tool(request)

        assert result.success is True

        # 检查分析结果 - 可能是新分析或已存在的分析
        if "analysis" in result.result:
            # 新分析的情况
            analysis = result.result["analysis"]
            assert "storage_results" in result.result
        elif "already_analyzed" in result.result:
            # 已分析的情况，使用现有上下文
            analysis = result.result["existing_context"]["full_file"]
        else:
            raise AssertionError(f"Unexpected result structure: {result.result}")

        # 检查分析结果的基本结构
        assert "language" in analysis
        assert analysis["language"] == "python"

    @pytest.mark.asyncio
    async def test_search_code_after_analysis(self, enhanced_service):
        """测试分析后的代码搜索"""
        # 首先分析一些代码文件
        files_to_analyze = {
            "utils.py": '''
def calculate_fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def factorial(n):
    """计算阶乘"""
    if n <= 1:
        return 1
    return n * factorial(n-1)
''',
            "algorithms.py": '''
def binary_search(arr, target):
    """二分搜索"""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

def quick_sort(arr):
    """快速排序"""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
''',
            "data_structures.py": '''
class Stack:
    """栈数据结构"""
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop() if self.items else None

    def peek(self):
        return self.items[-1] if self.items else None

class Queue:
    """队列数据结构"""
    def __init__(self):
        self.items = []

    def enqueue(self, item):
        self.items.insert(0, item)

    def dequeue(self):
        return self.items.pop() if self.items else None
''',
        }

        # 分析所有文件
        for file_path, content in files_to_analyze.items():
            analyze_request = ToolCallRequest(
                tool_name="analyze_code",
                arguments={"file_path": file_path, "content": content},
            )

            result = await enhanced_service.call_tool(analyze_request)
            assert result.success is True

        # 搜索函数
        search_request = ToolCallRequest(
            tool_name="search_code", arguments={"query": "fibonacci recursive function"}
        )

        search_result = await enhanced_service.call_tool(search_request)
        assert search_result.success is True

        results = search_result.result["results"]
        assert "items" in results

        # 应该能找到 fibonacci 相关的结果
        items = results["items"]
        fibonacci_found = any("fibonacci" in item["content"].lower() for item in items)
        assert fibonacci_found

        # 搜索类
        class_search_request = ToolCallRequest(
            tool_name="search_code", arguments={"query": "Stack data structure class"}
        )

        class_search_result = await enhanced_service.call_tool(class_search_request)
        assert class_search_result.success is True

        class_results = class_search_result.result["results"]
        class_items = class_results["items"]
        stack_found = any("stack" in item["content"].lower() for item in class_items)
        assert stack_found

    @pytest.mark.asyncio
    async def test_similar_code_search(self, enhanced_service):
        """测试相似代码搜索"""
        # 先分析一些代码
        code_samples = {
            "math1.py": "def add(a, b): return a + b",
            "math2.py": "def sum_numbers(x, y): return x + y",
            "math3.py": "def calculate_sum(num1, num2): result = num1 + num2; return result",
        }

        for file_path, content in code_samples.items():
            analyze_request = ToolCallRequest(
                tool_name="analyze_code",
                arguments={"file_path": file_path, "content": content},
            )

            result = await enhanced_service.call_tool(analyze_request)
            assert result.success is True

        # 搜索相似代码
        similar_request = ToolCallRequest(
            tool_name="find_similar_code",
            arguments={
                "code_snippet": "def plus(a, b): return a + b",
                "language": "python",
                "max_results": 5,
            },
        )

        similar_result = await enhanced_service.call_tool(similar_request)
        assert similar_result.success is True

        results = similar_result.result
        assert "results" in results
        assert "total_found" in results

    @pytest.mark.asyncio
    async def test_project_overview(self, enhanced_service):
        """测试项目概览"""
        # 分析多种语言的文件
        project_files = {
            "main.py": """
def main():
    print("Python main function")

if __name__ == "__main__":
    main()
""",
            "utils.js": """
function formatDate(date) {
    return date.toISOString();
}

export { formatDate };
""",
            "config.json": """
{
    "version": "1.0.0",
    "name": "test-project"
}
""",
            "README.md": """
# Test Project

This is a test project for integration testing.

## Features
- Python backend
- JavaScript frontend
- JSON configuration
""",
        }

        # 分析所有文件
        for file_path, content in project_files.items():
            analyze_request = ToolCallRequest(
                tool_name="analyze_code",
                arguments={"file_path": file_path, "content": content},
            )

            result = await enhanced_service.call_tool(analyze_request)
            assert result.success is True

        # 获取项目概览
        overview_request = ToolCallRequest(
            tool_name="get_project_overview", arguments={"include_files": True}
        )

        overview_result = await enhanced_service.call_tool(overview_request)
        assert overview_result.success is True

        overview = overview_result.result
        assert "total_data_items" in overview
        assert "language_distribution" in overview
        assert "file_count" in overview
        assert overview["file_count"] >= 4

        # 检查语言分布
        lang_dist = overview["language_distribution"]
        assert "python" in lang_dist
        assert "javascript" in lang_dist
        assert "json" in lang_dist
        assert "markdown" in lang_dist

    @pytest.mark.asyncio
    async def test_enhanced_file_operations_integration(self, enhanced_service):
        """测试增强文件操作与上下文引擎的集成"""
        # 使用增强文件读取工具
        python_code = '''
class Calculator:
    """简单计算器"""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def get_history(self):
        return self.history.copy()
'''

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(python_code)
            temp_file_path = f.name

        try:
            # 使用增强文件读取（会自动存储到 ChromaDB）
            enhanced_read_request = ToolCallRequest(
                tool_name="enhanced_read_file", arguments={"file_path": temp_file_path}
            )

            read_result = await enhanced_service.call_tool(enhanced_read_request)
            assert read_result.success is True

            # 现在搜索刚才读取的文件内容
            search_request = ToolCallRequest(
                tool_name="search_code",
                arguments={"query": "Calculator class with history"},
            )

            search_result = await enhanced_service.call_tool(search_request)
            assert search_result.success is True

            # 应该能找到刚才读取的文件内容
            results = search_result.result["results"]
            items = results["items"]
            calculator_found = any(
                "calculator" in item["content"].lower() for item in items
            )
            assert calculator_found

        finally:
            import os

            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_cross_tool_data_consistency(self, enhanced_service):
        """测试跨工具的数据一致性"""
        # 使用代码分析工具分析代码
        code_content = '''
def data_processor(items):
    """处理数据项列表"""
    processed = []
    for item in items:
        if isinstance(item, dict) and 'value' in item:
            processed.append(item['value'] * 2)
    return processed
'''

        analyze_request = ToolCallRequest(
            tool_name="analyze_code",
            arguments={"file_path": "processor.py", "content": code_content},
        )

        analyze_result = await enhanced_service.call_tool(analyze_request)
        assert analyze_result.success is True

        # 使用搜索工具查找刚才分析的代码
        search_request = ToolCallRequest(
            tool_name="search_code", arguments={"query": "data_processor function"}
        )

        search_result = await enhanced_service.call_tool(search_request)
        assert search_result.success is True

        # 使用项目概览工具查看整体状态
        overview_request = ToolCallRequest(
            tool_name="get_project_overview", arguments={"include_files": False}
        )

        overview_result = await enhanced_service.call_tool(overview_request)
        assert overview_result.success is True

        # 所有工具应该看到一致的数据
        overview = overview_result.result
        assert overview["file_count"] >= 1
        assert "python" in overview["language_distribution"]

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, enhanced_service):
        """测试集成环境下的错误处理"""
        # 测试分析无效代码
        invalid_code = """
def invalid_function(
    # 缺少参数和函数体
"""

        analyze_request = ToolCallRequest(
            tool_name="analyze_code",
            arguments={"file_path": "invalid.py", "content": invalid_code},
        )

        analyze_result = await enhanced_service.call_tool(analyze_request)
        # 即使代码无效，工具也应该能处理
        assert analyze_result.success is True

        # 测试搜索不存在的内容
        search_request = ToolCallRequest(
            tool_name="search_code",
            arguments={"query": "nonexistent_function_that_does_not_exist"},
        )

        search_result = await enhanced_service.call_tool(search_request)
        assert search_result.success is True
        # 应该返回空结果而不是错误
        results = search_result.result["results"]
        assert "items" in results

    @pytest.mark.asyncio
    async def test_performance_with_large_codebase(self, enhanced_service):
        """测试大代码库的性能"""
        # 生成多个文件来模拟大代码库
        for i in range(10):
            large_code = f'''
def function_{i}_1():
    """Function {i}_1 documentation"""
    return "result_{i}_1"

def function_{i}_2():
    """Function {i}_2 documentation"""
    return "result_{i}_2"

class Class_{i}:
    """Class {i} documentation"""

    def method_{i}_1(self):
        return f"method_{i}_1"

    def method_{i}_2(self):
        return f"method_{i}_2"
'''

            analyze_request = ToolCallRequest(
                tool_name="analyze_code",
                arguments={"file_path": f"module_{i}.py", "content": large_code},
            )

            result = await enhanced_service.call_tool(analyze_request)
            assert result.success is True

        # 测试搜索性能
        search_request = ToolCallRequest(
            tool_name="search_code", arguments={"query": "function documentation"}
        )

        search_result = await enhanced_service.call_tool(search_request)
        assert search_result.success is True

        # 检查是否返回了合理数量的结果
        results = search_result.result["results"]
        assert len(results["items"]) > 0

        # 测试项目概览性能
        overview_request = ToolCallRequest(
            tool_name="get_project_overview", arguments={"include_files": True}
        )

        overview_result = await enhanced_service.call_tool(overview_request)
        assert overview_result.success is True

        overview = overview_result.result
        assert overview["file_count"] >= 10
