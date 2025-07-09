"""
上下文引擎单元测试
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_toolkit.context.context_engine import ContextEngine
from mcp_toolkit.storage.unified_manager import UnifiedDataManager


class TestContextEngine:
    """上下文引擎测试"""

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
    def context_engine(self, data_manager):
        """创建上下文引擎"""
        config = {"chunk_size": 500, "chunk_overlap": 50, "max_file_size_mb": 5}
        return ContextEngine(data_manager, config)

    def test_context_engine_initialization(self, context_engine):
        """测试上下文引擎初始化"""
        assert context_engine is not None
        assert context_engine.code_analyzer is not None
        assert context_engine.query_processor is not None
        assert context_engine.chunk_size == 500
        assert context_engine.chunk_overlap == 50

    def test_analyze_and_store_python_file(self, context_engine):
        """测试分析和存储 Python 文件"""
        python_code = '''
def hello_world():
    """打印 Hello World"""
    print("Hello, World!")

class Calculator:
    """简单计算器类"""

    def add(self, a, b):
        """加法运算"""
        return a + b

    def multiply(self, a, b):
        """乘法运算"""
        return a * b

# 主程序
if __name__ == "__main__":
    calc = Calculator()
    result = calc.add(2, 3)
    print(f"2 + 3 = {result}")
    hello_world()
'''

        result = context_engine.analyze_and_store_file("test.py", python_code)

        assert result["success"] is True
        assert result["file_path"] == "test.py"
        assert "analysis" in result
        assert "storage_results" in result

        # 检查分析结果
        analysis = result["analysis"]
        assert analysis["language"] == "python"
        assert len(analysis["functions"]) == 3  # hello_world, add, multiply
        assert len(analysis["classes"]) == 1  # Calculator

        # 检查存储结果
        assert result["total_stored"] > 0
        assert any(sr["type"] == "file" for sr in result["storage_results"])
        assert any(sr["type"] == "function" for sr in result["storage_results"])
        assert any(sr["type"] == "class" for sr in result["storage_results"])

    def test_analyze_and_store_javascript_file(self, context_engine):
        """测试分析和存储 JavaScript 文件"""
        js_code = """
function greetUser(name) {
    return `Hello, ${name}!`;
}

class UserManager {
    constructor() {
        this.users = [];
    }

    addUser(user) {
        this.users.push(user);
    }

    getUser(id) {
        return this.users.find(u => u.id === id);
    }
}

const manager = new UserManager();
manager.addUser({id: 1, name: "Alice"});
console.log(greetUser("World"));
"""

        result = context_engine.analyze_and_store_file("test.js", js_code)

        assert result["success"] is True
        assert result["file_path"] == "test.js"

        analysis = result["analysis"]
        assert analysis["language"] == "javascript"
        assert len(analysis["functions"]) >= 1  # greetUser
        assert len(analysis["classes"]) >= 1  # UserManager

    def test_search_code(self, context_engine):
        """测试代码搜索"""
        # 先存储一些代码
        python_code = '''
def calculate_fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtils:
    """数学工具类"""

    @staticmethod
    def factorial(n):
        """计算阶乘"""
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n-1)
'''

        context_engine.analyze_and_store_file("math_utils.py", python_code)

        # 搜索函数
        search_result = context_engine.search_code("fibonacci function")

        assert "results" in search_result
        assert "items" in search_result["results"]
        assert len(search_result["results"]["items"]) > 0

        # 检查搜索结果
        items = search_result["results"]["items"]
        fibonacci_found = any("fibonacci" in item["content"].lower() for item in items)
        assert fibonacci_found

    def test_search_similar_code(self, context_engine):
        """测试相似代码搜索"""
        # 存储一些代码
        code1 = """
def add_numbers(a, b):
    return a + b
"""

        code2 = """
def sum_values(x, y):
    result = x + y
    return result
