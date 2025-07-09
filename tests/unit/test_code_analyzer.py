"""
代码分析器单元测试
"""

import pytest

from mcp_toolkit.context.code_analyzer import CodeAnalyzer


class TestCodeAnalyzer:
    """代码分析器测试"""

    @pytest.fixture
    def analyzer(self):
        """创建代码分析器"""
        config = {"chunk_size": 500, "chunk_overlap": 50}
        return CodeAnalyzer(config)

    def test_analyzer_initialization(self, analyzer):
        """测试分析器初始化"""
        assert analyzer is not None
        assert len(analyzer.supported_languages) > 0
        assert ".py" in analyzer.supported_languages
        assert analyzer.supported_languages[".py"] == "python"

    def test_analyze_python_file(self, analyzer):
        """测试分析 Python 文件"""
        python_code = '''
"""模块文档字符串"""
import os
import sys
from pathlib import Path

def hello_world():
    """打印 Hello World"""
    print("Hello, World!")

def calculate_sum(a: int, b: int) -> int:
    """计算两个数的和"""
    return a + b

@property
def get_value(self):
    return self._value

class Calculator:
    """计算器类"""

    def __init__(self):
        """初始化计算器"""
        self.result = 0

    def add(self, value):
        """加法"""
        self.result += value
        return self

    @staticmethod
    def multiply(a, b):
        """静态方法：乘法"""
        return a * b

    @classmethod
    def create_with_value(cls, value):
        """类方法：创建带初值的计算器"""
        calc = cls()
        calc.result = value
        return calc

async def async_function():
    """异步函数"""
    await some_async_operation()
'''

        result = analyzer.analyze_file("test.py", python_code)

        # 基本信息检查
        assert result["file_path"] == "test.py"
        assert result["language"] == "python"
        assert result["line_count"] > 0
        assert result["file_size"] == len(python_code)

        # 函数检查
        functions = result["functions"]
        assert (
            len(functions) >= 4
        )  # hello_world, calculate_sum, get_value, async_function

        hello_func = next((f for f in functions if f["name"] == "hello_world"), None)
        assert hello_func is not None
        assert hello_func["docstring"] == "打印 Hello World"
        assert hello_func["line_start"] > 0

        async_func = next((f for f in functions if f["name"] == "async_function"), None)
        assert async_func is not None
        assert async_func["is_async"] is True

        # 类检查
        classes = result["classes"]
        assert len(classes) == 1

        calc_class = classes[0]
        assert calc_class["name"] == "Calculator"
        assert calc_class["docstring"] == "计算器类"
        assert (
            len(calc_class["methods"]) >= 3
        )  # __init__, add, multiply, create_with_value

        # 检查方法类型
        methods = calc_class["methods"]
        multiply_method = next((m for m in methods if m["name"] == "multiply"), None)
        assert multiply_method is not None
        assert multiply_method["is_static"] is True

        create_method = next(
            (m for m in methods if m["name"] == "create_with_value"), None
        )
        assert create_method is not None
        assert create_method["is_class"] is True

        # 导入检查
        imports = result["imports"]
        assert len(imports) >= 3

        import_names = [imp["module"] for imp in imports]
        assert "os" in import_names
        assert "sys" in import_names

        # 代码块检查
        code_chunks = result["code_chunks"]
        assert len(code_chunks) > 0

        # 检查函数代码块
        func_chunks = [chunk for chunk in code_chunks if chunk["type"] == "function"]
        assert len(func_chunks) > 0

        # 检查类代码块
        class_chunks = [chunk for chunk in code_chunks if chunk["type"] == "class"]
        assert len(class_chunks) > 0

    def test_analyze_javascript_file(self, analyzer):
        """测试分析 JavaScript 文件"""
        js_code = """
// 用户管理模块
import { database } from './database.js';
import axios from 'axios';

function greetUser(name) {
    return `Hello, ${name}!`;
}

const calculateArea = (width, height) => {
    return width * height;
};

async function fetchUserData(userId) {
    try {
        const response = await axios.get(`/api/users/${userId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching user:', error);
        return null;
    }
}

class UserManager {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.users = new Map();
    }

    addUser(user) {
        this.users.set(user.id, user);
    }

    getUser(id) {
        return this.users.get(id);
    }

    async loadUser(id) {
        const userData = await fetchUserData(id);
        if (userData) {
            this.addUser(userData);
        }
        return userData;
    }
}

class AdminManager extends UserManager {
    constructor(apiUrl) {
        super(apiUrl);
        this.permissions = [];
    }
}

export { UserManager, greetUser };
"""

        result = analyzer.analyze_file("user_manager.js", js_code)

        # 基本信息检查
        assert result["file_path"] == "user_manager.js"
        assert result["language"] == "javascript"

        # 函数检查
        functions = result["functions"]
        assert len(functions) >= 3  # greetUser, calculateArea, fetchUserData

        function_names = [f["name"] for f in functions]
        assert "greetUser" in function_names
        assert "calculateArea" in function_names
        assert "fetchUserData" in function_names

        # 类检查
        classes = result["classes"]
        assert len(classes) >= 2  # UserManager, AdminManager

        class_names = [c["name"] for c in classes]
        assert "UserManager" in class_names
        assert "AdminManager" in class_names

        # 检查继承关系
        admin_class = next((c for c in classes if c["name"] == "AdminManager"), None)
        assert admin_class is not None
        assert admin_class["extends"] == "UserManager"

        # 导入检查
        imports = result["imports"]
        assert len(imports) >= 2

        import_modules = [imp["module"] for imp in imports]
        assert "./database.js" in import_modules
        assert "axios" in import_modules

    def test_analyze_generic_file(self, analyzer):
        """测试分析通用文件"""
        text_content = """
# Configuration File
# This is a comment

server:
  host: localhost
  port: 8080

database:
  url: postgresql://localhost/mydb
  # Another comment
  pool_size: 10

# More configuration
logging:
  level: INFO
  file: app.log
"""

        result = analyzer.analyze_file("config.txt", text_content)

        assert result["file_path"] == "config.txt"
        assert result["language"] == "text"
        assert result["file_size"] == len(text_content)
        assert result["line_count"] > 0

        # 通用分析应该包含基本统计
        assert "blank_lines" in result
        assert "comment_lines" in result
        assert result["comment_lines"] > 0  # 应该检测到注释行

    def test_analyze_yaml_file(self, analyzer):
        """测试分析 YAML 文件"""
        yaml_content = """
# Application Configuration
version: "1.0.0"
name: "My Application"

server:
  host: "0.0.0.0"
  port: 8080
  ssl: false

database:
  driver: "postgresql"
  host: "localhost"
  port: 5432
  name: "myapp"

features:
  - authentication
  - logging
  - monitoring
"""

        result = analyzer.analyze_file("config.yaml", yaml_content)

        assert result["file_path"] == "config.yaml"
        assert result["language"] == "yaml"
        assert result["file_size"] == len(yaml_content)

    def test_code_chunks_generation(self, analyzer):
        """测试代码块生成"""
        python_code = '''
def small_function():
    return "small"

def medium_function():
    """这是一个中等大小的函数"""
    data = []
    for i in range(100):
        data.append(i * 2)
    return data

class TestClass:
    """测试类"""

    def method1(self):
        return "method1"

    def method2(self):
        return "method2"
'''

        result = analyzer.analyze_file("chunks_test.py", python_code)
        code_chunks = result["code_chunks"]

        assert len(code_chunks) > 0

        # 检查函数块
        func_chunks = [chunk for chunk in code_chunks if chunk["type"] == "function"]
        assert len(func_chunks) >= 2

        # 检查类块
        class_chunks = [chunk for chunk in code_chunks if chunk["type"] == "class"]
        assert len(class_chunks) >= 1

        # 验证块内容
        for chunk in code_chunks:
            assert "content" in chunk
            assert len(chunk["content"]) > 0
            assert "type" in chunk

    def test_complexity_calculation(self, analyzer):
        """测试复杂度计算"""
        complex_code = """
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            for i in range(z):
                if i % 2 == 0:
                    try:
                        result = x / i
                    except ZeroDivisionError:
                        result = 0
                    finally:
                        pass
                else:
                    with open("file.txt") as f:
                        content = f.read()
        else:
            while y < 10:
                y += 1
    else:
        return None

    return result if result and result > 0 else 0
"""

        result = analyzer.analyze_file("complex.py", complex_code)

        # 复杂度应该大于0（包含多个控制结构）
        assert result["complexity_score"] > 0

    def test_comment_extraction(self, analyzer):
        """测试注释提取"""
        python_with_comments = '''
# 这是文件头注释
"""
模块文档字符串
多行文档
"""

def function_with_comments():
    # 这是行内注释
    """函数文档字符串"""
    x = 1  # 变量注释
    # 另一个注释
    return x
'''

        result = analyzer.analyze_file("comments.py", python_with_comments)
        comments = result["comments"]

        assert len(comments) > 0

        # 检查注释内容
        comment_texts = [comment["text"] for comment in comments]
        assert any("文件头注释" in text for text in comment_texts)
        assert any("行内注释" in text for text in comment_texts)

    def test_error_handling(self, analyzer):
        """测试错误处理"""
        # 测试语法错误的 Python 代码
        invalid_python = """
def invalid_function(
    # 缺少参数和函数体

class InvalidClass
    # 缺少冒号
    pass
"""

        result = analyzer.analyze_file("invalid.py", invalid_python)

        # 应该能处理语法错误
        assert result["file_path"] == "invalid.py"
        assert result["language"] == "python"

        # 应该包含错误信息
        assert "syntax_error" in result or len(result["functions"]) == 0

    def test_empty_file(self, analyzer):
        """测试空文件"""
        result = analyzer.analyze_file("empty.py", "")

        assert result["file_path"] == "empty.py"
        assert result["language"] == "python"
        assert result["file_size"] == 0
        assert result["line_count"] == 0
        assert len(result["functions"]) == 0
        assert len(result["classes"]) == 0

    def test_supported_languages(self, analyzer):
        """测试支持的语言"""
        test_cases = [
            ("test.py", "python"),
            ("test.js", "javascript"),
            ("test.ts", "typescript"),
            ("test.jsx", "javascript"),
            ("test.tsx", "typescript"),
            ("test.java", "java"),
            ("test.cpp", "cpp"),
            ("test.c", "c"),
            ("test.h", "c"),
            ("test.hpp", "cpp"),
            ("test.go", "go"),
            ("test.rs", "rust"),
            ("test.php", "php"),
            ("test.rb", "ruby"),
            ("test.sh", "shell"),
            ("test.sql", "sql"),
            ("test.html", "html"),
            ("test.css", "css"),
            ("test.json", "json"),
            ("test.yaml", "yaml"),
            ("test.yml", "yaml"),
            ("test.xml", "xml"),
            ("test.md", "markdown"),
            ("test.unknown", "text"),
        ]

        for file_path, expected_language in test_cases:
            result = analyzer.analyze_file(file_path, "# test content")
            assert result["language"] == expected_language, f"Failed for {file_path}"
