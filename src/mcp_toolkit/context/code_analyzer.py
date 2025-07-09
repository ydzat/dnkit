"""
代码分析器

提供代码解析、语法分析、依赖关系分析等功能。
支持多种编程语言的代码理解和结构化分析。
"""

import ast
import re
import tokenize
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.types import ConfigDict


class CodeAnalyzer:
    """代码分析器 - 支持多语言代码分析"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.supported_languages = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".sh": "shell",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".md": "markdown",
        }

    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """分析文件内容，提取结构化信息"""
        file_ext = Path(file_path).suffix.lower()
        language = self.supported_languages.get(file_ext, "text")

        analysis_result = {
            "file_path": file_path,
            "language": language,
            "file_size": len(content),
            "line_count": content.count("\n") + 1 if content else 0,
            "functions": [],
            "classes": [],
            "imports": [],
            "comments": [],
            "complexity_score": 0,
            "dependencies": [],
            "code_chunks": [],
        }

        if language == "python":
            analysis_result.update(self._analyze_python(content))
        elif language in ["javascript", "typescript"]:
            analysis_result.update(self._analyze_javascript(content))
        else:
            analysis_result.update(self._analyze_generic(content))

        # 生成代码块用于向量化
        analysis_result["code_chunks"] = self._generate_code_chunks(
            content, analysis_result
        )

        return analysis_result

    def _analyze_python(self, content: str) -> Dict[str, Any]:
        """分析 Python 代码"""
        result: Dict[str, Any] = {
            "functions": [],
            "classes": [],
            "imports": [],
            "comments": [],
            "complexity_score": 0,
        }

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": node.end_lineno or node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node),
                        "decorators": [
                            self._get_decorator_name(d) for d in node.decorator_list
                        ],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    }
                    result["functions"].append(func_info)

                elif isinstance(node, ast.ClassDef):
                    class_info: Dict[str, Any] = {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": node.end_lineno or node.lineno,
                        "bases": [self._get_base_name(base) for base in node.bases],
                        "docstring": ast.get_docstring(node),
                        "methods": [],
                    }

                    # 获取类方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "line_start": item.lineno,
                                "line_end": item.end_lineno or item.lineno,
                                "is_property": any(
                                    self._get_decorator_name(d) == "property"
                                    for d in item.decorator_list
                                ),
                                "is_static": any(
                                    self._get_decorator_name(d) == "staticmethod"
                                    for d in item.decorator_list
                                ),
                                "is_class": any(
                                    self._get_decorator_name(d) == "classmethod"
                                    for d in item.decorator_list
                                ),
                            }
                            class_info["methods"].append(method_info)

                    result["classes"].append(class_info)

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            result["imports"].append(
                                {
                                    "module": alias.name,
                                    "alias": alias.asname,
                                    "type": "import",
                                }
                            )
                    else:  # ImportFrom
                        module = node.module or ""
                        for alias in node.names:
                            result["imports"].append(
                                {
                                    "module": module,
                                    "name": alias.name,
                                    "alias": alias.asname,
                                    "type": "from_import",
                                }
                            )

            # 提取注释
            result["comments"] = self._extract_python_comments(content)

            # 计算复杂度分数
            result["complexity_score"] = self._calculate_complexity(tree)

        except SyntaxError as e:
            result["syntax_error"] = str(e)
        except Exception as e:
            result["analysis_error"] = str(e)

        return result

    def _analyze_javascript(self, content: str) -> Dict[str, Any]:
        """分析 JavaScript/TypeScript 代码（简化版）"""
        result: Dict[str, Any] = {
            "functions": [],
            "classes": [],
            "imports": [],
            "comments": [],
            "complexity_score": 0,
        }

        # 简单的正则表达式匹配（实际项目中应使用专门的JS解析器）

        # 匹配函数定义
        # 1. 传统函数声明: function functionName()
        func_pattern1 = r"function\s+(\w+)\s*\("
        for match in re.finditer(func_pattern1, content, re.MULTILINE):
            func_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            result["functions"].append(
                {"name": func_name, "line_start": line_num, "type": "function"}
            )

        # 2. 变量赋值函数: const/var/let name = function
        func_pattern2 = r"(?:const|var|let)\s+(\w+)\s*=\s*(?:async\s+)?function"
        for match in re.finditer(func_pattern2, content, re.MULTILINE):
            func_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            result["functions"].append(
                {"name": func_name, "line_start": line_num, "type": "function"}
            )

        # 3. 箭头函数: const name = () => 或 const name = async () =>
        arrow_pattern = r"(?:const|var|let)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"
        for match in re.finditer(arrow_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            result["functions"].append(
                {"name": func_name, "line_start": line_num, "type": "arrow_function"}
            )

        # 4. 类方法: methodName() { 或 async methodName() {
        method_pattern = r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{"
        for match in re.finditer(method_pattern, content, re.MULTILINE):
            method_name = match.group(1)
            # 排除一些关键字
            if method_name not in [
                "if",
                "for",
                "while",
                "switch",
                "catch",
                "function",
                "class",
            ]:
                line_num = content[: match.start()].count("\n") + 1
                result["functions"].append(
                    {"name": method_name, "line_start": line_num, "type": "method"}
                )

        # 匹配类定义
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            base_class = match.group(2)
            line_num = content[: match.start()].count("\n") + 1
            result["classes"].append(
                {"name": class_name, "line_start": line_num, "extends": base_class}
            )

        # 匹配导入语句
        import_pattern = r'(?:import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|import\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            module = match.group(1) or match.group(2) or match.group(3)
            if module:
                result["imports"].append({"module": module, "type": "import"})

        # 提取注释
        result["comments"] = self._extract_js_comments(content)

        return result

    def _analyze_generic(self, content: str) -> Dict[str, Any]:
        """通用代码分析（适用于不支持的语言）"""
        result: Dict[str, Any] = {
            "functions": [],
            "classes": [],
            "imports": [],
            "comments": [],
            "complexity_score": 0,
        }

        # 基本统计
        lines = content.split("\n")
        result["blank_lines"] = sum(1 for line in lines if not line.strip())
        result["comment_lines"] = sum(
            1 for line in lines if line.strip().startswith(("#", "//", "/*", "--"))
        )

        return result

    def _generate_code_chunks(
        self, content: str, analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成用于向量化的代码块"""
        chunks = []
        lines = content.split("\n")
        chunk_size = self.config.get("chunk_size", 1000)
        chunk_overlap = self.config.get("chunk_overlap", 100)

        # 基于函数和类的智能分块
        for func in analysis.get("functions", []):
            start_line = max(0, func["line_start"] - 1)
            end_line = min(len(lines), func.get("line_end", func["line_start"]))

            chunk_content = "\n".join(lines[start_line:end_line])
            if chunk_content.strip():
                chunks.append(
                    {
                        "content": chunk_content,
                        "type": "function",
                        "name": func["name"],
                        "line_start": func["line_start"],
                        "line_end": func.get("line_end", func["line_start"]),
                    }
                )

        for cls in analysis.get("classes", []):
            start_line = max(0, cls["line_start"] - 1)
            end_line = min(len(lines), cls.get("line_end", cls["line_start"]))

            chunk_content = "\n".join(lines[start_line:end_line])
            if chunk_content.strip():
                chunks.append(
                    {
                        "content": chunk_content,
                        "type": "class",
                        "name": cls["name"],
                        "line_start": cls["line_start"],
                        "line_end": cls.get("line_end", cls["line_start"]),
                    }
                )

        # 如果没有函数和类，使用固定大小分块
        if not chunks:
            for i in range(0, len(content), chunk_size - chunk_overlap):
                chunk_content = content[i : i + chunk_size]
                if chunk_content.strip():
                    chunks.append(
                        {
                            "content": chunk_content,
                            "type": "generic",
                            "char_start": i,
                            "char_end": i + len(chunk_content),
                        }
                    )

        return chunks

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """获取装饰器名称"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        return str(decorator)

    def _get_base_name(self, base: ast.expr) -> str:
        """获取基类名称"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return str(base)

    def _extract_python_comments(self, content: str) -> List[Dict[str, Any]]:
        """提取 Python 注释"""
        comments = []
        try:
            tokens = tokenize.generate_tokens(StringIO(content).readline)
            for token in tokens:
                if token.type == tokenize.COMMENT:
                    comments.append(
                        {
                            "text": token.string,
                            "line": token.start[0],
                            "type": "comment",
                        }
                    )
        except Exception:  # nosec B110
            pass  # 注释解析失败时忽略，不影响主要功能
        return comments

    def _extract_js_comments(self, content: str) -> List[Dict[str, Any]]:
        """提取 JavaScript 注释"""
        comments = []

        # 单行注释
        for match in re.finditer(r"//.*$", content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            comments.append(
                {"text": match.group(0), "line": line_num, "type": "single_line"}
            )

        # 多行注释
        for match in re.finditer(r"/\*.*?\*/", content, re.DOTALL):
            line_num = content[: match.start()].count("\n") + 1
            comments.append(
                {"text": match.group(0), "line": line_num, "type": "multi_line"}
            )

        return comments

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """计算代码复杂度（简化版）"""
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity
