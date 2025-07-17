"""
语义理解和智能推荐引擎

实现业务逻辑理解、设计模式识别、代码意图推断和智能代码补全功能。
"""

import ast
import json
import os
import re
import time
from collections import defaultdict
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


class BaseSemanticTool(BaseTool):
    """语义引擎工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager = UnifiedDataManager(
            self.config.get("chromadb_path", "./mcp_unified_db")
        )
        self.supported_languages = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
        }

    def _get_file_language(self, file_path: str) -> str:
        """获取文件语言类型"""
        ext = Path(file_path).suffix.lower()
        return self.supported_languages.get(ext, "unknown")

    def _read_file_safely(self, file_path: str) -> Optional[str]:
        """安全读取文件内容"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            # 静默处理文件读取错误，避免测试时的噪音输出
            return None

    def _find_files_by_pattern(self, directory: str, patterns: List[str]) -> List[str]:
        """根据模式查找文件"""
        files = []
        for pattern in patterns:
            if pattern.startswith("*."):
                ext = pattern[1:]
                for file_path in Path(directory).rglob(f"*{ext}"):
                    files.append(str(file_path))
        return files

    def _collect_target_files(self, target: Dict[str, Any]) -> List[str]:
        """收集目标文件"""
        target_type = target.get("type", "directory")
        path = target.get("path", ".")
        patterns = target.get("patterns", ["*.py", "*.js", "*.ts"])

        files = []

        if target_type == "file":
            if Path(path).is_file():
                files.append(path)
        elif target_type == "directory":
            files = self._find_files_by_pattern(path, patterns)
        elif target_type == "project":
            common_dirs = ["src", "lib", "app", "components", "modules"]
            for dir_name in common_dirs:
                dir_path = Path(path) / dir_name
                if dir_path.is_dir():
                    files.extend(self._find_files_by_pattern(str(dir_path), patterns))

            if not files:
                files = self._find_files_by_pattern(path, patterns)

        return files


