"""
智能分析和历史管理系统

提供代码质量分析、性能监控、历史趋势分析等智能化功能，
帮助 Agent 做出更好的开发决策。
"""

import json
import os
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

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


class BaseAnalysisTool(BaseTool):
    """智能分析工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager = UnifiedDataManager(
            self.config.get("chromadb_path", "./mcp_unified_db")
        )
        self.analysis_depth = self.config.get("analysis_depth", "medium")
        self.history_window = self.config.get("history_window_days", 30)

    def _get_project_files(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[str]:
        """获取项目文件列表"""
        if include_patterns is None:
            include_patterns = [
                "*.py",
                "*.js",
                "*.ts",
                "*.java",
                "*.cpp",
                "*.c",
                "*.go",
                "*.rs",
            ]
        if exclude_patterns is None:
            exclude_patterns = [
                "__pycache__",
                ".git",
                "node_modules",
                "*.pyc",
                "*.class",
            ]

        project_files = []
        current_dir = os.getcwd()

        for root, dirs, files in os.walk(current_dir):
            # 过滤目录
            dirs[:] = [
                d
                for d in dirs
                if not any(
                    pattern.replace("*", "") in d for pattern in exclude_patterns
                )
            ]

            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, current_dir)

                # 检查包含模式
                if include_patterns:
                    if not any(
                        self._match_pattern(rel_path, pattern)
                        for pattern in include_patterns
                    ):
                        continue

                # 检查排除模式
                if exclude_patterns:
                    if any(
                        self._match_pattern(rel_path, pattern)
                        for pattern in exclude_patterns
                    ):
                        continue

                project_files.append(rel_path)

        return project_files

    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """匹配文件模式"""
        if "*" in pattern:
            regex_pattern = pattern.replace("*", ".*")
            return re.match(regex_pattern, filename) is not None
        else:
            return pattern in filename

    def _get_operation_history(
        self, days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取操作历史"""
        if days is None:
            days = self.history_window

        try:
            results = self.data_manager.query_data(
                query="agent operation", data_type="agent_operation", n_results=1000
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                # 过滤时间范围
                cutoff_time = time.time() - (days * 24 * 3600)
                return [
                    op
                    for op in metadatas
                    if isinstance(op, dict) and op.get("timestamp", 0) > cutoff_time
                ]
            return []
        except Exception as e:
            print(f"获取操作历史失败: {e}")
            return []


class CodeQualityAnalyzer(BaseAnalysisTool):
    """代码质量分析工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_code_quality",
            description="分析代码质量和提供改进建议",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要分析的文件列表",
                            },
                            "directories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要分析的目录列表",
                            },
                            "patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "文件匹配模式",
                            },
                        },
                        "description": "分析目标",
                    },
                    "analysis_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "complexity",
                                "duplication",
                                "style",
                                "security",
                                "performance",
                                "maintainability",
                            ],
                        },
                        "description": "分析类型",
                        "default": ["complexity", "style", "maintainability"],
                    },
                    "severity_threshold": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "严重程度阈值",
                        "default": "medium",
                    },
                    "include_suggestions": {
                        "type": "boolean",
                        "description": "是否包含改进建议",
                        "default": True,
                    },
                    "compare_with_history": {
                        "type": "boolean",
                        "description": "是否与历史数据比较",
                        "default": True,
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行代码质量分析"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params.get("target", {})
            analysis_types = params.get(
                "analysis_types", ["complexity", "style", "maintainability"]
            )
            severity_threshold = params.get("severity_threshold", "medium")
            include_suggestions = params.get("include_suggestions", True)
            compare_with_history = params.get("compare_with_history", True)

            # 确定分析目标文件
            target_files = self._determine_target_files(target)

            if not target_files:
                return self._create_error_result(
                    "NO_FILES_FOUND", "没有找到要分析的文件"
                )

            # 执行代码质量分析
            analysis_result = self._perform_quality_analysis(
                target_files, analysis_types, severity_threshold, include_suggestions
            )

            if not analysis_result["success"]:
                return self._create_error_result(
                    "ANALYSIS_FAILED", analysis_result["error"]
                )

            # 与历史数据比较
            if compare_with_history:
                historical_comparison = self._compare_with_history(
                    analysis_result["data"]
                )
                analysis_result["data"]["historical_comparison"] = historical_comparison

            # 存储分析结果
            self._store_analysis_result("code_quality", analysis_result["data"])

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(analysis_result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            resources = ResourceUsage(
                memory_mb=len(str(analysis_result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(target_files),
            )

            return self._create_success_result(
                analysis_result["data"], metadata, resources
            )

        except Exception as e:
            print(f"代码质量分析执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _determine_target_files(self, target: Dict[str, Any]) -> List[str]:
        """确定目标文件"""
        target_files = []

        # 直接指定的文件
        if "files" in target:
            for file_path in target["files"]:
                if os.path.exists(file_path):
                    target_files.append(file_path)

        # 目录中的文件
        if "directories" in target:
            for directory in target["directories"]:
                if os.path.exists(directory):
                    for root, _, files in os.walk(directory):
                        for file in files:
                            if self._is_code_file(file):
                                target_files.append(os.path.join(root, file))

        # 模式匹配的文件
        if "patterns" in target:
            all_files = self._get_project_files(target["patterns"])
            target_files.extend(all_files)

        # 如果没有指定目标，分析所有代码文件
        if not target_files and not target:
            target_files = self._get_project_files()

        return list(set(target_files))  # 去重

    def _is_code_file(self, filename: str) -> bool:
        """判断是否为代码文件"""
        code_extensions = [
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".go",
            ".rs",
            ".php",
            ".rb",
        ]
        return any(filename.endswith(ext) for ext in code_extensions)

    def _perform_quality_analysis(
        self,
        files: List[str],
        analysis_types: List[str],
        severity_threshold: str,
        include_suggestions: bool,
    ) -> Dict[str, Any]:
        """执行质量分析"""
        try:
            analysis_results: Dict[str, Any] = {
                "files_analyzed": len(files),
                "analysis_types": analysis_types,
                "severity_threshold": severity_threshold,
                "timestamp": time.time(),
                "issues": [],
                "metrics": {},
                "summary": {},
            }

            total_lines = 0
            total_issues = 0
            severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

            for file_path in files:
                try:
                    file_analysis = self._analyze_single_file(file_path, analysis_types)

                    total_lines += file_analysis["lines_of_code"]

                    # 过滤严重程度
                    filtered_issues = self._filter_by_severity(
                        file_analysis["issues"], severity_threshold
                    )

                    total_issues += len(filtered_issues)

                    # 统计严重程度
                    for issue in filtered_issues:
                        severity_counts[issue["severity"]] += 1

                    if filtered_issues:  # 只包含有问题的文件
                        analysis_results["issues"].extend(
                            [{**issue, "file": file_path} for issue in filtered_issues]
                        )

                except Exception as e:
                    print(f"分析文件 {file_path} 失败: {e}")
                    continue

            # 计算指标
            analysis_results["metrics"] = {
                "total_lines": total_lines,
                "total_issues": total_issues,
                "issues_per_1000_lines": (total_issues / max(total_lines, 1)) * 1000,
                "severity_distribution": severity_counts,
            }

            # 生成摘要
            analysis_results["summary"] = self._generate_quality_summary(
                analysis_results, include_suggestions
            )

            return {"success": True, "data": analysis_results}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_single_file(
        self, file_path: str, analysis_types: List[str]
    ) -> Dict[str, Any]:
        """分析单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            issues = []

            # 复杂度分析
            if "complexity" in analysis_types:
                issues.extend(self._analyze_complexity(content, lines))

            # 代码重复分析
            if "duplication" in analysis_types:
                issues.extend(self._analyze_duplication(content, lines))

            # 代码风格分析
            if "style" in analysis_types:
                issues.extend(self._analyze_style(content, lines, file_path))

            # 安全性分析
            if "security" in analysis_types:
                issues.extend(self._analyze_security(content, lines))

            # 性能分析
            if "performance" in analysis_types:
                issues.extend(self._analyze_performance(content, lines))

            # 可维护性分析
            if "maintainability" in analysis_types:
                issues.extend(self._analyze_maintainability(content, lines))

            return {
                "lines_of_code": len(
                    [
                        line
                        for line in lines
                        if line.strip() and not line.strip().startswith("#")
                    ]
                ),
                "total_lines": len(lines),
                "issues": issues,
            }

        except Exception as e:
            return {
                "lines_of_code": 0,
                "total_lines": 0,
                "issues": [
                    {
                        "type": "file_error",
                        "severity": "medium",
                        "message": f"无法分析文件: {str(e)}",
                        "line": 1,
                    }
                ],
            }

    def _analyze_complexity(
        self, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """分析代码复杂度"""
        issues = []

        # 简单的圈复杂度分析
        complexity_keywords = [
            "if",
            "elif",
            "else",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
        ]

        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # 检查复杂的条件语句
            if any(keyword in stripped_line for keyword in complexity_keywords):
                # 计算条件复杂度
                condition_complexity = (
                    stripped_line.count("and") + stripped_line.count("or") + 1
                )

                if condition_complexity > 3:
                    issues.append(
                        {
                            "type": "complexity",
                            "severity": (
                                "medium" if condition_complexity <= 5 else "high"
                            ),
                            "message": f"复杂的条件语句 (复杂度: {condition_complexity})",
                            "line": i,
                            "suggestion": "考虑将复杂条件分解为多个简单条件",
                        }
                    )

            # 检查长函数
            if stripped_line.startswith("def "):
                function_lines = self._count_function_lines(lines, i - 1)
                if function_lines > 50:
                    issues.append(
                        {
                            "type": "complexity",
                            "severity": "medium" if function_lines <= 100 else "high",
                            "message": f"函数过长 ({function_lines} 行)",
                            "line": i,
                            "suggestion": "考虑将大函数分解为多个小函数",
                        }
                    )

        return issues

    def _count_function_lines(self, lines: List[str], start_index: int) -> int:
        """计算函数行数"""
        count = 1
        indent_level = len(lines[start_index]) - len(lines[start_index].lstrip())

        for i in range(start_index + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip():
                break
            count += 1

        return count

    def _analyze_duplication(
        self, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """分析代码重复"""
        issues = []

        # 简单的重复行检测
        line_counts = defaultdict(list)

        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if len(stripped_line) > 10 and not stripped_line.startswith("#"):
                line_counts[stripped_line].append(i)

        for _line_content, line_numbers in line_counts.items():
            if len(line_numbers) > 2:
                issues.append(
                    {
                        "type": "duplication",
                        "severity": "low" if len(line_numbers) <= 3 else "medium",
                        "message": f"重复代码行 (出现 {len(line_numbers)} 次)",
                        "line": line_numbers[0],
                        "suggestion": "考虑提取重复代码为函数或常量",
                    }
                )

        return issues

    def _analyze_style(
        self, content: str, lines: List[str], file_path: str
    ) -> List[Dict[str, Any]]:
        """分析代码风格"""
        issues = []

        # Python 风格检查
        if file_path.endswith(".py"):
            for i, line in enumerate(lines, 1):
                # 检查行长度
                if len(line) > 120:
                    issues.append(
                        {
                            "type": "style",
                            "severity": "low",
                            "message": f"行过长 ({len(line)} 字符)",
                            "line": i,
                            "suggestion": "将长行分解为多行",
                        }
                    )

                # 检查缩进
                if line.startswith("\t"):
                    issues.append(
                        {
                            "type": "style",
                            "severity": "low",
                            "message": "使用制表符缩进",
                            "line": i,
                            "suggestion": "使用4个空格进行缩进",
                        }
                    )

                # 检查尾随空格
                if line.rstrip() != line.rstrip(" \t"):
                    issues.append(
                        {
                            "type": "style",
                            "severity": "low",
                            "message": "行尾有多余空格",
                            "line": i,
                            "suggestion": "删除行尾空格",
                        }
                    )

        return issues

    def _analyze_security(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """分析安全性问题"""
        issues = []

        # 常见安全问题模式
        security_patterns = [
            (
                r"eval\s*\(",
                "使用 eval() 函数",
                "high",
                "避免使用 eval()，考虑更安全的替代方案",
            ),
            (
                r"exec\s*\(",
                "使用 exec() 函数",
                "high",
                "避免使用 exec()，考虑更安全的替代方案",
            ),
            (
                r'password\s*=\s*["\'][^"\']+["\']',
                "硬编码密码",
                "critical",
                "不要在代码中硬编码密码",
            ),
            (
                r'api_key\s*=\s*["\'][^"\']+["\']',
                "硬编码 API 密钥",
                "critical",
                "使用环境变量存储 API 密钥",
            ),
            (
                r"subprocess\.call\s*\(.*shell\s*=\s*True",
                "Shell 注入风险",
                "high",
                "避免使用 shell=True，或验证输入",
            ),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, message, severity, suggestion in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        {
                            "type": "security",
                            "severity": severity,
                            "message": message,
                            "line": i,
                            "suggestion": suggestion,
                        }
                    )

        return issues

    def _analyze_performance(
        self, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """分析性能问题"""
        issues = []

        # 性能问题模式
        performance_patterns = [
            (
                r"for\s+.*\s+in\s+range\s*\(\s*len\s*\(",
                "低效的循环",
                "medium",
                "考虑直接遍历列表而不是索引",
            ),
            (r"\.append\s*\(.*\)\s*$", "循环中的 append", "low", "考虑使用列表推导式"),
            (r"time\.sleep\s*\(", "阻塞式睡眠", "medium", "考虑使用异步睡眠"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, message, severity, suggestion in performance_patterns:
                if re.search(pattern, line):
                    issues.append(
                        {
                            "type": "performance",
                            "severity": severity,
                            "message": message,
                            "line": i,
                            "suggestion": suggestion,
                        }
                    )

        return issues

    def _analyze_maintainability(
        self, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """分析可维护性"""
        issues = []

        # 检查注释密度
        total_lines = len([line for line in lines if line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith("#")])

        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            if comment_ratio < 0.1:
                issues.append(
                    {
                        "type": "maintainability",
                        "severity": "medium",
                        "message": f"注释密度过低 ({comment_ratio:.1%})",
                        "line": 1,
                        "suggestion": "增加代码注释以提高可读性",
                    }
                )

        # 检查魔法数字
        for i, line in enumerate(lines, 1):
            # 查找数字常量（排除常见的 0, 1, -1）
            numbers = re.findall(r"\b(?<![\w.])\d{2,}\b(?![\w.])", line)
            for number in numbers:
                if int(number) not in [0, 1, -1, 100, 1000]:
                    issues.append(
                        {
                            "type": "maintainability",
                            "severity": "low",
                            "message": f"魔法数字: {number}",
                            "line": i,
                            "suggestion": "将魔法数字定义为命名常量",
                        }
                    )

        return issues

    def _filter_by_severity(
        self, issues: List[Dict[str, Any]], threshold: str
    ) -> List[Dict[str, Any]]:
        """按严重程度过滤问题"""
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        threshold_level = severity_levels.get(threshold, 2)

        return [
            issue
            for issue in issues
            if severity_levels.get(issue["severity"], 1) >= threshold_level
        ]

    def _generate_quality_summary(
        self, analysis_results: Dict[str, Any], include_suggestions: bool
    ) -> Dict[str, Any]:
        """生成质量摘要"""
        metrics = analysis_results["metrics"]
        issues = analysis_results["issues"]

        # 按类型分组问题
        issues_by_type: Dict[str, int] = defaultdict(int)
        issues_by_severity: Dict[str, int] = defaultdict(int)

        for issue in issues:
            issues_by_type[issue["type"]] += 1
            issues_by_severity[issue["severity"]] += 1

        # 计算质量评分 (0-100)
        base_score = 100
        penalty_weights = {"low": 1, "medium": 3, "high": 8, "critical": 20}

        total_penalty = sum(
            issues_by_severity[severity] * weight
            for severity, weight in penalty_weights.items()
        )

        quality_score = max(0, base_score - total_penalty)

        # 确定质量等级
        if quality_score >= 90:
            quality_grade = "A"
        elif quality_score >= 80:
            quality_grade = "B"
        elif quality_score >= 70:
            quality_grade = "C"
        elif quality_score >= 60:
            quality_grade = "D"
        else:
            quality_grade = "F"

        summary = {
            "quality_score": quality_score,
            "quality_grade": quality_grade,
            "total_issues": len(issues),
            "issues_by_type": dict(issues_by_type),
            "issues_by_severity": dict(issues_by_severity),
            "top_issues": self._get_top_issues(issues, 5),
        }

        if include_suggestions:
            summary["improvement_suggestions"] = self._generate_improvement_suggestions(
                issues_by_type, issues_by_severity
            )

        return summary

    def _get_top_issues(
        self, issues: List[Dict[str, Any]], limit: int
    ) -> List[Dict[str, Any]]:
        """获取最重要的问题"""
        severity_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        sorted_issues = sorted(
            issues, key=lambda x: severity_priority.get(x["severity"], 0), reverse=True
        )

        return sorted_issues[:limit]

    def _generate_improvement_suggestions(
        self, issues_by_type: Dict[str, int], issues_by_severity: Dict[str, int]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于问题类型的建议
        if issues_by_type.get("security", 0) > 0:
            suggestions.append("优先修复安全性问题，确保代码安全")

        if issues_by_type.get("complexity", 0) > 5:
            suggestions.append("重构复杂代码，提高代码可读性和可维护性")

        if issues_by_type.get("performance", 0) > 3:
            suggestions.append("优化性能问题，提升代码执行效率")

        if issues_by_type.get("style", 0) > 10:
            suggestions.append("统一代码风格，使用代码格式化工具")

        if issues_by_type.get("duplication", 0) > 3:
            suggestions.append("消除重复代码，提取公共函数或模块")

        # 基于严重程度的建议
        if issues_by_severity.get("critical", 0) > 0:
            suggestions.append("立即处理关键问题，这些问题可能导致严重后果")

        if issues_by_severity.get("high", 0) > 5:
            suggestions.append("优先处理高严重程度问题")

        return suggestions

    def _compare_with_history(self, current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """与历史数据比较"""
        try:
            # 获取历史分析结果
            results = self.data_manager.query_data(
                query="code quality analysis",
                data_type="code_quality_analysis",
                n_results=10,
            )

            if not results or not results.get("metadatas"):
                return {"status": "no_history", "message": "没有历史数据可供比较"}

            metadatas = results["metadatas"]
            if isinstance(metadatas, list) and len(metadatas) > 0:
                if isinstance(metadatas[0], list):
                    metadatas = metadatas[0] if metadatas[0] else []

            if not metadatas:
                return {"status": "no_history", "message": "没有历史数据可供比较"}

            # 获取最近的分析结果
            latest_history = max(metadatas, key=lambda x: x.get("timestamp", 0))

            current_score = current_analysis["summary"]["quality_score"]
            historical_score = latest_history.get("quality_score", 0)

            score_change = current_score - historical_score

            return {
                "status": "compared",
                "historical_score": historical_score,
                "current_score": current_score,
                "score_change": score_change,
                "trend": (
                    "improved"
                    if score_change > 0
                    else "declined" if score_change < 0 else "stable"
                ),
                "comparison_date": latest_history.get("timestamp"),
            }

        except Exception as e:
            return {"status": "error", "message": f"比较失败: {str(e)}"}

    def _store_analysis_result(self, analysis_type: str, data: Dict[str, Any]) -> None:
        """存储分析结果"""
        try:
            content = f"Code quality analysis: {analysis_type}"
            metadata = {
                "analysis_type": analysis_type,
                "files_analyzed": data["files_analyzed"],
                "total_issues": data["metrics"]["total_issues"],
                "quality_score": data["summary"]["quality_score"],
                "quality_grade": data["summary"]["quality_grade"],
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="code_quality_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储分析结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class PerformanceMonitor(BaseAnalysisTool):
    """性能监控工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="monitor_performance",
            description="监控和分析系统性能指标",
            parameters={
                "type": "object",
                "properties": {
                    "monitoring_scope": {
                        "type": "string",
                        "enum": ["operations", "tools", "system", "all"],
                        "description": "监控范围",
                        "default": "all",
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "duration_hours": {"type": "integer"},
                        },
                        "description": "时间范围",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "execution_time",
                                "memory_usage",
                                "cpu_usage",
                                "io_operations",
                                "error_rate",
                            ],
                        },
                        "description": "要监控的指标",
                        "default": ["execution_time", "memory_usage", "error_rate"],
                    },
                    "aggregation": {
                        "type": "string",
                        "enum": ["hourly", "daily", "weekly"],
                        "description": "数据聚合方式",
                        "default": "hourly",
                    },
                    "include_trends": {
                        "type": "boolean",
                        "description": "是否包含趋势分析",
                        "default": True,
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行性能监控"""
        start_time = time.time()
        params = request.parameters

        try:
            monitoring_scope = params.get("monitoring_scope", "all")
            time_range = params.get("time_range", {})
            metrics = params.get(
                "metrics", ["execution_time", "memory_usage", "error_rate"]
            )
            aggregation = params.get("aggregation", "hourly")
            include_trends = params.get("include_trends", True)

            # 确定监控时间范围
            start_timestamp, end_timestamp = self._determine_time_range(time_range)

            # 收集性能数据
            performance_data = self._collect_performance_data(
                monitoring_scope, start_timestamp, end_timestamp, metrics
            )

            if not performance_data["success"]:
                return self._create_error_result(
                    "DATA_COLLECTION_FAILED", performance_data["error"]
                )

            # 聚合数据
            aggregated_data = self._aggregate_performance_data(
                performance_data["data"], aggregation
            )

            # 趋势分析
            trends = {}
            if include_trends:
                trends = self._analyze_performance_trends(aggregated_data, metrics)

            # 生成性能报告
            performance_report = {
                "monitoring_scope": monitoring_scope,
                "time_range": {
                    "start": start_timestamp,
                    "end": end_timestamp,
                    "duration_hours": (end_timestamp - start_timestamp) / 3600,
                },
                "metrics": metrics,
                "aggregation": aggregation,
                "raw_data": performance_data["data"],
                "aggregated_data": aggregated_data,
                "trends": trends,
                "summary": self._generate_performance_summary(aggregated_data, metrics),
                "recommendations": self._generate_performance_recommendations(
                    aggregated_data, trends
                ),
                "timestamp": time.time(),
            }

            # 存储监控结果
            self._store_performance_result(performance_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(performance_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(performance_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(performance_report, metadata, resources)

        except Exception as e:
            print(f"性能监控执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _determine_time_range(self, time_range: Dict[str, Any]) -> Tuple[float, float]:
        """确定时间范围"""
        current_time = time.time()

        if "start_time" in time_range and "end_time" in time_range:
            # 解析时间字符串（简化实现）
            start_time = float(time_range["start_time"])
            end_time = float(time_range["end_time"])
        elif "duration_hours" in time_range:
            duration_seconds = time_range["duration_hours"] * 3600
            start_time = current_time - duration_seconds
            end_time = current_time
        else:
            # 默认最近24小时
            start_time = current_time - (24 * 3600)
            end_time = current_time

        return start_time, end_time

    def _collect_performance_data(
        self, scope: str, start_time: float, end_time: float, metrics: List[str]
    ) -> Dict[str, Any]:
        """收集性能数据"""
        try:
            performance_data: List[Dict[str, Any]] = []

            # 获取操作历史数据
            if scope in ["operations", "all"]:
                operations_data = self._collect_operations_performance(
                    start_time, end_time, metrics
                )
                performance_data.extend(operations_data)

            # 获取工具执行数据
            if scope in ["tools", "all"]:
                tools_data = self._collect_tools_performance(
                    start_time, end_time, metrics
                )
                performance_data.extend(tools_data)

            # 获取系统数据
            if scope in ["system", "all"]:
                system_data = self._collect_system_performance(
                    start_time, end_time, metrics
                )
                performance_data.extend(system_data)

            return {"success": True, "data": performance_data}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _collect_operations_performance(
        self, start_time: float, end_time: float, metrics: List[str]
    ) -> List[Dict[str, Any]]:
        """收集操作性能数据"""
        operations = self._get_operation_history()
        performance_data = []

        for op in operations:
            timestamp = op.get("timestamp", 0)
            if start_time <= timestamp <= end_time:
                data_point = {
                    "type": "operation",
                    "timestamp": timestamp,
                    "operation_type": op.get("operation_type", "unknown"),
                    "operation_id": op.get("operation_id", ""),
                }

                # 添加指标数据（模拟数据，实际应该从真实监控中获取）
                if "execution_time" in metrics:
                    data_point["execution_time"] = op.get("execution_time", 0)

                if "memory_usage" in metrics:
                    data_point["memory_usage"] = op.get("memory_used", 0)

                if "cpu_usage" in metrics:
                    data_point["cpu_usage"] = op.get("cpu_time", 0)

                if "io_operations" in metrics:
                    data_point["io_operations"] = op.get("io_operations", 0)

                if "error_rate" in metrics:
                    data_point["error_rate"] = 1 if op.get("error") else 0

                performance_data.append(data_point)

        return performance_data

    def _collect_tools_performance(
        self, start_time: float, end_time: float, metrics: List[str]
    ) -> List[Dict[str, Any]]:
        """收集工具性能数据"""
        # 这里应该从工具执行记录中获取数据
        # 简化实现，返回模拟数据
        return []

    def _collect_system_performance(
        self, start_time: float, end_time: float, metrics: List[str]
    ) -> List[Dict[str, Any]]:
        """收集系统性能数据"""
        # 这里应该从系统监控中获取数据
        # 简化实现，返回模拟数据
        return []

    def _aggregate_performance_data(
        self, data: List[Dict[str, Any]], aggregation: str
    ) -> Dict[str, Any]:
        """聚合性能数据"""
        if not data:
            return {}

        # 确定时间间隔
        interval_seconds = {"hourly": 3600, "daily": 86400, "weekly": 604800}.get(
            aggregation, 3600
        )

        # 按时间间隔分组数据
        grouped_data = defaultdict(list)

        for item in data:
            timestamp = item.get("timestamp", 0)
            interval_key = int(timestamp // interval_seconds) * interval_seconds
            grouped_data[interval_key].append(item)

        # 聚合每个时间间隔的数据
        aggregated: Dict[str, Any] = {}

        for interval_key, items in grouped_data.items():
            interval_stats: Dict[str, Any] = {
                "timestamp": interval_key,
                "count": len(items),
            }

            # 计算各指标的统计值
            for metric in [
                "execution_time",
                "memory_usage",
                "cpu_usage",
                "io_operations",
            ]:
                values = [item.get(metric, 0) for item in items if metric in item]
                if values:
                    interval_stats[metric] = {
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "total": sum(values),
                    }

            # 计算错误率
            error_count = sum(1 for item in items if item.get("error_rate", 0) > 0)
            interval_stats["error_rate"] = error_count / len(items) if items else 0

            aggregated[str(interval_key)] = interval_stats

        return aggregated

    def _analyze_performance_trends(
        self, aggregated_data: Dict[str, Any], metrics: List[str]
    ) -> Dict[str, Any]:
        """分析性能趋势"""
        if not aggregated_data:
            return {}

        trends = {}

        # 按时间排序
        sorted_intervals = sorted(aggregated_data.keys())

        for metric in metrics:
            if metric == "error_rate":
                values = [
                    aggregated_data[interval].get("error_rate", 0)
                    for interval in sorted_intervals
                ]
            else:
                values = [
                    aggregated_data[interval].get(metric, {}).get("avg", 0)
                    for interval in sorted_intervals
                ]

            if len(values) >= 2:
                # 简单的趋势分析
                recent_avg = sum(values[-3:]) / min(3, len(values))
                earlier_avg = (
                    sum(values[:-3]) / max(1, len(values) - 3)
                    if len(values) > 3
                    else values[0]
                )

                change_percent = (
                    (recent_avg - earlier_avg) / max(earlier_avg, 0.001)
                ) * 100

                if change_percent > 10:
                    trend = "increasing"
                elif change_percent < -10:
                    trend = "decreasing"
                else:
                    trend = "stable"

                trends[metric] = {
                    "trend": trend,
                    "change_percent": change_percent,
                    "recent_avg": recent_avg,
                    "earlier_avg": earlier_avg,
                    "values": values,
                }

        return trends

    def _generate_performance_summary(
        self, aggregated_data: Dict[str, Any], metrics: List[str]
    ) -> Dict[str, Any]:
        """生成性能摘要"""
        if not aggregated_data:
            return {"status": "no_data"}

        summary = {
            "total_intervals": len(aggregated_data),
            "total_operations": sum(
                interval.get("count", 0) for interval in aggregated_data.values()
            ),
        }

        # 计算整体统计
        for metric in metrics:
            if metric == "error_rate":
                error_rates = [
                    interval.get("error_rate", 0)
                    for interval in aggregated_data.values()
                ]
                summary[f"{metric}_avg"] = (
                    sum(error_rates) / len(error_rates) if error_rates else 0
                )
            else:
                values = []
                for interval in aggregated_data.values():
                    metric_data = interval.get(metric, {})
                    if isinstance(metric_data, dict) and "avg" in metric_data:
                        values.append(metric_data["avg"])

                if values:
                    summary[f"{metric}_avg"] = sum(values) / len(values)
                    summary[f"{metric}_min"] = min(values)
                    summary[f"{metric}_max"] = max(values)

        return summary

    def _generate_performance_recommendations(
        self, aggregated_data: Dict[str, Any], trends: Dict[str, Any]
    ) -> List[str]:
        """生成性能建议"""
        recommendations = []

        # 基于趋势的建议
        for metric, trend_data in trends.items():
            trend = trend_data.get("trend", "stable")
            change_percent = trend_data.get("change_percent", 0)

            if metric == "execution_time" and trend == "increasing":
                recommendations.append(
                    f"执行时间呈上升趋势 (+{change_percent:.1f}%)，建议优化性能"
                )

            elif metric == "memory_usage" and trend == "increasing":
                recommendations.append(
                    f"内存使用呈上升趋势 (+{change_percent:.1f}%)，检查内存泄漏"
                )

            elif metric == "error_rate" and trend == "increasing":
                recommendations.append(
                    f"错误率呈上升趋势 (+{change_percent:.1f}%)，需要调查错误原因"
                )

        # 基于绝对值的建议
        if aggregated_data:
            avg_error_rate = sum(
                interval.get("error_rate", 0) for interval in aggregated_data.values()
            ) / len(aggregated_data)

            if avg_error_rate > 0.1:  # 10%
                recommendations.append("错误率过高，建议加强错误处理和监控")

        return recommendations

    def _store_performance_result(self, data: Dict[str, Any]) -> None:
        """存储性能监控结果"""
        try:
            content = f"Performance monitoring: {data['monitoring_scope']}"
            metadata = {
                "monitoring_scope": data["monitoring_scope"],
                "duration_hours": data["time_range"]["duration_hours"],
                "total_operations": data["summary"].get("total_operations", 0),
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="performance_monitoring", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储性能监控结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class HistoryTrendAnalyzer(BaseAnalysisTool):
    """历史趋势分析工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_history_trends",
            description="分析历史数据趋势和模式",
            parameters={
                "type": "object",
                "properties": {
                    "analysis_target": {
                        "type": "string",
                        "enum": [
                            "operations",
                            "code_quality",
                            "performance",
                            "errors",
                            "all",
                        ],
                        "description": "分析目标",
                        "default": "all",
                    },
                    "time_period": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "default": 30},
                            "weeks": {"type": "integer"},
                            "months": {"type": "integer"},
                        },
                        "description": "分析时间段",
                    },
                    "trend_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "volume",
                                "quality",
                                "performance",
                                "patterns",
                                "anomalies",
                            ],
                        },
                        "description": "趋势类型",
                        "default": ["volume", "quality", "performance"],
                    },
                    "granularity": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "数据粒度",
                        "default": "daily",
                    },
                    "include_predictions": {
                        "type": "boolean",
                        "description": "是否包含趋势预测",
                        "default": False,
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行历史趋势分析"""
        start_time = time.time()
        params = request.parameters

        try:
            analysis_target = params.get("analysis_target", "all")
            time_period = params.get("time_period", {"days": 30})
            trend_types = params.get(
                "trend_types", ["volume", "quality", "performance"]
            )
            granularity = params.get("granularity", "daily")
            include_predictions = params.get("include_predictions", False)

            # 确定分析时间范围
            end_time = time.time()
            start_timestamp = self._calculate_start_time(end_time, time_period)

            # 收集历史数据
            historical_data = self._collect_historical_data(
                analysis_target, start_timestamp, end_time
            )

            if not historical_data["success"]:
                return self._create_error_result(
                    "DATA_COLLECTION_FAILED", historical_data["error"]
                )

            # 执行趋势分析
            trend_analysis = self._perform_trend_analysis(
                historical_data["data"], trend_types, granularity
            )

            # 预测分析
            predictions = {}
            if include_predictions:
                predictions = self._generate_trend_predictions(trend_analysis)

            # 生成分析报告
            analysis_report = {
                "analysis_target": analysis_target,
                "time_period": {
                    "start": start_timestamp,
                    "end": end_time,
                    "duration_days": (end_time - start_timestamp) / 86400,
                },
                "trend_types": trend_types,
                "granularity": granularity,
                "historical_data": historical_data["data"],
                "trend_analysis": trend_analysis,
                "predictions": predictions,
                "insights": self._generate_trend_insights(trend_analysis),
                "recommendations": self._generate_trend_recommendations(trend_analysis),
                "timestamp": time.time(),
            }

            # 存储分析结果
            self._store_trend_result(analysis_report)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(analysis_report)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(analysis_report)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(analysis_report, metadata, resources)

        except Exception as e:
            print(f"历史趋势分析执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _calculate_start_time(
        self, end_time: float, time_period: Dict[str, Any]
    ) -> float:
        """计算开始时间"""
        if "days" in time_period:
            return end_time - (float(time_period["days"]) * 86400)
        elif "weeks" in time_period:
            return end_time - (float(time_period["weeks"]) * 604800)
        elif "months" in time_period:
            return end_time - (float(time_period["months"]) * 2592000)  # 30天/月
        else:
            return end_time - (30 * 86400)  # 默认30天

    def _collect_historical_data(
        self, target: str, start_time: float, end_time: float
    ) -> Dict[str, Any]:
        """收集历史数据"""
        try:
            historical_data = {}

            if target in ["operations", "all"]:
                operations = self._get_operation_history()
                filtered_ops = [
                    op
                    for op in operations
                    if start_time <= op.get("timestamp", 0) <= end_time
                ]
                historical_data["operations"] = filtered_ops

            if target in ["code_quality", "all"]:
                quality_data = self._get_quality_history(start_time, end_time)
                historical_data["code_quality"] = quality_data

            if target in ["performance", "all"]:
                performance_data = self._get_performance_history(start_time, end_time)
                historical_data["performance"] = performance_data

            if target in ["errors", "all"]:
                error_data = self._get_error_history(start_time, end_time)
                historical_data["errors"] = error_data

            return {"success": True, "data": historical_data}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_quality_history(
        self, start_time: float, end_time: float
    ) -> List[Dict[str, Any]]:
        """获取代码质量历史"""
        try:
            results = self.data_manager.query_data(
                query="code quality analysis",
                data_type="code_quality_analysis",
                n_results=100,
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                return [
                    data
                    for data in metadatas
                    if isinstance(data, dict)
                    and start_time <= data.get("timestamp", 0) <= end_time
                ]
            return []
        except Exception:
            return []

    def _get_performance_history(
        self, start_time: float, end_time: float
    ) -> List[Dict[str, Any]]:
        """获取性能历史"""
        try:
            results = self.data_manager.query_data(
                query="performance monitoring",
                data_type="performance_monitoring",
                n_results=100,
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                return [
                    data
                    for data in metadatas
                    if isinstance(data, dict)
                    and start_time <= data.get("timestamp", 0) <= end_time
                ]
            return []
        except Exception:
            return []

    def _get_error_history(
        self, start_time: float, end_time: float
    ) -> List[Dict[str, Any]]:
        """获取错误历史"""
        operations = self._get_operation_history()
        return [
            op
            for op in operations
            if (
                start_time <= op.get("timestamp", 0) <= end_time
                and op.get("error")
                or op.get("operation_type") == "error"
            )
        ]

    def _perform_trend_analysis(
        self, data: Dict[str, Any], trend_types: List[str], granularity: str
    ) -> Dict[str, Any]:
        """执行趋势分析"""
        analysis_results = {}

        # 音量趋势分析
        if "volume" in trend_types:
            analysis_results["volume"] = self._analyze_volume_trends(data, granularity)

        # 质量趋势分析
        if "quality" in trend_types:
            analysis_results["quality"] = self._analyze_quality_trends(
                data, granularity
            )

        # 性能趋势分析
        if "performance" in trend_types:
            analysis_results["performance"] = self._analyze_performance_trends_history(
                data, granularity
            )

        # 模式分析
        if "patterns" in trend_types:
            analysis_results["patterns"] = self._analyze_patterns(data, granularity)

        # 异常检测
        if "anomalies" in trend_types:
            analysis_results["anomalies"] = self._detect_anomalies(data, granularity)

        return analysis_results

    def _analyze_volume_trends(
        self, data: Dict[str, Any], granularity: str
    ) -> Dict[str, Any]:
        """分析音量趋势"""
        operations = data.get("operations", [])

        if not operations:
            return {"status": "no_data"}

        # 按时间分组
        time_groups = self._group_by_time(operations, granularity)

        # 计算每个时间段的操作数量
        volume_data = {}
        for time_key, ops in time_groups.items():
            volume_data[time_key] = {
                "total_operations": len(ops),
                "operation_types": self._count_operation_types(ops),
            }

        # 计算趋势
        volumes = [
            (
                float(data["total_operations"])
                if isinstance(data["total_operations"], (int, float, str))
                else 0.0
            )
            for data in volume_data.values()
        ]
        trend = self._calculate_trend(volumes)

        return {
            "status": "analyzed",
            "volume_data": volume_data,
            "trend": trend,
            "peak_period": (
                max(
                    volume_data.items(),
                    key=lambda x: (
                        float(x[1]["total_operations"])
                        if isinstance(x[1]["total_operations"], (int, float, str))
                        else 0.0
                    ),
                )[0]
                if volume_data
                else None
            ),
            "low_period": (
                min(
                    volume_data.items(),
                    key=lambda x: (
                        float(x[1]["total_operations"])
                        if isinstance(x[1]["total_operations"], (int, float, str))
                        else 0.0
                    ),
                )[0]
                if volume_data
                else None
            ),
        }

    def _analyze_quality_trends(
        self, data: Dict[str, Any], granularity: str
    ) -> Dict[str, Any]:
        """分析质量趋势"""
        quality_data = data.get("code_quality", [])

        if not quality_data:
            return {"status": "no_data"}

        # 按时间分组
        time_groups = self._group_by_time(quality_data, granularity)

        # 计算每个时间段的质量指标
        quality_trends = {}
        for time_key, items in time_groups.items():
            if items:
                avg_score = sum(item.get("quality_score", 0) for item in items) / len(
                    items
                )
                avg_issues = sum(item.get("total_issues", 0) for item in items) / len(
                    items
                )

                quality_trends[time_key] = {
                    "avg_quality_score": avg_score,
                    "avg_total_issues": avg_issues,
                    "samples": len(items),
                }

        # 计算趋势
        scores = [data["avg_quality_score"] for data in quality_trends.values()]
        score_trend = self._calculate_trend(scores)

        return {
            "status": "analyzed",
            "quality_trends": quality_trends,
            "score_trend": score_trend,
            "best_period": (
                max(quality_trends.items(), key=lambda x: x[1]["avg_quality_score"])[0]
                if quality_trends
                else None
            ),
            "worst_period": (
                min(quality_trends.items(), key=lambda x: x[1]["avg_quality_score"])[0]
                if quality_trends
                else None
            ),
        }

    def _analyze_performance_trends_history(
        self, data: Dict[str, Any], granularity: str
    ) -> Dict[str, Any]:
        """分析性能趋势历史"""
        operations = data.get("operations", [])

        if not operations:
            return {"status": "no_data"}

        # 按时间分组
        time_groups = self._group_by_time(operations, granularity)

        # 计算每个时间段的性能指标
        performance_trends = {}
        for time_key, ops in time_groups.items():
            exec_times = [
                op.get("execution_time", 0) for op in ops if op.get("execution_time")
            ]
            memory_usage = [
                op.get("memory_used", 0) for op in ops if op.get("memory_used")
            ]

            if exec_times or memory_usage:
                performance_trends[time_key] = {
                    "avg_execution_time": (
                        sum(exec_times) / len(exec_times) if exec_times else 0
                    ),
                    "avg_memory_usage": (
                        sum(memory_usage) / len(memory_usage) if memory_usage else 0
                    ),
                    "operations_count": len(ops),
                }

        # 计算趋势
        exec_times = [
            data["avg_execution_time"] for data in performance_trends.values()
        ]
        exec_time_trend = self._calculate_trend(exec_times)

        return {
            "status": "analyzed",
            "performance_trends": performance_trends,
            "execution_time_trend": exec_time_trend,
            "fastest_period": (
                min(
                    performance_trends.items(), key=lambda x: x[1]["avg_execution_time"]
                )[0]
                if performance_trends
                else None
            ),
            "slowest_period": (
                max(
                    performance_trends.items(), key=lambda x: x[1]["avg_execution_time"]
                )[0]
                if performance_trends
                else None
            ),
        }

    def _analyze_patterns(
        self, data: Dict[str, Any], granularity: str
    ) -> Dict[str, Any]:
        """分析模式"""
        operations = data.get("operations", [])

        if not operations:
            return {"status": "no_data"}

        # 分析操作类型模式
        operation_patterns = self._analyze_operation_patterns(operations)

        # 分析时间模式
        time_patterns = self._analyze_time_patterns(operations)

        return {
            "status": "analyzed",
            "operation_patterns": operation_patterns,
            "time_patterns": time_patterns,
        }

    def _detect_anomalies(
        self, data: Dict[str, Any], granularity: str
    ) -> Dict[str, Any]:
        """检测异常"""
        operations = data.get("operations", [])

        if not operations:
            return {"status": "no_data"}

        anomalies = []

        # 检测执行时间异常
        exec_times = [
            op.get("execution_time", 0) for op in operations if op.get("execution_time")
        ]
        if exec_times:
            avg_time = sum(exec_times) / len(exec_times)
            std_dev = (
                sum((t - avg_time) ** 2 for t in exec_times) / len(exec_times)
            ) ** 0.5
            threshold = avg_time + 2 * std_dev

            for op in operations:
                exec_time = op.get("execution_time", 0)
                if exec_time > threshold:
                    anomalies.append(
                        {
                            "type": "execution_time_anomaly",
                            "operation_id": op.get("operation_id"),
                            "timestamp": op.get("timestamp"),
                            "value": exec_time,
                            "threshold": threshold,
                            "severity": (
                                "high" if exec_time > threshold * 1.5 else "medium"
                            ),
                        }
                    )

        return {
            "status": "analyzed",
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
        }

    def _group_by_time(
        self, items: List[Dict[str, Any]], granularity: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按时间分组"""
        interval_seconds = {"daily": 86400, "weekly": 604800, "monthly": 2592000}.get(
            granularity, 86400
        )

        groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

        for item in items:
            timestamp = item.get("timestamp", 0)
            interval_key = int(timestamp // interval_seconds) * interval_seconds
            groups[interval_key].append(item)

        return {str(k): v for k, v in groups.items()}

    def _count_operation_types(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """统计操作类型"""
        type_counts: Dict[str, int] = defaultdict(int)
        for op in operations:
            op_type = op.get("operation_type", "unknown")
            type_counts[op_type] += 1
        return dict(type_counts)

    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """计算趋势"""
        if len(values) < 2:
            return {"trend": "insufficient_data"}

        # 简单的线性趋势计算
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        if slope > 0.1:
            trend = "increasing"
        elif slope < -0.1:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope": slope,
            "start_value": values[0],
            "end_value": values[-1],
            "change_percent": ((values[-1] - values[0]) / max(values[0], 0.001)) * 100,
        }

    def _analyze_operation_patterns(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析操作模式"""
        # 分析最常见的操作序列
        operation_sequences = []
        for i in range(len(operations) - 1):
            current_type = operations[i].get("operation_type", "unknown")
            next_type = operations[i + 1].get("operation_type", "unknown")
            operation_sequences.append((current_type, next_type))

        sequence_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        for seq in operation_sequences:
            sequence_counts[seq] += 1

        # 获取最常见的序列
        common_sequences = sorted(
            sequence_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "common_sequences": [
                {"sequence": f"{seq[0]} -> {seq[1]}", "count": count}
                for seq, count in common_sequences
            ],
            "total_sequences": len(operation_sequences),
        }

    def _analyze_time_patterns(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析时间模式"""
        # 按小时分组操作
        hour_counts: Dict[int, int] = defaultdict(int)
        for op in operations:
            timestamp = op.get("timestamp", 0)
            hour = int((timestamp % 86400) // 3600)  # 一天中的小时
            hour_counts[hour] += 1

        # 找出最活跃的时间段
        peak_hour = (
            max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0
        )

        return {
            "hourly_distribution": dict(hour_counts),
            "peak_hour": peak_hour,
            "total_operations": sum(hour_counts.values()),
        }

    def _generate_trend_predictions(
        self, trend_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成趋势预测"""
        predictions = {}

        # 基于音量趋势预测
        if "volume" in trend_analysis:
            volume_trend = trend_analysis["volume"].get("trend", {})
            if volume_trend.get("trend") == "increasing":
                predictions["volume"] = {
                    "prediction": "操作量将继续增长",
                    "confidence": "medium",
                    "recommendation": "准备扩展资源以应对增长",
                }
            elif volume_trend.get("trend") == "decreasing":
                predictions["volume"] = {
                    "prediction": "操作量可能继续下降",
                    "confidence": "medium",
                    "recommendation": "分析下降原因，优化用户体验",
                }

        # 基于质量趋势预测
        if "quality" in trend_analysis:
            quality_trend = trend_analysis["quality"].get("score_trend", {})
            if quality_trend.get("trend") == "decreasing":
                predictions["quality"] = {
                    "prediction": "代码质量可能继续下降",
                    "confidence": "high",
                    "recommendation": "立即采取措施改善代码质量",
                }

        return predictions

    def _generate_trend_insights(self, trend_analysis: Dict[str, Any]) -> List[str]:
        """生成趋势洞察"""
        insights = []

        # 音量洞察
        if "volume" in trend_analysis:
            volume_data = trend_analysis["volume"]
            if volume_data.get("status") == "analyzed":
                trend = volume_data.get("trend", {})
                if trend.get("trend") == "increasing":
                    insights.append(
                        f"操作量呈上升趋势，增长率为 {trend.get('change_percent', 0):.1f}%"
                    )

        # 质量洞察
        if "quality" in trend_analysis:
            quality_data = trend_analysis["quality"]
            if quality_data.get("status") == "analyzed":
                trend = quality_data.get("score_trend", {})
                if trend.get("trend") == "decreasing":
                    insights.append(
                        f"代码质量呈下降趋势，下降幅度为 {abs(trend.get('change_percent', 0)):.1f}%"
                    )

        # 性能洞察
        if "performance" in trend_analysis:
            perf_data = trend_analysis["performance"]
            if perf_data.get("status") == "analyzed":
                trend = perf_data.get("execution_time_trend", {})
                if trend.get("trend") == "increasing":
                    insights.append("执行时间呈上升趋势，性能可能在下降")

        return insights

    def _generate_trend_recommendations(
        self, trend_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成趋势建议"""
        recommendations = []

        # 基于音量趋势的建议
        if "volume" in trend_analysis:
            volume_data = trend_analysis["volume"]
            if volume_data.get("status") == "analyzed":
                trend = volume_data.get("trend", {})
                if (
                    trend.get("trend") == "increasing"
                    and trend.get("change_percent", 0) > 50
                ):
                    recommendations.append("操作量快速增长，建议优化系统性能和扩展资源")

        # 基于质量趋势的建议
        if "quality" in trend_analysis:
            quality_data = trend_analysis["quality"]
            if quality_data.get("status") == "analyzed":
                trend = quality_data.get("score_trend", {})
                if trend.get("trend") == "decreasing":
                    recommendations.append("代码质量下降，建议加强代码审查和重构")

        # 基于异常检测的建议
        if "anomalies" in trend_analysis:
            anomaly_data = trend_analysis["anomalies"]
            if anomaly_data.get("total_anomalies", 0) > 0:
                recommendations.append("检测到性能异常，建议调查异常原因并优化")

        return recommendations

    def _store_trend_result(self, data: Dict[str, Any]) -> None:
        """存储趋势分析结果"""
        try:
            content = f"History trend analysis: {data['analysis_target']}"
            metadata = {
                "analysis_target": data["analysis_target"],
                "duration_days": data["time_period"]["duration_days"],
                "trend_types": ",".join(data["trend_types"]),
                "insights_count": len(data["insights"]),
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="history_trend_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储趋势分析结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class IntelligentAnalysisTools:
    """智能分析工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有智能分析工具"""
        return [
            CodeQualityAnalyzer(self.config),
            PerformanceMonitor(self.config),
            HistoryTrendAnalyzer(self.config),
        ]
