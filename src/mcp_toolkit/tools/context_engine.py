"""
增强上下文引擎工具

实现深度代码理解、依赖分析、调用图构建和重构建议功能。
"""

import ast
import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from ..storage.unified_manager import UnifiedDataManager
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
)


class BaseContextTool(BaseTool):
    """上下文引擎工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager = UnifiedDataManager(
            self.config.get("chromadb_path", "./mcp_unified_db")
        )
        self.supported_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".cs": "csharp",
            ".kt": "kotlin",
            ".swift": "swift",
        }

    def _get_file_language(self, file_path: str) -> str:
        """获取文件语言类型"""
        ext = Path(file_path).suffix.lower()
        return self.supported_extensions.get(ext, "unknown")

    def _read_file_safely(self, file_path: str) -> Optional[str]:
        """安全读取文件内容"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None

    def _find_files_by_pattern(self, directory: str, patterns: List[str]) -> List[str]:
        """根据模式查找文件"""
        files = []
        for pattern in patterns:
            if pattern.startswith("*."):
                # 扩展名模式
                ext = pattern[1:]
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        if filename.endswith(ext):
                            files.append(os.path.join(root, filename))
            else:
                # 文件名模式
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        if re.match(pattern, filename):
                            files.append(os.path.join(root, filename))
        return files

    def _collect_target_files(self, target: Dict[str, Any]) -> List[str]:
        """收集目标文件"""
        target_type = target.get("type", "directory")
        path = target.get("path", ".")
        patterns = target.get("patterns", ["*.py", "*.js", "*.ts"])

        files = []

        if target_type == "file":
            if os.path.isfile(path):
                files.append(path)
        elif target_type == "directory":
            files = self._find_files_by_pattern(path, patterns)
        elif target_type == "project":
            # 项目级别分析，查找多个目录
            common_dirs = ["src", "lib", "app", "components", "modules"]
            for dir_name in common_dirs:
                if os.path.isdir(os.path.join(path, dir_name)):
                    files.extend(
                        self._find_files_by_pattern(
                            os.path.join(path, dir_name), patterns
                        )
                    )

            # 如果没有找到常见目录，则分析根目录
            if not files:
                files = self._find_files_by_pattern(path, patterns)

        return files