class SemanticUnderstanding(BaseSemanticTool):
    """语义理解引擎"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="understand_semantics",
            description="理解代码的业务逻辑、设计模式和架构意图",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "directory", "function", "class"],
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
                    "understanding_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "business_logic",
                                "design_patterns",
                                "code_intent",
                                "architecture",
                            ],
                        },
                        "description": "理解类型",
                        "default": ["business_logic", "design_patterns", "code_intent"],
                    },
                    "analysis_depth": {
                        "type": "string",
                        "enum": ["shallow", "medium", "deep"],
                        "description": "分析深度",
                        "default": "medium",
                    },
                    "include_suggestions": {
                        "type": "boolean",
                        "description": "是否包含改进建议",
                        "default": True,
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行语义理解"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {"type": "directory", "path": "."})
            understanding_types = params.get(
                "understanding_types",
                ["business_logic", "design_patterns", "code_intent"],
            )
            analysis_depth = params.get("analysis_depth", "medium")
            include_suggestions = params.get("include_suggestions", True)

            # 收集目标文件
            target_files = self._collect_target_files(target)

            if not target_files:
                return self._create_error_result("NO_FILES", "未找到符合条件的文件")

            # 执行语义理解分析
            understanding_results = {}

            if "business_logic" in understanding_types:
                understanding_results["business_logic"] = self._analyze_business_logic(
                    target_files, analysis_depth
                )

            if "design_patterns" in understanding_types:
                understanding_results["design_patterns"] = (
                    self._identify_design_patterns(target_files, analysis_depth)
                )

            if "code_intent" in understanding_types:
                understanding_results["code_intent"] = self._infer_code_intent(
                    target_files, analysis_depth
                )

            if "architecture" in understanding_types:
                understanding_results["architecture"] = (
                    self._analyze_architecture_patterns(target_files, analysis_depth)
                )

            # 生成理解报告
            understanding_report = {
                "target": target,
                "understanding_types": understanding_types,
                "analysis_depth": analysis_depth,
                "files_analyzed": len(target_files),
                "understanding_results": understanding_results,
                "summary": self._generate_understanding_summary(understanding_results),
                "insights": self._generate_semantic_insights(understanding_results),
                "suggestions": (
                    self._generate_improvement_suggestions(understanding_results)
                    if include_suggestions
                    else None
                ),
                "timestamp": time.time(),
            }

            # 存储理解结果
            self._store_understanding_result(
                "semantic_understanding", understanding_report
            )

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(understanding_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            resources = ResourceUsage(
                memory_mb=len(str(understanding_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            return self._create_success_result(
                understanding_report, metadata, resources
            )

        except Exception as e:
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _analyze_business_logic(self, files: List[str], depth: str) -> Dict[str, Any]:
        """分析业务逻辑"""
        business_logic: Dict[str, Any] = {
            "domains": [],
            "entities": [],
            "operations": [],
            "workflows": [],
            "business_rules": [],
        }

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            file_logic = self._extract_business_logic_from_file(
                content, language, file_path, depth
            )

            # 合并结果
            for key in business_logic:
                business_logic[key].extend(file_logic.get(key, []))

        # 分析业务域
        business_logic["domain_analysis"] = self._analyze_business_domains(
            business_logic
        )

        return business_logic

    def _extract_business_logic_from_file(
        self, content: str, language: str, file_path: str, depth: str
    ) -> Dict[str, Any]:
        """从文件中提取业务逻辑"""
        logic: Dict[str, List[Any]] = {
            "domains": [],
            "entities": [],
            "operations": [],
            "workflows": [],
            "business_rules": [],
        }

        if language == "python":
            logic = self._extract_python_business_logic(content, file_path, depth)
        elif language in ["javascript", "typescript"]:
            logic = self._extract_js_business_logic(content, file_path, depth)

        return logic

    def _extract_python_business_logic(
        self, content: str, file_path: str, depth: str
    ) -> Dict[str, Any]:
        """提取Python业务逻辑"""
        logic: Dict[str, List[Any]] = {
            "domains": [],
            "entities": [],
            "operations": [],
            "workflows": [],
            "business_rules": [],
        }

        try:
            tree = ast.parse(content)

            # 分析类（可能是实体）
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entity_info = self._analyze_class_as_entity(node, file_path)
                    if entity_info:
                        logic["entities"].append(entity_info)

                elif isinstance(node, ast.FunctionDef):
                    # 分析函数（可能是操作或业务规则）
                    func_info = self._analyze_function_business_logic(node, file_path)
                    if func_info["type"] == "operation":
                        logic["operations"].append(func_info)
                    elif func_info["type"] == "business_rule":
                        logic["business_rules"].append(func_info)

            # 分析工作流（基于函数调用序列）
            workflows = self._extract_workflows_from_ast(tree, file_path)
            logic["workflows"].extend(workflows)

            # 推断业务域
            domain = self._infer_domain_from_file(file_path, content)
            if domain:
                logic["domains"].append(domain)

        except SyntaxError:
            pass

        return logic

    def _analyze_class_as_entity(
        self, class_node: ast.ClassDef, file_path: str
    ) -> Optional[Dict[str, Any]]:
        """分析类作为业务实体"""
        # 检查是否像业务实体
        entity_indicators = [
            "model",
            "entity",
            "data",
            "user",
            "order",
            "product",
            "customer",
        ]
        class_name_lower = class_node.name.lower()

        if any(indicator in class_name_lower for indicator in entity_indicators):
            # 提取属性
            attributes = []
            methods = []

            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("__"):
                        continue  # 跳过魔法方法
                    methods.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "is_property": self._is_property_method(node),
                        }
                    )
                elif isinstance(node, ast.Assign):
                    # 类属性
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(
                                {
                                    "name": target.id,
                                    "line": node.lineno,
                                    "type": "class_attribute",
                                }
                            )

            return {
                "name": class_node.name,
                "file": file_path,
                "line": class_node.lineno,
                "type": "entity",
                "attributes": attributes,
                "methods": methods,
                "business_relevance": self._calculate_business_relevance(
                    class_node.name, attributes, methods
                ),
            }

        return None

    def _is_property_method(self, func_node: ast.FunctionDef) -> bool:
        """判断是否为属性方法"""
        # 检查装饰器
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "property":
                return True
        return False

    def _analyze_function_business_logic(
        self, func_node: ast.FunctionDef, file_path: str
    ) -> Dict[str, Any]:
        """分析函数的业务逻辑"""
        func_name_lower = func_node.name.lower()

        # 操作关键词
        operation_keywords = [
            "create",
            "update",
            "delete",
            "process",
            "calculate",
            "validate",
            "send",
            "get",
            "find",
        ]
        # 业务规则关键词
        rule_keywords = [
            "check",
            "verify",
            "validate",
            "ensure",
            "require",
            "allow",
            "deny",
        ]

        func_type = "operation"
        if any(keyword in func_name_lower for keyword in rule_keywords):
            func_type = "business_rule"
        elif any(keyword in func_name_lower for keyword in operation_keywords):
            func_type = "operation"

        # 分析函数复杂度和业务相关性
        complexity = self._calculate_function_complexity(func_node)
        business_score = self._calculate_business_score(func_node.name, func_node)

        return {
            "name": func_node.name,
            "file": file_path,
            "line": func_node.lineno,
            "type": func_type,
            "complexity": complexity,
            "business_score": business_score,
            "parameters": [arg.arg for arg in func_node.args.args],
            "docstring": ast.get_docstring(func_node),
        }

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """计算函数复杂度"""
        complexity = 1
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
        return complexity

    def _calculate_business_score(self, name: str, func_node: ast.FunctionDef) -> float:
        """计算业务相关性分数"""
        score = 0.0
        name_lower = name.lower()

        # 基于名称的业务关键词
        business_keywords = [
            "user",
            "customer",
            "order",
            "product",
            "payment",
            "invoice",
            "account",
            "login",
            "register",
            "purchase",
            "sale",
            "inventory",
            "report",
            "analytics",
        ]

        for keyword in business_keywords:
            if keyword in name_lower:
                score += 0.3

        # 基于文档字符串
        docstring = ast.get_docstring(func_node)
        if docstring:
            doc_lower = docstring.lower()
            for keyword in business_keywords:
                if keyword in doc_lower:
                    score += 0.1

        return min(score, 1.0)

    def _calculate_business_relevance(
        self, name: str, attributes: List[Dict], methods: List[Dict]
    ) -> float:
        """计算业务相关性"""
        score = 0.0

        # 基于类名
        business_class_names = [
            "user",
            "customer",
            "order",
            "product",
            "payment",
            "account",
        ]
        name_lower = name.lower()
        for biz_name in business_class_names:
            if biz_name in name_lower:
                score += 0.4

        # 基于属性名
        business_attr_names = [
            "id",
            "name",
            "email",
            "price",
            "quantity",
            "status",
            "date",
        ]
        for attr in attributes:
            attr_lower = attr["name"].lower()
            for biz_attr in business_attr_names:
                if biz_attr in attr_lower:
                    score += 0.1

        return min(score, 1.0)

    def _extract_workflows_from_ast(
        self, tree: ast.AST, file_path: str
    ) -> List[Dict[str, Any]]:
        """从AST提取工作流"""
        workflows = []

        # 查找函数中的调用序列
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                call_sequence = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        call_info = self._extract_call_info(child)
                        if call_info:
                            call_sequence.append(call_info)

                if len(call_sequence) >= 3:  # 至少3个步骤才算工作流
                    workflows.append(
                        {
                            "name": f"{node.name}_workflow",
                            "function": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "steps": call_sequence,
                            "complexity": len(call_sequence),
                        }
                    )

        return workflows

    def _extract_call_info(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        """提取调用信息"""
        if isinstance(call_node.func, ast.Name):
            return {
                "type": "function_call",
                "name": call_node.func.id,
                "line": call_node.lineno,
            }
        elif isinstance(call_node.func, ast.Attribute):
            return {
                "type": "method_call",
                "name": call_node.func.attr,
                "object": self._get_object_name(call_node.func.value),
                "line": call_node.lineno,
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

    def _infer_domain_from_file(
        self, file_path: str, content: str
    ) -> Optional[Dict[str, Any]]:
        """从文件推断业务域"""
        file_name = Path(file_path).stem.lower()
        content_lower = content.lower()

        # 业务域关键词映射
        domain_keywords = {
            "user_management": ["user", "auth", "login", "register", "profile"],
            "e_commerce": ["product", "order", "cart", "payment", "checkout"],
            "financial": ["payment", "invoice", "billing", "transaction", "account"],
            "content_management": ["article", "post", "content", "media", "cms"],
            "analytics": ["report", "analytics", "metrics", "dashboard", "stats"],
        }

        for domain, keywords in domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in file_name:
                    score += 2
                if keyword in content_lower:
                    score += 1

            if score >= 3:
                return {
                    "name": domain,
                    "file": file_path,
                    "confidence": min(score / 10, 1.0),
                    "keywords_found": [
                        kw for kw in keywords if kw in file_name or kw in content_lower
                    ],
                }

        return None

    def _extract_js_business_logic(
        self, content: str, file_path: str, depth: str
    ) -> Dict[str, Any]:
        """提取JavaScript业务逻辑（简化实现）"""
        logic: Dict[str, List[Any]] = {
            "domains": [],
            "entities": [],
            "operations": [],
            "workflows": [],
            "business_rules": [],
        }

        # 简化的JS分析
        lines = content.split("\n")

        # 查找类或对象定义
        for line_num, line in enumerate(lines, 1):
            # 类定义
            class_match = re.search(r"class\s+(\w+)", line)
            if class_match:
                class_name = class_match.group(1)
                if self._is_business_entity_name(class_name):
                    logic["entities"].append(
                        {
                            "name": class_name,
                            "file": file_path,
                            "line": line_num,
                            "type": "entity",
                            "language": "javascript",
                        }
                    )

            # 函数定义
            func_match = re.search(
                r"(?:function\s+(\w+)|(\w+)\s*[:=]\s*(?:function|\([^)]*\)\s*=>))", line
            )
            if func_match:
                func_name = func_match.group(1) or func_match.group(2)
                if self._is_business_operation_name(func_name):
                    logic["operations"].append(
                        {
                            "name": func_name,
                            "file": file_path,
                            "line": line_num,
                            "type": "operation",
                            "language": "javascript",
                        }
                    )

        return logic

    def _is_business_entity_name(self, name: str) -> bool:
        """判断是否为业务实体名称"""
        business_entities = [
            "user",
            "customer",
            "order",
            "product",
            "payment",
            "account",
            "invoice",
        ]
        name_lower = name.lower()
        return any(entity in name_lower for entity in business_entities)

    def _is_business_operation_name(self, name: str) -> bool:
        """判断是否为业务操作名称"""
        business_operations = [
            "create",
            "update",
            "delete",
            "process",
            "calculate",
            "validate",
            "send",
            "get",
        ]
        name_lower = name.lower()
        return any(op in name_lower for op in business_operations)

    def _analyze_business_domains(
        self, business_logic: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析业务域"""
        domains = business_logic.get("domains", [])
        entities = business_logic.get("entities", [])
        operations = business_logic.get("operations", [])

        # 统计域分布
        domain_stats: Dict[str, int] = defaultdict(int)
        for domain in domains:
            domain_stats[domain["name"]] += 1

        # 分析实体-操作关系
        entity_operation_map = defaultdict(list)
        for operation in operations:
            op_name_lower = operation["name"].lower()
            for entity in entities:
                entity_name_lower = entity["name"].lower()
                if entity_name_lower in op_name_lower:
                    entity_operation_map[entity["name"]].append(operation["name"])

        return {
            "domain_distribution": dict(domain_stats),
            "total_domains": len(domain_stats),
            "entity_operation_mapping": dict(entity_operation_map),
            "domain_complexity": self._calculate_domain_complexity(
                domains, entities, operations
            ),
        }

    def _calculate_domain_complexity(
        self, domains: List[Dict], entities: List[Dict], operations: List[Dict]
    ) -> Dict[str, Any]:
        """计算域复杂度"""
        return {
            "entity_count": len(entities),
            "operation_count": len(operations),
            "avg_operations_per_entity": len(operations) / max(len(entities), 1),
            "complexity_score": (len(entities) * 0.3 + len(operations) * 0.7) / 10,
        }

    def _identify_design_patterns(self, files: List[str], depth: str) -> Dict[str, Any]:
        """识别设计模式"""
        patterns_found: Dict[str, List[Any]] = {
            "singleton": [],
            "factory": [],
            "observer": [],
            "strategy": [],
            "decorator": [],
            "adapter": [],
        }

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            language = self._get_file_language(file_path)
            if language == "python":
                file_patterns = self._detect_python_patterns(content, file_path)
                for pattern_type, instances in file_patterns.items():
                    patterns_found[pattern_type].extend(instances)

        return {
            "patterns_by_type": patterns_found,
            "total_patterns": sum(
                len(instances) for instances in patterns_found.values()
            ),
            "pattern_distribution": {k: len(v) for k, v in patterns_found.items()},
            "complexity_score": self._calculate_pattern_complexity(patterns_found),
        }

    def _detect_python_patterns(
        self, content: str, file_path: str
    ) -> Dict[str, List[Dict]]:
        """检测Python设计模式"""
        patterns: Dict[str, List[Dict[str, Any]]] = {
            "singleton": [],
            "factory": [],
            "observer": [],
            "strategy": [],
            "decorator": [],
            "adapter": [],
        }

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 检测单例模式
                    if self._is_singleton_pattern(node):
                        patterns["singleton"].append(
                            {
                                "class_name": node.name,
                                "file": file_path,
                                "line": node.lineno,
                                "confidence": 0.9,
                            }
                        )

                    # 检测工厂模式
                    if self._is_factory_pattern(node):
                        patterns["factory"].append(
                            {
                                "class_name": node.name,
                                "file": file_path,
                                "line": node.lineno,
                                "confidence": 0.8,
                            }
                        )

                    # 检测装饰器模式
                    if self._is_decorator_pattern(node):
                        patterns["decorator"].append(
                            {
                                "class_name": node.name,
                                "file": file_path,
                                "line": node.lineno,
                                "confidence": 0.85,
                            }
                        )

        except SyntaxError:
            pass

        return patterns

    def _is_singleton_pattern(self, class_node: ast.ClassDef) -> bool:
        """检测单例模式"""
        has_instance_var = False
        has_new_method = False

        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_instance":
                        has_instance_var = True

            elif isinstance(node, ast.FunctionDef) and node.name == "__new__":
                has_new_method = True

        return has_instance_var and has_new_method

    def _is_factory_pattern(self, class_node: ast.ClassDef) -> bool:
        """检测工厂模式"""
        factory_keywords = ["factory", "creator", "builder"]
        class_name_lower = class_node.name.lower()

        if any(keyword in class_name_lower for keyword in factory_keywords):
            # 检查是否有创建方法
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    method_name_lower = node.name.lower()
                    if any(
                        keyword in method_name_lower
                        for keyword in ["create", "make", "build"]
                    ):
                        return True

        return False

    def _is_decorator_pattern(self, class_node: ast.ClassDef) -> bool:
        """检测装饰器模式"""
        decorator_keywords = ["decorator", "wrapper"]
        class_name_lower = class_node.name.lower()

        if any(keyword in class_name_lower for keyword in decorator_keywords):
            return True

        # 检查是否有包装行为
        has_component = False
        has_operation = False

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == "__init__":
                    # 检查构造函数是否接受组件参数
                    if len(node.args.args) > 1:  # self + component
                        has_component = True
                elif "operation" in node.name.lower() or "execute" in node.name.lower():
                    has_operation = True

        return has_component and has_operation

    def _calculate_pattern_complexity(self, patterns: Dict[str, List]) -> float:
        """计算模式复杂度"""
        complexity_weights = {
            "singleton": 0.3,
            "factory": 0.5,
            "observer": 0.7,
            "strategy": 0.6,
            "decorator": 0.8,
            "adapter": 0.4,
        }

        total_complexity = 0.0
        for pattern_type, instances in patterns.items():
            weight = complexity_weights.get(pattern_type, 0.5)
            total_complexity += len(instances) * weight

        return total_complexity

    def _infer_code_intent(self, files: List[str], depth: str) -> Dict[str, Any]:
        """推断代码意图"""
        intent_analysis: Dict[str, Any] = {
            "primary_purposes": [],
            "secondary_purposes": [],
            "architectural_intent": [],
            "business_intent": [],
        }

        for file_path in files:
            content = self._read_file_safely(file_path)
            if not content:
                continue

            file_intent = self._analyze_file_intent(content, file_path, depth)

            # 合并意图分析结果
            for category in intent_analysis:
                intent_analysis[category].extend(file_intent.get(category, []))

        # 分析意图分布和优先级
        intent_analysis["intent_distribution"] = self._analyze_intent_distribution(
            intent_analysis
        )
        intent_analysis["confidence_scores"] = self._calculate_intent_confidence(
            intent_analysis
        )

        return intent_analysis

    def _analyze_file_intent(
        self, content: str, file_path: str, depth: str
    ) -> Dict[str, Any]:
        """分析单个文件的意图"""
        intent: Dict[str, List[Any]] = {
            "primary_purposes": [],
            "secondary_purposes": [],
            "architectural_intent": [],
            "business_intent": [],
        }

        # 基于文件名推断意图
        file_name = Path(file_path).stem.lower()

        # 架构意图关键词
        arch_keywords = {
            "controller": "request_handling",
            "service": "business_logic",
            "repository": "data_access",
            "model": "data_representation",
            "view": "presentation",
            "middleware": "request_processing",
            "config": "configuration",
            "utils": "utility_functions",
        }

        for keyword, intent_type in arch_keywords.items():
            if keyword in file_name:
                intent["architectural_intent"].append(
                    {
                        "type": intent_type,
                        "file": file_path,
                        "confidence": 0.8,
                        "evidence": f"filename contains '{keyword}'",
                    }
                )

        # 分析代码内容推断业务意图
        language = self._get_file_language(file_path)
        if language == "python":
            business_intent = self._extract_python_business_intent(content, file_path)
            intent["business_intent"].extend(business_intent)

        return intent

    def _extract_python_business_intent(
        self, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """提取Python代码的业务意图"""
        business_intents = []

        try:
            tree = ast.parse(content)

            # 分析类和函数的业务意图
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    intent = self._infer_class_business_intent(node, file_path)
                    if intent:
                        business_intents.append(intent)

                elif isinstance(node, ast.FunctionDef):
                    intent = self._infer_function_business_intent(node, file_path)
                    if intent:
                        business_intents.append(intent)

        except SyntaxError:
            pass

        return business_intents

    def _infer_class_business_intent(
        self, class_node: ast.ClassDef, file_path: str
    ) -> Optional[Dict[str, Any]]:
        """推断类的业务意图"""
        class_name_lower = class_node.name.lower()

        # 业务实体意图
        entity_keywords = ["user", "customer", "order", "product", "payment", "account"]
        for keyword in entity_keywords:
            if keyword in class_name_lower:
                return {
                    "type": "business_entity",
                    "entity_type": keyword,
                    "class_name": class_node.name,
                    "file": file_path,
                    "line": class_node.lineno,
                    "confidence": 0.9,
                }

        # 服务类意图
        service_keywords = ["service", "manager", "handler", "processor"]
        for keyword in service_keywords:
            if keyword in class_name_lower:
                return {
                    "type": "business_service",
                    "service_type": keyword,
                    "class_name": class_node.name,
                    "file": file_path,
                    "line": class_node.lineno,
                    "confidence": 0.8,
                }

        return None

    def _infer_function_business_intent(
        self, func_node: ast.FunctionDef, file_path: str
    ) -> Optional[Dict[str, Any]]:
        """推断函数的业务意图"""
        func_name_lower = func_node.name.lower()

        # CRUD 操作意图
        crud_mapping = {
            "create": "create_operation",
            "add": "create_operation",
            "insert": "create_operation",
            "get": "read_operation",
            "find": "read_operation",
            "fetch": "read_operation",
            "update": "update_operation",
            "modify": "update_operation",
            "edit": "update_operation",
            "delete": "delete_operation",
            "remove": "delete_operation",
        }

        for keyword, operation_type in crud_mapping.items():
            if keyword in func_name_lower:
                return {
                    "type": "crud_operation",
                    "operation_type": operation_type,
                    "function_name": func_node.name,
                    "file": file_path,
                    "line": func_node.lineno,
                    "confidence": 0.85,
                }

        return None

    def _analyze_intent_distribution(
        self, intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析意图分布"""
        distribution = {}

        for category, intents in intent_analysis.items():
            if isinstance(intents, list):
                type_counts: Dict[str, int] = {}
                for intent in intents:
                    intent_type = intent.get("type", "unknown")
                    type_counts[intent_type] = type_counts.get(intent_type, 0) + 1
                distribution[category] = type_counts

        return distribution

    def _calculate_intent_confidence(
        self, intent_analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """计算意图置信度"""
        confidence_scores = {}

        for category, intents in intent_analysis.items():
            if isinstance(intents, list) and intents:
                avg_confidence = sum(
                    intent.get("confidence", 0.5) for intent in intents
                ) / len(intents)
                confidence_scores[category] = avg_confidence
            else:
                confidence_scores[category] = 0.0

        return confidence_scores

    def _analyze_architecture_patterns(
        self, files: List[str], depth: str
    ) -> Dict[str, Any]:
        """分析架构模式"""
        architecture_analysis = {
            "mvc_pattern": self._detect_mvc_pattern(files),
            "layered_architecture": self._detect_layered_architecture(files),
            "microservice_indicators": self._detect_microservice_patterns(files),
            "repository_pattern": self._detect_repository_pattern(files),
        }

        return {
            "detected_patterns": architecture_analysis,
            "architecture_score": self._calculate_architecture_score(
                architecture_analysis
            ),
            "recommendations": self._generate_architecture_recommendations(
                architecture_analysis
            ),
        }

    def _detect_mvc_pattern(self, files: List[str]) -> Dict[str, Any]:
        """检测MVC模式"""
        mvc_components: Dict[str, List[str]] = {
            "models": [],
            "views": [],
            "controllers": [],
        }

        for file_path in files:
            file_name_lower = Path(file_path).stem.lower()

            if "model" in file_name_lower:
                mvc_components["models"].append(file_path)
            elif "view" in file_name_lower:
                mvc_components["views"].append(file_path)
            elif "controller" in file_name_lower:
                mvc_components["controllers"].append(file_path)

        has_mvc = all(len(components) > 0 for components in mvc_components.values())

        return {
            "detected": has_mvc,
            "components": mvc_components,
            "confidence": 0.9 if has_mvc else 0.3,
            "completeness": sum(
                1 for components in mvc_components.values() if components
            )
            / 3,
        }

    def _detect_layered_architecture(self, files: List[str]) -> Dict[str, Any]:
        """检测分层架构"""
        layers: Dict[str, List[str]] = {
            "presentation": [],
            "business": [],
            "data": [],
            "service": [],
        }

        layer_keywords = {
            "presentation": ["view", "ui", "frontend", "web"],
            "business": ["service", "logic", "domain", "core"],
            "data": ["repository", "dao", "model", "entity"],
            "service": ["api", "service", "endpoint", "handler"],
        }

        for file_path in files:
            file_path_lower = file_path.lower()

            for layer, keywords in layer_keywords.items():
                if any(keyword in file_path_lower for keyword in keywords):
                    layers[layer].append(file_path)

        detected_layers = sum(1 for layer_files in layers.values() if layer_files)

        return {
            "detected": detected_layers >= 2,
            "layers": layers,
            "layer_count": detected_layers,
            "confidence": min(detected_layers / 4, 1.0),
        }

    def _detect_microservice_patterns(self, files: List[str]) -> Dict[str, Any]:
        """检测微服务模式指标"""
        microservice_indicators = {
            "api_endpoints": 0,
            "config_files": 0,
            "docker_files": 0,
            "service_discovery": 0,
        }

        for file_path in files:
            file_name = Path(file_path).name.lower()

            if "api" in file_name or "endpoint" in file_name:
                microservice_indicators["api_endpoints"] += 1
            elif "config" in file_name or file_name.endswith(
                (".yaml", ".yml", ".json")
            ):
                microservice_indicators["config_files"] += 1
            elif "dockerfile" in file_name or file_name == "docker-compose.yml":
                microservice_indicators["docker_files"] += 1
            elif "discovery" in file_name or "registry" in file_name:
                microservice_indicators["service_discovery"] += 1

        total_indicators = sum(microservice_indicators.values())

        return {
            "detected": total_indicators >= 3,
            "indicators": microservice_indicators,
            "total_score": total_indicators,
            "confidence": min(total_indicators / 10, 1.0),
        }

    def _detect_repository_pattern(self, files: List[str]) -> Dict[str, Any]:
        """检测仓储模式"""
        repository_files = []
        interface_files = []

        for file_path in files:
            file_name_lower = Path(file_path).name.lower()

            if "repository" in file_name_lower:
                repository_files.append(file_path)
            elif "interface" in file_name_lower or "abstract" in file_name_lower:
                interface_files.append(file_path)

        return {
            "detected": len(repository_files) > 0,
            "repository_files": repository_files,
            "interface_files": interface_files,
            "confidence": 0.8 if repository_files else 0.2,
        }

    def _calculate_architecture_score(
        self, architecture_analysis: Dict[str, Any]
    ) -> float:
        """计算架构分数"""
        weights = {
            "mvc_pattern": 0.3,
            "layered_architecture": 0.4,
            "microservice_indicators": 0.2,
            "repository_pattern": 0.1,
        }

        total_score = 0.0
        for pattern, analysis in architecture_analysis.items():
            weight = weights.get(pattern, 0.25)
            confidence = analysis.get("confidence", 0.0)
            total_score += weight * confidence

        return total_score

    def _generate_architecture_recommendations(
        self, architecture_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成架构建议"""
        recommendations = []

        if not architecture_analysis["mvc_pattern"]["detected"]:
            recommendations.append("考虑采用MVC模式来分离关注点")

        if architecture_analysis["layered_architecture"]["layer_count"] < 3:
            recommendations.append("建议实现更清晰的分层架构")

        if not architecture_analysis["repository_pattern"]["detected"]:
            recommendations.append("考虑使用仓储模式来抽象数据访问")

        return recommendations

    def _generate_understanding_summary(
        self, understanding_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成理解摘要"""
        summary: Dict[str, Any] = {
            "total_analysis_types": len(understanding_results),
            "key_findings": [],
            "complexity_indicators": {},
            "confidence_levels": {},
        }

        for analysis_type, results in understanding_results.items():
            if analysis_type == "business_logic":
                entity_count = len(results.get("entities", []))
                operation_count = len(results.get("operations", []))
                summary["key_findings"].append(
                    f"发现 {entity_count} 个业务实体和 {operation_count} 个业务操作"
                )
                summary["complexity_indicators"]["business_complexity"] = (
                    entity_count + operation_count
                )

            elif analysis_type == "design_patterns":
                pattern_count = results.get("total_patterns", 0)
                summary["key_findings"].append(f"识别出 {pattern_count} 个设计模式")
                summary["complexity_indicators"]["pattern_complexity"] = pattern_count

            elif analysis_type == "architecture":
                detected_patterns = sum(
                    1
                    for pattern in results.get("detected_patterns", {}).values()
                    if pattern.get("detected", False)
                )
                summary["key_findings"].append(f"检测到 {detected_patterns} 种架构模式")
                summary["complexity_indicators"][
                    "architecture_complexity"
                ] = detected_patterns

        return summary

    def _generate_semantic_insights(
        self, understanding_results: Dict[str, Any]
    ) -> List[str]:
        """生成语义洞察"""
        insights = []

        # 业务逻辑洞察
        if "business_logic" in understanding_results:
            business_data = understanding_results["business_logic"]
            domain_count = len(
                business_data.get("domain_analysis", {}).get("domain_distribution", {})
            )
            if domain_count > 1:
                insights.append(f"项目涉及 {domain_count} 个业务域，建议考虑域驱动设计")

        # 设计模式洞察
        if "design_patterns" in understanding_results:
            pattern_data = understanding_results["design_patterns"]
            if pattern_data.get("total_patterns", 0) > 5:
                insights.append("项目使用了多种设计模式，显示出良好的设计意识")

        # 架构洞察
        if "architecture" in understanding_results:
            arch_data = understanding_results["architecture"]
            arch_score = arch_data.get("architecture_score", 0)
            if arch_score > 0.7:
                insights.append("项目具有清晰的架构结构")
            elif arch_score < 0.3:
                insights.append("建议改进项目架构，增强代码组织性")

        return insights

    def _generate_improvement_suggestions(
        self, understanding_results: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于业务逻辑分析的建议
        if "business_logic" in understanding_results:
            business_data = understanding_results["business_logic"]
            entities = business_data.get("entities", [])
            operations = business_data.get("operations", [])

            if len(entities) > 10:
                suggestions.append("考虑将业务实体按域进行分组，提高代码组织性")

            if len(operations) > 20:
                suggestions.append("业务操作较多，建议使用服务层模式进行组织")

        # 基于设计模式的建议
        if "design_patterns" in understanding_results:
            pattern_data = understanding_results["design_patterns"]
            patterns_by_type = pattern_data.get("patterns_by_type", {})

            if len(patterns_by_type.get("singleton", [])) > 3:
                suggestions.append("单例模式使用较多，注意避免过度使用影响测试性")

            if (
                not patterns_by_type.get("factory", [])
                and len(patterns_by_type.get("singleton", [])) > 0
            ):
                suggestions.append("考虑使用工厂模式来管理对象创建")

        # 基于架构分析的建议
        if "architecture" in understanding_results:
            arch_data = understanding_results["architecture"]
            recommendations = arch_data.get("recommendations", [])
            suggestions.extend(recommendations)

        return suggestions

    def _store_understanding_result(
        self, data_type: str, result: Dict[str, Any]
    ) -> None:
        """存储理解结果到ChromaDB"""
        try:
            content = json.dumps(result, ensure_ascii=False)
            metadata = {
                "data_type": data_type,
                "timestamp": str(result.get("timestamp", time.time())),
                "analysis_types": ",".join(
                    result.get("understanding_types", [])
                ),  # 转换为字符串
                "files_count": int(result.get("files_analyzed", 0)),
            }

            # 异步存储（这里简化为同步调用）
            self.data_manager.store_data(
                data_type=data_type, content=content, metadata=metadata
            )
        except Exception as e:  # nosec B110
            # 静默处理存储错误
            pass

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class CodeCompletionEngine(BaseSemanticTool):
    """智能代码补全引擎"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_code_completions",
            description="获取智能代码补全建议",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "position": {
                        "type": "object",
                        "properties": {
                            "line": {"type": "integer", "description": "行号"},
                            "column": {"type": "integer", "description": "列号"},
                        },
                        "description": "光标位置",
                    },
                    "context": {
                        "type": "string",
                        "description": "当前代码上下文",
                    },
                    "completion_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "variables",
                                "functions",
                                "classes",
                                "imports",
                                "patterns",
                            ],
                        },
                        "description": "补全类型",
                        "default": ["variables", "functions", "classes"],
                    },
                    "max_suggestions": {
                        "type": "integer",
                        "description": "最大建议数量",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["file_path", "position", "context"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行代码补全"""
        start_time = time.time()
        params = request.parameters

        try:
            file_path = params.get("file_path")
            position = params.get("position", {"line": 1, "column": 0})
            context = params.get("context", "")
            completion_types = params.get(
                "completion_types", ["variables", "functions", "classes"]
            )
            max_suggestions = params.get("max_suggestions", 10)

            if not file_path:
                return self._create_error_result(
                    "MISSING_PARAMETER", "缺少文件路径参数"
                )

            # 分析当前上下文
            current_context = await self._analyze_current_context(
                file_path, position, context
            )

            # 生成基础补全建议
            base_completions = await self._generate_base_completions(
                current_context, completion_types, max_suggestions
            )

            # 语义增强
            semantic_completions = await self._enhance_with_semantics(
                base_completions, current_context
            )

            # 个性化排序
            personalized_completions = await self._personalize_completions(
                semantic_completions, file_path
            )

            # 创建补全报告
            completion_report = {
                "file_path": file_path,
                "position": position,
                "completion_types": completion_types,
                "completions": personalized_completions[:max_suggestions],
                "context_analysis": current_context,
                "total_suggestions": len(personalized_completions),
                "timestamp": time.time(),
            }

            # 存储补全结果
            self._store_completion_result("code_completion", completion_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(completion_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(completion_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(completion_report, metadata, resources)

        except Exception as e:
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    async def _analyze_current_context(
        self, file_path: str, position: Dict, context: str
    ) -> Dict[str, Any]:
        """分析当前代码上下文"""
        context_analysis = {
            "file_path": file_path,
            "position": position,
            "language": self._get_file_language(file_path),
            "current_scope": None,
            "available_variables": [],
            "available_functions": [],
            "available_classes": [],
            "imports": [],
            "context_type": "unknown",
        }

        # 读取完整文件内容，如果文件不存在则使用提供的上下文
        full_content = self._read_file_safely(file_path)
        if not full_content:
            # 如果文件不存在，使用提供的上下文进行分析
            full_content = context
            if not full_content:
                return context_analysis

        # 分析语言特定的上下文
        language = context_analysis["language"]
        if language == "python":
            context_analysis = await self._analyze_python_context(
                full_content, position, context, context_analysis
            )
        elif language in ["javascript", "typescript"]:
            context_analysis = await self._analyze_js_context(
                full_content, position, context, context_analysis
            )

        return context_analysis

    async def _analyze_python_context(
        self, content: str, position: Dict, context: str, base_analysis: Dict
    ) -> Dict[str, Any]:
        """分析Python代码上下文"""
        try:
            tree = ast.parse(content)
            line_num = position.get("line", 1)

            # 查找当前作用域
            current_scope = self._find_current_scope(tree, line_num)
            base_analysis["current_scope"] = current_scope

            # 提取可用的变量、函数和类
            base_analysis["available_variables"] = self._extract_available_variables(
                tree, line_num
            )
            base_analysis["available_functions"] = self._extract_available_functions(
                tree
            )
            base_analysis["available_classes"] = self._extract_available_classes(tree)
            base_analysis["imports"] = self._extract_imports(tree)

            # 确定上下文类型
            base_analysis["context_type"] = self._determine_context_type(
                context, current_scope
            )

        except SyntaxError as e:
            # 静默处理语法错误
            pass

        return base_analysis

    def _find_current_scope(
        self, tree: ast.AST, line_num: int
    ) -> Optional[Dict[str, Any]]:
        """查找当前作用域"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if hasattr(node, "lineno") and node.lineno <= line_num:
                    # 检查是否在这个节点的范围内
                    if (
                        hasattr(node, "end_lineno")
                        and node.end_lineno
                        and node.end_lineno >= line_num
                    ):
                        return {
                            "type": (
                                "function"
                                if isinstance(node, ast.FunctionDef)
                                else "class"
                            ),
                            "name": node.name,
                            "line_start": node.lineno,
                            "line_end": getattr(node, "end_lineno", line_num),
                        }

        return {
            "type": "module",
            "name": "global",
            "line_start": 1,
            "line_end": float("inf"),
        }

    def _extract_available_variables(
        self, tree: ast.AST, line_num: int
    ) -> List[Dict[str, Any]]:
        """提取可用变量"""
        variables = []

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and hasattr(node, "lineno")
                and node.lineno < line_num
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(
                            {
                                "name": target.id,
                                "type": "variable",
                                "line": node.lineno,
                                "scope": "local",
                            }
                        )

        return variables

    def _extract_available_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取可用函数"""
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(
                    {
                        "name": node.name,
                        "type": "function",
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node),
                    }
                )

        return functions

    def _extract_available_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取可用类"""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        methods.append(child.name)

                classes.append(
                    {
                        "name": node.name,
                        "type": "class",
                        "line": node.lineno,
                        "methods": methods,
                        "docstring": ast.get_docstring(node),
                    }
                )

        return classes

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """提取导入信息"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append(
                        {
                            "type": "from_import",
                            "module": node.module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )

        return imports

    def _determine_context_type(
        self, context: str, current_scope: Optional[Dict]
    ) -> str:
        """确定上下文类型"""
        context_lower = context.lower().strip()

        # 检查是否在函数调用中
        if context_lower.endswith("("):
            return "function_call"

        # 检查是否在属性访问中
        if "." in context_lower and not context_lower.endswith("."):
            return "attribute_access"

        # 检查是否在导入语句中
        if context_lower.startswith("import ") or context_lower.startswith("from "):
            return "import_statement"

        # 检查是否在类定义中
        if current_scope and current_scope.get("type") == "class":
            return "class_context"

        # 检查是否在函数定义中
        if current_scope and current_scope.get("type") == "function":
            return "function_context"

        return "general"

    async def _analyze_js_context(
        self, content: str, position: Dict, context: str, base_analysis: Dict
    ) -> Dict[str, Any]:
        """分析JavaScript/TypeScript代码上下文（简化实现）"""
        lines = content.split("\n")
        line_num = position.get("line", 1)

        # 简单的JavaScript上下文分析
        if line_num <= len(lines):
            current_line = lines[line_num - 1] if line_num > 0 else ""

            # 提取函数定义
            functions = []
            for i, line in enumerate(lines, 1):
                if re.search(r"function\s+(\w+)", line):
                    match = re.search(r"function\s+(\w+)", line)
                    if match:
                        functions.append(
                            {"name": match.group(1), "type": "function", "line": i}
                        )

            base_analysis["available_functions"] = functions
            base_analysis["context_type"] = self._determine_js_context_type(
                current_line, context
            )

        return base_analysis

    def _determine_js_context_type(self, current_line: str, context: str) -> str:
        """确定JavaScript上下文类型"""
        context_lower = context.lower().strip()

        if context_lower.endswith("("):
            return "function_call"
        elif "." in context_lower:
            return "property_access"
        elif context_lower.startswith("import ") or context_lower.startswith(
            "require("
        ):
            return "import_statement"
        else:
            return "general"

    async def _generate_base_completions(
        self, context_analysis: Dict, completion_types: List[str], max_suggestions: int
    ) -> List[Dict[str, Any]]:
        """生成基础补全建议"""
        completions = []
        context_type = context_analysis.get("context_type", "general")

        # 根据上下文类型生成不同的补全建议
        if "variables" in completion_types:
            variable_completions = self._generate_variable_completions(
                context_analysis, context_type
            )
            completions.extend(variable_completions)

        if "functions" in completion_types:
            function_completions = self._generate_function_completions(
                context_analysis, context_type
            )
            completions.extend(function_completions)

        if "classes" in completion_types:
            class_completions = self._generate_class_completions(
                context_analysis, context_type
            )
            completions.extend(class_completions)

        if "imports" in completion_types:
            import_completions = self._generate_import_completions(
                context_analysis, context_type
            )
            completions.extend(import_completions)

        if "patterns" in completion_types:
            pattern_completions = self._generate_pattern_completions(
                context_analysis, context_type
            )
            completions.extend(pattern_completions)

        # 按相关性排序
        completions.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        return completions[: max_suggestions * 2]  # 生成更多候选，后续筛选

    def _generate_variable_completions(
        self, context_analysis: Dict, context_type: str
    ) -> List[Dict[str, Any]]:
        """生成变量补全建议"""
        completions = []
        variables = context_analysis.get("available_variables", [])

        for var in variables:
            completion = {
                "text": var["name"],
                "type": "variable",
                "description": f"变量 {var['name']}",
                "relevance_score": 0.8,
                "source": "local_scope",
                "detail": {
                    "scope": var.get("scope", "local"),
                    "line": var.get("line", 0),
                },
            }

            # 根据上下文调整相关性
            if context_type == "function_context":
                completion["relevance_score"] += 0.1

            completions.append(completion)

        return completions

    def _generate_function_completions(
        self, context_analysis: Dict, context_type: str
    ) -> List[Dict[str, Any]]:
        """生成函数补全建议"""
        completions = []
        functions = context_analysis.get("available_functions", [])

        for func in functions:
            args_str = ", ".join(func.get("args", []))
            completion = {
                "text": f"{func['name']}({args_str})",
                "type": "function",
                "description": func.get("docstring", f"函数 {func['name']}"),
                "relevance_score": 0.9,
                "source": "local_scope",
                "detail": {
                    "args": func.get("args", []),
                    "line": func.get("line", 0),
                    "signature": f"{func['name']}({args_str})",
                },
            }

            # 根据上下文调整相关性
            if context_type == "function_call":
                completion["relevance_score"] += 0.2

            completions.append(completion)

        return completions

    def _generate_class_completions(
        self, context_analysis: Dict, context_type: str
    ) -> List[Dict[str, Any]]:
        """生成类补全建议"""
        completions = []
        classes = context_analysis.get("available_classes", [])

        for cls in classes:
            completion = {
                "text": cls["name"],
                "type": "class",
                "description": cls.get("docstring", f"类 {cls['name']}"),
                "relevance_score": 0.85,
                "source": "local_scope",
                "detail": {
                    "methods": cls.get("methods", []),
                    "line": cls.get("line", 0),
                },
            }

            # 根据上下文调整相关性
            if context_type == "class_context":
                completion["relevance_score"] += 0.15

            completions.append(completion)

        return completions

    def _generate_import_completions(
        self, context_analysis: Dict, context_type: str
    ) -> List[Dict[str, Any]]:
        """生成导入补全建议"""
        completions = []

        if context_type == "import_statement":
            # 常用Python库建议
            common_imports = [
                {"name": "os", "description": "操作系统接口"},
                {"name": "sys", "description": "系统特定参数和函数"},
                {"name": "json", "description": "JSON编码和解码"},
                {"name": "datetime", "description": "日期和时间处理"},
                {"name": "re", "description": "正则表达式"},
                {"name": "pathlib", "description": "面向对象的文件系统路径"},
                {"name": "typing", "description": "类型提示支持"},
                {"name": "collections", "description": "专门的容器数据类型"},
            ]

            for imp in common_imports:
                completion = {
                    "text": imp["name"],
                    "type": "import",
                    "description": imp["description"],
                    "relevance_score": 0.7,
                    "source": "standard_library",
                    "detail": {"module": imp["name"], "category": "standard_library"},
                }
                completions.append(completion)

        return completions

    def _generate_pattern_completions(
        self, context_analysis: Dict, context_type: str
    ) -> List[Dict[str, Any]]:
        """生成模式补全建议"""
        completions = []
        language = context_analysis.get("language", "python")

        if language == "python":
            # Python常用模式
            patterns = [
                {
                    "text": "if __name__ == '__main__':",
                    "description": "主程序入口模式",
                    "category": "entry_point",
                },
                {
                    "text": "try:\n    pass\nexcept Exception as e:\n    pass",
                    "description": "异常处理模式",
                    "category": "error_handling",
                },
                {
                    "text": "with open('filename', 'r') as f:\n    content = f.read()",
                    "description": "文件读取模式",
                    "category": "file_handling",
                },
                {
                    "text": "for i, item in enumerate(items):",
                    "description": "枚举循环模式",
                    "category": "iteration",
                },
            ]

            for pattern in patterns:
                completion = {
                    "text": pattern["text"],
                    "type": "pattern",
                    "description": pattern["description"],
                    "relevance_score": 0.6,
                    "source": "code_patterns",
                    "detail": {"category": pattern["category"], "language": language},
                }
                completions.append(completion)

        return completions

    async def _enhance_with_semantics(
        self, base_completions: List[Dict], context_analysis: Dict
    ) -> List[Dict[str, Any]]:
        """使用语义信息增强补全建议"""
        enhanced_completions = []

        for completion in base_completions:
            enhanced_completion = completion.copy()

            # 使用ChromaDB进行语义搜索
            semantic_matches = await self._find_semantic_matches(
                completion, context_analysis
            )

            if semantic_matches:
                # 调整相关性分数
                enhanced_completion["relevance_score"] += 0.1
                enhanced_completion["semantic_matches"] = len(semantic_matches)
                enhanced_completion["detail"]["semantic_context"] = semantic_matches[
                    :3
                ]  # 前3个匹配

            enhanced_completions.append(enhanced_completion)

        return enhanced_completions

    async def _find_semantic_matches(
        self, completion: Dict, context_analysis: Dict
    ) -> List[Dict]:
        """在ChromaDB中查找语义匹配"""
        try:
            query_text = f"{completion['text']} {completion.get('description', '')}"

            # 查询相似的代码补全记录
            results = self.data_manager.query_data(
                query=query_text, data_type="code_completion", n_results=5
            )

            matches = []
            if results and results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results.get("metadatas", [[]])[0]
                    if i < len(metadata):
                        matches.append(
                            {
                                "content": doc,
                                "metadata": metadata[i],
                                "distance": (
                                    results.get("distances", [[1.0]])[0][i]
                                    if results.get("distances")
                                    else 1.0
                                ),
                            }
                        )

            return matches

        except Exception as e:
            return []

    async def _personalize_completions(
        self, completions: List[Dict], file_path: str
    ) -> List[Dict[str, Any]]:
        """个性化补全建议"""
        personalized_completions = []

        # 查询用户历史偏好
        user_preferences = await self._get_user_preferences(file_path)

        for completion in completions:
            personalized_completion = completion.copy()

            # 根据用户偏好调整分数
            preference_boost = self._calculate_preference_boost(
                completion, user_preferences
            )
            personalized_completion["relevance_score"] += preference_boost

            # 添加个性化信息
            personalized_completion["personalization"] = {
                "preference_boost": preference_boost,
                "user_frequency": user_preferences.get(completion["text"], 0),
            }

            personalized_completions.append(personalized_completion)

        # 重新排序
        personalized_completions.sort(key=lambda x: x["relevance_score"], reverse=True)

        return personalized_completions

    async def _get_user_preferences(self, file_path: str) -> Dict[str, float]:
        """获取用户偏好"""
        try:
            # 查询用户的历史补全使用记录
            results = self.data_manager.query_data(
                query=f"file_path:{file_path}",
                data_type="user_completion_history",
                n_results=100,
            )

            preferences = {}
            if results and results.get("metadatas") and results["metadatas"][0]:
                for metadata in results["metadatas"][0]:
                    completion_text = metadata.get("completion_text", "")
                    usage_count = metadata.get("usage_count", 0)
                    preferences[completion_text] = usage_count

            return preferences

        except Exception as e:
            return {}

    def _calculate_preference_boost(
        self, completion: Dict, preferences: Dict[str, float]
    ) -> float:
        """计算偏好加成"""
        completion_text = completion["text"]
        usage_count = preferences.get(completion_text, 0)

        # 使用对数函数避免过度偏向高频项
        if isinstance(usage_count, (int, float)) and usage_count > 0:
            boost_value = 0.1 * (1 + float(usage_count) ** 0.5)
            return float(min(0.3, boost_value))

        return 0.0

    def _store_completion_result(self, data_type: str, result: Dict[str, Any]) -> None:
        """存储补全结果到ChromaDB"""
        try:
            content = json.dumps(result, ensure_ascii=False)
            metadata = {
                "data_type": data_type,
                "file_path": str(result.get("file_path", "")),
                "timestamp": str(result.get("timestamp", time.time())),
                "completion_count": int(len(result.get("completions", []))),
                "context_type": str(
                    result.get("context_analysis", {}).get("context_type", "unknown")
                ),
            }

            # 异步存储（这里简化为同步调用）
            self.data_manager.store_data(
                data_type=data_type, content=content, metadata=metadata
            )
        except Exception as e:  # nosec B110
            # 静默处理存储错误
            pass

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class PatternRecognizer(BaseSemanticTool):
    """智能模式识别器"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="recognize_patterns",
            description="识别代码中的设计模式和编程模式",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "directory", "code_snippet"],
                                "description": "分析目标类型",
                                "default": "directory",
                            },
                            "path": {
                                "type": "string",
                                "description": "目标路径",
                                "default": ".",
                            },
                            "content": {
                                "type": "string",
                                "description": "代码内容（当type为code_snippet时）",
                            },
                        },
                        "description": "分析目标配置",
                    },
                    "pattern_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "design_patterns",
                                "coding_patterns",
                                "anti_patterns",
                                "performance_patterns",
                                "security_patterns",
                            ],
                        },
                        "description": "模式类型",
                        "default": ["design_patterns", "coding_patterns"],
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "置信度阈值",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["target"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行模式识别"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {"type": "directory", "path": "."})
            pattern_types = params.get(
                "pattern_types", ["design_patterns", "coding_patterns"]
            )
            confidence_threshold = params.get("confidence_threshold", 0.7)

            # 收集分析目标
            analysis_targets = await self._collect_analysis_targets(target)

            if not analysis_targets:
                return self._create_error_result("NO_TARGETS", "未找到分析目标")

            # 执行模式识别
            pattern_results = {}

            for pattern_type in pattern_types:
                if pattern_type == "design_patterns":
                    pattern_results[pattern_type] = (
                        await self._recognize_design_patterns(
                            analysis_targets, confidence_threshold
                        )
                    )
                elif pattern_type == "coding_patterns":
                    pattern_results[pattern_type] = (
                        await self._recognize_coding_patterns(
                            analysis_targets, confidence_threshold
                        )
                    )
                elif pattern_type == "anti_patterns":
                    pattern_results[pattern_type] = await self._recognize_anti_patterns(
                        analysis_targets, confidence_threshold
                    )
                elif pattern_type == "performance_patterns":
                    pattern_results[pattern_type] = (
                        await self._recognize_performance_patterns(
                            analysis_targets, confidence_threshold
                        )
                    )
                elif pattern_type == "security_patterns":
                    pattern_results[pattern_type] = (
                        await self._recognize_security_patterns(
                            analysis_targets, confidence_threshold
                        )
                    )

            # 生成模式识别报告
            recognition_report = {
                "target": target,
                "pattern_types": pattern_types,
                "confidence_threshold": confidence_threshold,
                "targets_analyzed": len(analysis_targets),
                "patterns_found": pattern_results,
                "summary": self._generate_pattern_summary(pattern_results),
                "recommendations": self._generate_pattern_recommendations(
                    pattern_results
                ),
                "timestamp": time.time(),
            }

            # 存储识别结果
            self._store_pattern_result("pattern_recognition", recognition_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(recognition_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(analysis_targets),
            )

            resources = ResourceUsage(
                memory_mb=len(str(recognition_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(analysis_targets),
            )

            return self._create_success_result(recognition_report, metadata, resources)

        except Exception as e:
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    async def _collect_analysis_targets(
        self, target: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """收集分析目标"""
        targets = []
        target_type = target.get("type", "directory")

        if target_type == "file":
            path = target.get("path", "")
            if Path(path).is_file():
                content = self._read_file_safely(path)
                if content:
                    targets.append(
                        {
                            "type": "file",
                            "path": path,
                            "content": content,
                            "language": self._get_file_language(path),
                        }
                    )

        elif target_type == "directory":
            path = target.get("path", ".")
            patterns = ["*.py", "*.js", "*.ts", "*.java"]
            files = self._find_files_by_pattern(path, patterns)

            for file_path in files:
                content = self._read_file_safely(file_path)
                if content:
                    targets.append(
                        {
                            "type": "file",
                            "path": file_path,
                            "content": content,
                            "language": self._get_file_language(file_path),
                        }
                    )

        elif target_type == "code_snippet":
            content = target.get("content", "")
            if content:
                targets.append(
                    {
                        "type": "snippet",
                        "path": "snippet",
                        "content": content,
                        "language": "python",  # 默认Python
                    }
                )

        return targets

    async def _recognize_design_patterns(
        self, targets: List[Dict], threshold: float
    ) -> Dict[str, Any]:
        """识别设计模式"""
        patterns_found: Dict[str, List[Any]] = {
            "singleton": [],
            "factory": [],
            "observer": [],
            "strategy": [],
            "decorator": [],
            "adapter": [],
            "builder": [],
            "command": [],
        }

        for target in targets:
            content = target["content"]
            language = target["language"]
            path = target["path"]

            if language == "python":
                file_patterns = self._detect_python_design_patterns(
                    content, path, threshold
                )
                for pattern_type, instances in file_patterns.items():
                    patterns_found[pattern_type].extend(instances)

        return {
            "patterns_by_type": patterns_found,
            "total_patterns": sum(
                len(instances) for instances in patterns_found.values()
            ),
            "high_confidence_patterns": self._filter_high_confidence_patterns(
                patterns_found, threshold
            ),
            "pattern_complexity_score": self._calculate_design_pattern_complexity(
                patterns_found
            ),
        }

    def _detect_python_design_patterns(
        self, content: str, file_path: str, threshold: float
    ) -> Dict[str, List[Dict]]:
        """检测Python设计模式（增强版）"""
        patterns: Dict[str, List[Dict[str, Any]]] = {
            "singleton": [],
            "factory": [],
            "observer": [],
            "strategy": [],
            "decorator": [],
            "adapter": [],
            "builder": [],
            "command": [],
        }

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 检测各种设计模式
                    pattern_checks = [
                        ("singleton", self._is_singleton_pattern_enhanced),
                        ("factory", self._is_factory_pattern_enhanced),
                        ("observer", self._is_observer_pattern),
                        ("strategy", self._is_strategy_pattern),
                        ("decorator", self._is_decorator_pattern_enhanced),
                        ("adapter", self._is_adapter_pattern),
                        ("builder", self._is_builder_pattern),
                        ("command", self._is_command_pattern),
                    ]

                    for pattern_name, check_func in pattern_checks:
                        confidence = check_func(node, content)
                        if confidence >= threshold:
                            patterns[pattern_name].append(
                                {
                                    "class_name": node.name,
                                    "file": file_path,
                                    "line": node.lineno,
                                    "confidence": confidence,
                                    "evidence": self._get_pattern_evidence(
                                        node, pattern_name
                                    ),
                                }
                            )

        except SyntaxError:
            pass

        return patterns

    def _is_singleton_pattern_enhanced(
        self, class_node: ast.ClassDef, content: str
    ) -> float:
        """增强的单例模式检测"""
        confidence = 0.0
        evidence_count = 0

        # 检查类变量 _instance
        has_instance_var = False
        has_new_method = False
        has_init_guard = False

        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in [
                        "_instance",
                        "__instance",
                    ]:
                        has_instance_var = True
                        evidence_count += 1

            elif isinstance(node, ast.FunctionDef):
                if node.name == "__new__":
                    has_new_method = True
                    evidence_count += 1

                    # 检查__new__方法中的单例逻辑
                    for child in ast.walk(node):
                        if isinstance(child, ast.If):
                            has_init_guard = True
                            evidence_count += 1
                            break

        # 计算置信度
        if has_instance_var and has_new_method:
            confidence = 0.8
            if has_init_guard:
                confidence = 0.95
        elif has_instance_var or has_new_method:
            confidence = 0.4

        return confidence

    def _is_factory_pattern_enhanced(
        self, class_node: ast.ClassDef, content: str
    ) -> float:
        """增强的工厂模式检测"""
        confidence = 0.0

        # 检查类名是否包含工厂相关词汇
        class_name_lower = class_node.name.lower()
        factory_keywords = ["factory", "creator", "builder", "maker"]

        name_match = any(keyword in class_name_lower for keyword in factory_keywords)

        # 检查是否有创建方法
        has_create_method = False
        create_methods = []

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_name_lower = node.name.lower()
                if any(
                    keyword in method_name_lower
                    for keyword in ["create", "make", "build", "produce"]
                ):
                    has_create_method = True
                    create_methods.append(node.name)

        # 检查是否返回不同类型的对象
        returns_objects = False
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value:
                        if isinstance(child.value, ast.Call):
                            returns_objects = True
                            break

        # 计算置信度
        if name_match and has_create_method:
            confidence = 0.8
            if returns_objects:
                confidence = 0.9
            if len(create_methods) > 1:
                confidence = min(confidence + 0.1, 1.0)
        elif name_match or has_create_method:
            confidence = 0.5

        return confidence

    def _is_decorator_pattern_enhanced(
        self, class_node: ast.ClassDef, content: str
    ) -> float:
        """增强的装饰器模式检测"""
        confidence = 0.0

        # 检查类名是否包含装饰器相关词汇
        class_name_lower = class_node.name.lower()
        decorator_keywords = ["decorator", "wrapper", "proxy"]

        name_match = any(keyword in class_name_lower for keyword in decorator_keywords)

        # 检查是否有包装行为
        has_component = False
        has_operation = False
        has_delegation = False

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == "__init__":
                    # 检查构造函数是否接受组件参数
                    if len(node.args.args) > 1:  # self + component
                        has_component = True
                elif any(
                    keyword in node.name.lower()
                    for keyword in ["operation", "execute", "process", "handle"]
                ):
                    has_operation = True

                    # 检查是否有委托调用
                    for child in ast.walk(node):
                        if isinstance(child, ast.Attribute):
                            has_delegation = True
                            break

        # 计算置信度
        if name_match and has_component and has_operation:
            confidence = 0.9
            if has_delegation:
                confidence = 0.95
        elif (name_match and has_component) or (has_component and has_operation):
            confidence = 0.7
        elif name_match or has_component:
            confidence = 0.4

        return confidence

    def _is_adapter_pattern(self, class_node: ast.ClassDef, content: str) -> float:
        """检测适配器模式"""
        confidence = 0.0

        # 检查类名是否包含适配器相关词汇
        class_name_lower = class_node.name.lower()
        adapter_keywords = ["adapter", "wrapper", "bridge"]

        name_match = any(keyword in class_name_lower for keyword in adapter_keywords)

        # 检查是否有适配行为
        has_adaptee = False
        has_target_interface = False

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == "__init__":
                    # 检查是否接受被适配对象
                    if len(node.args.args) > 1:
                        has_adaptee = True
                else:
                    # 检查是否实现目标接口
                    has_target_interface = True

        # 计算置信度
        if name_match and has_adaptee and has_target_interface:
            confidence = 0.85
        elif name_match and (has_adaptee or has_target_interface):
            confidence = 0.6
        elif name_match:
            confidence = 0.4

        return confidence

    def _is_observer_pattern(self, class_node: ast.ClassDef, content: str) -> float:
        """检测观察者模式"""
        confidence = 0.0

        # 检查是否有观察者相关的方法
        observer_methods = [
            "attach",
            "detach",
            "notify",
            "update",
            "subscribe",
            "unsubscribe",
        ]
        found_methods = []

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name in observer_methods:
                    found_methods.append(node.name)

        # 检查是否有观察者列表
        has_observer_list = False
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and "observer" in target.id.lower():
                        has_observer_list = True
                        break

        # 计算置信度
        if len(found_methods) >= 2:
            confidence = 0.7
            if has_observer_list:
                confidence = 0.9
            if "notify" in found_methods and "update" in found_methods:
                confidence = 0.95

        return confidence

    def _is_strategy_pattern(self, class_node: ast.ClassDef, content: str) -> float:
        """检测策略模式"""
        confidence = 0.0

        # 检查类名是否包含策略相关词汇
        class_name_lower = class_node.name.lower()
        strategy_keywords = ["strategy", "algorithm", "policy"]

        name_match = any(keyword in class_name_lower for keyword in strategy_keywords)

        # 检查是否有执行方法
        has_execute_method = False
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_name_lower = node.name.lower()
                if any(
                    keyword in method_name_lower
                    for keyword in ["execute", "run", "apply", "process"]
                ):
                    has_execute_method = True
                    break

        # 检查是否是抽象基类或接口
        has_abstract_method = False
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                # 检查装饰器
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Name)
                        and decorator.id == "abstractmethod"
                    ):
                        has_abstract_method = True
                        break

        # 计算置信度
        if name_match and has_execute_method:
            confidence = 0.8
            if has_abstract_method:
                confidence = 0.9
        elif name_match or has_execute_method:
            confidence = 0.5

        return confidence

    def _is_builder_pattern(self, class_node: ast.ClassDef, content: str) -> float:
        """检测建造者模式"""
        confidence = 0.0

        # 检查类名
        class_name_lower = class_node.name.lower()
        builder_keywords = ["builder", "constructor", "factory"]

        name_match = any(keyword in class_name_lower for keyword in builder_keywords)

        # 检查是否有链式调用方法
        chain_methods = 0
        build_method = False

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_name_lower = node.name.lower()

                # 检查build方法
                if method_name_lower in ["build", "create", "construct"]:
                    build_method = True

                # 检查返回self的方法（链式调用）
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Return)
                        and isinstance(child.value, ast.Name)
                        and child.value.id == "self"
                    ):
                        chain_methods += 1
                        break

        # 计算置信度
        if name_match and build_method and chain_methods >= 2:
            confidence = 0.9
        elif (name_match and build_method) or chain_methods >= 3:
            confidence = 0.7
        elif name_match or build_method or chain_methods >= 1:
            confidence = 0.4

        return confidence

    def _is_command_pattern(self, class_node: ast.ClassDef, content: str) -> float:
        """检测命令模式"""
        confidence = 0.0

        # 检查类名
        class_name_lower = class_node.name.lower()
        command_keywords = ["command", "action", "operation", "request"]

        name_match = any(keyword in class_name_lower for keyword in command_keywords)

        # 检查是否有execute方法
        has_execute = False
        has_undo = False

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_name_lower = node.name.lower()
                if method_name_lower in ["execute", "run", "perform", "do"]:
                    has_execute = True
                elif method_name_lower in ["undo", "reverse", "rollback"]:
                    has_undo = True

        # 计算置信度
        if name_match and has_execute:
            confidence = 0.8
            if has_undo:
                confidence = 0.95
        elif name_match or has_execute:
            confidence = 0.5

        return confidence

    def _get_pattern_evidence(
        self, class_node: ast.ClassDef, pattern_name: str
    ) -> List[str]:
        """获取模式证据"""
        evidence = []

        if pattern_name == "singleton":
            for node in class_node.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and "_instance" in target.id:
                            evidence.append(f"类变量 {target.id}")
                elif isinstance(node, ast.FunctionDef) and node.name == "__new__":
                    evidence.append("重写 __new__ 方法")

        elif pattern_name == "factory":
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    method_name_lower = node.name.lower()
                    if any(
                        keyword in method_name_lower
                        for keyword in ["create", "make", "build"]
                    ):
                        evidence.append(f"工厂方法 {node.name}")

        return evidence

    async def _recognize_coding_patterns(
        self, targets: List[Dict], threshold: float
    ) -> Dict[str, Any]:
        """识别编程模式"""
        patterns_found: Dict[str, List[Any]] = {
            "naming_conventions": [],
            "error_handling": [],
            "resource_management": [],
            "iteration_patterns": [],
            "function_patterns": [],
        }

        for target in targets:
            content = target["content"]
            language = target["language"]
            path = target["path"]

            if language == "python":
                file_patterns = self._detect_python_coding_patterns(
                    content, path, threshold
                )
                for pattern_type, instances in file_patterns.items():
                    patterns_found[pattern_type].extend(instances)

        return {
            "patterns_by_type": patterns_found,
            "total_patterns": sum(
                len(instances) for instances in patterns_found.values()
            ),
            "pattern_quality_score": self._calculate_coding_pattern_quality(
                patterns_found
            ),
        }

    def _detect_python_coding_patterns(
        self, content: str, file_path: str, threshold: float
    ) -> Dict[str, List[Dict]]:
        """检测Python编程模式"""
        patterns: Dict[str, List[Dict[str, Any]]] = {
            "naming_conventions": [],
            "error_handling": [],
            "resource_management": [],
            "iteration_patterns": [],
            "function_patterns": [],
        }

        try:
            tree = ast.parse(content)

            # 检测命名约定
            naming_patterns = self._check_naming_conventions(tree, file_path)
            patterns["naming_conventions"].extend(naming_patterns)

            # 检测错误处理模式
            error_patterns = self._check_error_handling_patterns(tree, file_path)
            patterns["error_handling"].extend(error_patterns)

            # 检测资源管理模式
            resource_patterns = self._check_resource_management_patterns(
                tree, file_path
            )
            patterns["resource_management"].extend(resource_patterns)

            # 检测迭代模式
            iteration_patterns = self._check_iteration_patterns(tree, file_path)
            patterns["iteration_patterns"].extend(iteration_patterns)

            # 检测函数模式
            function_patterns = self._check_function_patterns(tree, file_path)
            patterns["function_patterns"].extend(function_patterns)

        except SyntaxError:
            pass

        return patterns

    def _check_naming_conventions(self, tree: ast.AST, file_path: str) -> List[Dict]:
        """检查命名约定"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查类名是否遵循PascalCase
                if node.name[0].isupper() and "_" not in node.name:
                    patterns.append(
                        {
                            "type": "pascal_case_class",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "confidence": 0.9,
                            "description": "类名遵循PascalCase约定",
                        }
                    )

            elif isinstance(node, ast.FunctionDef):
                # 检查函数名是否遵循snake_case
                if node.name.islower() and not node.name.startswith("__"):
                    patterns.append(
                        {
                            "type": "snake_case_function",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "confidence": 0.8,
                            "description": "函数名遵循snake_case约定",
                        }
                    )

        return patterns

    def _check_error_handling_patterns(
        self, tree: ast.AST, file_path: str
    ) -> List[Dict]:
        """检查错误处理模式"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                # 检查try-except模式
                has_specific_except = False
                has_finally = bool(node.finalbody)

                for handler in node.handlers:
                    if handler.type:  # 有具体的异常类型
                        has_specific_except = True
                        break

                confidence = 0.7
                if has_specific_except:
                    confidence += 0.1
                if has_finally:
                    confidence += 0.1

                patterns.append(
                    {
                        "type": "try_except_pattern",
                        "file": file_path,
                        "line": node.lineno,
                        "confidence": confidence,
                        "description": f"异常处理模式 (具体异常: {has_specific_except}, finally: {has_finally})",
                        "details": {
                            "has_specific_except": has_specific_except,
                            "has_finally": has_finally,
                            "handler_count": len(node.handlers),
                        },
                    }
                )

        return patterns

    def _check_resource_management_patterns(
        self, tree: ast.AST, file_path: str
    ) -> List[Dict]:
        """检查资源管理模式"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                # 检查with语句（上下文管理器）
                patterns.append(
                    {
                        "type": "context_manager_pattern",
                        "file": file_path,
                        "line": node.lineno,
                        "confidence": 0.9,
                        "description": "使用上下文管理器进行资源管理",
                        "details": {"context_count": len(node.items)},
                    }
                )

        return patterns

    def _check_iteration_patterns(self, tree: ast.AST, file_path: str) -> List[Dict]:
        """检查迭代模式"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # 检查enumerate使用
                if isinstance(node.iter, ast.Call):
                    if (
                        isinstance(node.iter.func, ast.Name)
                        and node.iter.func.id == "enumerate"
                    ):
                        patterns.append(
                            {
                                "type": "enumerate_pattern",
                                "file": file_path,
                                "line": node.lineno,
                                "confidence": 0.8,
                                "description": "使用enumerate进行索引迭代",
                            }
                        )

                    # 检查zip使用
                    elif (
                        isinstance(node.iter.func, ast.Name)
                        and node.iter.func.id == "zip"
                    ):
                        patterns.append(
                            {
                                "type": "zip_pattern",
                                "file": file_path,
                                "line": node.lineno,
                                "confidence": 0.8,
                                "description": "使用zip进行并行迭代",
                            }
                        )

        return patterns

    def _check_function_patterns(self, tree: ast.AST, file_path: str) -> List[Dict]:
        """检查函数模式"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查装饰器使用
                if node.decorator_list:
                    patterns.append(
                        {
                            "type": "decorator_pattern",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "confidence": 0.8,
                            "description": f"函数使用装饰器: {len(node.decorator_list)}个",
                            "details": {"decorator_count": len(node.decorator_list)},
                        }
                    )

                # 检查文档字符串
                if ast.get_docstring(node):
                    patterns.append(
                        {
                            "type": "docstring_pattern",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "confidence": 0.9,
                            "description": "函数包含文档字符串",
                        }
                    )

        return patterns

    async def _recognize_anti_patterns(
        self, targets: List[Dict], threshold: float
    ) -> Dict[str, Any]:
        """识别反模式"""
        anti_patterns_found: Dict[str, List[Any]] = {
            "code_smells": [],
            "performance_issues": [],
            "maintainability_issues": [],
            "security_issues": [],
        }

        for target in targets:
            content = target["content"]
            language = target["language"]
            path = target["path"]

            if language == "python":
                file_anti_patterns = self._detect_python_anti_patterns(
                    content, path, threshold
                )
                for pattern_type, instances in file_anti_patterns.items():
                    anti_patterns_found[pattern_type].extend(instances)

        return {
            "anti_patterns_by_type": anti_patterns_found,
            "total_anti_patterns": sum(
                len(instances) for instances in anti_patterns_found.values()
            ),
            "severity_distribution": self._calculate_anti_pattern_severity(
                anti_patterns_found
            ),
        }

    def _detect_python_anti_patterns(
        self, content: str, file_path: str, threshold: float
    ) -> Dict[str, List[Dict]]:
        """检测Python反模式"""
        anti_patterns: Dict[str, List[Dict[str, Any]]] = {
            "code_smells": [],
            "performance_issues": [],
            "maintainability_issues": [],
            "security_issues": [],
        }

        try:
            tree = ast.parse(content)

            # 检测代码异味
            code_smells = self._detect_code_smells(tree, file_path, content)
            anti_patterns["code_smells"].extend(code_smells)

            # 检测性能问题
            performance_issues = self._detect_performance_issues(tree, file_path)
            anti_patterns["performance_issues"].extend(performance_issues)

            # 检测可维护性问题
            maintainability_issues = self._detect_maintainability_issues(
                tree, file_path
            )
            anti_patterns["maintainability_issues"].extend(maintainability_issues)

            # 检测安全问题
            security_issues = self._detect_security_issues(tree, file_path, content)
            anti_patterns["security_issues"].extend(security_issues)

        except SyntaxError:
            pass

        return anti_patterns

    def _detect_code_smells(
        self, tree: ast.AST, file_path: str, content: str
    ) -> List[Dict]:
        """检测代码异味"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检测长函数
                if hasattr(node, "end_lineno") and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    if func_length > 50:
                        smells.append(
                            {
                                "type": "long_function",
                                "name": node.name,
                                "file": file_path,
                                "line": node.lineno,
                                "severity": "medium",
                                "confidence": 0.9,
                                "description": f"函数过长 ({func_length} 行)",
                                "details": {"length": func_length},
                            }
                        )

                # 检测参数过多
                arg_count = len(node.args.args)
                if arg_count > 5:
                    smells.append(
                        {
                            "type": "too_many_parameters",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "severity": "medium",
                            "confidence": 0.8,
                            "description": f"参数过多 ({arg_count} 个)",
                            "details": {"parameter_count": arg_count},
                        }
                    )

            elif isinstance(node, ast.ClassDef):
                # 检测大类
                method_count = sum(
                    1 for child in node.body if isinstance(child, ast.FunctionDef)
                )
                if method_count > 20:
                    smells.append(
                        {
                            "type": "large_class",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "severity": "high",
                            "confidence": 0.9,
                            "description": f"类过大 ({method_count} 个方法)",
                            "details": {"method_count": method_count},
                        }
                    )

        return smells

    def _detect_performance_issues(self, tree: ast.AST, file_path: str) -> List[Dict]:
        """检测性能问题"""
        issues = []

        for node in ast.walk(tree):
            # 检测嵌套循环
            if isinstance(node, ast.For):
                nested_loops = 0
                for child in ast.walk(node):
                    if isinstance(child, (ast.For, ast.While)) and child != node:
                        nested_loops += 1

                if nested_loops >= 2:
                    issues.append(
                        {
                            "type": "nested_loops",
                            "file": file_path,
                            "line": node.lineno,
                            "severity": "medium",
                            "confidence": 0.8,
                            "description": f"嵌套循环 ({nested_loops + 1} 层)",
                            "details": {"nesting_level": nested_loops + 1},
                        }
                    )

        return issues

    def _detect_maintainability_issues(
        self, tree: ast.AST, file_path: str
    ) -> List[Dict]:
        """检测可维护性问题"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检测缺少文档字符串
                if not ast.get_docstring(node) and not node.name.startswith("_"):
                    issues.append(
                        {
                            "type": "missing_docstring",
                            "name": node.name,
                            "file": file_path,
                            "line": node.lineno,
                            "severity": "low",
                            "confidence": 0.7,
                            "description": "公共函数缺少文档字符串",
                        }
                    )

        return issues

    def _detect_security_issues(
        self, tree: ast.AST, file_path: str, content: str
    ) -> List[Dict]:
        """检测安全问题"""
        issues = []

        # 检测eval/exec使用
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec"]:
                    issues.append(
                        {
                            "type": "dangerous_function",
                            "function": node.func.id,
                            "file": file_path,
                            "line": node.lineno,
                            "severity": "high",
                            "confidence": 0.95,
                            "description": f"使用危险函数 {node.func.id}",
                        }
                    )

        # 检测硬编码密码
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if re.search(r'password\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                issues.append(
                    {
                        "type": "hardcoded_password",
                        "file": file_path,
                        "line": i,
                        "severity": "high",
                        "confidence": 0.8,
                        "description": "可能存在硬编码密码",
                    }
                )

        return issues

    def _filter_high_confidence_patterns(
        self, patterns: Dict, threshold: float
    ) -> Dict[str, List]:
        """过滤高置信度模式"""
        high_confidence = {}
        for pattern_type, instances in patterns.items():
            high_confidence[pattern_type] = [
                instance
                for instance in instances
                if instance.get("confidence", 0.0) >= threshold
            ]
        return high_confidence

    def _calculate_design_pattern_complexity(self, patterns: Dict) -> float:
        """计算设计模式复杂度"""
        complexity_weights = {
            "singleton": 0.3,
            "factory": 0.5,
            "observer": 0.8,
            "strategy": 0.6,
            "decorator": 0.7,
            "adapter": 0.4,
            "builder": 0.6,
            "command": 0.5,
        }

        total_complexity = 0.0
        for pattern_type, instances in patterns.items():
            weight = complexity_weights.get(pattern_type, 0.5)
            total_complexity += len(instances) * weight

        return total_complexity

    def _calculate_coding_pattern_quality(self, patterns: Dict) -> float:
        """计算编程模式质量分数"""
        quality_weights = {
            "naming_conventions": 0.2,
            "error_handling": 0.3,
            "resource_management": 0.3,
            "iteration_patterns": 0.1,
            "function_patterns": 0.1,
        }

        total_score = 0.0
        for pattern_type, instances in patterns.items():
            weight = quality_weights.get(pattern_type, 0.2)
            total_score += len(instances) * weight

        return min(total_score, 10.0)  # 最高10分

    def _calculate_anti_pattern_severity(self, anti_patterns: Dict) -> Dict[str, int]:
        """计算反模式严重程度分布"""
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for _pattern_type, instances in anti_patterns.items():
            for instance in instances:
                severity = instance.get("severity", "medium")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return severity_counts

    async def _recognize_performance_patterns(
        self, targets: List[Dict], threshold: float
    ) -> Dict[str, Any]:
        """识别性能模式"""
        # 简化实现，返回基本结构
        return {"patterns_found": [], "total_patterns": 0, "performance_score": 0.0}

    async def _recognize_security_patterns(
        self, targets: List[Dict], threshold: float
    ) -> Dict[str, Any]:
        """识别安全模式"""
        # 简化实现，返回基本结构
        return {"patterns_found": [], "total_patterns": 0, "security_score": 0.0}

    def _generate_pattern_summary(
        self, pattern_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成模式摘要"""
        summary: Dict[str, Any] = {
            "total_pattern_types": len(pattern_results),
            "key_findings": [],
            "quality_indicators": {},
        }

        for pattern_type, results in pattern_results.items():
            if pattern_type == "design_patterns":
                total_patterns = results.get("total_patterns", 0)
                summary["key_findings"].append(f"发现 {total_patterns} 个设计模式")
                summary["quality_indicators"]["design_pattern_usage"] = total_patterns

            elif pattern_type == "coding_patterns":
                total_patterns = results.get("total_patterns", 0)
                summary["key_findings"].append(f"发现 {total_patterns} 个编程模式")
                summary["quality_indicators"]["coding_pattern_quality"] = results.get(
                    "pattern_quality_score", 0.0
                )

            elif pattern_type == "anti_patterns":
                total_anti_patterns = results.get("total_anti_patterns", 0)
                summary["key_findings"].append(f"发现 {total_anti_patterns} 个反模式")
                summary["quality_indicators"][
                    "anti_pattern_count"
                ] = total_anti_patterns

        return summary

    def _generate_pattern_recommendations(
        self, pattern_results: Dict[str, Any]
    ) -> List[str]:
        """生成模式建议"""
        recommendations = []

        # 基于设计模式的建议
        if "design_patterns" in pattern_results:
            design_data = pattern_results["design_patterns"]
            patterns_by_type = design_data.get("patterns_by_type", {})

            if len(patterns_by_type.get("singleton", [])) > 3:
                recommendations.append("单例模式使用较多，考虑是否过度使用")

            if not patterns_by_type.get("factory", []) and patterns_by_type.get(
                "singleton", []
            ):
                recommendations.append("考虑使用工厂模式来管理对象创建")

        # 基于反模式的建议
        if "anti_patterns" in pattern_results:
            anti_data = pattern_results["anti_patterns"]
            severity_dist = anti_data.get("severity_distribution", {})

            if severity_dist.get("high", 0) > 0:
                recommendations.append("发现高严重性问题，建议优先修复")

            if severity_dist.get("medium", 0) > 5:
                recommendations.append("中等严重性问题较多，建议逐步改进")

        return recommendations

    def _store_pattern_result(self, data_type: str, result: Dict[str, Any]) -> None:
        """存储模式识别结果到ChromaDB"""
        try:
            content = json.dumps(result, ensure_ascii=False)
            metadata = {
                "data_type": data_type,
                "timestamp": str(result.get("timestamp", time.time())),
                "pattern_types": ",".join(
                    result.get("pattern_types", [])
                ),  # 转换为字符串
                "targets_count": int(result.get("targets_analyzed", 0)),
            }

            # 异步存储（这里简化为同步调用）
            self.data_manager.store_data(
                data_type=data_type, content=content, metadata=metadata
            )
        except Exception as e:  # nosec B110
            # 静默处理存储错误
            pass

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class BestPracticeAdvisor(BaseSemanticTool):
    """最佳实践建议器"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_best_practices",
            description="获取最佳实践建议",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["file", "function", "class", "project"],
                                "description": "分析目标类型",
                                "default": "file",
                            },
                            "path": {
                                "type": "string",
                                "description": "目标路径",
                                "default": ".",
                            },
                            "name": {
                                "type": "string",
                                "description": "目标名称（函数名或类名）",
                            },
                        },
                        "description": "分析目标配置",
                    },
                    "advice_categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "code_quality",
                                "performance",
                                "security",
                                "maintainability",
                                "testing",
                            ],
                        },
                        "description": "建议类别",
                        "default": ["code_quality", "maintainability"],
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言",
                        "default": "auto_detect",
                    },
                    "priority_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "优先级过滤",
                        "default": "medium",
                    },
                },
                "required": ["target"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行最佳实践分析"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {"type": "file", "path": "."})
            advice_categories = params.get(
                "advice_categories", ["code_quality", "maintainability"]
            )
            language = params.get("language", "auto_detect")
            priority_level = params.get("priority_level", "medium")

            # 分析目标代码
            code_analysis = await self._analyze_target_code(target, language)

            if not code_analysis:
                return self._create_error_result("ANALYSIS_FAILED", "代码分析失败")

            # 生成分类建议
            practice_advice = {}

            for category in advice_categories:
                if category == "code_quality":
                    practice_advice[category] = await self._analyze_code_quality(
                        code_analysis, language, priority_level
                    )
                elif category == "performance":
                    practice_advice[category] = await self._analyze_performance(
                        code_analysis, language, priority_level
                    )
                elif category == "security":
                    practice_advice[category] = await self._analyze_security(
                        code_analysis, language, priority_level
                    )
                elif category == "maintainability":
                    practice_advice[category] = await self._analyze_maintainability(
                        code_analysis, language, priority_level
                    )
                elif category == "testing":
                    practice_advice[category] = await self._analyze_testing(
                        code_analysis, language, priority_level
                    )

            # 生成行动计划
            action_plan = self._generate_action_plan(practice_advice, priority_level)

            # 创建最佳实践报告
            practice_report = {
                "target": target,
                "advice_categories": advice_categories,
                "language": language,
                "priority_level": priority_level,
                "code_analysis": code_analysis,
                "practice_advice": practice_advice,
                "action_plan": action_plan,
                "estimated_effort": self._estimate_implementation_effort(action_plan),
                "expected_benefits": self._calculate_expected_benefits(practice_advice),
                "timestamp": time.time(),
            }

            # 存储建议结果
            self._store_advice_result("best_practice_advice", practice_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(practice_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(practice_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(practice_report, metadata, resources)

        except Exception as e:
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    async def _analyze_target_code(
        self, target: Dict, language: str
    ) -> Optional[Dict[str, Any]]:
        """分析目标代码"""
        target_type = target.get("type", "file")
        path = target.get("path", ".")

        analysis = {
            "target_type": target_type,
            "path": path,
            "language": language,
            "files_analyzed": [],
            "code_structure": {},
            "metrics": {},
        }

        if target_type == "file":
            if Path(path).is_file():
                content = self._read_file_safely(path)
                if content:
                    if language == "auto_detect":
                        language = self._get_file_language(path)

                    file_analysis = self._analyze_single_file(content, path, language)
                    analysis["files_analyzed"].append(path)
                    analysis["code_structure"][path] = file_analysis
                    analysis["language"] = language

        elif target_type == "project":
            # 分析整个项目
            patterns = (
                ["*.py", "*.js", "*.ts"]
                if language == "auto_detect"
                else [f"*.{language}"]
            )
            files = self._find_files_by_pattern(path, patterns)

            for file_path in files[:20]:  # 限制分析文件数量
                content = self._read_file_safely(file_path)
                if content:
                    file_language = self._get_file_language(file_path)
                    file_analysis = self._analyze_single_file(
                        content, file_path, file_language
                    )
                    analysis["files_analyzed"].append(file_path)
                    analysis["code_structure"][file_path] = file_analysis

        # 计算整体指标
        analysis["metrics"] = self._calculate_overall_metrics(
            analysis["code_structure"]
        )

        return analysis if analysis["files_analyzed"] else None

    def _analyze_single_file(
        self, content: str, file_path: str, language: str
    ) -> Dict[str, Any]:
        """分析单个文件"""
        analysis: Dict[str, Any] = {
            "language": language,
            "line_count": len(content.split("\n")),
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity_metrics": {},
            "quality_issues": [],
        }

        if language == "python":
            try:
                tree = ast.parse(content)

                # 提取函数信息
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_analysis = self._analyze_function(node, content)
                        analysis["functions"].append(func_analysis)

                    elif isinstance(node, ast.ClassDef):
                        class_analysis = self._analyze_class(node, content)
                        analysis["classes"].append(class_analysis)

                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        import_info = self._analyze_import(node)
                        analysis["imports"].append(import_info)

                # 计算复杂度指标
                analysis["complexity_metrics"] = self._calculate_file_complexity(
                    tree, content
                )

                # 检测质量问题
                analysis["quality_issues"] = self._detect_quality_issues(
                    tree, content, file_path
                )

            except SyntaxError as e:
                analysis["syntax_error"] = str(e)

        return analysis

    def _analyze_function(
        self, func_node: ast.FunctionDef, content: str
    ) -> Dict[str, Any]:
        """分析函数"""
        return {
            "name": func_node.name,
            "line_start": func_node.lineno,
            "line_end": getattr(func_node, "end_lineno", func_node.lineno),
            "parameter_count": len(func_node.args.args),
            "has_docstring": bool(ast.get_docstring(func_node)),
            "complexity": self._calculate_function_complexity(func_node),
            "decorators": len(func_node.decorator_list),
        }

    def _analyze_class(self, class_node: ast.ClassDef, content: str) -> Dict[str, Any]:
        """分析类"""
        methods = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods.append(node.name)

        return {
            "name": class_node.name,
            "line_start": class_node.lineno,
            "line_end": getattr(class_node, "end_lineno", class_node.lineno),
            "method_count": len(methods),
            "methods": methods,
            "has_docstring": bool(ast.get_docstring(class_node)),
            "inheritance": len(class_node.bases),
        }

    def _analyze_import(self, import_node: ast.AST) -> Dict[str, Any]:
        """分析导入"""
        if isinstance(import_node, ast.Import):
            return {
                "type": "import",
                "modules": [alias.name for alias in import_node.names],
                "line": import_node.lineno,
            }
        elif isinstance(import_node, ast.ImportFrom):
            return {
                "type": "from_import",
                "module": import_node.module,
                "names": [alias.name for alias in import_node.names],
                "line": import_node.lineno,
            }

        return {}

    def _calculate_file_complexity(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """计算文件复杂度"""
        metrics = {
            "cyclomatic_complexity": 0,
            "function_count": 0,
            "class_count": 0,
            "line_count": len(content.split("\n")),
            "comment_ratio": 0.0,
        }

        # 计算圈复杂度
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics["function_count"] += 1
                metrics["cyclomatic_complexity"] += self._calculate_function_complexity(
                    node
                )
            elif isinstance(node, ast.ClassDef):
                metrics["class_count"] += 1

        # 计算注释比例
        lines = content.split("\n")
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        metrics["comment_ratio"] = comment_lines / max(len(lines), 1)

        return metrics

    def _detect_quality_issues(
        self, tree: ast.AST, content: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """检测质量问题"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检测长函数
                if hasattr(node, "end_lineno") and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    if func_length > 30:
                        issues.append(
                            {
                                "type": "long_function",
                                "severity": "medium",
                                "function": node.name,
                                "line": node.lineno,
                                "details": {"length": func_length},
                            }
                        )

                # 检测参数过多
                if len(node.args.args) > 4:
                    issues.append(
                        {
                            "type": "too_many_parameters",
                            "severity": "low",
                            "function": node.name,
                            "line": node.lineno,
                            "details": {"parameter_count": len(node.args.args)},
                        }
                    )

                # 检测缺少文档字符串
                if not ast.get_docstring(node) and not node.name.startswith("_"):
                    issues.append(
                        {
                            "type": "missing_docstring",
                            "severity": "low",
                            "function": node.name,
                            "line": node.lineno,
                        }
                    )

        return issues

    def _calculate_overall_metrics(
        self, code_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算整体指标"""
        metrics = {
            "total_files": len(code_structure),
            "total_functions": 0,
            "total_classes": 0,
            "total_lines": 0,
            "average_complexity": 0.0,
            "quality_score": 0.0,
        }

        total_complexity = 0
        total_issues = 0

        for _file_path, file_analysis in code_structure.items():
            metrics["total_functions"] += len(file_analysis.get("functions", []))
            metrics["total_classes"] += len(file_analysis.get("classes", []))
            metrics["total_lines"] += file_analysis.get("line_count", 0)

            file_complexity = file_analysis.get("complexity_metrics", {}).get(
                "cyclomatic_complexity", 0
            )
            total_complexity += file_complexity

            total_issues += len(file_analysis.get("quality_issues", []))

        if metrics["total_functions"] > 0:
            metrics["average_complexity"] = (
                total_complexity / metrics["total_functions"]
            )

        # 计算质量分数 (0-100)
        if metrics["total_lines"] > 0:
            issue_density = total_issues / (
                metrics["total_lines"] / 100
            )  # 每100行的问题数
            metrics["quality_score"] = max(0, 100 - issue_density * 10)

        return metrics

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """计算函数复杂度（圈复杂度）"""
        complexity = 1  # 基础复杂度

        for node in ast.walk(func_node):
            # 条件语句增加复杂度
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            # 异常处理增加复杂度
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            # 逻辑运算符增加复杂度
            elif isinstance(node, ast.BoolOp):
                if isinstance(node.op, (ast.And, ast.Or)):
                    complexity += len(node.values) - 1
            # 三元运算符增加复杂度
            elif isinstance(node, ast.IfExp):
                complexity += 1

        return complexity

    async def _analyze_code_quality(
        self, code_analysis: Dict, language: str, priority_level: str
    ) -> Dict[str, Any]:
        """分析代码质量"""
        quality_advice = {
            "overall_score": code_analysis.get("metrics", {}).get("quality_score", 0.0),
            "issues": [],
            "recommendations": [],
            "improvements": [],
        }

        # 收集所有质量问题
        for file_path, file_analysis in code_analysis.get("code_structure", {}).items():
            quality_issues = file_analysis.get("quality_issues", [])
            for issue in quality_issues:
                if self._meets_priority_threshold(
                    issue.get("severity", "low"), priority_level
                ):
                    issue["file"] = file_path
                    quality_advice["issues"].append(issue)

        # 生成建议
        quality_advice["recommendations"] = self._generate_quality_recommendations(
            quality_advice["issues"], code_analysis["metrics"]
        )

        # 生成改进措施
        quality_advice["improvements"] = self._generate_quality_improvements(
            quality_advice["issues"], language
        )

        return quality_advice

    async def _analyze_performance(
        self, code_analysis: Dict, language: str, priority_level: str
    ) -> Dict[str, Any]:
        """分析性能"""
        performance_advice = {
            "complexity_score": code_analysis.get("metrics", {}).get(
                "average_complexity", 0.0
            ),
            "issues": [],
            "recommendations": [],
            "optimizations": [],
        }

        # 检测性能问题
        for file_path, file_analysis in code_analysis.get("code_structure", {}).items():
            # 检查高复杂度函数
            for func in file_analysis.get("functions", []):
                if func.get("complexity", 0) > 10:
                    performance_advice["issues"].append(
                        {
                            "type": "high_complexity_function",
                            "severity": "medium",
                            "file": file_path,
                            "function": func["name"],
                            "line": func["line_start"],
                            "complexity": func["complexity"],
                        }
                    )

        # 生成性能建议
        performance_advice["recommendations"] = (
            self._generate_performance_recommendations(
                performance_advice["issues"], language
            )
        )

        performance_advice["optimizations"] = self._generate_performance_optimizations(
            code_analysis, language
        )

        return performance_advice

    async def _analyze_security(
        self, code_analysis: Dict, language: str, priority_level: str
    ) -> Dict[str, Any]:
        """分析安全性"""
        security_advice: Dict[str, Any] = {
            "risk_level": "low",
            "vulnerabilities": [],
            "recommendations": [],
            "security_practices": [],
        }

        # 基础安全检查（简化实现）
        for file_path, file_analysis in code_analysis.get("code_structure", {}).items():
            # 检查导入的安全性
            for import_info in file_analysis.get("imports", []):
                if import_info.get("type") == "import":
                    for module in import_info.get("modules", []):
                        if module in ["subprocess", "os", "sys"]:
                            security_advice["vulnerabilities"].append(
                                {
                                    "type": "potentially_dangerous_import",
                                    "severity": "low",
                                    "file": file_path,
                                    "module": module,
                                    "line": import_info["line"],
                                }
                            )

        # 评估风险等级
        if security_advice["vulnerabilities"]:
            vulnerabilities = security_advice["vulnerabilities"]
            if isinstance(vulnerabilities, list):
                high_risk_count = sum(
                    1
                    for v in vulnerabilities
                    if isinstance(v, dict) and v.get("severity") == "high"
                )
            else:
                high_risk_count = 0
            if high_risk_count > 0:
                security_advice["risk_level"] = "high"
            elif len(security_advice["vulnerabilities"]) > 3:
                security_advice["risk_level"] = "medium"

        # 生成安全建议
        vulnerabilities = security_advice["vulnerabilities"]
        if isinstance(vulnerabilities, list):
            security_advice["recommendations"] = (
                self._generate_security_recommendations(vulnerabilities, language)
            )
        else:
            security_advice["recommendations"] = []

        security_advice["security_practices"] = self._generate_security_practices(
            language
        )

        return security_advice

    async def _analyze_maintainability(
        self, code_analysis: Dict, language: str, priority_level: str
    ) -> Dict[str, Any]:
        """分析可维护性"""
        maintainability_advice: Dict[str, Any] = {
            "maintainability_score": 0.0,
            "issues": [],
            "recommendations": [],
            "refactoring_suggestions": [],
        }

        metrics = code_analysis.get("metrics", {})

        # 计算可维护性分数
        quality_score = metrics.get("quality_score", 0.0)
        complexity_penalty = min(metrics.get("average_complexity", 0.0) * 5, 30)
        maintainability_advice["maintainability_score"] = max(
            0, quality_score - complexity_penalty
        )

        # 收集可维护性问题
        for file_path, file_analysis in code_analysis.get("code_structure", {}).items():
            # 检查大类
            for cls in file_analysis.get("classes", []):
                if cls.get("method_count", 0) > 15:
                    maintainability_advice["issues"].append(
                        {
                            "type": "large_class",
                            "severity": "medium",
                            "file": file_path,
                            "class": cls["name"],
                            "method_count": cls["method_count"],
                        }
                    )

            # 检查缺少文档的函数
            undocumented_functions = [
                func
                for func in file_analysis.get("functions", [])
                if not func.get("has_docstring", False)
                and not func["name"].startswith("_")
            ]

            if len(undocumented_functions) > 3:
                maintainability_advice["issues"].append(
                    {
                        "type": "insufficient_documentation",
                        "severity": "low",
                        "file": file_path,
                        "undocumented_count": len(undocumented_functions),
                    }
                )

        # 生成建议
        issues = maintainability_advice["issues"]
        if isinstance(issues, list):
            maintainability_advice["recommendations"] = (
                self._generate_maintainability_recommendations(issues, metrics)
            )
        else:
            maintainability_advice["recommendations"] = []

        maintainability_advice["refactoring_suggestions"] = (
            self._generate_refactoring_suggestions(code_analysis, language)
        )

        return maintainability_advice

    async def _analyze_testing(
        self, code_analysis: Dict, language: str, priority_level: str
    ) -> Dict[str, Any]:
        """分析测试"""
        testing_advice: Dict[str, Any] = {
            "test_coverage_estimate": 0.0,
            "testability_score": 0.0,
            "issues": [],
            "recommendations": [],
            "testing_strategies": [],
        }

        # 简化的测试分析
        total_functions = code_analysis.get("metrics", {}).get("total_functions", 0)

        # 检查是否有测试文件
        test_files = [
            path
            for path in code_analysis.get("files_analyzed", [])
            if "test" in Path(path).name.lower()
        ]

        if test_files:
            testing_advice["test_coverage_estimate"] = min(len(test_files) * 20, 100)

        # 计算可测试性分数
        avg_complexity = code_analysis.get("metrics", {}).get("average_complexity", 0.0)
        testing_advice["testability_score"] = max(0, 100 - avg_complexity * 10)

        # 生成测试建议
        if not test_files:
            testing_advice["issues"].append(
                {
                    "type": "no_test_files",
                    "severity": "medium",
                    "description": "项目中未发现测试文件",
                }
            )

        issues = testing_advice["issues"]
        if isinstance(issues, list):
            testing_advice["recommendations"] = self._generate_testing_recommendations(
                issues, total_functions
            )
        else:
            testing_advice["recommendations"] = []

        testing_advice["testing_strategies"] = self._generate_testing_strategies(
            language
        )

        return testing_advice

    def _meets_priority_threshold(self, severity: str, priority_level: str) -> bool:
        """检查是否满足优先级阈值"""
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        priority_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        return severity_levels.get(severity, 1) >= priority_levels.get(
            priority_level, 2
        )

    def _generate_quality_recommendations(
        self, issues: List[Dict], metrics: Dict
    ) -> List[str]:
        """生成质量建议"""
        recommendations = []

        # 基于问题类型的建议
        issue_types: Dict[str, int] = {}
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        if issue_types.get("long_function", 0) > 2:
            recommendations.append("多个函数过长，建议拆分为更小的函数")

        if issue_types.get("too_many_parameters", 0) > 1:
            recommendations.append("多个函数参数过多，考虑使用对象或配置类")

        if issue_types.get("missing_docstring", 0) > 5:
            recommendations.append("缺少文档字符串的函数较多，建议补充文档")

        # 基于整体指标的建议
        quality_score = metrics.get("quality_score", 0.0)
        if quality_score < 60:
            recommendations.append("整体代码质量较低，建议进行全面重构")
        elif quality_score < 80:
            recommendations.append("代码质量有待提升，建议逐步改进")

        return recommendations

    def _generate_quality_improvements(
        self, issues: List[Dict], language: str
    ) -> List[Dict]:
        """生成质量改进措施"""
        improvements = []

        for issue in issues:
            if issue["type"] == "long_function":
                improvements.append(
                    {
                        "issue_type": issue["type"],
                        "action": "拆分函数",
                        "description": f"将 {issue.get('function', 'unknown')} 函数拆分为多个小函数",
                        "effort": "medium",
                        "benefit": "提高代码可读性和可维护性",
                    }
                )

            elif issue["type"] == "too_many_parameters":
                improvements.append(
                    {
                        "issue_type": issue["type"],
                        "action": "重构参数",
                        "description": f"为 {issue.get('function', 'unknown')} 函数使用配置对象或减少参数",
                        "effort": "low",
                        "benefit": "简化函数接口",
                    }
                )

        return improvements

    def _generate_performance_recommendations(
        self, issues: List[Dict], language: str
    ) -> List[str]:
        """生成性能建议"""
        recommendations = []

        high_complexity_count = sum(
            1 for issue in issues if issue["type"] == "high_complexity_function"
        )

        if high_complexity_count > 0:
            recommendations.append(
                f"发现 {high_complexity_count} 个高复杂度函数，建议重构以提高性能"
            )

        if language == "python":
            recommendations.extend(
                [
                    "考虑使用列表推导式替代循环",
                    "对于大数据处理，考虑使用 numpy 或 pandas",
                    "使用 functools.lru_cache 缓存计算结果",
                ]
            )

        return recommendations

    def _generate_performance_optimizations(
        self, code_analysis: Dict, language: str
    ) -> List[Dict]:
        """生成性能优化建议"""
        optimizations = []

        metrics = code_analysis.get("metrics", {})
        avg_complexity = metrics.get("average_complexity", 0.0)

        if avg_complexity > 5:
            optimizations.append(
                {
                    "type": "complexity_reduction",
                    "description": "降低函数复杂度",
                    "impact": "high",
                    "effort": "medium",
                    "techniques": ["提取方法", "简化条件逻辑", "使用多态替代条件"],
                }
            )

        if language == "python":
            optimizations.append(
                {
                    "type": "python_specific",
                    "description": "Python性能优化",
                    "impact": "medium",
                    "effort": "low",
                    "techniques": ["使用生成器", "避免全局变量", "使用局部变量缓存"],
                }
            )

        return optimizations

    def _generate_security_recommendations(
        self, vulnerabilities: List[Dict], language: str
    ) -> List[str]:
        """生成安全建议"""
        recommendations = []

        if vulnerabilities:
            recommendations.append("发现潜在安全风险，建议进行安全审查")

        if language == "python":
            recommendations.extend(
                [
                    "避免使用 eval() 和 exec() 函数",
                    "对用户输入进行验证和清理",
                    "使用参数化查询防止SQL注入",
                    "定期更新依赖库以修复安全漏洞",
                ]
            )

        return recommendations

    def _generate_security_practices(self, language: str) -> List[Dict]:
        """生成安全实践建议"""
        practices = [
            {
                "category": "input_validation",
                "title": "输入验证",
                "description": "对所有用户输入进行验证和清理",
                "priority": "high",
            },
            {
                "category": "error_handling",
                "title": "错误处理",
                "description": "避免在错误信息中泄露敏感信息",
                "priority": "medium",
            },
            {
                "category": "dependency_management",
                "title": "依赖管理",
                "description": "定期更新和审查第三方依赖",
                "priority": "medium",
            },
        ]

        return practices

    def _generate_maintainability_recommendations(
        self, issues: List[Dict], metrics: Dict
    ) -> List[str]:
        """生成可维护性建议"""
        recommendations = []

        large_class_count = sum(1 for issue in issues if issue["type"] == "large_class")
        if large_class_count > 0:
            recommendations.append("发现大类，建议拆分以提高可维护性")

        insufficient_doc_count = sum(
            1 for issue in issues if issue["type"] == "insufficient_documentation"
        )
        if insufficient_doc_count > 0:
            recommendations.append("文档不足，建议补充函数和类的文档字符串")

        avg_complexity = metrics.get("average_complexity", 0.0)
        if avg_complexity > 5:
            recommendations.append("平均复杂度较高，建议简化函数逻辑")

        return recommendations

    def _generate_refactoring_suggestions(
        self, code_analysis: Dict, language: str
    ) -> List[Dict]:
        """生成重构建议"""
        suggestions = []

        metrics = code_analysis.get("metrics", {})

        # 基于指标的重构建议
        if metrics.get("average_complexity", 0.0) > 7:
            suggestions.append(
                {
                    "type": "complexity_refactoring",
                    "title": "降低复杂度",
                    "description": "重构高复杂度函数，提取子函数",
                    "priority": "high",
                    "estimated_effort": "medium",
                }
            )

        if (
            metrics.get("total_functions", 0) > 50
            and metrics.get("total_classes", 0) < 5
        ):
            suggestions.append(
                {
                    "type": "structure_refactoring",
                    "title": "改进代码结构",
                    "description": "将相关函数组织到类中，提高代码结构",
                    "priority": "medium",
                    "estimated_effort": "high",
                }
            )

        return suggestions

    def _generate_testing_recommendations(
        self, issues: List[Dict], total_functions: int
    ) -> List[str]:
        """生成测试建议"""
        recommendations = []

        if any(issue["type"] == "no_test_files" for issue in issues):
            recommendations.append("建议为项目添加单元测试")

        if total_functions > 10:
            recommendations.append("函数较多，建议实施测试驱动开发(TDD)")
            recommendations.append("考虑使用代码覆盖率工具监控测试质量")

        return recommendations

    def _generate_testing_strategies(self, language: str) -> List[Dict]:
        """生成测试策略"""
        strategies = [
            {
                "type": "unit_testing",
                "title": "单元测试",
                "description": "为每个函数编写单元测试",
                "tools": (
                    ["pytest", "unittest"]
                    if language == "python"
                    else ["jest", "mocha"]
                ),
            },
            {
                "type": "integration_testing",
                "title": "集成测试",
                "description": "测试模块间的交互",
                "tools": (
                    ["pytest", "requests"]
                    if language == "python"
                    else ["supertest", "cypress"]
                ),
            },
        ]

        return strategies

    def _generate_action_plan(
        self, practice_advice: Dict, priority_level: str
    ) -> List[Dict]:
        """生成行动计划"""
        action_plan = []

        # 收集所有建议并按优先级排序
        all_issues = []
        for category, advice in practice_advice.items():
            issues = advice.get("issues", [])
            for issue in issues:
                issue["category"] = category
                all_issues.append(issue)

        # 按严重程度排序
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        all_issues.sort(
            key=lambda x: severity_order.get(x.get("severity", "low"), 1), reverse=True
        )

        # 生成行动项
        for i, issue in enumerate(all_issues[:10]):  # 限制前10个问题
            action_plan.append(
                {
                    "priority": i + 1,
                    "category": issue["category"],
                    "issue_type": issue["type"],
                    "severity": issue.get("severity", "low"),
                    "description": self._get_action_description(issue),
                    "estimated_effort": self._estimate_effort(issue),
                    "expected_benefit": self._estimate_benefit(issue),
                }
            )

        return action_plan

    def _get_action_description(self, issue: Dict) -> str:
        """获取行动描述"""
        issue_type = issue.get("type", "unknown")

        descriptions = {
            "long_function": f"重构函数 {issue.get('function', 'unknown')}，拆分为更小的函数",
            "too_many_parameters": f"简化函数 {issue.get('function', 'unknown')} 的参数列表",
            "missing_docstring": f"为函数 {issue.get('function', 'unknown')} 添加文档字符串",
            "large_class": f"重构类 {issue.get('class', 'unknown')}，考虑拆分",
            "high_complexity_function": f"降低函数 {issue.get('function', 'unknown')} 的复杂度",
        }

        return descriptions.get(issue_type, f"处理 {issue_type} 问题")

    def _estimate_effort(self, issue: Dict) -> str:
        """估算工作量"""
        issue_type = issue.get("type", "unknown")

        effort_map = {
            "missing_docstring": "low",
            "too_many_parameters": "low",
            "long_function": "medium",
            "large_class": "high",
            "high_complexity_function": "medium",
        }

        return effort_map.get(issue_type, "medium")

    def _estimate_benefit(self, issue: Dict) -> str:
        """估算收益"""
        severity = issue.get("severity", "low")

        benefit_map = {
            "critical": "very_high",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }

        return benefit_map.get(severity, "medium")

    def _estimate_implementation_effort(
        self, action_plan: List[Dict]
    ) -> Dict[str, Any]:
        """估算实施工作量"""
        effort_counts = {"low": 0, "medium": 0, "high": 0}

        for action in action_plan:
            effort = action.get("estimated_effort", "medium")
            effort_counts[effort] = effort_counts.get(effort, 0) + 1

        # 计算总工作量（以小时为单位）
        effort_hours = {"low": 2, "medium": 8, "high": 24}

        total_hours = sum(
            effort_counts[level] * effort_hours[level] for level in effort_counts
        )

        return {
            "total_hours": total_hours,
            "effort_distribution": effort_counts,
            "estimated_days": total_hours / 8,
            "complexity": (
                "high" if total_hours > 40 else "medium" if total_hours > 16 else "low"
            ),
        }

    def _calculate_expected_benefits(self, practice_advice: Dict) -> Dict[str, Any]:
        """计算预期收益"""
        benefits = {
            "code_quality_improvement": 0.0,
            "maintainability_improvement": 0.0,
            "performance_improvement": 0.0,
            "security_improvement": 0.0,
            "overall_score": 0.0,
        }

        # 基于各类建议计算收益
        for category, advice in practice_advice.items():
            issues = advice.get("issues", [])
            high_severity_count = sum(
                1 for issue in issues if issue.get("severity") in ["high", "critical"]
            )

            if category == "code_quality":
                benefits["code_quality_improvement"] = min(high_severity_count * 10, 50)
            elif category == "maintainability":
                benefits["maintainability_improvement"] = min(
                    high_severity_count * 15, 60
                )
            elif category == "performance":
                benefits["performance_improvement"] = min(high_severity_count * 12, 40)
            elif category == "security":
                benefits["security_improvement"] = min(high_severity_count * 20, 80)

        # 计算总体分数
        benefits["overall_score"] = sum(benefits.values()) / 4

        return benefits

    def _store_advice_result(self, data_type: str, result: Dict[str, Any]) -> None:
        """存储建议结果到ChromaDB"""
        try:
            content = json.dumps(result, ensure_ascii=False)
            metadata = {
                "data_type": data_type,
                "timestamp": str(result.get("timestamp", time.time())),
                "advice_categories": ",".join(
                    result.get("advice_categories", [])
                ),  # 转换为字符串
                "priority_level": str(result.get("priority_level", "medium")),
                "target_type": str(result.get("target", {}).get("type", "unknown")),
            }

            # 异步存储（这里简化为同步调用）
            self.data_manager.store_data(
                data_type=data_type, content=content, metadata=metadata
            )
        except Exception as e:  # nosec B110
            # 静默处理存储错误
            pass

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class SemanticIntelligenceTools:
    """语义智能工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有语义智能工具"""
        return [
            SemanticUnderstanding(self.config),
            CodeCompletionEngine(self.config),
            PatternRecognizer(self.config),
            BestPracticeAdvisor(self.config),
        ]
