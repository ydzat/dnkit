"""
Agent 自动化提示系统

为 Agent 提供智能化的开发提示、任务分解和执行建议，
提升 Agent 在复杂开发任务中的表现。
"""

import json
import time
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


class BaseAgentTool(BaseTool):
    """Agent 自动化工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager = UnifiedDataManager(
            self.config.get("chromadb_path", "./mcp_unified_db")
        )
        self.max_suggestions = self.config.get("max_suggestions", 10)
        self.context_window = self.config.get("context_window", 5000)

    def _analyze_project_context(self) -> Dict[str, Any]:
        """分析项目上下文"""
        try:
            # 获取最近的操作历史
            recent_operations = self._get_recent_operations(20)

            # 分析文件类型分布
            file_types: Dict[str, int] = {}
            modified_files = set()

            for op in recent_operations:
                file_path = op.get("file_path", "")
                if file_path:
                    modified_files.add(file_path)
                    ext = self._get_file_extension(file_path)
                    file_types[ext] = file_types.get(ext, 0) + 1

            # 分析操作模式
            operation_types: Dict[str, int] = {}
            for op in recent_operations:
                op_type = op.get("operation_type", "unknown")
                operation_types[op_type] = operation_types.get(op_type, 0) + 1

            return {
                "recent_operations_count": len(recent_operations),
                "modified_files": list(modified_files),
                "file_types": file_types,
                "operation_patterns": operation_types,
                "primary_language": self._detect_primary_language(file_types),
                "activity_level": self._assess_activity_level(recent_operations),
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_recent_operations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的操作"""
        try:
            results = self.data_manager.query_data(
                query="agent operation", data_type="agent_operation", n_results=limit
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        return metadatas[0] if metadatas[0] else []
                    else:
                        return metadatas
            return []
        except Exception as e:
            print(f"获取最近操作失败: {e}")
            return []

    def _get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名"""
        if "." in file_path:
            return file_path.split(".")[-1].lower()
        return "unknown"

    def _detect_primary_language(self, file_types: Dict[str, int]) -> str:
        """检测主要编程语言"""
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "java": "Java",
            "cpp": "C++",
            "c": "C",
            "go": "Go",
            "rs": "Rust",
            "php": "PHP",
            "rb": "Ruby",
            "yaml": "YAML",
            "yml": "YAML",
            "json": "JSON",
            "md": "Markdown",
        }

        if not file_types:
            return "unknown"

        # 找到最常用的文件类型
        most_common = max(file_types.items(), key=lambda x: x[1])
        return language_map.get(most_common[0], most_common[0])

    def _assess_activity_level(self, operations: List[Dict[str, Any]]) -> str:
        """评估活动水平"""
        if not operations:
            return "inactive"

        # 计算最近1小时内的操作数量
        current_time = time.time()
        recent_ops = [
            op
            for op in operations
            if current_time - op.get("timestamp", 0) < 3600  # 1小时
        ]

        if len(recent_ops) > 10:
            return "high"
        elif len(recent_ops) > 5:
            return "medium"
        elif len(recent_ops) > 0:
            return "low"
        else:
            return "inactive"


class TaskDecompositionTool(BaseAgentTool):
    """任务分解工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="decompose_task",
            description="将复杂任务分解为可执行的子任务",
            parameters={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "任务描述",
                    },
                    "context": {
                        "type": "object",
                        "properties": {
                            "project_type": {"type": "string"},
                            "language": {"type": "string"},
                            "complexity": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                            },
                            "deadline": {"type": "string"},
                        },
                        "description": "任务上下文信息",
                    },
                    "decomposition_level": {
                        "type": "string",
                        "enum": ["high", "medium", "detailed"],
                        "description": "分解粒度",
                        "default": "medium",
                    },
                    "include_estimates": {
                        "type": "boolean",
                        "description": "是否包含时间估算",
                        "default": True,
                    },
                    "include_dependencies": {
                        "type": "boolean",
                        "description": "是否分析依赖关系",
                        "default": True,
                    },
                },
                "required": ["task_description"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行任务分解"""
        start_time = time.time()
        params = request.parameters

        try:
            task_description = params["task_description"]
            context = params.get("context", {})
            decomposition_level = params.get("decomposition_level", "medium")
            include_estimates = params.get("include_estimates", True)
            include_dependencies = params.get("include_dependencies", True)

            # 分析项目上下文
            project_context = self._analyze_project_context()

            # 执行任务分解
            decomposition_result = self._decompose_task(
                task_description,
                context,
                decomposition_level,
                include_estimates,
                include_dependencies,
                project_context,
            )

            if not decomposition_result["success"]:
                return self._create_error_result(
                    "DECOMPOSITION_FAILED", decomposition_result["error"]
                )

            # 存储分解结果
            self._store_decomposition_result(task_description, decomposition_result)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(decomposition_result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(decomposition_result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(
                decomposition_result["data"], metadata, resources
            )

        except Exception as e:
            print(f"任务分解执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _decompose_task(
        self,
        task_description: str,
        context: Dict[str, Any],
        level: str,
        include_estimates: bool,
        include_dependencies: bool,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行任务分解逻辑"""
        try:
            # 基于任务描述和上下文生成子任务
            subtasks = self._generate_subtasks(
                task_description, context, level, project_context
            )

            # 添加时间估算
            if include_estimates:
                subtasks = self._add_time_estimates(subtasks, context)

            # 分析依赖关系
            dependencies = []
            if include_dependencies:
                dependencies = self._analyze_dependencies(subtasks)

            # 生成执行建议
            execution_suggestions = self._generate_execution_suggestions(
                subtasks, context, project_context
            )

            return {
                "success": True,
                "data": {
                    "original_task": task_description,
                    "context": context,
                    "project_context": project_context,
                    "subtasks": subtasks,
                    "dependencies": dependencies,
                    "execution_suggestions": execution_suggestions,
                    "decomposition_level": level,
                    "total_subtasks": len(subtasks),
                    "estimated_total_time": sum(
                        task.get("estimated_minutes", 0) for task in subtasks
                    ),
                    "complexity_assessment": self._assess_task_complexity(subtasks),
                    "timestamp": time.time(),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_subtasks(
        self,
        task_description: str,
        context: Dict[str, Any],
        level: str,
        project_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """生成子任务"""
        # 基于任务类型和上下文生成子任务
        language = context.get("language") or project_context.get(
            "primary_language", "unknown"
        )
        project_type = context.get("project_type", "general")

        # 基础任务模板
        base_tasks = []

        # 根据任务描述关键词判断任务类型
        task_lower = task_description.lower()

        if "api" in task_lower or "接口" in task_lower:
            base_tasks = self._generate_api_tasks(task_description, language)
        elif "database" in task_lower or "数据库" in task_lower:
            base_tasks = self._generate_database_tasks(task_description, language)
        elif "ui" in task_lower or "界面" in task_lower or "前端" in task_lower:
            base_tasks = self._generate_ui_tasks(task_description, language)
        elif "test" in task_lower or "测试" in task_lower:
            base_tasks = self._generate_test_tasks(task_description, language)
        elif "deploy" in task_lower or "部署" in task_lower:
            base_tasks = self._generate_deployment_tasks(task_description, language)
        else:
            base_tasks = self._generate_general_tasks(task_description, language)

        # 根据分解级别调整任务粒度
        if level == "detailed":
            base_tasks = self._add_detailed_subtasks(base_tasks)
        elif level == "high":
            base_tasks = self._merge_high_level_tasks(base_tasks)

        return base_tasks

    def _generate_api_tasks(
        self, description: str, language: str
    ) -> List[Dict[str, Any]]:
        """生成API开发任务"""
        return [
            {
                "id": "api_design",
                "title": "API 设计",
                "description": "设计 API 接口规范和数据结构",
                "type": "design",
                "priority": "high",
                "estimated_minutes": 60,
            },
            {
                "id": "api_implementation",
                "title": "API 实现",
                "description": f"使用 {language} 实现 API 核心逻辑",
                "type": "implementation",
                "priority": "high",
                "estimated_minutes": 120,
            },
            {
                "id": "api_validation",
                "title": "输入验证",
                "description": "实现请求参数验证和错误处理",
                "type": "implementation",
                "priority": "medium",
                "estimated_minutes": 45,
            },
            {
                "id": "api_testing",
                "title": "API 测试",
                "description": "编写和执行 API 测试用例",
                "type": "testing",
                "priority": "high",
                "estimated_minutes": 90,
            },
            {
                "id": "api_documentation",
                "title": "API 文档",
                "description": "编写 API 使用文档和示例",
                "type": "documentation",
                "priority": "medium",
                "estimated_minutes": 30,
            },
        ]

    def _generate_database_tasks(
        self, description: str, language: str
    ) -> List[Dict[str, Any]]:
        """生成数据库相关任务"""
        return [
            {
                "id": "db_design",
                "title": "数据库设计",
                "description": "设计数据表结构和关系",
                "type": "design",
                "priority": "high",
                "estimated_minutes": 90,
            },
            {
                "id": "db_migration",
                "title": "数据库迁移",
                "description": "创建数据库迁移脚本",
                "type": "implementation",
                "priority": "high",
                "estimated_minutes": 60,
            },
            {
                "id": "db_models",
                "title": "数据模型",
                "description": f"使用 {language} 实现数据模型",
                "type": "implementation",
                "priority": "high",
                "estimated_minutes": 75,
            },
            {
                "id": "db_queries",
                "title": "查询优化",
                "description": "实现和优化数据库查询",
                "type": "implementation",
                "priority": "medium",
                "estimated_minutes": 45,
            },
            {
                "id": "db_testing",
                "title": "数据库测试",
                "description": "测试数据操作和性能",
                "type": "testing",
                "priority": "medium",
                "estimated_minutes": 60,
            },
        ]

    def _generate_ui_tasks(
        self, description: str, language: str
    ) -> List[Dict[str, Any]]:
        """生成UI开发任务"""
        return [
            {
                "id": "ui_design",
                "title": "界面设计",
                "description": "设计用户界面布局和交互",
                "type": "design",
                "priority": "high",
                "estimated_minutes": 120,
            },
            {
                "id": "ui_components",
                "title": "组件开发",
                "description": f"使用 {language} 开发UI组件",
                "type": "implementation",
                "priority": "high",
                "estimated_minutes": 150,
            },
            {
                "id": "ui_styling",
                "title": "样式实现",
                "description": "实现CSS样式和响应式设计",
                "type": "implementation",
                "priority": "medium",
                "estimated_minutes": 90,
            },
            {
                "id": "ui_interaction",
                "title": "交互逻辑",
                "description": "实现用户交互和事件处理",
                "type": "implementation",
                "priority": "high",
                "estimated_minutes": 75,
            },
            {
                "id": "ui_testing",
                "title": "界面测试",
                "description": "测试界面功能和兼容性",
                "type": "testing",
                "priority": "medium",
                "estimated_minutes": 60,
            },
        ]

    def _generate_test_tasks(
        self, description: str, language: str
    ) -> List[Dict[str, Any]]:
        """生成测试任务"""
        return [
            {
                "id": "test_planning",
                "title": "测试规划",
                "description": "制定测试策略和计划",
                "type": "planning",
                "priority": "high",
                "estimated_minutes": 45,
            },
            {
                "id": "unit_tests",
                "title": "单元测试",
                "description": f"使用 {language} 编写单元测试",
                "type": "testing",
                "priority": "high",
                "estimated_minutes": 120,
            },
            {
                "id": "integration_tests",
                "title": "集成测试",
                "description": "编写和执行集成测试",
                "type": "testing",
                "priority": "medium",
                "estimated_minutes": 90,
            },
            {
                "id": "test_automation",
                "title": "测试自动化",
                "description": "设置自动化测试流程",
                "type": "automation",
                "priority": "medium",
                "estimated_minutes": 75,
            },
        ]

    def _generate_deployment_tasks(
        self, description: str, language: str
    ) -> List[Dict[str, Any]]:
        """生成部署任务"""
        return [
            {
                "id": "deploy_config",
                "title": "部署配置",
                "description": "配置部署环境和参数",
                "type": "configuration",
                "priority": "high",
                "estimated_minutes": 60,
            },
            {
                "id": "deploy_script",
                "title": "部署脚本",
                "description": "编写自动化部署脚本",
                "type": "automation",
                "priority": "high",
                "estimated_minutes": 90,
            },
            {
                "id": "deploy_testing",
                "title": "部署测试",
                "description": "测试部署流程和环境",
                "type": "testing",
                "priority": "high",
                "estimated_minutes": 45,
            },
            {
                "id": "deploy_monitoring",
                "title": "监控设置",
                "description": "设置部署后监控和日志",
                "type": "monitoring",
                "priority": "medium",
                "estimated_minutes": 30,
            },
        ]

    def _generate_general_tasks(
        self, description: str, language: str
    ) -> List[Dict[str, Any]]:
        """生成通用任务"""
        return [
            {
                "id": "analysis",
                "title": "需求分析",
                "description": "分析任务需求和技术方案",
                "type": "analysis",
                "priority": "high",
                "estimated_minutes": 60,
            },
            {
                "id": "design",
                "title": "方案设计",
                "description": "设计技术实现方案",
                "type": "design",
                "priority": "high",
                "estimated_minutes": 90,
            },
            {
                "id": "implementation",
                "title": "功能实现",
                "description": f"使用 {language} 实现核心功能",
                "type": "implementation",
                "priority": "high",
                "estimated_minutes": 120,
            },
            {
                "id": "testing",
                "title": "功能测试",
                "description": "测试实现的功能",
                "type": "testing",
                "priority": "medium",
                "estimated_minutes": 60,
            },
            {
                "id": "optimization",
                "title": "性能优化",
                "description": "优化代码性能和质量",
                "type": "optimization",
                "priority": "low",
                "estimated_minutes": 45,
            },
        ]

    def _add_detailed_subtasks(
        self, tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """添加详细子任务"""
        detailed_tasks = []
        for task in tasks:
            detailed_tasks.append(task)
            # 为每个主任务添加详细子步骤
            if task["type"] == "implementation":
                detailed_tasks.extend(
                    [
                        {
                            "id": f"{task['id']}_setup",
                            "title": f"{task['title']} - 环境准备",
                            "description": "准备开发环境和依赖",
                            "type": "setup",
                            "priority": "medium",
                            "estimated_minutes": 15,
                            "parent_id": task["id"],
                        },
                        {
                            "id": f"{task['id']}_code_review",
                            "title": f"{task['title']} - 代码审查",
                            "description": "审查和优化实现代码",
                            "type": "review",
                            "priority": "medium",
                            "estimated_minutes": 20,
                            "parent_id": task["id"],
                        },
                    ]
                )
        return detailed_tasks

    def _merge_high_level_tasks(
        self, tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并为高级任务"""
        # 按类型分组任务
        task_groups: Dict[str, List[Dict[str, Any]]] = {}
        for task in tasks:
            task_type = task["type"]
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(task)

        # 合并同类型任务
        merged_tasks = []
        for task_type, group_tasks in task_groups.items():
            if len(group_tasks) > 1:
                # 合并多个同类型任务
                total_time = sum(
                    task.get("estimated_minutes", 0) for task in group_tasks
                )
                merged_task = {
                    "id": f"merged_{task_type}",
                    "title": f"{task_type.title()} 阶段",
                    "description": f"完成所有 {task_type} 相关任务",
                    "type": task_type,
                    "priority": "high",
                    "estimated_minutes": total_time,
                    "subtasks": [task["title"] for task in group_tasks],
                }
                merged_tasks.append(merged_task)
            else:
                merged_tasks.extend(group_tasks)

        return merged_tasks

    def _add_time_estimates(
        self, tasks: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """添加时间估算"""
        complexity_multiplier = {"low": 0.8, "medium": 1.0, "high": 1.5}

        multiplier = complexity_multiplier.get(context.get("complexity", "medium"), 1.0)

        for task in tasks:
            if "estimated_minutes" in task:
                task["estimated_minutes"] = int(task["estimated_minutes"] * multiplier)
                task["estimated_hours"] = round(task["estimated_minutes"] / 60, 1)

        return tasks

    def _analyze_dependencies(
        self, tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """分析任务依赖关系"""
        dependencies = []

        # 基于任务类型定义常见依赖关系
        dependency_rules = {
            "design": [],  # 设计任务通常没有前置依赖
            "analysis": [],  # 分析任务通常是起始任务
            "planning": [],  # 规划任务通常是起始任务
            "setup": ["analysis", "planning"],
            "implementation": ["design", "setup"],
            "testing": ["implementation"],
            "review": ["implementation"],
            "optimization": ["testing"],
            "documentation": ["implementation", "testing"],
            "deployment": ["testing", "optimization"],
            "monitoring": ["deployment"],
        }

        # 为每个任务查找依赖
        for task in tasks:
            task_type = task["type"]
            required_types = dependency_rules.get(task_type, [])

            for required_type in required_types:
                # 查找对应类型的任务
                for dep_task in tasks:
                    if (
                        dep_task["type"] == required_type
                        and dep_task["id"] != task["id"]
                    ):
                        dependencies.append(
                            {
                                "task_id": task["id"],
                                "depends_on": dep_task["id"],
                                "dependency_type": "sequential",
                            }
                        )
                        break

        return dependencies

    def _generate_execution_suggestions(
        self,
        tasks: List[Dict[str, Any]],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:
        """生成执行建议"""
        suggestions = []

        # 基于项目上下文的建议
        primary_language = project_context.get("primary_language", "unknown")
        activity_level = project_context.get("activity_level", "low")

        if primary_language != "unknown":
            suggestions.append(f"建议使用 {primary_language} 作为主要开发语言")

        if activity_level == "high":
            suggestions.append("检测到高频开发活动，建议创建检查点以便回滚")

        # 基于任务类型的建议
        task_types = set(task["type"] for task in tasks)

        if "testing" in task_types:
            suggestions.append("建议在实现完成后立即执行测试任务")

        if "implementation" in task_types and "design" in task_types:
            suggestions.append("建议先完成设计任务，再开始实现")

        if len(tasks) > 5:
            suggestions.append("任务较多，建议分批执行并定期检查进度")

        # 基于复杂度的建议
        complexity = context.get("complexity", "medium")
        if complexity == "high":
            suggestions.append("高复杂度任务，建议增加代码审查和测试时间")

        # 基于截止时间的建议
        if "deadline" in context:
            suggestions.append("注意截止时间，建议优先执行高优先级任务")

        return suggestions

    def _assess_task_complexity(self, tasks: List[Dict[str, Any]]) -> str:
        """评估任务复杂度"""
        total_time = sum(task.get("estimated_minutes", 0) for task in tasks)
        task_count = len(tasks)

        # 基于时间和任务数量评估复杂度
        if total_time > 480 or task_count > 8:  # 8小时或8个以上任务
            return "high"
        elif total_time > 240 or task_count > 5:  # 4小时或5个以上任务
            return "medium"
        else:
            return "low"

    def _store_decomposition_result(
        self, task_description: str, result: Dict[str, Any]
    ) -> None:
        """存储分解结果"""
        try:
            content = f"Task decomposition: {task_description}"
            metadata = {
                "task_description": task_description,
                "subtasks_count": result["data"]["total_subtasks"],
                "estimated_time": result["data"]["estimated_total_time"],
                "complexity": result["data"]["complexity_assessment"],
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="task_decomposition", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储分解结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ExecutionGuidanceTool(BaseAgentTool):
    """执行指导工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_execution_guidance",
            description="获取任务执行指导和建议",
            parameters={
                "type": "object",
                "properties": {
                    "current_task": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "type": {"type": "string"},
                        },
                        "description": "当前任务信息",
                        "required": ["title", "type"],
                    },
                    "context": {
                        "type": "object",
                        "properties": {
                            "completed_tasks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "已完成的任务ID列表",
                            },
                            "available_tools": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "可用工具列表",
                            },
                            "current_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "当前项目文件列表",
                            },
                            "errors_encountered": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "遇到的错误列表",
                            },
                        },
                        "description": "执行上下文",
                    },
                    "guidance_type": {
                        "type": "string",
                        "enum": [
                            "step_by_step",
                            "best_practices",
                            "troubleshooting",
                            "optimization",
                        ],
                        "description": "指导类型",
                        "default": "step_by_step",
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["brief", "detailed", "comprehensive"],
                        "description": "详细程度",
                        "default": "detailed",
                    },
                },
                "required": ["current_task"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行指导生成"""
        start_time = time.time()
        params = request.parameters

        try:
            current_task = params["current_task"]
            context = params.get("context", {})
            guidance_type = params.get("guidance_type", "step_by_step")
            detail_level = params.get("detail_level", "detailed")

            # 分析项目上下文
            project_context = self._analyze_project_context()

            # 生成执行指导
            guidance_result = self._generate_execution_guidance(
                current_task, context, guidance_type, detail_level, project_context
            )

            if not guidance_result["success"]:
                return self._create_error_result(
                    "GUIDANCE_GENERATION_FAILED", guidance_result["error"]
                )

            # 存储指导结果
            self._store_guidance_result(current_task, guidance_result)

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(guidance_result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(guidance_result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(
                guidance_result["data"], metadata, resources
            )

        except Exception as e:
            print(f"执行指导生成异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _generate_execution_guidance(
        self,
        current_task: Dict[str, Any],
        context: Dict[str, Any],
        guidance_type: str,
        detail_level: str,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成执行指导"""
        try:
            task_type = current_task.get("type", "general")
            task_title = current_task.get("title", "未知任务")

            # 根据指导类型生成不同的指导内容
            if guidance_type == "step_by_step":
                guidance_content = self._generate_step_by_step_guidance(
                    current_task, context, detail_level, project_context
                )
            elif guidance_type == "best_practices":
                guidance_content = self._generate_best_practices_guidance(
                    current_task, context, project_context
                )
            elif guidance_type == "troubleshooting":
                guidance_content = self._generate_troubleshooting_guidance(
                    current_task, context, project_context
                )
            elif guidance_type == "optimization":
                guidance_content = self._generate_optimization_guidance(
                    current_task, context, project_context
                )
            else:
                guidance_content = self._generate_general_guidance(
                    current_task, context, project_context
                )

            return {
                "success": True,
                "data": {
                    "task_info": current_task,
                    "guidance_type": guidance_type,
                    "detail_level": detail_level,
                    "guidance_content": guidance_content,
                    "project_context": project_context,
                    "recommendations": self._generate_recommendations(
                        current_task, context, project_context
                    ),
                    "potential_issues": self._identify_potential_issues(
                        current_task, context, project_context
                    ),
                    "success_criteria": self._define_success_criteria(current_task),
                    "timestamp": time.time(),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_step_by_step_guidance(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        detail_level: str,
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成分步指导"""
        task_type = task.get("type", "general")
        language = project_context.get("primary_language", "Python")

        # 基于任务类型生成步骤
        if task_type == "implementation":
            steps = self._get_implementation_steps(task, language, detail_level)
        elif task_type == "testing":
            steps = self._get_testing_steps(task, language, detail_level)
        elif task_type == "design":
            steps = self._get_design_steps(task, detail_level)
        elif task_type == "deployment":
            steps = self._get_deployment_steps(task, detail_level)
        else:
            steps = self._get_general_steps(task, detail_level)

        return {
            "type": "step_by_step",
            "steps": steps,
            "estimated_time": sum(step.get("estimated_minutes", 0) for step in steps),
            "prerequisites": self._get_task_prerequisites(task, context),
            "tools_needed": self._get_required_tools(task, context),
        }

    def _get_implementation_steps(
        self, task: Dict[str, Any], language: str, detail_level: str
    ) -> List[Dict[str, Any]]:
        """获取实现任务的步骤"""
        base_steps = [
            {
                "step": 1,
                "title": "分析需求",
                "description": "仔细分析任务需求和技术要求",
                "estimated_minutes": 15,
                "actions": ["阅读任务描述", "确定输入输出要求", "识别技术约束"],
            },
            {
                "step": 2,
                "title": "设计方案",
                "description": "设计技术实现方案",
                "estimated_minutes": 30,
                "actions": ["选择合适的算法或架构", "设计数据结构", "规划代码结构"],
            },
            {
                "step": 3,
                "title": "编写代码",
                "description": f"使用 {language} 实现核心功能",
                "estimated_minutes": 60,
                "actions": ["创建必要的文件", "实现核心逻辑", "添加错误处理"],
            },
            {
                "step": 4,
                "title": "测试验证",
                "description": "测试实现的功能",
                "estimated_minutes": 30,
                "actions": ["编写测试用例", "执行功能测试", "修复发现的问题"],
            },
        ]

        if detail_level == "comprehensive":
            # 添加更详细的步骤
            base_steps.extend(
                [
                    {
                        "step": 5,
                        "title": "代码审查",
                        "description": "审查代码质量和规范",
                        "estimated_minutes": 20,
                        "actions": ["检查代码风格", "优化性能", "添加注释和文档"],
                    },
                    {
                        "step": 6,
                        "title": "集成测试",
                        "description": "测试与其他组件的集成",
                        "estimated_minutes": 25,
                        "actions": ["测试接口兼容性", "验证数据流", "检查边界条件"],
                    },
                ]
            )

        return base_steps

    def _get_testing_steps(
        self, task: Dict[str, Any], language: str, detail_level: str
    ) -> List[Dict[str, Any]]:
        """获取测试任务的步骤"""
        return [
            {
                "step": 1,
                "title": "测试规划",
                "description": "制定测试策略和计划",
                "estimated_minutes": 20,
                "actions": ["确定测试范围", "选择测试框架", "设计测试用例"],
            },
            {
                "step": 2,
                "title": "环境准备",
                "description": "准备测试环境",
                "estimated_minutes": 15,
                "actions": ["安装测试依赖", "配置测试数据", "设置测试环境"],
            },
            {
                "step": 3,
                "title": "编写测试",
                "description": f"使用 {language} 编写测试代码",
                "estimated_minutes": 45,
                "actions": ["编写单元测试", "编写集成测试", "添加断言和验证"],
            },
            {
                "step": 4,
                "title": "执行测试",
                "description": "运行测试并分析结果",
                "estimated_minutes": 20,
                "actions": ["运行测试套件", "分析测试结果", "修复失败的测试"],
            },
        ]

    def _get_design_steps(
        self, task: Dict[str, Any], detail_level: str
    ) -> List[Dict[str, Any]]:
        """获取设计任务的步骤"""
        return [
            {
                "step": 1,
                "title": "需求分析",
                "description": "深入分析设计需求",
                "estimated_minutes": 30,
                "actions": ["收集用户需求", "分析技术约束", "确定设计目标"],
            },
            {
                "step": 2,
                "title": "方案设计",
                "description": "设计技术方案",
                "estimated_minutes": 45,
                "actions": ["设计系统架构", "选择技术栈", "设计接口规范"],
            },
            {
                "step": 3,
                "title": "原型制作",
                "description": "创建设计原型",
                "estimated_minutes": 60,
                "actions": ["创建概念原型", "验证设计可行性", "收集反馈意见"],
            },
            {
                "step": 4,
                "title": "文档编写",
                "description": "编写设计文档",
                "estimated_minutes": 30,
                "actions": ["编写技术规范", "创建设计图表", "记录设计决策"],
            },
        ]

    def _get_deployment_steps(
        self, task: Dict[str, Any], detail_level: str
    ) -> List[Dict[str, Any]]:
        """获取部署任务的步骤"""
        return [
            {
                "step": 1,
                "title": "环境准备",
                "description": "准备部署环境",
                "estimated_minutes": 30,
                "actions": ["配置服务器环境", "安装必要依赖", "设置环境变量"],
            },
            {
                "step": 2,
                "title": "构建应用",
                "description": "构建应用程序",
                "estimated_minutes": 20,
                "actions": ["编译源代码", "打包应用文件", "生成部署包"],
            },
            {
                "step": 3,
                "title": "部署应用",
                "description": "部署到目标环境",
                "estimated_minutes": 25,
                "actions": ["上传部署包", "执行部署脚本", "启动应用服务"],
            },
            {
                "step": 4,
                "title": "验证部署",
                "description": "验证部署结果",
                "estimated_minutes": 15,
                "actions": ["测试应用功能", "检查服务状态", "验证性能指标"],
            },
        ]

    def _get_general_steps(
        self, task: Dict[str, Any], detail_level: str
    ) -> List[Dict[str, Any]]:
        """获取通用任务的步骤"""
        return [
            {
                "step": 1,
                "title": "任务分析",
                "description": "分析任务要求和目标",
                "estimated_minutes": 20,
                "actions": ["理解任务目标", "识别关键要求", "评估复杂度"],
            },
            {
                "step": 2,
                "title": "方案制定",
                "description": "制定执行方案",
                "estimated_minutes": 30,
                "actions": ["选择实现方法", "规划执行步骤", "准备必要资源"],
            },
            {
                "step": 3,
                "title": "执行实施",
                "description": "执行具体任务",
                "estimated_minutes": 60,
                "actions": ["按计划执行", "监控执行进度", "处理遇到的问题"],
            },
            {
                "step": 4,
                "title": "验证完成",
                "description": "验证任务完成情况",
                "estimated_minutes": 20,
                "actions": ["检查执行结果", "验证质量标准", "记录完成状态"],
            },
        ]

    def _generate_best_practices_guidance(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成最佳实践指导"""
        task_type = task.get("type", "general")
        language = project_context.get("primary_language", "Python")

        practices = {
            "implementation": [
                "遵循代码规范和风格指南",
                "编写清晰的注释和文档",
                "使用有意义的变量和函数名",
                "实现适当的错误处理",
                "编写可测试的代码",
                f"遵循 {language} 的最佳实践",
            ],
            "testing": [
                "编写全面的测试用例",
                "使用测试驱动开发(TDD)",
                "保持测试的独立性",
                "使用模拟和存根技术",
                "定期运行测试套件",
            ],
            "design": [
                "遵循设计原则(SOLID等)",
                "考虑可扩展性和维护性",
                "使用合适的设计模式",
                "进行充分的需求分析",
                "创建清晰的文档",
            ],
        }

        return {
            "type": "best_practices",
            "practices": practices.get(task_type, practices["implementation"]),
            "language_specific": self._get_language_specific_practices(language),
            "common_pitfalls": self._get_common_pitfalls(task_type),
            "quality_checklist": self._get_quality_checklist(task_type),
        }

    def _generate_troubleshooting_guidance(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成故障排除指导"""
        errors = context.get("errors_encountered", [])

        troubleshooting_steps = [
            {
                "step": "识别问题",
                "description": "准确识别和描述问题",
                "actions": ["收集错误信息", "重现问题场景", "分析错误日志"],
            },
            {
                "step": "分析原因",
                "description": "分析问题的根本原因",
                "actions": ["检查代码逻辑", "验证输入数据", "检查环境配置"],
            },
            {
                "step": "制定方案",
                "description": "制定解决方案",
                "actions": ["评估多种解决方案", "选择最佳方案", "制定实施计划"],
            },
            {
                "step": "实施修复",
                "description": "实施解决方案",
                "actions": ["修改相关代码", "测试修复效果", "验证问题解决"],
            },
        ]

        return {
            "type": "troubleshooting",
            "troubleshooting_steps": troubleshooting_steps,
            "common_issues": self._get_common_issues(task.get("type", "general")),
            "debugging_tips": self._get_debugging_tips(
                project_context.get("primary_language", "Python")
            ),
            "error_analysis": self._analyze_errors(errors) if errors else None,
        }

    def _generate_optimization_guidance(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成优化指导"""
        return {
            "type": "optimization",
            "performance_tips": [
                "分析性能瓶颈",
                "优化算法复杂度",
                "减少不必要的计算",
                "使用缓存机制",
                "优化数据结构选择",
            ],
            "code_quality_tips": [
                "重构重复代码",
                "简化复杂逻辑",
                "提高代码可读性",
                "减少代码耦合",
                "增强代码复用性",
            ],
            "resource_optimization": [
                "优化内存使用",
                "减少IO操作",
                "优化网络请求",
                "使用异步处理",
                "实现资源池化",
            ],
            "monitoring_suggestions": [
                "添加性能监控",
                "设置关键指标",
                "实现日志记录",
                "建立告警机制",
            ],
        }

    def _generate_general_guidance(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成通用指导"""
        return {
            "type": "general",
            "general_tips": [
                "仔细阅读任务要求",
                "制定详细的执行计划",
                "定期检查进度",
                "及时处理遇到的问题",
                "保持代码和文档的同步",
            ],
            "workflow_suggestions": [
                "使用版本控制系统",
                "定期创建检查点",
                "进行代码审查",
                "编写测试用例",
                "记录重要决策",
            ],
        }

    def _get_task_prerequisites(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> List[str]:
        """获取任务前置条件"""
        task_type = task.get("type", "general")
        completed_tasks = context.get("completed_tasks", [])

        prerequisites = {
            "implementation": ["需求分析完成", "设计方案确定"],
            "testing": ["功能实现完成", "测试环境准备"],
            "deployment": ["代码测试通过", "部署环境配置"],
            "design": ["需求收集完成", "技术调研完成"],
        }

        return prerequisites.get(task_type, ["任务依赖分析完成"])

    def _get_required_tools(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> List[str]:
        """获取所需工具"""
        task_type = task.get("type", "general")
        available_tools = context.get("available_tools", [])

        required_tools = {
            "implementation": ["代码编辑器", "调试工具", "版本控制"],
            "testing": ["测试框架", "代码覆盖率工具", "性能分析工具"],
            "deployment": ["构建工具", "部署脚本", "监控工具"],
            "design": ["设计工具", "原型工具", "文档工具"],
        }

        return required_tools.get(task_type, ["基础开发工具"])

    def _get_language_specific_practices(self, language: str) -> List[str]:
        """获取语言特定的最佳实践"""
        practices = {
            "Python": [
                "遵循PEP 8代码风格",
                "使用虚拟环境",
                "编写docstring文档",
                "使用类型提示",
                "遵循Pythonic编程风格",
            ],
            "JavaScript": [
                "使用严格模式",
                "避免全局变量",
                "使用现代ES6+语法",
                "进行代码压缩和优化",
                "使用模块化开发",
            ],
            "Java": [
                "遵循Java命名约定",
                "使用适当的访问修饰符",
                "实现equals和hashCode",
                "使用泛型提高类型安全",
                "遵循SOLID原则",
            ],
        }

        return practices.get(language, ["遵循语言最佳实践"])

    def _get_common_pitfalls(self, task_type: str) -> List[str]:
        """获取常见陷阱"""
        pitfalls = {
            "implementation": [
                "忽略边界条件处理",
                "缺乏适当的错误处理",
                "过度优化或过早优化",
                "忽略代码可读性",
                "缺乏单元测试",
            ],
            "testing": [
                "测试覆盖率不足",
                "测试用例相互依赖",
                "忽略边界条件测试",
                "测试数据不充分",
                "缺乏集成测试",
            ],
            "design": [
                "过度设计或设计不足",
                "忽略非功能性需求",
                "缺乏可扩展性考虑",
                "设计文档不完整",
                "忽略用户体验",
            ],
        }

        return pitfalls.get(task_type, ["缺乏充分的规划"])

    def _get_quality_checklist(self, task_type: str) -> List[str]:
        """获取质量检查清单"""
        checklists = {
            "implementation": [
                "代码符合规范要求",
                "功能实现完整正确",
                "错误处理适当",
                "代码注释清晰",
                "通过单元测试",
            ],
            "testing": [
                "测试用例覆盖全面",
                "测试结果准确可靠",
                "测试环境配置正确",
                "测试文档完整",
                "自动化测试可执行",
            ],
            "design": [
                "设计满足需求",
                "架构合理可行",
                "接口定义清晰",
                "文档完整准确",
                "设计可扩展维护",
            ],
        }

        return checklists.get(task_type, ["任务完成度检查"])

    def _get_common_issues(self, task_type: str) -> List[Dict[str, str]]:
        """获取常见问题"""
        issues = {
            "implementation": [
                {"issue": "编译错误", "solution": "检查语法和依赖"},
                {"issue": "逻辑错误", "solution": "使用调试工具逐步排查"},
                {"issue": "性能问题", "solution": "分析算法复杂度和资源使用"},
            ],
            "testing": [
                {"issue": "测试失败", "solution": "检查测试用例和实现逻辑"},
                {"issue": "环境问题", "solution": "验证测试环境配置"},
                {"issue": "数据问题", "solution": "检查测试数据的有效性"},
            ],
        }

        return issues.get(
            task_type, [{"issue": "通用问题", "solution": "系统性分析和解决"}]
        )

    def _get_debugging_tips(self, language: str) -> List[str]:
        """获取调试技巧"""
        tips = {
            "Python": [
                "使用pdb调试器",
                "添加print语句调试",
                "使用IDE断点功能",
                "检查异常堆栈信息",
                "使用日志记录",
            ],
            "JavaScript": [
                "使用console.log调试",
                "使用浏览器开发者工具",
                "设置断点调试",
                "检查网络请求",
                "使用错误监控工具",
            ],
        }

        return tips.get(language, ["使用调试工具", "添加日志输出", "逐步排查问题"])

    def _analyze_errors(self, errors: List[str]) -> Dict[str, Any]:
        """分析错误信息"""
        if not errors:
            return {}

        error_categories = {"syntax": 0, "runtime": 0, "logic": 0, "environment": 0}

        # 简单的错误分类
        for error in errors:
            error_lower = error.lower()
            if any(
                keyword in error_lower
                for keyword in ["syntax", "invalid", "unexpected"]
            ):
                error_categories["syntax"] += 1
            elif any(
                keyword in error_lower for keyword in ["runtime", "exception", "error"]
            ):
                error_categories["runtime"] += 1
            elif any(
                keyword in error_lower for keyword in ["config", "environment", "path"]
            ):
                error_categories["environment"] += 1
            else:
                error_categories["logic"] += 1

        return {
            "total_errors": len(errors),
            "error_categories": error_categories,
            "most_common_category": max(error_categories.items(), key=lambda x: x[1])[
                0
            ],
            "suggestions": self._get_error_suggestions(error_categories),
        }

    def _get_error_suggestions(self, error_categories: Dict[str, int]) -> List[str]:
        """根据错误类型获取建议"""
        suggestions = []

        if error_categories["syntax"] > 0:
            suggestions.append("检查代码语法和拼写错误")

        if error_categories["runtime"] > 0:
            suggestions.append("添加异常处理和输入验证")

        if error_categories["environment"] > 0:
            suggestions.append("检查环境配置和依赖安装")

        if error_categories["logic"] > 0:
            suggestions.append("仔细检查业务逻辑和算法实现")

        return suggestions

    def _generate_recommendations(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:
        """生成推荐建议"""
        recommendations = []

        # 基于任务类型的推荐
        task_type = task.get("type", "general")
        if task_type == "implementation":
            recommendations.extend(
                [
                    "先编写测试用例，再实现功能",
                    "使用版本控制跟踪代码变更",
                    "定期进行代码审查",
                ]
            )

        # 基于项目上下文的推荐
        activity_level = project_context.get("activity_level", "low")
        if activity_level == "high":
            recommendations.append("建议创建检查点以便快速回滚")

        # 基于错误历史的推荐
        errors = context.get("errors_encountered", [])
        if errors:
            recommendations.append("建议先解决已知错误再继续开发")

        return recommendations

    def _identify_potential_issues(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """识别潜在问题"""
        issues = []

        # 基于任务复杂度识别问题
        task_description = task.get("description", "")
        if len(task_description) > 200:
            issues.append(
                {
                    "type": "complexity",
                    "description": "任务描述较长，可能存在复杂度过高的问题",
                    "suggestion": "考虑将任务分解为更小的子任务",
                }
            )

        # 基于项目状态识别问题
        modified_files = project_context.get("modified_files", [])
        if len(modified_files) > 10:
            issues.append(
                {
                    "type": "scope",
                    "description": "涉及文件较多，可能影响范围过大",
                    "suggestion": "建议创建备份或检查点",
                }
            )

        return issues

    def _define_success_criteria(self, task: Dict[str, Any]) -> List[str]:
        """定义成功标准"""
        task_type = task.get("type", "general")

        criteria = {
            "implementation": [
                "功能按需求正确实现",
                "代码通过所有测试",
                "代码符合质量标准",
                "文档完整准确",
            ],
            "testing": [
                "测试用例覆盖全面",
                "所有测试通过",
                "测试报告完整",
                "发现的问题已修复",
            ],
            "design": [
                "设计满足所有需求",
                "架构合理可行",
                "文档清晰完整",
                "通过设计评审",
            ],
            "deployment": [
                "应用成功部署",
                "功能正常运行",
                "性能满足要求",
                "监控正常工作",
            ],
        }

        return criteria.get(task_type, ["任务目标达成", "质量标准满足"])

    def _store_guidance_result(
        self, task: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        """存储指导结果"""
        try:
            content = f"Execution guidance for task: {task.get('title', 'Unknown')}"
            metadata = {
                "task_title": task.get("title", ""),
                "task_type": task.get("type", ""),
                "guidance_type": result["data"]["guidance_type"],
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="execution_guidance", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储指导结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class AgentAutomationTools:
    """Agent 自动化工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有 Agent 自动化工具"""
        return [
            TaskDecompositionTool(self.config),
            ExecutionGuidanceTool(self.config),
        ]