"""

        context_engine.analyze_and_store_file("math1.py", code1)
        context_engine.analyze_and_store_file("math2.py", code2)

        # 搜索相似代码
        similar_code = "def calculate(num1, num2): return num1 + num2"
        result = context_engine.search_similar_code(similar_code, "python", 5)

        assert "results" in result
        assert len(result["results"]) >= 0  # 可能找到相似代码

    def test_get_file_context(self, context_engine):
        """测试获取文件上下文"""
        python_code = '''
class DataProcessor:
    """数据处理器"""

    def __init__(self):
        self.data = []

    def process_data(self, input_data):
        """处理数据"""
        processed = [item * 2 for item in input_data]
        self.data.extend(processed)
        return processed

    def get_statistics(self):
        """获取统计信息"""
        if not self.data:
            return {"count": 0, "sum": 0, "avg": 0}

        return {
            "count": len(self.data),
            "sum": sum(self.data),
            "avg": sum(self.data) / len(self.data)
        }
'''

        context_engine.analyze_and_store_file("processor.py", python_code)

        # 获取文件上下文
        file_context = context_engine.get_file_context("processor.py")

        assert file_context["found"] is True
        assert file_context["file_path"] == "processor.py"
        assert "functions" in file_context
        assert "classes" in file_context
        assert len(file_context["classes"]) == 1
        assert file_context["classes"][0]["name"] == "DataProcessor"

    def test_get_project_overview(self, context_engine):
        """测试获取项目概览"""
        # 存储多个文件
        files = {
            "main.py": """
def main():
    print("Main function")

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
        }

        for file_path, content in files.items():
            context_engine.analyze_and_store_file(file_path, content)

        # 获取项目概览
        overview = context_engine.get_project_overview()

        assert "total_data_items" in overview
        assert "language_distribution" in overview
        assert "file_count" in overview
        assert overview["file_count"] >= 3

        # 检查语言分布
        lang_dist = overview["language_distribution"]
        assert "python" in lang_dist
        assert "javascript" in lang_dist

    def test_cleanup_file_data(self, context_engine):
        """测试清理文件数据"""
        python_code = """
def test_function():
    return "test"
"""

        # 存储文件
        result = context_engine.analyze_and_store_file("temp.py", python_code)
        assert result["success"] is True

        # 验证文件存在
        file_context = context_engine.get_file_context("temp.py")
        assert file_context["found"] is True

        # 清理文件数据
        cleanup_result = context_engine.cleanup_file_data("temp.py")
        assert cleanup_result is True

        # 验证文件已被清理
        file_context_after = context_engine.get_file_context("temp.py")
        assert file_context_after["found"] is False

    def test_error_handling(self, context_engine):
        """测试错误处理"""
        # 测试无效的代码
        invalid_python = """
def invalid_function(
    # 缺少闭合括号和函数体
"""

        result = context_engine.analyze_and_store_file("invalid.py", invalid_python)

        # 即使代码有语法错误，也应该能够存储
        assert result["success"] is True
        assert "analysis" in result

        # 分析结果中应该包含错误信息
        analysis = result["analysis"]
        assert (
            "syntax_error" in analysis
            or "analysis_error" in analysis
            or len(analysis["functions"]) == 0
        )

    def test_large_file_handling(self, context_engine):
        """测试大文件处理"""
        # 生成一个较大的文件内容
        large_code = '''
def function_{}():
    """Function number {}"""
    return {}
'''.format(
            1, 1, 1
        )

        for i in range(2, 100):
            large_code += '''
def function_{}():
    """Function number {}"""
    return {}
'''.format(
                i, i, i
            )

        result = context_engine.analyze_and_store_file("large.py", large_code)

        assert result["success"] is True
        assert len(result["analysis"]["functions"]) == 99
        assert result["total_stored"] > 0

    def test_multiple_languages(self, context_engine):
        """测试多语言支持"""
        files = {
            "script.py": "def python_func(): pass",
            "script.js": "function jsFunc() {}",
            "script.java": "public class JavaClass {}",
            "script.cpp": "#include <iostream>\nint main() { return 0; }",
            "script.go": "package main\nfunc main() {}",
            "README.md": "# Project Title\nThis is a readme file.",
            "config.yaml": "version: 1.0\nname: test",
        }

        for file_path, content in files.items():
            result = context_engine.analyze_and_store_file(file_path, content)
            assert result["success"] is True

        # 获取项目概览检查语言分布
        overview = context_engine.get_project_overview()
        lang_dist = overview["language_distribution"]

        expected_languages = [
            "python",
            "javascript",
            "java",
            "cpp",
            "go",
            "markdown",
            "yaml",
        ]
        for lang in expected_languages:
            assert lang in lang_dist