class DependencyAnalyzer(BaseContextTool):
    """依赖关系分析器"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_dependencies",
            description="分析代码依赖关系和影响范围",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "directory", "project"],
                                "description": "分析目标类型",
                                "default": "directory",
                            },
                            "path": {
                                "type": "string",
                                "description": "目标路径",
                                "default": ".",
                            },
                            "patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "文件匹配模式",
                                "default": ["*.py", "*.js", "*.ts"],
                            },
                        },
                        "description": "分析目标配置",
                    },
                    "analysis_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "imports",
                                "exports",
                                "circular",
                                "impact",
                                "graph",
                            ],
                        },
                        "description": "分析类型",
                        "default": ["imports", "circular", "impact"],
                    },
                    "depth_limit": {
                        "type": "integer",
                        "description": "依赖深度限制",
                        "default": 10,
                    },
                    "include_external": {
                        "type": "boolean",
                        "description": "是否包含外部依赖",
                        "default": False,
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["detailed", "summary", "graph"],
                        "description": "输出格式",
                        "default": "detailed",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行依赖分析"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {"type": "directory", "path": "."})
            analysis_types = params.get(
                "analysis_types", ["imports", "circular", "impact"]
            )
            depth_limit = params.get("depth_limit", 10)
            include_external = params.get("include_external", False)
            output_format = params.get("output_format", "detailed")

            # 解析目标路径
            if "path" in target:
                target["path"] = self._resolve_path(target["path"], request)

            # 收集目标文件
            target_files = self._collect_target_files(target)

            if not target_files:
                return self._create_error_result("NO_FILES", "未找到符合条件的文件")

            # 执行依赖分析
            analysis_results = {}

            if "imports" in analysis_types:
                analysis_results["imports"] = self._analyze_imports(
                    target_files, include_external
                )

            if "exports" in analysis_types:
                analysis_results["exports"] = self._analyze_exports(target_files)

            if "circular" in analysis_types:
                analysis_results["circular"] = self._detect_circular_dependencies(
                    target_files
                )

            if "impact" in analysis_types:
                analysis_results["impact"] = self._analyze_impact(target_files)

            if "graph" in analysis_types:
                analysis_results["graph"] = self._build_dependency_graph(
                    target_files, depth_limit
                )

            # 生成分析报告
            analysis_report = {
                "target": target,
                "analysis_types": analysis_types,
                "files_analyzed": len(target_files),
                "analysis_results": analysis_results,
                "summary": self._generate_dependency_summary(analysis_results),
                "recommendations": self._generate_dependency_recommendations(
                    analysis_results
                ),
                "timestamp": time.time(),
            }

            # 格式化输出
            if output_format == "summary":
                analysis_report = self._format_summary_output(analysis_report)
            elif output_format == "graph":
                analysis_report = self._format_graph_output(analysis_report)

            # 存储分析结果
            self._store_analysis_result("dependency_analysis", analysis_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(analysis_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            resources = ResourceUsage(
                memory_mb=len(str(analysis_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            return self._create_success_result(analysis_report, metadata, resources)

        except Exception as e:
            print(f"依赖分析执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _collect_target_files(self, target: Dict[str, Any]) -> List[str]:
        """收集目标文件"""
        target_type = target.get("type", "directory")
        path = target.get("path", ".")
        patterns = target.get("patterns", ["*.py", "*.js", "*.ts"])

        files = []

        if target_type == "file":
            if os.path.isfile(path):
                files.append(path)
        elif target_type == "directory":
            files = self._find_files_by_pattern(path, patterns)
        elif target_type == "project":
            # 项目级别分析，查找多个目录
            common_dirs = ["src", "lib", "app", "components", "modules"]
            for dir_name in common_dirs:
                if os.path.isdir(os.path.join(path, dir_name)):
                    files.extend(
                        self._find_files_by_pattern(
                            os.path.join(path, dir_name), patterns
                        )
                    )

            # 如果没有找到常见目录，则分析根目录
            if not files:
                files = self._find_files_by_pattern(path, patterns)

        return files

    def _analyze_imports(
        self, files: List[str], include_external: bool
    ) -> Dict[str, Any]:
        """分析导入依赖"""
        imports_data = {}

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            file_imports = self._extract_imports(content, language, include_external)

            imports_data[file_path] = {
                "language": language,
                "imports": file_imports,
                "import_count": len(file_imports),
            }

        return {
            "files": imports_data,
            "total_imports": sum(
                data["import_count"] for data in imports_data.values()
            ),
            "import_statistics": self._calculate_import_statistics(imports_data),
        }

    def _extract_imports(
        self, content: str, language: str, include_external: bool
    ) -> List[Dict[str, Any]]:
        """提取导入语句"""
        imports = []

        if language == "python":
            imports = self._extract_python_imports(content, include_external)
        elif language in ["javascript", "typescript"]:
            imports = self._extract_js_imports(content, include_external)
        elif language == "java":
            imports = self._extract_java_imports(content, include_external)
        # 可以扩展支持更多语言

        return imports

    def _extract_python_imports(
        self, content: str, include_external: bool
    ) -> List[Dict[str, Any]]:
        """提取Python导入"""
        imports = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "is_external": self._is_external_module(alias.name),
                        }

                        if include_external or not import_info["is_external"]:
                            imports.append(import_info)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        import_info = {
                            "type": "from_import",
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "level": node.level,
                            "is_external": self._is_external_module(module),
                        }

                        if include_external or not import_info["is_external"]:
                            imports.append(import_info)

        except SyntaxError as e:
            print(f"Python语法错误: {e}")

        return imports

    def _extract_js_imports(
        self, content: str, include_external: bool
    ) -> List[Dict[str, Any]]:
        """提取JavaScript/TypeScript导入"""
        imports = []

        # 使用正则表达式提取导入语句（简化实现）
        import_patterns = [
            r'import\s+(.+?)\s+from\s+["\'](.+?)["\']',
            r'import\s+["\'](.+?)["\']',
            r'const\s+(.+?)\s*=\s*require\s*\(\s*["\'](.+?)["\']\s*\)',
            r'require\s*\(\s*["\'](.+?)["\']\s*\)',
        ]

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in import_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    if len(match.groups()) == 2:
                        imported, module = match.groups()
                    else:
                        module = match.group(1)
                        imported = None

                    import_info = {
                        "type": "import",
                        "module": module,
                        "imported": imported,
                        "line": line_num,
                        "is_external": self._is_external_js_module(module),
                    }

                    if include_external or not import_info["is_external"]:
                        imports.append(import_info)

        return imports

    def _extract_java_imports(
        self, content: str, include_external: bool
    ) -> List[Dict[str, Any]]:
        """提取Java导入"""
        imports = []

        import_pattern = r"import\s+(static\s+)?([a-zA-Z_][a-zA-Z0-9_.]*(?:\.\*)?)\s*;"
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(import_pattern, line)
            for match in matches:
                is_static = match.group(1) is not None
                module = match.group(2)

                import_info = {
                    "type": "static_import" if is_static else "import",
                    "module": module,
                    "line": line_num,
                    "is_external": self._is_external_java_module(module),
                }

                if include_external or not import_info["is_external"]:
                    imports.append(import_info)

        return imports

    def _is_external_module(self, module_name: str) -> bool:
        """判断是否为外部Python模块"""
        if not module_name:
            return False

        # 相对导入
        if module_name.startswith("."):
            return False

        # 标准库模块（简化判断）
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "operator",
            "pathlib",
            "re",
            "math",
            "random",
            "string",
            "typing",
            "dataclasses",
            "enum",
            "abc",
            "asyncio",
            "threading",
            "multiprocessing",
            "subprocess",
            "urllib",
            "http",
            "socket",
        }

        root_module = module_name.split(".")[0]
        return root_module not in stdlib_modules

    def _is_external_js_module(self, module_name: str) -> bool:
        """判断是否为外部JavaScript模块"""
        if not module_name:
            return False

        # 相对路径
        if module_name.startswith(".") or module_name.startswith("/"):
            return False

        # Node.js内置模块
        builtin_modules = {
            "fs",
            "path",
            "os",
            "util",
            "events",
            "stream",
            "buffer",
            "crypto",
            "http",
            "https",
            "url",
            "querystring",
            "zlib",
        }

        return module_name not in builtin_modules

    def _is_external_java_module(self, module_name: str) -> bool:
        """判断是否为外部Java模块"""
        if not module_name:
            return False

        # Java标准库包
        jdk_packages = {
            "java.lang",
            "java.util",
            "java.io",
            "java.nio",
            "java.net",
            "java.time",
            "java.text",
            "java.math",
            "java.security",
            "javax.swing",
            "javax.sql",
            "javax.xml",
        }

        for pkg in jdk_packages:
            if module_name.startswith(pkg):
                return False

        return True

    def _calculate_import_statistics(
        self, imports_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算导入统计"""
        total_files = len(imports_data)
        if total_files == 0:
            return {}

        import_counts = [data["import_count"] for data in imports_data.values()]

        # 统计最常用的模块
        module_usage: Dict[str, int] = defaultdict(int)
        for data in imports_data.values():
            for imp in data["imports"]:
                module_usage[imp["module"]] += 1

        most_used_modules = sorted(
            module_usage.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_files": total_files,
            "avg_imports_per_file": sum(import_counts) / total_files,
            "max_imports_in_file": max(import_counts) if import_counts else 0,
            "min_imports_in_file": min(import_counts) if import_counts else 0,
            "most_used_modules": most_used_modules,
        }

    def _analyze_exports(self, files: List[str]) -> Dict[str, Any]:
        """分析导出依赖"""
        # 简化实现，主要针对Python和JavaScript
        exports_data = {}

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            file_exports = self._extract_exports(content, language)

            exports_data[file_path] = {
                "language": language,
                "exports": file_exports,
                "export_count": len(file_exports),
            }

        return {
            "files": exports_data,
            "total_exports": sum(
                data["export_count"] for data in exports_data.values()
            ),
        }

    def _extract_exports(self, content: str, language: str) -> List[Dict[str, Any]]:
        """提取导出语句"""
        exports = []

        if language == "python":
            # Python通过__all__或函数/类定义来导出
            exports = self._extract_python_exports(content)
        elif language in ["javascript", "typescript"]:
            exports = self._extract_js_exports(content)

        return exports

    def _extract_python_exports(self, content: str) -> List[Dict[str, Any]]:
        """提取Python导出"""
        exports = []

        try:
            tree = ast.parse(content)

            # 查找__all__定义
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(node.value, ast.List):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Str):
                                        exports.append(
                                            {
                                                "type": "explicit_export",
                                                "name": elt.s,
                                                "line": node.lineno,
                                            }
                                        )

            # 查找公共函数和类定义
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not node.name.startswith("_"):  # 公共成员
                        exports.append(
                            {
                                "type": (
                                    "function"
                                    if isinstance(node, ast.FunctionDef)
                                    else "class"
                                ),
                                "name": node.name,
                                "line": node.lineno,
                            }
                        )

        except SyntaxError:
            pass

        return exports

    def _extract_js_exports(self, content: str) -> List[Dict[str, Any]]:
        """提取JavaScript导出"""
        exports = []

        export_patterns = [
            r"export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)",
            r"export\s+default\s+(\w+)",
            r"export\s*{\s*([^}]+)\s*}",
            r"module\.exports\s*=\s*(\w+)",
            r"exports\.(\w+)\s*=",
        ]

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in export_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    export_name = match.group(1)
                    exports.append(
                        {"type": "export", "name": export_name, "line": line_num}
                    )

        return exports

    def _detect_circular_dependencies(self, files: List[str]) -> Dict[str, Any]:
        """检测循环依赖"""
        # 构建依赖图
        dependency_graph = {}

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            imports = self._extract_imports(content, language, False)  # 只分析内部依赖

            dependencies = []
            for imp in imports:
                if not imp.get("is_external", True):
                    # 尝试解析为文件路径
                    dep_file = self._resolve_import_to_file(imp, file_path, files)
                    if dep_file:
                        dependencies.append(dep_file)

            dependency_graph[file_path] = dependencies

        # 使用DFS检测循环
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependency_graph.get(node, []):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for file_path in dependency_graph:
            if file_path not in visited:
                dfs(file_path, [])

        return {
            "cycles_found": len(cycles),
            "cycles": cycles,
            "dependency_graph": dependency_graph,
            "analysis_summary": self._summarize_circular_analysis(
                cycles, dependency_graph
            ),
        }

    def _resolve_import_to_file(
        self, import_info: Dict[str, Any], current_file: str, all_files: List[str]
    ) -> Optional[str]:
        """将导入语句解析为文件路径"""
        module = import_info.get("module", "")
        if not module:
            return None

        current_dir = os.path.dirname(current_file)

        # 处理相对导入
        if module.startswith("."):
            # Python相对导入
            level = import_info.get("level", 1)
            base_dir = current_dir
            for _ in range(level - 1):
                base_dir = os.path.dirname(base_dir)

            module_path = module.lstrip(".")
            if module_path:
                target_path = os.path.join(base_dir, module_path.replace(".", os.sep))
            else:
                target_path = base_dir
        else:
            # 绝对导入或相对路径
            if module.startswith("./") or module.startswith("../"):
                # JavaScript相对路径
                target_path = os.path.normpath(os.path.join(current_dir, module))
            else:
                # 尝试作为模块路径
                target_path = module.replace(".", os.sep)

        # 尝试匹配现有文件
        for file_path in all_files:
            if (
                target_path in file_path
                or file_path.endswith(target_path + ".py")
                or file_path.endswith(target_path + ".js")
            ):
                return file_path

        return None

    def _summarize_circular_analysis(
        self, cycles: List[List[str]], dependency_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """总结循环依赖分析"""
        total_files = len(dependency_graph)
        files_in_cycles = set()

        for cycle in cycles:
            files_in_cycles.update(cycle)

        return {
            "total_files_analyzed": total_files,
            "files_with_cycles": len(files_in_cycles),
            "cycle_percentage": (
                len(files_in_cycles) / total_files * 100 if total_files > 0 else 0
            ),
            "largest_cycle_size": max(len(cycle) for cycle in cycles) if cycles else 0,
            "average_cycle_size": (
                sum(len(cycle) for cycle in cycles) / len(cycles) if cycles else 0
            ),
        }

    def _analyze_impact(self, files: List[str]) -> Dict[str, Any]:
        """分析影响范围"""
        # 构建反向依赖图（谁依赖于谁）
        reverse_deps = defaultdict(set)
        forward_deps = defaultdict(set)

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            imports = self._extract_imports(content, language, False)

            for imp in imports:
                if not imp.get("is_external", True):
                    dep_file = self._resolve_import_to_file(imp, file_path, files)
                    if dep_file:
                        reverse_deps[dep_file].add(file_path)
                        forward_deps[file_path].add(dep_file)

        # 计算每个文件的影响范围
        impact_analysis = {}

        for file_path in files:
            # 直接依赖者
            direct_dependents = list(reverse_deps.get(file_path, set()))

            # 间接依赖者（使用BFS）
            all_dependents = self._find_all_dependents(file_path, reverse_deps)

            # 依赖的文件
            direct_dependencies = list(forward_deps.get(file_path, set()))
            all_dependencies = self._find_all_dependencies(file_path, forward_deps)

            impact_analysis[file_path] = {
                "direct_dependents": direct_dependents,
                "all_dependents": list(all_dependents),
                "direct_dependencies": direct_dependencies,
                "all_dependencies": list(all_dependencies),
                "impact_score": len(all_dependents),  # 影响分数
                "dependency_score": len(all_dependencies),  # 依赖分数
            }

        # 找出高影响文件
        high_impact_files = sorted(
            impact_analysis.items(),
            key=lambda x: (
                float(x[1]["impact_score"])
                if isinstance(x[1]["impact_score"], (int, float, str))
                else 0
            ),
            reverse=True,
        )[:10]

        return {
            "impact_analysis": impact_analysis,
            "high_impact_files": high_impact_files,
            "statistics": self._calculate_impact_statistics(impact_analysis),
        }

    def _find_all_dependents(
        self, file_path: str, reverse_deps: Dict[str, Set[str]]
    ) -> Set[str]:
        """查找所有依赖者（递归）"""
        all_dependents = set()
        queue = deque([file_path])
        visited = set()

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            dependents = reverse_deps.get(current, set())
            for dependent in dependents:
                if dependent not in all_dependents:
                    all_dependents.add(dependent)
                    queue.append(dependent)

        return all_dependents

    def _find_all_dependencies(
        self, file_path: str, forward_deps: Dict[str, Set[str]]
    ) -> Set[str]:
        """查找所有依赖（递归）"""
        all_dependencies = set()
        queue = deque([file_path])
        visited = set()

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            dependencies = forward_deps.get(current, set())
            for dependency in dependencies:
                if dependency not in all_dependencies:
                    all_dependencies.add(dependency)
                    queue.append(dependency)

        return all_dependencies

    def _calculate_impact_statistics(
        self, impact_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算影响统计"""
        if not impact_analysis:
            return {}

        impact_scores = [data["impact_score"] for data in impact_analysis.values()]
        dependency_scores = [
            data["dependency_score"] for data in impact_analysis.values()
        ]

        return {
            "total_files": len(impact_analysis),
            "avg_impact_score": sum(impact_scores) / len(impact_scores),
            "max_impact_score": max(impact_scores),
            "avg_dependency_score": sum(dependency_scores) / len(dependency_scores),
            "max_dependency_score": max(dependency_scores),
            "files_with_high_impact": len([s for s in impact_scores if s > 5]),
            "files_with_many_deps": len([s for s in dependency_scores if s > 10]),
        }

    def _build_dependency_graph(
        self, files: List[str], depth_limit: int
    ) -> Dict[str, Any]:
        """构建依赖图"""
        graph: Dict[str, Any] = {"nodes": [], "edges": [], "metadata": {}}

        # 构建节点
        for file_path in files:
            graph["nodes"].append(
                {
                    "id": file_path,
                    "label": os.path.basename(file_path),
                    "type": "file",
                    "language": self._get_file_language(file_path),
                }
            )

        # 构建边
        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            imports = self._extract_imports(content, language, False)

            for imp in imports:
                if not imp.get("is_external", True):
                    dep_file = self._resolve_import_to_file(imp, file_path, files)
                    if dep_file:
                        graph["edges"].append(
                            {
                                "source": file_path,
                                "target": dep_file,
                                "type": "dependency",
                                "import_info": imp,
                            }
                        )

        graph["metadata"] = {
            "total_nodes": len(graph["nodes"]),
            "total_edges": len(graph["edges"]),
            "density": (
                len(graph["edges"]) / (len(graph["nodes"]) * (len(graph["nodes"]) - 1))
                if len(graph["nodes"]) > 1
                else 0
            ),
        }

        return graph

    def _generate_dependency_summary(
        self, analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成依赖摘要"""
        summary = {}

        if "imports" in analysis_results:
            imports_data = analysis_results["imports"]
            summary["imports"] = {
                "total_imports": imports_data.get("total_imports", 0),
                "files_with_imports": len(imports_data.get("files", {})),
                "avg_imports_per_file": imports_data.get("import_statistics", {}).get(
                    "avg_imports_per_file", 0
                ),
            }

        if "circular" in analysis_results:
            circular_data = analysis_results["circular"]
            summary["circular_dependencies"] = {
                "cycles_found": circular_data.get("cycles_found", 0),
                "files_affected": circular_data.get("analysis_summary", {}).get(
                    "files_with_cycles", 0
                ),
            }

        if "impact" in analysis_results:
            impact_data = analysis_results["impact"]
            summary["impact_analysis"] = {
                "high_impact_files": len(impact_data.get("high_impact_files", [])),
                "avg_impact_score": impact_data.get("statistics", {}).get(
                    "avg_impact_score", 0
                ),
            }

        return summary

    def _generate_dependency_recommendations(
        self, analysis_results: Dict[str, Any]
    ) -> List[str]:
        """生成依赖建议"""
        recommendations = []

        # 循环依赖建议
        if "circular" in analysis_results:
            cycles_found = analysis_results["circular"].get("cycles_found", 0)
            if cycles_found > 0:
                recommendations.append(
                    f"发现 {cycles_found} 个循环依赖，建议重构以消除循环"
                )
                if cycles_found > 5:
                    recommendations.append("循环依赖过多，建议重新设计模块架构")

        # 导入建议
        if "imports" in analysis_results:
            stats = analysis_results["imports"].get("import_statistics", {})
            avg_imports = stats.get("avg_imports_per_file", 0)
            if avg_imports > 20:
                recommendations.append("平均导入数过多，建议减少模块间耦合")

        # 影响分析建议
        if "impact" in analysis_results:
            high_impact_files = analysis_results["impact"].get("high_impact_files", [])
            if len(high_impact_files) > 0:
                top_file = high_impact_files[0][0]
                recommendations.append(
                    f"文件 {os.path.basename(top_file)} 影响范围较大，修改时需谨慎"
                )

        if not recommendations:
            recommendations.append("依赖结构良好，无明显问题")

        return recommendations

    def _format_summary_output(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """格式化摘要输出"""
        return {
            "target": report["target"],
            "files_analyzed": report["files_analyzed"],
            "summary": report["summary"],
            "recommendations": report["recommendations"],
            "timestamp": report["timestamp"],
        }

    def _format_graph_output(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """格式化图形输出"""
        graph_data = report["analysis_results"].get("graph", {})
        return {
            "target": report["target"],
            "graph": graph_data,
            "summary": report["summary"],
            "timestamp": report["timestamp"],
        }

    def _store_analysis_result(self, analysis_type: str, data: Dict[str, Any]) -> None:
        """存储分析结果"""
        try:
            content = f"Dependency analysis: {analysis_type}"
            metadata = {
                "analysis_type": analysis_type,
                "files_analyzed": data.get("files_analyzed", 0),
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="dependency_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储分析结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class CallGraphBuilder(BaseContextTool):
    """调用图构建器"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="build_call_graph",
            description="构建函数调用关系图和数据流分析",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "directory", "function"],
                                "description": "分析目标类型",
                                "default": "directory",
                            },
                            "path": {
                                "type": "string",
                                "description": "目标路径",
                                "default": ".",
                            },
                            "function_name": {
                                "type": "string",
                                "description": "特定函数名（当type为function时）",
                            },
                            "patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "文件匹配模式",
                                "default": ["*.py", "*.js", "*.ts"],
                            },
                        },
                        "description": "分析目标配置",
                    },
                    "analysis_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "call_graph",
                                "data_flow",
                                "dead_code",
                                "hotspots",
                            ],
                        },
                        "description": "分析类型",
                        "default": ["call_graph", "dead_code"],
                    },
                    "depth_limit": {
                        "type": "integer",
                        "description": "调用深度限制",
                        "default": 5,
                    },
                    "include_external": {
                        "type": "boolean",
                        "description": "是否包含外部函数调用",
                        "default": False,
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["detailed", "summary", "graph"],
                        "description": "输出格式",
                        "default": "detailed",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行调用图构建"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {"type": "directory", "path": "."})
            analysis_types = params.get("analysis_types", ["call_graph", "dead_code"])
            depth_limit = params.get("depth_limit", 5)
            include_external = params.get("include_external", False)
            output_format = params.get("output_format", "detailed")

            # 收集目标文件
            target_files = self._collect_target_files(target)

            if not target_files:
                return self._create_error_result("NO_FILES", "未找到符合条件的文件")

            # 提取所有函数定义
            all_functions = self._extract_all_functions(target_files)

            # 执行调用图分析
            analysis_results = {}

            if "call_graph" in analysis_types:
                analysis_results["call_graph"] = self._build_call_graph(
                    all_functions, depth_limit, include_external
                )

            if "data_flow" in analysis_types:
                analysis_results["data_flow"] = self._analyze_data_flow(all_functions)

            if "dead_code" in analysis_types:
                analysis_results["dead_code"] = self._detect_dead_code(all_functions)

            if "hotspots" in analysis_types:
                analysis_results["hotspots"] = self._identify_hotspots(all_functions)

            # 生成分析报告
            analysis_report = {
                "target": target,
                "analysis_types": analysis_types,
                "files_analyzed": len(target_files),
                "functions_found": len(all_functions),
                "analysis_results": analysis_results,
                "summary": self._generate_call_graph_summary(analysis_results),
                "recommendations": self._generate_call_graph_recommendations(
                    analysis_results
                ),
                "timestamp": time.time(),
            }

            # 格式化输出
            if output_format == "summary":
                analysis_report = self._format_call_graph_summary_output(
                    analysis_report
                )
            elif output_format == "graph":
                analysis_report = self._format_call_graph_output(analysis_report)

            # 存储分析结果
            self._store_call_graph_result("call_graph_analysis", analysis_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(analysis_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            resources = ResourceUsage(
                memory_mb=len(str(analysis_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            return self._create_success_result(analysis_report, metadata, resources)

        except Exception as e:
            print(f"调用图构建执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _extract_all_functions(self, files: List[str]) -> Dict[str, Dict[str, Any]]:
        """提取所有函数定义"""
        all_functions = {}

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            functions = self._extract_functions_from_file(content, language, file_path)

            for func_name, func_info in functions.items():
                # 使用文件路径和函数名作为唯一标识
                unique_key = f"{file_path}::{func_name}"
                all_functions[unique_key] = func_info

        return all_functions

    def _extract_functions_from_file(
        self, content: str, language: str, file_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """从文件中提取函数"""
        functions = {}

        if language == "python":
            functions = self._extract_python_functions(content, file_path)
        elif language in ["javascript", "typescript"]:
            functions = self._extract_js_functions(content, file_path)
        elif language == "java":
            functions = self._extract_java_functions(content, file_path)

        return functions

    def _extract_python_functions(
        self, content: str, file_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """提取Python函数"""
        functions = {}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 提取函数调用
                    calls = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            call_info = self._extract_call_info(child)
                            if call_info:
                                calls.append(call_info)

                    # 提取参数和返回类型
                    args = [arg.arg for arg in node.args.args]

                    functions[node.name] = {
                        "name": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                        "args": args,
                        "calls": calls,
                        "is_method": self._is_method(node),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "complexity": self._calculate_complexity(node),
                    }

        except SyntaxError as e:
            print(f"Python语法错误 {file_path}: {e}")

        return functions

    def _extract_call_info(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        """提取调用信息"""
        if isinstance(call_node.func, ast.Name):
            return {
                "type": "function_call",
                "name": call_node.func.id,
                "line": call_node.lineno,
                "args_count": len(call_node.args),
            }
        elif isinstance(call_node.func, ast.Attribute):
            return {
                "type": "method_call",
                "name": call_node.func.attr,
                "object": self._get_object_name(call_node.func.value),
                "line": call_node.lineno,
                "args_count": len(call_node.args),
            }
        return None

    def _get_object_name(self, node: ast.AST) -> str:
        """获取对象名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_object_name(node.value)}.{node.attr}"
        else:
            return "unknown"

    def _is_method(self, func_node: ast.FunctionDef) -> bool:
        """判断是否为方法"""
        # 简单判断：如果第一个参数是self或cls，认为是方法
        if func_node.args.args:
            first_arg = func_node.args.args[0].arg
            return first_arg in ["self", "cls"]
        return False

    def _calculate_complexity(self, func_node: ast.FunctionDef) -> int:
        """计算函数复杂度（简化版圈复杂度）"""
        complexity = 1  # 基础复杂度

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _extract_js_functions(
        self, content: str, file_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """提取JavaScript函数（简化实现）"""
        functions = {}

        # 使用正则表达式提取函数定义
        function_patterns = [
            r"function\s+(\w+)\s*\([^)]*\)\s*{",
            r"(\w+)\s*:\s*function\s*\([^)]*\)\s*{",
            r"(\w+)\s*=\s*function\s*\([^)]*\)\s*{",
            r"(\w+)\s*=\s*\([^)]*\)\s*=>\s*{",
            r"const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{",
            r"let\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{",
            r"var\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{",
        ]

        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in function_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    func_name = match.group(1)

                    # 提取函数调用（简化）
                    calls = self._extract_js_calls(content, line_num)

                    functions[func_name] = {
                        "name": func_name,
                        "file": file_path,
                        "line": line_num,
                        "calls": calls,
                        "language": "javascript",
                    }

        return functions

    def _extract_js_calls(self, content: str, start_line: int) -> List[Dict[str, Any]]:
        """提取JavaScript函数调用（简化）"""
        calls = []

        # 简化的调用提取
        call_pattern = r"(\w+)\s*\("
        lines = content.split("\n")[
            start_line - 1 : start_line + 20
        ]  # 只看函数附近的行

        for i, line in enumerate(lines):
            matches = re.finditer(call_pattern, line)
            for match in matches:
                calls.append(
                    {
                        "type": "function_call",
                        "name": match.group(1),
                        "line": start_line + i,
                    }
                )

        return calls

    def _extract_java_functions(
        self, content: str, file_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """提取Java方法（简化实现）"""
        functions: Dict[str, Dict[str, Any]] = {}

        method_pattern = r"(?:public|private|protected)?\s*(?:static)?\s*(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*{"
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(method_pattern, line)
            for match in matches:
                method_name = match.group(1)

                # 跳过构造函数和常见关键字
                if method_name in ["if", "for", "while", "switch", "try", "catch"]:
                    continue

                functions[method_name] = {
                    "name": method_name,
                    "file": file_path,
                    "line": line_num,
                    "calls": [],  # 简化实现
                    "language": "java",
                }

        return functions

    def _build_call_graph(
        self,
        functions: Dict[str, Dict[str, Any]],
        depth_limit: int,
        include_external: bool,
    ) -> Dict[str, Any]:
        """构建调用图"""
        graph: Dict[str, Any] = {"nodes": [], "edges": [], "metadata": {}}

        # 创建函数节点
        for func_key, func_info in functions.items():
            graph["nodes"].append(
                {
                    "id": func_key,
                    "name": func_info["name"],
                    "file": func_info["file"],
                    "line": func_info["line"],
                    "type": "function",
                    "complexity": func_info.get("complexity", 1),
                }
            )

        # 创建调用边
        for func_key, func_info in functions.items():
            for call in func_info.get("calls", []):
                call_name = call["name"]

                # 查找被调用的函数
                target_func = self._find_function_by_name(call_name, functions)
                if target_func:
                    graph["edges"].append(
                        {
                            "source": func_key,
                            "target": target_func,
                            "type": "calls",
                            "line": call["line"],
                        }
                    )
                elif include_external:
                    # 添加外部函数节点
                    external_key = f"external::{call_name}"
                    if not any(node["id"] == external_key for node in graph["nodes"]):
                        graph["nodes"].append(
                            {
                                "id": external_key,
                                "name": call_name,
                                "type": "external_function",
                            }
                        )

                    graph["edges"].append(
                        {
                            "source": func_key,
                            "target": external_key,
                            "type": "external_call",
                            "line": call["line"],
                        }
                    )

        graph["metadata"] = {
            "total_functions": len(
                [n for n in graph["nodes"] if n["type"] == "function"]
            ),
            "total_calls": len(graph["edges"]),
            "external_calls": len(
                [e for e in graph["edges"] if e["type"] == "external_call"]
            ),
            "call_density": (
                len(graph["edges"]) / len(graph["nodes"]) if graph["nodes"] else 0
            ),
        }

        return graph

    def _find_function_by_name(
        self, name: str, functions: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """根据名称查找函数"""
        for func_key, func_info in functions.items():
            if func_info["name"] == name:
                return func_key
        return None

    def _analyze_data_flow(
        self, functions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析数据流（简化实现）"""
        # 这是一个复杂的分析，这里提供简化版本
        data_flow: Dict[str, Any] = {
            "variable_usage": {},
            "parameter_flow": {},
            "return_flow": {},
        }

        # 简化的数据流分析
        for func_key, func_info in functions.items():
            data_flow["variable_usage"][func_key] = {
                "parameters": func_info.get("args", []),
                "local_vars": [],  # 需要更复杂的AST分析
                "global_vars": [],
            }

        return data_flow

    def _detect_dead_code(self, functions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """检测死代码"""
        # 构建调用关系
        called_functions = set()

        for func_info in functions.values():
            for call in func_info.get("calls", []):
                target_func = self._find_function_by_name(call["name"], functions)
                if target_func:
                    called_functions.add(target_func)

        # 找出未被调用的函数
        all_functions = set(functions.keys())
        dead_functions = all_functions - called_functions

        # 排除入口函数（main, __init__等）
        entry_patterns = ["main", "__init__", "__main__", "init", "setup"]
        dead_functions = {
            func
            for func in dead_functions
            if not any(
                pattern in functions[func]["name"].lower() for pattern in entry_patterns
            )
        }

        return {
            "dead_functions": list(dead_functions),
            "dead_count": len(dead_functions),
            "total_functions": len(functions),
            "dead_percentage": (
                len(dead_functions) / len(functions) * 100 if functions else 0
            ),
        }

    def _identify_hotspots(
        self, functions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """识别热点函数"""
        # 计算每个函数被调用的次数
        call_counts: Dict[str, int] = defaultdict(int)

        for func_info in functions.values():
            for call in func_info.get("calls", []):
                target_func = self._find_function_by_name(call["name"], functions)
                if target_func:
                    call_counts[target_func] += 1

        # 按调用次数排序
        hotspots = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)

        # 结合复杂度分析
        complex_functions = sorted(
            functions.items(), key=lambda x: x[1].get("complexity", 1), reverse=True
        )

        return {
            "most_called": hotspots[:10],
            "most_complex": [(k, v["complexity"]) for k, v in complex_functions[:10]],
            "hotspot_analysis": self._analyze_hotspot_patterns(hotspots, functions),
        }

    def _analyze_hotspot_patterns(
        self, hotspots: List[Tuple[str, int]], functions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析热点模式"""
        if not hotspots:
            return {}

        # 分析热点函数的特征
        hotspot_files: Dict[str, int] = defaultdict(int)
        hotspot_complexity = []

        for func_key, _call_count in hotspots[:10]:
            func_info = functions[func_key]
            hotspot_files[func_info["file"]] += 1
            hotspot_complexity.append(func_info.get("complexity", 1))

        return {
            "hotspot_files": dict(hotspot_files),
            "avg_hotspot_complexity": (
                sum(hotspot_complexity) / len(hotspot_complexity)
                if hotspot_complexity
                else 0
            ),
            "max_call_count": hotspots[0][1] if hotspots else 0,
        }

    def _generate_call_graph_summary(
        self, analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成调用图摘要"""
        summary = {}

        if "call_graph" in analysis_results:
            graph_data = analysis_results["call_graph"]
            summary["call_graph"] = graph_data.get("metadata", {})

        if "dead_code" in analysis_results:
            dead_data = analysis_results["dead_code"]
            summary["dead_code"] = {
                "dead_functions": dead_data.get("dead_count", 0),
                "dead_percentage": dead_data.get("dead_percentage", 0),
            }

        if "hotspots" in analysis_results:
            hotspot_data = analysis_results["hotspots"]
            summary["hotspots"] = {
                "top_called_function": (
                    hotspot_data.get("most_called", [{}])[0]
                    if hotspot_data.get("most_called")
                    else {}
                ),
                "most_complex_function": (
                    hotspot_data.get("most_complex", [{}])[0]
                    if hotspot_data.get("most_complex")
                    else {}
                ),
            }

        return summary

    def _generate_call_graph_recommendations(
        self, analysis_results: Dict[str, Any]
    ) -> List[str]:
        """生成调用图建议"""
        recommendations = []

        # 死代码建议
        if "dead_code" in analysis_results:
            dead_data = analysis_results["dead_code"]
            dead_count = dead_data.get("dead_count", 0)
            if dead_count > 0:
                recommendations.append(
                    f"发现 {dead_count} 个未使用的函数，建议清理死代码"
                )

        # 热点建议
        if "hotspots" in analysis_results:
            hotspot_data = analysis_results["hotspots"]
            most_complex = hotspot_data.get("most_complex", [])
            if most_complex and most_complex[0][1] > 10:
                recommendations.append("存在高复杂度函数，建议重构以降低复杂度")

        # 调用图建议
        if "call_graph" in analysis_results:
            graph_data = analysis_results["call_graph"]
            call_density = graph_data.get("metadata", {}).get("call_density", 0)
            if call_density > 5:
                recommendations.append("函数调用密度较高，建议检查是否存在过度耦合")

        if not recommendations:
            recommendations.append("代码结构良好，无明显问题")

        return recommendations

    def _format_call_graph_summary_output(
        self, report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """格式化调用图摘要输出"""
        return {
            "target": report["target"],
            "functions_found": report["functions_found"],
            "summary": report["summary"],
            "recommendations": report["recommendations"],
            "timestamp": report["timestamp"],
        }

    def _format_call_graph_output(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """格式化调用图输出"""
        graph_data = report["analysis_results"].get("call_graph", {})
        return {
            "target": report["target"],
            "call_graph": graph_data,
            "summary": report["summary"],
            "timestamp": report["timestamp"],
        }

    def _store_call_graph_result(
        self, analysis_type: str, data: Dict[str, Any]
    ) -> None:
        """存储调用图结果"""
        try:
            content = f"Call graph analysis: {analysis_type}"
            metadata = {
                "analysis_type": analysis_type,
                "functions_found": data.get("functions_found", 0),
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="call_graph_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储调用图结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class RefactoringAdvisor(BaseContextTool):
    """重构建议器"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="suggest_refactoring",
            description="分析代码并提供重构建议",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "directory", "function"],
                                "description": "分析目标类型",
                                "default": "directory",
                            },
                            "path": {
                                "type": "string",
                                "description": "目标路径",
                                "default": ".",
                            },
                            "patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "文件匹配模式",
                                "default": ["*.py", "*.js", "*.ts"],
                            },
                        },
                        "description": "分析目标配置",
                    },
                    "refactoring_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "code_smells",
                                "complexity",
                                "duplication",
                                "naming",
                                "structure",
                            ],
                        },
                        "description": "重构类型",
                        "default": ["code_smells", "complexity", "duplication"],
                    },
                    "severity_threshold": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "严重程度阈值",
                        "default": "medium",
                    },
                    "include_suggestions": {
                        "type": "boolean",
                        "description": "是否包含具体建议",
                        "default": True,
                    },
                    "prioritize_by": {
                        "type": "string",
                        "enum": ["severity", "impact", "effort"],
                        "description": "优先级排序方式",
                        "default": "severity",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行重构建议"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {"type": "directory", "path": "."})
            refactoring_types = params.get(
                "refactoring_types", ["code_smells", "complexity", "duplication"]
            )
            severity_threshold = params.get("severity_threshold", "medium")
            include_suggestions = params.get("include_suggestions", True)
            prioritize_by = params.get("prioritize_by", "severity")

            # 收集目标文件
            target_files = self._collect_target_files(target)

            if not target_files:
                return self._create_error_result("NO_FILES", "未找到符合条件的文件")

            # 执行重构分析
            analysis_results = {}

            if "code_smells" in refactoring_types:
                analysis_results["code_smells"] = self._detect_code_smells(target_files)

            if "complexity" in refactoring_types:
                analysis_results["complexity"] = self._analyze_complexity_issues(
                    target_files
                )

            if "duplication" in refactoring_types:
                analysis_results["duplication"] = self._detect_code_duplication(
                    target_files
                )

            if "naming" in refactoring_types:
                analysis_results["naming"] = self._analyze_naming_issues(target_files)

            if "structure" in refactoring_types:
                analysis_results["structure"] = self._analyze_structural_issues(
                    target_files
                )

            # 过滤和排序建议
            filtered_suggestions = self._filter_suggestions(
                analysis_results, severity_threshold
            )
            prioritized_suggestions = self._prioritize_suggestions(
                filtered_suggestions, prioritize_by
            )

            # 生成重构报告
            refactoring_report = {
                "target": target,
                "refactoring_types": refactoring_types,
                "files_analyzed": len(target_files),
                "analysis_results": analysis_results,
                "suggestions": prioritized_suggestions,
                "summary": self._generate_refactoring_summary(
                    analysis_results, prioritized_suggestions
                ),
                "action_plan": (
                    self._generate_action_plan(prioritized_suggestions)
                    if include_suggestions
                    else None
                ),
                "timestamp": time.time(),
            }

            # 存储分析结果
            self._store_refactoring_result("refactoring_analysis", refactoring_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(refactoring_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            resources = ResourceUsage(
                memory_mb=len(str(refactoring_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            return self._create_success_result(refactoring_report, metadata, resources)

        except Exception as e:
            print(f"重构建议执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _detect_code_smells(self, files: List[str]) -> Dict[str, Any]:
        """检测代码异味"""
        code_smells = []

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            file_smells = self._detect_file_smells(content, language, file_path)
            code_smells.extend(file_smells)

        # 按类型分组
        smells_by_type = defaultdict(list)
        for smell in code_smells:
            smells_by_type[smell["type"]].append(smell)

        return {
            "total_smells": len(code_smells),
            "smells_by_type": dict(smells_by_type),
            "all_smells": code_smells,
        }

    def _detect_file_smells(
        self, content: str, language: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """检测文件中的代码异味"""
        smells = []

        if language == "python":
            smells.extend(self._detect_python_smells(content, file_path))
        elif language in ["javascript", "typescript"]:
            smells.extend(self._detect_js_smells(content, file_path))

        # 通用异味检测
        smells.extend(self._detect_generic_smells(content, file_path))

        return smells

    def _detect_python_smells(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """检测Python代码异味"""
        smells = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # 长函数
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, "end_lineno") and node.end_lineno:
                        func_length = node.end_lineno - node.lineno
                        if func_length > 50:
                            smells.append(
                                {
                                    "type": "long_function",
                                    "severity": (
                                        "high" if func_length > 100 else "medium"
                                    ),
                                    "file": file_path,
                                    "line": node.lineno,
                                    "function": node.name,
                                    "description": f"函数过长 ({func_length} 行)",
                                    "suggestion": "将长函数分解为多个小函数",
                                }
                            )

                    # 参数过多
                    if len(node.args.args) > 5:
                        smells.append(
                            {
                                "type": "too_many_parameters",
                                "severity": "medium",
                                "file": file_path,
                                "line": node.lineno,
                                "function": node.name,
                                "description": f"参数过多 ({len(node.args.args)} 个)",
                                "suggestion": "使用参数对象或配置类",
                            }
                        )

                # 深层嵌套
                if isinstance(node, (ast.If, ast.For, ast.While)):
                    nesting_level = self._calculate_nesting_level(node)
                    if nesting_level > 3:
                        smells.append(
                            {
                                "type": "deep_nesting",
                                "severity": "medium",
                                "file": file_path,
                                "line": node.lineno,
                                "description": f"嵌套层次过深 ({nesting_level} 层)",
                                "suggestion": "提取函数或使用早期返回",
                            }
                        )

        except SyntaxError:
            pass

        return smells

    def _calculate_nesting_level(self, node: ast.AST, level: int = 0) -> int:
        """计算嵌套层次"""
        max_level = level

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                child_level = self._calculate_nesting_level(child, level + 1)
                max_level = max(max_level, child_level)

        return max_level

    def _detect_js_smells(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """检测JavaScript代码异味"""
        smells = []

        lines = content.split("\n")

        # 检测长函数（简化）
        in_function = False
        function_start = 0
        brace_count = 0

        for line_num, line in enumerate(lines, 1):
            if re.search(r"function\s+\w+|=>\s*{", line):
                in_function = True
                function_start = line_num
                brace_count = line.count("{") - line.count("}")
            elif in_function:
                brace_count += line.count("{") - line.count("}")
                if brace_count <= 0:
                    func_length = line_num - function_start
                    if func_length > 50:
                        smells.append(
                            {
                                "type": "long_function",
                                "severity": "high" if func_length > 100 else "medium",
                                "file": file_path,
                                "line": function_start,
                                "description": f"函数过长 ({func_length} 行)",
                                "suggestion": "将长函数分解为多个小函数",
                            }
                        )
                    in_function = False

        return smells

    def _detect_generic_smells(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """检测通用代码异味"""
        smells = []
        lines = content.split("\n")

        # 检测重复代码行
        line_counts = defaultdict(list)
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if (
                len(stripped) > 10
                and not stripped.startswith("#")
                and not stripped.startswith("//")
            ):
                line_counts[stripped].append(line_num)

        for _line_content, line_numbers in line_counts.items():
            if len(line_numbers) > 3:
                smells.append(
                    {
                        "type": "duplicate_code",
                        "severity": "medium",
                        "file": file_path,
                        "line": line_numbers[0],
                        "description": f"重复代码行 (出现 {len(line_numbers)} 次)",
                        "suggestion": "提取重复代码为函数或常量",
                    }
                )

        # 检测长行
        for line_num, line in enumerate(lines, 1):
            if len(line) > 120:
                smells.append(
                    {
                        "type": "long_line",
                        "severity": "low",
                        "file": file_path,
                        "line": line_num,
                        "description": f"行过长 ({len(line)} 字符)",
                        "suggestion": "将长行分解为多行",
                    }
                )

        return smells

    def _analyze_complexity_issues(self, files: List[str]) -> Dict[str, Any]:
        """分析复杂度问题"""
        complexity_issues = []

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            if language == "python":
                issues = self._analyze_python_complexity(content, file_path)
                complexity_issues.extend(issues)

        return {
            "total_issues": len(complexity_issues),
            "issues": complexity_issues,
            "high_complexity_functions": [
                issue for issue in complexity_issues if issue.get("complexity", 0) > 10
            ],
        }

    def _analyze_python_complexity(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """分析Python复杂度"""
        issues = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_cyclomatic_complexity(node)
                    if complexity > 7:  # 阈值
                        issues.append(
                            {
                                "type": "high_complexity",
                                "severity": "high" if complexity > 15 else "medium",
                                "file": file_path,
                                "line": node.lineno,
                                "function": node.name,
                                "complexity": complexity,
                                "description": f"圈复杂度过高 ({complexity})",
                                "suggestion": "分解函数以降低复杂度",
                            }
                        )

        except SyntaxError:
            pass

        return issues

    def _calculate_cyclomatic_complexity(self, func_node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(node, ast.comprehension):
                complexity += 1

        return complexity

    def _detect_code_duplication(self, files: List[str]) -> Dict[str, Any]:
        """检测代码重复"""
        duplications = []

        # 简化的重复检测：比较函数签名和结构
        all_functions: Dict[str, Dict[str, Any]] = {}

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            if language == "python":
                functions = self._extract_function_signatures(content, file_path)
                for func_name, func_info in functions.items():
                    signature = func_info["signature"]
                    if signature in all_functions:
                        duplications.append(
                            {
                                "type": "duplicate_function",
                                "severity": "medium",
                                "files": [all_functions[signature]["file"], file_path],
                                "functions": [
                                    all_functions[signature]["name"],
                                    func_name,
                                ],
                                "description": "发现重复的函数实现",
                                "suggestion": "提取公共函数或使用继承",
                            }
                        )
                    else:
                        all_functions[signature] = func_info

        return {"total_duplications": len(duplications), "duplications": duplications}

    def _extract_function_signatures(
        self, content: str, file_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """提取函数签名"""
        functions = {}

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 简化的签名：参数数量和类型
                    signature = f"{len(node.args.args)}_args"

                    functions[node.name] = {
                        "name": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "signature": signature,
                    }

        except SyntaxError:
            pass

        return functions

    def _analyze_naming_issues(self, files: List[str]) -> Dict[str, Any]:
        """分析命名问题"""
        naming_issues = []

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            if language == "python":
                issues = self._analyze_python_naming(content, file_path)
                naming_issues.extend(issues)

        return {"total_issues": len(naming_issues), "issues": naming_issues}

    def _analyze_python_naming(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """分析Python命名"""
        issues = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 检查函数命名
                    if not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
                        issues.append(
                            {
                                "type": "naming_convention",
                                "severity": "low",
                                "file": file_path,
                                "line": node.lineno,
                                "name": node.name,
                                "description": "函数名不符合Python命名规范",
                                "suggestion": "使用小写字母和下划线",
                            }
                        )

                    # 检查过短的名称
                    if len(node.name) < 3 and node.name not in ["id", "ok", "go"]:
                        issues.append(
                            {
                                "type": "short_name",
                                "severity": "low",
                                "file": file_path,
                                "line": node.lineno,
                                "name": node.name,
                                "description": "函数名过短，不够描述性",
                                "suggestion": "使用更具描述性的名称",
                            }
                        )

                elif isinstance(node, ast.ClassDef):
                    # 检查类命名
                    if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                        issues.append(
                            {
                                "type": "naming_convention",
                                "severity": "low",
                                "file": file_path,
                                "line": node.lineno,
                                "name": node.name,
                                "description": "类名不符合Python命名规范",
                                "suggestion": "使用驼峰命名法",
                            }
                        )

        except SyntaxError:
            pass

        return issues

    def _analyze_structural_issues(self, files: List[str]) -> Dict[str, Any]:
        """分析结构问题"""
        structural_issues = []

        # 分析文件大小
        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            lines = content.split("\n")
            if len(lines) > 500:
                structural_issues.append(
                    {
                        "type": "large_file",
                        "severity": "medium",
                        "file": file_path,
                        "description": f"文件过大 ({len(lines)} 行)",
                        "suggestion": "将大文件分解为多个模块",
                    }
                )

        return {"total_issues": len(structural_issues), "issues": structural_issues}

    def _filter_suggestions(
        self, analysis_results: Dict[str, Any], severity_threshold: str
    ) -> List[Dict[str, Any]]:
        """过滤建议"""
        severity_levels = {"low": 1, "medium": 2, "high": 3}
        threshold_level = severity_levels.get(severity_threshold, 2)

        all_suggestions = []

        for analysis_type, results in analysis_results.items():
            if analysis_type == "code_smells":
                all_suggestions.extend(results.get("all_smells", []))
            elif analysis_type == "complexity":
                all_suggestions.extend(results.get("issues", []))
            elif analysis_type == "duplication":
                all_suggestions.extend(results.get("duplications", []))
            elif analysis_type == "naming":
                all_suggestions.extend(results.get("issues", []))
            elif analysis_type == "structure":
                all_suggestions.extend(results.get("issues", []))

        # 过滤严重程度
        filtered = [
            suggestion
            for suggestion in all_suggestions
            if severity_levels.get(suggestion.get("severity", "low"), 1)
            >= threshold_level
        ]

        return filtered

    def _prioritize_suggestions(
        self, suggestions: List[Dict[str, Any]], prioritize_by: str
    ) -> List[Dict[str, Any]]:
        """排序建议"""
        if prioritize_by == "severity":
            severity_order = {"high": 3, "medium": 2, "low": 1}
            return sorted(
                suggestions,
                key=lambda x: severity_order.get(x.get("severity", "low"), 1),
                reverse=True,
            )
        elif prioritize_by == "impact":
            # 简化的影响评估
            impact_weights = {
                "high_complexity": 3,
                "long_function": 2,
                "duplicate_code": 2,
                "deep_nesting": 2,
                "large_file": 1,
            }
            return sorted(
                suggestions,
                key=lambda x: impact_weights.get(x.get("type", ""), 1),
                reverse=True,
            )
        elif prioritize_by == "effort":
            # 简化的工作量评估（低工作量优先）
            effort_weights = {
                "long_line": 1,
                "naming_convention": 1,
                "short_name": 1,
                "duplicate_code": 2,
                "long_function": 3,
                "high_complexity": 3,
            }
            return sorted(
                suggestions, key=lambda x: effort_weights.get(x.get("type", ""), 2)
            )

        return suggestions

    def _generate_refactoring_summary(
        self, analysis_results: Dict[str, Any], suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成重构摘要"""
        summary: Dict[str, Any] = {
            "total_suggestions": len(suggestions),
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "top_issues": [],
        }

        for suggestion in suggestions:
            summary["by_severity"][suggestion.get("severity", "low")] += 1
            summary["by_type"][suggestion.get("type", "unknown")] += 1

        # 转换为普通字典
        by_severity = summary["by_severity"]
        by_type = summary["by_type"]
        if isinstance(by_severity, dict):
            summary["by_severity"] = dict(by_severity)
        if isinstance(by_type, dict):
            summary["by_type"] = dict(by_type)

        # 获取最重要的问题
        summary["top_issues"] = suggestions[:5]

        return summary

    def _generate_action_plan(
        self, suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成行动计划"""
        plan: Dict[str, List[Any]] = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
        }

        for suggestion in suggestions:
            severity = suggestion.get("severity", "low")
            suggestion_type = suggestion.get("type", "")

            action = {
                "description": suggestion.get("description", ""),
                "suggestion": suggestion.get("suggestion", ""),
                "file": suggestion.get("file", ""),
                "line": suggestion.get("line", 0),
            }

            if severity == "high" or suggestion_type in [
                "high_complexity",
                "duplicate_code",
            ]:
                plan["immediate_actions"].append(action)
            elif severity == "medium":
                plan["short_term_actions"].append(action)
            else:
                plan["long_term_actions"].append(action)

        return plan

    def _store_refactoring_result(
        self, analysis_type: str, data: Dict[str, Any]
    ) -> None:
        """存储重构结果"""
        try:
            content = f"Refactoring analysis: {analysis_type}"
            metadata = {
                "analysis_type": analysis_type,
                "files_analyzed": data.get("files_analyzed", 0),
                "total_suggestions": data.get("summary", {}).get(
                    "total_suggestions", 0
                ),
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="refactoring_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储重构结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ContextEngineTools:
    """上下文引擎工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有上下文引擎工具"""
        return [
            DependencyAnalyzer(self.config),
            CallGraphBuilder(self.config),
            RefactoringAdvisor(self.config),
        ]
