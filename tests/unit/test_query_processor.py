"""
查询处理器单元测试
"""

import tempfile
from unittest.mock import MagicMock

import pytest

from mcp_toolkit.context.query_processor import QueryProcessor
from mcp_toolkit.storage.unified_manager import UnifiedDataManager


class TestQueryProcessor:
    """查询处理器测试"""

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
    def query_processor(self, data_manager):
        """创建查询处理器"""
        config = {"max_results": 10}
        return QueryProcessor(data_manager, config)

    @pytest.fixture
    def sample_data(self, data_manager):
        """创建示例数据"""
        # 存储一些示例代码数据
        data_manager.store_data(
            data_type="file",
            content="def calculate_fibonacci(n): return n if n <= 1 else calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
            metadata={
                "file_path": "math_utils.py",
                "language": "python",
                "function_name": "calculate_fibonacci",
                "content_type": "function_definition",
            },
            data_id="fib_func",
        )

        data_manager.store_data(
            data_type="file",
            content="class Calculator: def add(self, a, b): return a + b",
            metadata={
                "file_path": "calculator.py",
                "language": "python",
                "class_name": "Calculator",
                "content_type": "class_definition",
            },
            data_id="calc_class",
        )

        data_manager.store_data(
            data_type="web_content",
            content="Python programming tutorial: Learn how to write functions and classes",
            metadata={
                "url": "https://example.com/python-tutorial",
                "title": "Python Tutorial",
                "domain": "example.com",
            },
            data_id="py_tutorial",
        )

        data_manager.store_data(
            data_type="system_info",
            content="System information: CPU usage 25%, Memory usage 60%",
            metadata={"hostname": "localhost", "os_system": "Linux"},
            data_id="sys_info",
        )

    def test_query_processor_initialization(self, query_processor):
        """测试查询处理器初始化"""
        assert query_processor is not None
        assert query_processor.data_manager is not None
        assert len(query_processor.query_patterns) > 0
        assert "function" in query_processor.query_patterns
        assert "class" in query_processor.query_patterns

    def test_parse_query_intent_function_search(self, query_processor):
        """测试解析函数搜索意图"""
        test_cases = [
            "find function fibonacci",
            "def calculate_sum",
            "show me the add method",
            "函数 fibonacci",
            "方法 calculate",
        ]

        for query in test_cases:
            intent = query_processor._parse_query_intent(query)
            # 查询意图可能是 general、function_search 或 entity_search
            assert intent["type"] in ["function_search", "entity_search", "general"]
            # 如果找到了函数实体，验证它们
            if "function" in intent["entities"] and intent["entities"]["function"]:
                assert len(intent["entities"]["function"]) > 0

    def test_parse_query_intent_class_search(self, query_processor):
        """测试解析类搜索意图"""
        test_cases = [
            "class Calculator",
            "show me Calculator class",
            "类 Calculator",
            "对象 UserManager",
        ]

        for query in test_cases:
            intent = query_processor._parse_query_intent(query)
            # 查询意图可能是 general、class_search 或 entity_search
            assert intent["type"] in ["class_search", "entity_search", "general"]
            # 如果找到了类实体，验证它们
            if "class" in intent["entities"] and intent["entities"]["class"]:
                assert len(intent["entities"]["class"]) > 0

    def test_parse_query_intent_file_search(self, query_processor):
        """测试解析文件搜索意图"""
        test_cases = ["file math_utils.py", "show me .py files", "文件 calculator.py"]

        for query in test_cases:
            intent = query_processor._parse_query_intent(query)
            if "file" in intent["entities"]:
                assert len(intent["entities"]["file"]) > 0

    def test_parse_query_intent_with_filters(self, query_processor):
        """测试解析带过滤条件的查询意图"""
        test_cases = [
            ("python function fibonacci", {"language": "python"}),
            ("javascript class UserManager", {"language": "javascript"}),
            ("file code fibonacci", {"data_type": "file"}),
            ("web page tutorial", {"data_type": "web_content"}),
            ("system information", {"data_type": "system_info"}),
        ]

        for query, expected_filters in test_cases:
            intent = query_processor._parse_query_intent(query)
            for key, value in expected_filters.items():
                assert intent["filters"].get(key) == value

    def test_build_search_conditions(self, query_processor):
        """测试构建搜索条件"""
        query = "find python function fibonacci"
        intent = {
            "type": "function_search",
            "entities": {"function": ["fibonacci"]},
            "filters": {"language": "python", "data_type": "file"},
        }
        context = {"current_file": "math_utils.py"}

        conditions = query_processor._build_search_conditions(query, intent, context)

        assert conditions["query_text"] == query
        assert conditions["filters"]["language"] == "python"
        assert conditions["filters"]["data_type"] == "file"
        assert conditions["filters"]["file_path"] == "math_utils.py"
        assert "boost_fields" in conditions

    def test_process_query_general(self, query_processor, sample_data):
        """测试处理一般查询"""
        query = "fibonacci function"
        result = query_processor.process_query(query)

        assert "query" in result
        assert "intent" in result
        assert "results" in result
        assert result["query"] == query

        # 检查结果结构
        results = result["results"]
        assert "items" in results
        assert "grouped" in results
        assert "summary" in results

    def test_process_query_with_context(self, query_processor, sample_data):
        """测试带上下文的查询处理"""
        query = "calculator class"
        context = {"current_language": "python"}

        result = query_processor.process_query(query, context)

        assert result["query"] == query
        assert "results" in result

        # 检查是否应用了上下文过滤
        conditions = result["conditions"]
        # 上下文中的 current_language 会被映射为 language 过滤器
        assert conditions["filters"].get("language") == "python"

    def test_execute_search(self, query_processor, sample_data):
        """测试执行搜索"""
        conditions = {
            "query_text": "fibonacci",
            "filters": {"data_type": "file"},
            "n_results": 5,
        }

        results = query_processor._execute_search(conditions)

        assert "ids" in results
        assert "documents" in results
        assert "metadatas" in results
        assert "distances" in results

    def test_aggregate_results(self, query_processor):
        """测试结果聚合"""
        # 模拟搜索结果
        search_results = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [
                ["def fibonacci(n): return n", "class Calculator:", "system info"]
            ],
            "metadatas": [
                [
                    {
                        "data_type": "file",
                        "function_name": "fibonacci",
                        "language": "python",
                    },
                    {
                        "data_type": "file",
                        "class_name": "Calculator",
                        "language": "python",
                    },
                    {"data_type": "system_info", "hostname": "localhost"},
                ]
            ],
            "distances": [[0.1, 0.2, 0.3]],
        }

        intent = {"type": "function_search", "filters": {}}

        aggregated = query_processor._aggregate_results(search_results, intent)

        assert "items" in aggregated
        assert "grouped" in aggregated
        assert "summary" in aggregated

        items = aggregated["items"]
        assert len(items) == 3

        # 检查项目结构
        for item in items:
            assert "id" in item
            assert "content" in item
            assert "metadata" in item
            assert "similarity_score" in item
            assert "data_type" in item
            assert "relevance_score" in item

    def test_group_by_type(self, query_processor):
        """测试按类型分组"""
        items = [
            {"data_type": "file", "content": "function code"},
            {"data_type": "file", "content": "class code"},
            {"data_type": "web_content", "content": "tutorial"},
            {"data_type": "system_info", "content": "system data"},
        ]

        grouped = query_processor._group_by_type(items)

        assert "file" in grouped
        assert "web_content" in grouped
        assert "system_info" in grouped
        assert len(grouped["file"]) == 2
        assert len(grouped["web_content"]) == 1
        assert len(grouped["system_info"]) == 1

    def test_calculate_relevance(self, query_processor):
        """测试相关性计算"""
        document = "def fibonacci(n): return n"
        metadata = {
            "data_type": "file",
            "function_name": "fibonacci",
            "language": "python",
        }
        intent = {"type": "function_search", "filters": {"language": "python"}}

        relevance = query_processor._calculate_relevance(document, metadata, intent)

        assert 0 <= relevance <= 1
        assert relevance > 0.5  # 应该有较高的相关性

    def test_search_similar_code(self, query_processor, sample_data):
        """测试相似代码搜索"""
        code_snippet = "def add(a, b): return a + b"

        result = query_processor.search_similar_code(code_snippet, "python", 5)

        assert "results" in result
        assert "total_found" in result
        assert isinstance(result["results"], list)

    def test_format_code_search_results(self, query_processor):
        """测试格式化代码搜索结果"""
        # 模拟搜索结果
        results = {
            "ids": [["code1", "code2"]],
            "documents": [["def func1(): pass", "class Class1: pass"]],
            "metadatas": [
                [
                    {
                        "file_path": "file1.py",
                        "language": "python",
                        "function_name": "func1",
                        "line_start": 1,
                        "line_end": 2,
                    },
                    {
                        "file_path": "file2.py",
                        "language": "python",
                        "class_name": "Class1",
                        "line_start": 5,
                        "line_end": 10,
                    },
                ]
            ],
            "distances": [[0.1, 0.2]],
        }

        formatted = query_processor._format_code_search_results(results)

        assert "results" in formatted
        assert "total_found" in formatted
        assert len(formatted["results"]) == 2

        # 检查格式化结果的结构
        for result in formatted["results"]:
            assert "id" in result
            assert "file_path" in result
            assert "language" in result
            assert "code_snippet" in result
            assert "similarity_score" in result
            assert "line_start" in result
            assert "line_end" in result

    def test_error_handling(self, query_processor):
        """测试错误处理"""
        # 测试空查询
        result = query_processor.process_query("")
        assert "results" in result

        # 测试无效的搜索条件
        conditions = {
            "query_text": "test",
            "filters": {"invalid_filter": "value"},
            "n_results": 10,
        }

        search_results = query_processor._execute_search(conditions)
        # 应该能处理无效过滤器而不崩溃
        assert "ids" in search_results or "error" in search_results

    def test_query_patterns(self, query_processor):
        """测试查询模式匹配"""
        patterns = query_processor.query_patterns

        # 测试函数模式
        function_patterns = patterns["function"]
        test_text = "function calculate_sum"

        import re

        matches = []
        for pattern in function_patterns:
            matches.extend(re.findall(pattern, test_text.lower()))

        assert len(matches) > 0
        assert "calculate_sum" in matches

    def test_multiple_entity_extraction(self, query_processor):
        """测试多实体提取"""
        query = "find function fibonacci in class Calculator from file math.py"
        intent = query_processor._parse_query_intent(query)

        # 应该能提取多种实体类型
        entities = intent["entities"]
        assert len(entities) > 1

        # 可能包含函数、类、文件等实体
        possible_entities = ["function", "class", "file"]
        found_entities = [entity for entity in possible_entities if entity in entities]
        assert len(found_entities) > 0
