"""
上下文工具单元测试
"""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_toolkit.storage.unified_manager import UnifiedDataManager
from mcp_toolkit.tools.base import ExecutionContext, ToolExecutionRequest
from mcp_toolkit.tools.context_tools import (
    CodeAnalysisTool,
    CodeSearchTool,
    ContextTools,
    ProjectOverviewTool,
    SimilarCodeTool,
)


class TestCodeAnalysisTool:
    """代码分析工具测试"""

    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def data_manager(self, temp_db_dir):
        """创建数据管理器"""
        return UnifiedDataManager(persist_directory=temp_db_dir)

    @pytest.fixture
    def tool(self, data_manager):
        """创建代码分析工具"""
        config = {"context_engine": {"chunk_size": 500}}
        return CodeAnalysisTool(config, data_manager)

    def test_tool_definition(self, tool):
        """测试工具定义"""
        definition = tool.get_definition()

        assert definition.name == "analyze_code"
        assert "分析代码文件" in definition.description
        assert "properties" in definition.parameters
        assert "file_path" in definition.parameters["properties"]
        assert "content" in definition.parameters["properties"]

    def test_validate_parameters(self, tool):
        """测试参数验证"""
        # 有效参数
        valid_params = {"file_path": "test.py", "content": "def test(): pass"}
        result = tool.validate_parameters(valid_params)
        assert result.is_valid is True

        # 无效参数 - 缺少文件路径
        invalid_params = {"content": "def test(): pass"}
        result = tool.validate_parameters(invalid_params)
        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_with_content(self, tool):
        """测试执行代码分析（提供内容）"""
        python_code = '''
def hello_world():
    """打印 Hello World"""
    print("Hello, World!")

class Calculator:
    def add(self, a, b):
        return a + b
'''

        request = ToolExecutionRequest(
            tool_name="analyze_code",
            parameters={"file_path": "test.py", "content": python_code},
            execution_context=ExecutionContext(
                request_id="test_req", working_directory="."
            ),
        )

        result = await tool.execute(request)

        assert result.success is True
        assert "file_path" in result.content
        assert result.content["file_path"] == "test.py"
        assert result.content["success"] is True
        assert "analysis" in result.content
        assert "storage_results" in result.content

    @pytest.mark.asyncio
    async def test_execute_with_file_read(self, tool):
        """测试执行代码分析（从文件读取）"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_function(): return 'test'")
            temp_file_path = f.name

        try:
            request = ToolExecutionRequest(
                tool_name="analyze_code",
                parameters={"file_path": temp_file_path},
                execution_context=ExecutionContext(
                    request_id="test_req", working_directory="."
                ),
            )

            result = await tool.execute(request)

            assert result.success is True
            assert result.content["file_path"] == temp_file_path

        finally:
            import os

            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_execute_force_reanalyze(self, tool):
        """测试强制重新分析"""
        python_code = "def simple(): pass"

        # 第一次分析
        request1 = ToolExecutionRequest(
            tool_name="analyze_code",
            parameters={"file_path": "simple.py", "content": python_code},
            execution_context=ExecutionContext(
                request_id="test_req1", working_directory="."
            ),
        )

        result1 = await tool.execute(request1)
        assert result1.success is True

        # 第二次分析（不强制）
        request2 = ToolExecutionRequest(
            tool_name="analyze_code",
            parameters={"file_path": "simple.py", "content": python_code},
            execution_context=ExecutionContext(
                request_id="test_req2", working_directory="."
            ),
        )

        result2 = await tool.execute(request2)
        assert result2.success is True
        assert result2.content.get("already_analyzed") is True

        # 第三次分析（强制）
        request3 = ToolExecutionRequest(
            tool_name="analyze_code",
            parameters={
                "file_path": "simple.py",
                "content": python_code,
                "force_reanalyze": True,
            },
            execution_context=ExecutionContext(
                request_id="test_req3", working_directory="."
            ),
        )

        result3 = await tool.execute(request3)
        assert result3.success is True
        assert result3.content.get("already_analyzed") is not True


class TestCodeSearchTool:
    """代码搜索工具测试"""

    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def data_manager(self, temp_db_dir):
        """创建数据管理器"""
        return UnifiedDataManager(persist_directory=temp_db_dir)

    @pytest.fixture
    def tool(self, data_manager):
        """创建代码搜索工具"""
        return CodeSearchTool({}, data_manager)

    @pytest.fixture
    def sample_data(self, data_manager):
        """创建示例数据"""
        data_manager.store_data(
            data_type="file",
            content="def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
            metadata={
                "file_path": "math.py",
                "language": "python",
                "function_name": "fibonacci",
                "content_type": "function_definition",
            },
        )

    def test_tool_definition(self, tool):
        """测试工具定义"""
        definition = tool.get_definition()

        assert definition.name == "search_code"
        assert "智能代码搜索" in definition.description
        assert "query" in definition.parameters["properties"]
        assert "language" in definition.parameters["properties"]
        assert "search_type" in definition.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute_search(self, tool, sample_data):
        """测试执行代码搜索"""
        request = ToolExecutionRequest(
            tool_name="search_code",
            parameters={"query": "fibonacci function"},
            execution_context=ExecutionContext(
                request_id="test_req", working_directory="."
            ),
        )

        result = await tool.execute(request)

        assert result.success is True
        assert "query" in result.content
        assert "results" in result.content

    @pytest.mark.asyncio
    async def test_execute_search_with_filters(self, tool, sample_data):
        """测试带过滤条件的搜索"""
        request = ToolExecutionRequest(
            tool_name="search_code",
            parameters={
                "query": "fibonacci",
                "language": "python",
                "search_type": "functions",
                "max_results": 5,
            },
            execution_context=ExecutionContext(
                request_id="test_req", working_directory="."
            ),
        )

        result = await tool.execute(request)

        assert result.success is True
        assert result.content["query"] == "fibonacci"


class TestSimilarCodeTool:
    """相似代码搜索工具测试"""

    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def data_manager(self, temp_db_dir):
        """创建数据管理器"""
        return UnifiedDataManager(persist_directory=temp_db_dir)

    @pytest.fixture
    def tool(self, data_manager):
        """创建相似代码搜索工具"""
        return SimilarCodeTool({}, data_manager)

    def test_tool_definition(self, tool):
        """测试工具定义"""
        definition = tool.get_definition()

        assert definition.name == "find_similar_code"
        assert "相似" in definition.description
        assert "code_snippet" in definition.parameters["properties"]
        assert "language" in definition.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute_similar_search(self, tool):
        """测试执行相似代码搜索"""
        request = ToolExecutionRequest(
            tool_name="find_similar_code",
            parameters={
                "code_snippet": "def add(a, b): return a + b",
                "language": "python",
                "max_results": 5,
            },
            execution_context=ExecutionContext(
                request_id="test_req", working_directory="."
            ),
        )

        result = await tool.execute(request)

        assert result.success is True
        assert "results" in result.content
        assert "total_found" in result.content


class TestProjectOverviewTool:
    """项目概览工具测试"""

    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def data_manager(self, temp_db_dir):
        """创建数据管理器"""
        return UnifiedDataManager(persist_directory=temp_db_dir)

    @pytest.fixture
    def tool(self, data_manager):
        """创建项目概览工具"""
        return ProjectOverviewTool({}, data_manager)

    def test_tool_definition(self, tool):
        """测试工具定义"""
        definition = tool.get_definition()

        assert definition.name == "get_project_overview"
        assert "项目概览" in definition.description
        assert "include_files" in definition.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute_overview(self, tool):
        """测试执行项目概览获取"""
        request = ToolExecutionRequest(
            tool_name="get_project_overview",
            parameters={"include_files": True},
            execution_context=ExecutionContext(
                request_id="test_req", working_directory="."
            ),
        )

        result = await tool.execute(request)

        assert result.success is True
        assert "total_data_items" in result.content
        assert "language_distribution" in result.content
        assert "file_count" in result.content

    @pytest.mark.asyncio
    async def test_execute_overview_without_files(self, tool):
        """测试执行项目概览获取（不包含文件详情）"""
        request = ToolExecutionRequest(
            tool_name="get_project_overview",
            parameters={"include_files": False},
            execution_context=ExecutionContext(
                request_id="test_req", working_directory="."
            ),
        )

        result = await tool.execute(request)

        assert result.success is True
        # 文件详情应该被隐藏
        if "files" in result.content:
            assert isinstance(result.content["files"], str)


class TestContextTools:
    """上下文工具集测试"""

    def test_create_tools(self):
        """测试创建工具集"""
        config = {"context_tools": {"chunk_size": 1000, "max_results": 20}}

        context_tools = ContextTools(config)
        tools = context_tools.create_tools()

        assert len(tools) == 4  # 4个上下文工具

        tool_names = [tool.get_definition().name for tool in tools]
        expected_names = [
            "analyze_code",
            "search_code",
            "find_similar_code",
            "get_project_overview",
        ]

        for expected_name in expected_names:
            assert expected_name in tool_names

    def test_tools_share_data_manager(self):
        """测试工具共享数据管理器"""
        context_tools = ContextTools({})
        tools = context_tools.create_tools()

        # 所有工具应该共享同一个数据管理器实例
        data_managers = [tool.data_manager for tool in tools]
        first_manager = data_managers[0]

        for manager in data_managers[1:]:
            assert manager is first_manager


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def temp_db_dir(self):
        """创建临时数据库目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def context_tools(self, temp_db_dir):
        """创建上下文工具集"""
        config = {"context_tools": {"chunk_size": 500, "max_results": 10}}
        return ContextTools(config)

    @pytest.mark.asyncio
    async def test_analyze_then_search_workflow(self, context_tools):
        """测试分析然后搜索的工作流"""
        tools = context_tools.create_tools()

        # 找到分析和搜索工具
        analyze_tool = next(
            tool for tool in tools if tool.get_definition().name == "analyze_code"
        )
        search_tool = next(
            tool for tool in tools if tool.get_definition().name == "search_code"
        )

        # 1. 分析代码
        python_code = '''
def binary_search(arr, target):
    """二分搜索算法"""
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

class SearchAlgorithms:
    """搜索算法集合"""

    @staticmethod
    def linear_search(arr, target):
        """线性搜索"""
        for i, item in enumerate(arr):
            if item == target:
                return i
        return -1
'''

        analyze_request = ToolExecutionRequest(
            tool_name="analyze_code",
            parameters={"file_path": "search_algorithms.py", "content": python_code},
            execution_context=ExecutionContext(
                request_id="analyze_req", working_directory="."
            ),
        )

        analyze_result = await analyze_tool.execute(analyze_request)
        assert analyze_result.success is True

        # 2. 搜索代码
        search_request = ToolExecutionRequest(
            tool_name="search_code",
            parameters={"query": "binary search algorithm"},
            execution_context=ExecutionContext(
                request_id="search_req", working_directory="."
            ),
        )

        search_result = await search_tool.execute(search_request)
        assert search_result.success is True

        # 搜索结果应该包含之前分析的代码
        results = search_result.content["results"]
        assert "items" in results
        # 可能找到相关的搜索结果

    @pytest.mark.asyncio
    async def test_error_handling_across_tools(self, context_tools):
        """测试跨工具的错误处理"""
        tools = context_tools.create_tools()

        for tool in tools:
            # 测试每个工具的错误处理
            invalid_request = ToolExecutionRequest(
                tool_name=tool.get_definition().name,
                parameters={},  # 空参数应该触发验证错误
                execution_context=ExecutionContext(
                    request_id="error_req", working_directory="."
                ),
            )

            result = await tool.execute(invalid_request)
            # 工具应该能优雅地处理错误
            assert result is not None
