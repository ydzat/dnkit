"""
Agent 行为自动机系统

实现状态机驱动的 Agent 行为控制，提供一致性检查、决策记录和学习优化功能。
"""

import json
import time
from enum import Enum
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


class AgentState(Enum):
    """Agent 状态枚举"""

    IDLE = "idle"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    ERROR_HANDLING = "error_handling"
    LEARNING = "learning"
    COMPLETED = "completed"


class TransitionTrigger(Enum):
    """状态转换触发器"""

    START_TASK = "start_task"
    ANALYSIS_COMPLETE = "analysis_complete"
    PLAN_READY = "plan_ready"
    EXECUTION_COMPLETE = "execution_complete"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    ERROR_OCCURRED = "error_occurred"
    ERROR_RESOLVED = "error_resolved"
    LEARNING_COMPLETE = "learning_complete"
    TASK_COMPLETE = "task_complete"
    RESET = "reset"


class BaseAgentBehaviorTool(BaseTool):
    """Agent 行为工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager = UnifiedDataManager(
            self.config.get("chromadb_path", "./mcp_unified_db")
        )
        self.max_state_history = self.config.get("max_state_history", 1000)
        self.learning_enabled = self.config.get("learning_enabled", True)

    def _get_current_state(self, session_id: str) -> AgentState:
        """获取当前状态"""
        try:
            results = self.data_manager.query_data(
                query=f"agent state {session_id}", data_type="agent_state", n_results=1
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                if metadatas:
                    latest_state = max(metadatas, key=lambda x: x.get("timestamp", 0))
                    return AgentState(latest_state.get("state", "idle"))

            return AgentState.IDLE
        except Exception as e:
            print(f"获取当前状态失败: {e}")
            return AgentState.IDLE

    def _store_state_transition(
        self,
        session_id: str,
        from_state: AgentState,
        to_state: AgentState,
        trigger: TransitionTrigger,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """存储状态转换"""
        try:
            content = f"State transition: {from_state.value} -> {to_state.value}"
            metadata = {
                "session_id": session_id,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "trigger": trigger.value,
                "timestamp": time.time(),
                "context_summary": json.dumps(context or {})[:500],  # 限制长度
            }

            self.data_manager.store_data(
                data_type="agent_state", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储状态转换失败: {e}")

    def _get_state_history(
        self, session_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取状态历史"""
        try:
            results = self.data_manager.query_data(
                query=f"agent state {session_id}",
                data_type="agent_state",
                n_results=limit,
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                # 按时间排序
                return sorted(
                    [
                        m
                        for m in metadatas
                        if isinstance(m, dict) and m.get("session_id") == session_id
                    ],
                    key=lambda x: x.get("timestamp", 0),
                    reverse=True,
                )
            return []
        except Exception as e:
            print(f"获取状态历史失败: {e}")
            return []


class StateMachineController(BaseAgentBehaviorTool):
    """状态机控制器"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.state_transitions = self._define_state_transitions()
        self.prompt_templates = self._load_prompt_templates()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="control_agent_state",
            description="控制 Agent 状态机转换和行为",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID",
                    },
                    "action": {
                        "type": "string",
                        "enum": [
                            "get_state",
                            "transition",
                            "get_history",
                            "get_prompt",
                            "reset",
                        ],
                        "description": "操作类型",
                    },
                    "trigger": {
                        "type": "string",
                        "enum": [t.value for t in TransitionTrigger],
                        "description": "状态转换触发器",
                    },
                    "context": {
                        "type": "object",
                        "description": "上下文信息",
                    },
                    "force_transition": {
                        "type": "boolean",
                        "description": "是否强制转换",
                        "default": False,
                    },
                },
                "required": ["session_id", "action"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行状态机控制"""
        start_time = time.time()
        params = request.parameters

        try:
            session_id = params["session_id"]
            action = params["action"]

            if action == "get_state":
                result = self._get_current_state_info(session_id)
            elif action == "transition":
                trigger = TransitionTrigger(params["trigger"])
                context = params.get("context", {})
                force = params.get("force_transition", False)
                result = self._handle_state_transition(
                    session_id, trigger, context, force
                )
            elif action == "get_history":
                result = self._get_state_history_info(session_id)
            elif action == "get_prompt":
                result = self._get_state_prompt(session_id)
            elif action == "reset":
                result = self._reset_state_machine(session_id)
            else:
                return self._create_error_result(
                    "INVALID_ACTION", f"不支持的操作: {action}"
                )

            if not result["success"]:
                return self._create_error_result("OPERATION_FAILED", result["error"])

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(result["data"], metadata, resources)

        except Exception as e:
            print(f"状态机控制执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _define_state_transitions(
        self,
    ) -> Dict[AgentState, Dict[TransitionTrigger, AgentState]]:
        """定义状态转换规则"""
        return {
            AgentState.IDLE: {
                TransitionTrigger.START_TASK: AgentState.ANALYZING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.ANALYZING: {
                TransitionTrigger.ANALYSIS_COMPLETE: AgentState.PLANNING,
                TransitionTrigger.ERROR_OCCURRED: AgentState.ERROR_HANDLING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.PLANNING: {
                TransitionTrigger.PLAN_READY: AgentState.EXECUTING,
                TransitionTrigger.ERROR_OCCURRED: AgentState.ERROR_HANDLING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.EXECUTING: {
                TransitionTrigger.EXECUTION_COMPLETE: AgentState.VALIDATING,
                TransitionTrigger.ERROR_OCCURRED: AgentState.ERROR_HANDLING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.VALIDATING: {
                TransitionTrigger.VALIDATION_PASSED: AgentState.LEARNING,
                TransitionTrigger.VALIDATION_FAILED: AgentState.PLANNING,
                TransitionTrigger.ERROR_OCCURRED: AgentState.ERROR_HANDLING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.ERROR_HANDLING: {
                TransitionTrigger.ERROR_RESOLVED: AgentState.PLANNING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.LEARNING: {
                TransitionTrigger.LEARNING_COMPLETE: AgentState.COMPLETED,
                TransitionTrigger.TASK_COMPLETE: AgentState.COMPLETED,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
            AgentState.COMPLETED: {
                TransitionTrigger.START_TASK: AgentState.ANALYZING,
                TransitionTrigger.RESET: AgentState.IDLE,
            },
        }

    def _load_prompt_templates(self) -> Dict[AgentState, str]:
        """加载提示模板"""
        return {
            AgentState.IDLE: """
你现在处于空闲状态。等待新任务开始。

当前状态：IDLE
可用操作：
- 接收新任务
- 查看历史记录
- 系统重置

请等待任务指令或选择下一步操作。
""",
            AgentState.ANALYZING: """
你现在处于分析状态。请仔细分析当前任务。

当前状态：ANALYZING
主要任务：
1. 理解任务需求和目标
2. 分析技术约束和限制
3. 识别潜在风险和挑战
4. 收集必要的上下文信息

分析完成后，请触发 ANALYSIS_COMPLETE 转换到规划阶段。
""",
            AgentState.PLANNING: """
你现在处于规划状态。基于分析结果制定执行计划。

当前状态：PLANNING
主要任务：
1. 制定详细的执行步骤
2. 分配资源和时间
3. 确定成功标准
4. 准备备选方案

规划完成后，请触发 PLAN_READY 转换到执行阶段。
""",
            AgentState.EXECUTING: """
你现在处于执行状态。按照计划执行任务。

当前状态：EXECUTING
主要任务：
1. 按步骤执行计划
2. 监控执行进度
3. 处理执行中的问题
4. 记录执行结果

执行完成后，请触发 EXECUTION_COMPLETE 转换到验证阶段。
""",
            AgentState.VALIDATING: """
你现在处于验证状态。验证执行结果的正确性。

当前状态：VALIDATING
主要任务：
1. 检查执行结果是否符合预期
2. 验证功能的正确性
3. 评估质量标准
4. 确认任务完成度

验证通过请触发 VALIDATION_PASSED，失败请触发 VALIDATION_FAILED。
""",
            AgentState.ERROR_HANDLING: """
你现在处于错误处理状态。处理执行过程中的错误。

当前状态：ERROR_HANDLING
主要任务：
1. 分析错误原因
2. 制定解决方案
3. 实施修复措施
4. 验证修复效果

错误解决后，请触发 ERROR_RESOLVED 返回规划阶段。
""",
            AgentState.LEARNING: """
你现在处于学习状态。从执行过程中学习和优化。

当前状态：LEARNING
主要任务：
1. 总结执行经验
2. 识别改进点
3. 更新知识库
4. 优化未来执行

学习完成后，请触发 LEARNING_COMPLETE 完成任务。
""",
            AgentState.COMPLETED: """
你现在处于完成状态。任务已成功完成。

当前状态：COMPLETED
任务状态：已完成
可用操作：
- 开始新任务
- 查看执行报告
- 系统重置

准备好接收新任务或进行其他操作。
""",
        }

    def _get_current_state_info(self, session_id: str) -> Dict[str, Any]:
        """获取当前状态信息"""
        try:
            current_state = self._get_current_state(session_id)
            available_transitions = list(
                self.state_transitions.get(current_state, {}).keys()
            )

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "current_state": current_state.value,
                    "available_transitions": [t.value for t in available_transitions],
                    "prompt_template": self.prompt_templates.get(current_state, ""),
                    "timestamp": time.time(),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_state_transition(
        self,
        session_id: str,
        trigger: TransitionTrigger,
        context: Dict[str, Any],
        force: bool,
    ) -> Dict[str, Any]:
        """处理状态转换"""
        try:
            current_state = self._get_current_state(session_id)

            # 检查转换是否有效
            if not force:
                valid_transitions = self.state_transitions.get(current_state, {})
                if trigger not in valid_transitions:
                    return {
                        "success": False,
                        "error": f"无效的状态转换: {current_state.value} -> {trigger.value}",
                    }

                next_state = valid_transitions[trigger]
            else:
                # 强制转换，需要指定目标状态
                target_state = context.get("target_state")
                if not target_state:
                    return {"success": False, "error": "强制转换需要指定目标状态"}
                next_state = AgentState(target_state)

            # 执行状态转换
            self._store_state_transition(
                session_id, current_state, next_state, trigger, context
            )

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "transition": {
                        "from": current_state.value,
                        "to": next_state.value,
                        "trigger": trigger.value,
                        "timestamp": time.time(),
                    },
                    "new_prompt": self.prompt_templates.get(next_state, ""),
                    "context": context,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_state_history_info(self, session_id: str) -> Dict[str, Any]:
        """获取状态历史信息"""
        try:
            history = self._get_state_history(session_id, 20)

            # 统计状态分布
            state_counts: Dict[str, int] = {}
            transition_counts: Dict[str, int] = {}

            for record in history:
                from_state = record.get("from_state")
                to_state = record.get("to_state")
                trigger = record.get("trigger")

                if to_state is not None:
                    state_counts[to_state] = state_counts.get(to_state, 0) + 1
                if from_state is not None and to_state is not None:
                    transition_key = f"{from_state}->{to_state}"
                    transition_counts[transition_key] = (
                        transition_counts.get(transition_key, 0) + 1
                    )

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "history": history,
                    "statistics": {
                        "total_transitions": len(history),
                        "state_distribution": state_counts,
                        "common_transitions": sorted(
                            transition_counts.items(), key=lambda x: x[1], reverse=True
                        )[:5],
                    },
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_state_prompt(self, session_id: str) -> Dict[str, Any]:
        """获取当前状态的提示"""
        try:
            current_state = self._get_current_state(session_id)
            prompt = self.prompt_templates.get(current_state, "")

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "current_state": current_state.value,
                    "prompt": prompt,
                    "timestamp": time.time(),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _reset_state_machine(self, session_id: str) -> Dict[str, Any]:
        """重置状态机"""
        try:
            current_state = self._get_current_state(session_id)

            # 记录重置操作
            self._store_state_transition(
                session_id,
                current_state,
                AgentState.IDLE,
                TransitionTrigger.RESET,
                {"reason": "manual_reset"},
            )

            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "reset_from": current_state.value,
                    "new_state": AgentState.IDLE.value,
                    "prompt": self.prompt_templates[AgentState.IDLE],
                    "timestamp": time.time(),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class BehaviorValidator(BaseAgentBehaviorTool):
    """行为验证器"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="validate_agent_behavior",
            description="验证 Agent 行为的一致性和正确性",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID",
                    },
                    "validation_type": {
                        "type": "string",
                        "enum": [
                            "consistency",
                            "decision_quality",
                            "anomaly_detection",
                            "performance",
                        ],
                        "description": "验证类型",
                    },
                    "behavior_data": {
                        "type": "object",
                        "properties": {
                            "actions": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "执行的动作列表",
                            },
                            "decisions": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "做出的决策列表",
                            },
                            "context": {
                                "type": "object",
                                "description": "执行上下文",
                            },
                        },
                        "description": "行为数据",
                    },
                    "validation_criteria": {
                        "type": "object",
                        "properties": {
                            "consistency_threshold": {"type": "number", "default": 0.8},
                            "performance_threshold": {"type": "number", "default": 0.7},
                            "anomaly_sensitivity": {"type": "number", "default": 0.5},
                        },
                        "description": "验证标准",
                    },
                },
                "required": ["session_id", "validation_type", "behavior_data"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行行为验证"""
        start_time = time.time()
        params = request.parameters

        try:
            session_id = params["session_id"]
            validation_type = params["validation_type"]
            behavior_data = params["behavior_data"]
            criteria = params.get("validation_criteria", {})

            # 执行相应的验证
            if validation_type == "consistency":
                result = self._validate_consistency(session_id, behavior_data, criteria)
            elif validation_type == "decision_quality":
                result = self._validate_decision_quality(
                    session_id, behavior_data, criteria
                )
            elif validation_type == "anomaly_detection":
                result = self._detect_anomalies(session_id, behavior_data, criteria)
            elif validation_type == "performance":
                result = self._validate_performance(session_id, behavior_data, criteria)
            else:
                return self._create_error_result(
                    "INVALID_TYPE", f"不支持的验证类型: {validation_type}"
                )

            if not result["success"]:
                return self._create_error_result("VALIDATION_FAILED", result["error"])

            # 存储验证结果
            self._store_validation_result(session_id, validation_type, result["data"])

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(result["data"], metadata, resources)

        except Exception as e:
            print(f"行为验证执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _validate_consistency(
        self, session_id: str, behavior_data: Dict[str, Any], criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证行为一致性"""
        try:
            actions = behavior_data.get("actions", [])
            decisions = behavior_data.get("decisions", [])
            threshold = criteria.get("consistency_threshold", 0.8)

            # 获取历史行为数据
            historical_behavior = self._get_historical_behavior(session_id)

            # 分析行为模式
            current_patterns = self._extract_behavior_patterns(actions, decisions)
            historical_patterns = self._extract_behavior_patterns(
                historical_behavior.get("actions", []),
                historical_behavior.get("decisions", []),
            )

            # 计算一致性分数
            consistency_score = self._calculate_consistency_score(
                current_patterns, historical_patterns
            )

            # 识别不一致的行为
            inconsistencies = self._identify_inconsistencies(
                current_patterns, historical_patterns, threshold
            )

            validation_result = {
                "session_id": session_id,
                "validation_type": "consistency",
                "consistency_score": consistency_score,
                "threshold": threshold,
                "passed": consistency_score >= threshold,
                "inconsistencies": inconsistencies,
                "patterns_analyzed": {
                    "current": current_patterns,
                    "historical": historical_patterns,
                },
                "recommendations": self._generate_consistency_recommendations(
                    inconsistencies
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": validation_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_decision_quality(
        self, session_id: str, behavior_data: Dict[str, Any], criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证决策质量"""
        try:
            decisions = behavior_data.get("decisions", [])
            context = behavior_data.get("context", {})

            # 分析决策质量
            quality_metrics = {
                "rationality": self._assess_decision_rationality(decisions, context),
                "effectiveness": self._assess_decision_effectiveness(decisions),
                "timeliness": self._assess_decision_timeliness(decisions),
                "consistency": self._assess_decision_consistency(decisions),
            }

            # 计算总体质量分数
            overall_score = sum(quality_metrics.values()) / len(quality_metrics)

            # 识别问题决策
            problematic_decisions = self._identify_problematic_decisions(
                decisions, quality_metrics
            )

            validation_result = {
                "session_id": session_id,
                "validation_type": "decision_quality",
                "overall_score": overall_score,
                "quality_metrics": quality_metrics,
                "decisions_analyzed": len(decisions),
                "problematic_decisions": problematic_decisions,
                "recommendations": self._generate_decision_recommendations(
                    quality_metrics, problematic_decisions
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": validation_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _detect_anomalies(
        self, session_id: str, behavior_data: Dict[str, Any], criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测异常行为"""
        try:
            actions = behavior_data.get("actions", [])
            decisions = behavior_data.get("decisions", [])
            sensitivity = criteria.get("anomaly_sensitivity", 0.5)

            # 获取正常行为基线
            baseline_behavior = self._get_behavior_baseline(session_id)

            # 检测各种类型的异常
            anomalies = {
                "action_anomalies": self._detect_action_anomalies(
                    actions, baseline_behavior, sensitivity
                ),
                "decision_anomalies": self._detect_decision_anomalies(
                    decisions, baseline_behavior, sensitivity
                ),
                "timing_anomalies": self._detect_timing_anomalies(
                    behavior_data, baseline_behavior, sensitivity
                ),
                "pattern_anomalies": self._detect_pattern_anomalies(
                    behavior_data, baseline_behavior, sensitivity
                ),
            }

            # 计算异常严重程度
            total_anomalies = sum(
                len(anomaly_list) for anomaly_list in anomalies.values()
            )
            severity = self._calculate_anomaly_severity(
                total_anomalies, len(actions) + len(decisions)
            )

            validation_result = {
                "session_id": session_id,
                "validation_type": "anomaly_detection",
                "total_anomalies": total_anomalies,
                "severity": severity,
                "anomalies": anomalies,
                "sensitivity": sensitivity,
                "recommendations": self._generate_anomaly_recommendations(
                    anomalies, severity
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": validation_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_performance(
        self, session_id: str, behavior_data: Dict[str, Any], criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证性能表现"""
        try:
            actions = behavior_data.get("actions", [])
            context = behavior_data.get("context", {})
            threshold = criteria.get("performance_threshold", 0.7)

            # 计算性能指标
            performance_metrics = {
                "efficiency": self._calculate_efficiency(actions, context),
                "accuracy": self._calculate_accuracy(actions, context),
                "speed": self._calculate_speed(actions, context),
                "resource_usage": self._calculate_resource_usage(actions, context),
            }

            # 计算总体性能分数
            overall_performance = sum(performance_metrics.values()) / len(
                performance_metrics
            )

            # 识别性能瓶颈
            bottlenecks = self._identify_performance_bottlenecks(
                actions, performance_metrics
            )

            validation_result = {
                "session_id": session_id,
                "validation_type": "performance",
                "overall_performance": overall_performance,
                "threshold": threshold,
                "passed": overall_performance >= threshold,
                "performance_metrics": performance_metrics,
                "bottlenecks": bottlenecks,
                "recommendations": self._generate_performance_recommendations(
                    performance_metrics, bottlenecks
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": validation_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_historical_behavior(self, session_id: str) -> Dict[str, Any]:
        """获取历史行为数据"""
        try:
            results = self.data_manager.query_data(
                query=f"behavior validation {session_id}",
                data_type="behavior_validation",
                n_results=50,
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                # 聚合历史行为数据
                all_actions: List[Dict[str, Any]] = []
                all_decisions: List[Dict[str, Any]] = []

                for record in metadatas:
                    if (
                        isinstance(record, dict)
                        and record.get("session_id") == session_id
                    ):
                        # 这里应该从记录中提取行为数据
                        # 简化实现，返回空数据
                        pass

                return {"actions": all_actions, "decisions": all_decisions}

            return {"actions": [], "decisions": []}
        except Exception:
            return {"actions": [], "decisions": []}

    def _extract_behavior_patterns(
        self, actions: List[Dict], decisions: List[Dict]
    ) -> Dict[str, Any]:
        """提取行为模式"""
        patterns: Dict[str, Any] = {
            "action_sequences": [],
            "decision_patterns": [],
            "timing_patterns": [],
            "frequency_patterns": {},
        }

        # 分析动作序列
        if len(actions) > 1:
            for i in range(len(actions) - 1):
                current_action = actions[i].get("type", "unknown")
                next_action = actions[i + 1].get("type", "unknown")
                patterns["action_sequences"].append(f"{current_action}->{next_action}")

        # 分析决策模式
        decision_types = [d.get("type", "unknown") for d in decisions]
        patterns["decision_patterns"] = list(set(decision_types))

        # 分析频率模式
        frequency_patterns = patterns["frequency_patterns"]
        for action in actions:
            action_type = action.get("type", "unknown")
            frequency_patterns[action_type] = frequency_patterns.get(action_type, 0) + 1

        return patterns

    def _calculate_consistency_score(self, current: Dict, historical: Dict) -> float:
        """计算一致性分数"""
        if not historical.get("action_sequences"):
            return 1.0  # 没有历史数据时认为一致

        # 简单的一致性计算
        current_sequences = set(current.get("action_sequences", []))
        historical_sequences = set(historical.get("action_sequences", []))

        if not current_sequences:
            return 1.0

        intersection = current_sequences.intersection(historical_sequences)
        return len(intersection) / len(current_sequences)

    def _identify_inconsistencies(
        self, current: Dict, historical: Dict, threshold: float
    ) -> List[Dict]:
        """识别不一致的行为"""
        inconsistencies = []

        # 检查新的动作序列
        current_sequences = set(current.get("action_sequences", []))
        historical_sequences = set(historical.get("action_sequences", []))

        new_sequences = current_sequences - historical_sequences
        for seq in new_sequences:
            inconsistencies.append(
                {
                    "type": "new_action_sequence",
                    "description": f"新的动作序列: {seq}",
                    "severity": "medium",
                }
            )

        return inconsistencies

    def _generate_consistency_recommendations(
        self, inconsistencies: List[Dict]
    ) -> List[str]:
        """生成一致性建议"""
        recommendations = []

        if inconsistencies:
            recommendations.append("检测到行为不一致，建议审查执行逻辑")

            new_sequences = [
                inc for inc in inconsistencies if inc["type"] == "new_action_sequence"
            ]
            if new_sequences:
                recommendations.append(
                    f"发现 {len(new_sequences)} 个新的动作序列，建议验证其合理性"
                )
        else:
            recommendations.append("行为表现一致，继续保持")

        return recommendations

    def _assess_decision_rationality(
        self, decisions: List[Dict], context: Dict
    ) -> float:
        """评估决策合理性"""
        if not decisions:
            return 1.0

        # 简化的合理性评估
        rational_decisions = 0
        for decision in decisions:
            # 检查决策是否有充分的理由
            if decision.get("reasoning") and len(decision["reasoning"]) > 10:
                rational_decisions += 1

        return rational_decisions / len(decisions)

    def _assess_decision_effectiveness(self, decisions: List[Dict]) -> float:
        """评估决策有效性"""
        if not decisions:
            return 1.0

        # 简化的有效性评估
        effective_decisions = 0
        for decision in decisions:
            # 检查决策是否达到预期结果
            if decision.get("outcome") == "success":
                effective_decisions += 1

        return effective_decisions / len(decisions) if decisions else 1.0

    def _assess_decision_timeliness(self, decisions: List[Dict]) -> float:
        """评估决策及时性"""
        if not decisions:
            return 1.0

        # 简化的及时性评估
        timely_decisions = 0
        for decision in decisions:
            # 检查决策时间是否合理
            decision_time = decision.get("decision_time", 0)
            if decision_time < 5000:  # 5秒内
                timely_decisions += 1

        return timely_decisions / len(decisions)

    def _assess_decision_consistency(self, decisions: List[Dict]) -> float:
        """评估决策一致性"""
        if len(decisions) < 2:
            return 1.0

        # 检查相似情况下的决策一致性
        consistent_decisions = 0
        total_comparisons = 0

        for i in range(len(decisions)):
            for j in range(i + 1, len(decisions)):
                if self._are_similar_contexts(decisions[i], decisions[j]):
                    total_comparisons += 1
                    if decisions[i].get("type") == decisions[j].get("type"):
                        consistent_decisions += 1

        return (
            consistent_decisions / total_comparisons if total_comparisons > 0 else 1.0
        )

    def _are_similar_contexts(self, decision1: Dict, decision2: Dict) -> bool:
        """判断两个决策的上下文是否相似"""
        # 简化的相似性判断
        context1 = decision1.get("context", {})
        context2 = decision2.get("context", {})

        # 检查关键字段是否相似
        task_type1 = context1.get("task_type")
        task_type2 = context2.get("task_type")
        return task_type1 is not None and task_type1 == task_type2

    def _identify_problematic_decisions(
        self, decisions: List[Dict], metrics: Dict
    ) -> List[Dict]:
        """识别问题决策"""
        problematic = []

        for decision in decisions:
            issues = []

            # 检查各种问题
            if not decision.get("reasoning"):
                issues.append("缺乏决策理由")

            if decision.get("outcome") == "failure":
                issues.append("决策结果失败")

            if decision.get("decision_time", 0) > 10000:  # 10秒
                issues.append("决策时间过长")

            if issues:
                problematic.append({"decision": decision, "issues": issues})

        return problematic

    def _generate_decision_recommendations(
        self, metrics: Dict, problematic: List[Dict]
    ) -> List[str]:
        """生成决策建议"""
        recommendations = []

        if metrics.get("rationality", 1.0) < 0.7:
            recommendations.append("提高决策理由的详细程度和逻辑性")

        if metrics.get("effectiveness", 1.0) < 0.7:
            recommendations.append("改进决策策略以提高成功率")

        if metrics.get("timeliness", 1.0) < 0.7:
            recommendations.append("优化决策过程以提高响应速度")

        if problematic:
            recommendations.append(f"发现 {len(problematic)} 个问题决策，建议详细分析")

        return recommendations

    def _get_behavior_baseline(self, session_id: str) -> Dict[str, Any]:
        """获取行为基线"""
        # 简化实现，返回默认基线
        return {
            "normal_action_types": ["analyze", "plan", "execute", "validate"],
            "normal_decision_types": ["continue", "retry", "abort"],
            "normal_timing": {"min": 100, "max": 5000, "avg": 1000},
            "normal_patterns": [],
        }

    def _detect_action_anomalies(
        self, actions: List[Dict], baseline: Dict, sensitivity: float
    ) -> List[Dict]:
        """检测动作异常"""
        anomalies = []
        normal_types = set(baseline.get("normal_action_types", []))

        for action in actions:
            action_type = action.get("type", "unknown")
            if action_type not in normal_types:
                anomalies.append(
                    {
                        "type": "unknown_action_type",
                        "action": action,
                        "description": f"未知的动作类型: {action_type}",
                    }
                )

        return anomalies

    def _detect_decision_anomalies(
        self, decisions: List[Dict], baseline: Dict, sensitivity: float
    ) -> List[Dict]:
        """检测决策异常"""
        anomalies = []
        normal_types = set(baseline.get("normal_decision_types", []))

        for decision in decisions:
            decision_type = decision.get("type", "unknown")
            if decision_type not in normal_types:
                anomalies.append(
                    {
                        "type": "unknown_decision_type",
                        "decision": decision,
                        "description": f"未知的决策类型: {decision_type}",
                    }
                )

        return anomalies

    def _detect_timing_anomalies(
        self, behavior_data: Dict, baseline: Dict, sensitivity: float
    ) -> List[Dict]:
        """检测时间异常"""
        anomalies = []
        normal_timing = baseline.get("normal_timing", {})

        actions = behavior_data.get("actions", [])
        for action in actions:
            duration = action.get("duration", 0)
            if duration > normal_timing.get("max", 5000) * (1 + sensitivity):
                anomalies.append(
                    {
                        "type": "slow_action",
                        "action": action,
                        "description": f"动作执行时间异常: {duration}ms",
                    }
                )

        return anomalies

    def _detect_pattern_anomalies(
        self, behavior_data: Dict, baseline: Dict, sensitivity: float
    ) -> List[Dict]:
        """检测模式异常"""
        # 简化实现
        return []

    def _calculate_anomaly_severity(
        self, total_anomalies: int, total_behaviors: int
    ) -> str:
        """计算异常严重程度"""
        if total_behaviors == 0:
            return "none"

        anomaly_rate = total_anomalies / total_behaviors

        if anomaly_rate > 0.3:
            return "high"
        elif anomaly_rate > 0.1:
            return "medium"
        elif anomaly_rate > 0:
            return "low"
        else:
            return "none"

    def _generate_anomaly_recommendations(
        self, anomalies: Dict, severity: str
    ) -> List[str]:
        """生成异常建议"""
        recommendations = []

        if severity == "high":
            recommendations.append("检测到高严重程度异常，建议立即停止并检查系统")
        elif severity == "medium":
            recommendations.append("检测到中等程度异常，建议仔细监控")
        elif severity == "low":
            recommendations.append("检测到轻微异常，建议持续观察")

        total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
        if total_anomalies > 0:
            recommendations.append(f"总计发现 {total_anomalies} 个异常行为")

        return recommendations

    def _calculate_efficiency(self, actions: List[Dict], context: Dict) -> float:
        """计算效率"""
        if not actions:
            return 1.0

        # 简化的效率计算
        successful_actions = sum(1 for action in actions if action.get("success", True))
        return successful_actions / len(actions)

    def _calculate_accuracy(self, actions: List[Dict], context: Dict) -> float:
        """计算准确性"""
        if not actions:
            return 1.0

        # 简化的准确性计算
        accurate_actions = sum(1 for action in actions if action.get("accurate", True))
        return accurate_actions / len(actions)

    def _calculate_speed(self, actions: List[Dict], context: Dict) -> float:
        """计算速度"""
        if not actions:
            return 1.0

        # 简化的速度计算
        total_time = sum(float(action.get("duration", 1000)) for action in actions)
        avg_time = total_time / len(actions)

        # 假设1000ms是标准时间
        return min(1.0, 1000.0 / avg_time)

    def _calculate_resource_usage(self, actions: List[Dict], context: Dict) -> float:
        """计算资源使用效率"""
        if not actions:
            return 1.0

        # 简化的资源使用计算
        total_memory = sum(float(action.get("memory_used", 1)) for action in actions)
        avg_memory = total_memory / len(actions)

        # 假设1MB是标准内存使用
        return min(1.0, 1.0 / avg_memory)

    def _identify_performance_bottlenecks(
        self, actions: List[Dict], metrics: Dict
    ) -> List[Dict]:
        """识别性能瓶颈"""
        bottlenecks = []

        # 找出最慢的动作
        slowest_actions = sorted(
            actions, key=lambda x: x.get("duration", 0), reverse=True
        )[:3]
        for action in slowest_actions:
            if action.get("duration", 0) > 5000:  # 5秒
                bottlenecks.append(
                    {
                        "type": "slow_action",
                        "action": action,
                        "description": f"动作执行缓慢: {action.get('duration', 0)}ms",
                    }
                )

        # 找出内存使用最多的动作
        memory_heavy_actions = sorted(
            actions, key=lambda x: x.get("memory_used", 0), reverse=True
        )[:3]
        for action in memory_heavy_actions:
            if action.get("memory_used", 0) > 10:  # 10MB
                bottlenecks.append(
                    {
                        "type": "memory_heavy",
                        "action": action,
                        "description": f"内存使用过多: {action.get('memory_used', 0)}MB",
                    }
                )

        return bottlenecks

    def _generate_performance_recommendations(
        self, metrics: Dict, bottlenecks: List[Dict]
    ) -> List[str]:
        """生成性能建议"""
        recommendations = []

        if metrics.get("efficiency", 1.0) < 0.8:
            recommendations.append("提高动作成功率以改善效率")

        if metrics.get("speed", 1.0) < 0.7:
            recommendations.append("优化动作执行速度")

        if metrics.get("resource_usage", 1.0) < 0.7:
            recommendations.append("优化资源使用效率")

        if bottlenecks:
            recommendations.append(f"发现 {len(bottlenecks)} 个性能瓶颈，建议优化")

        return recommendations

    def _store_validation_result(
        self, session_id: str, validation_type: str, data: Dict[str, Any]
    ) -> None:
        """存储验证结果"""
        try:
            content = f"Behavior validation: {validation_type} for {session_id}"
            metadata = {
                "session_id": session_id,
                "validation_type": validation_type,
                "passed": data.get("passed", True),
                "score": data.get("overall_score", data.get("consistency_score", 1.0)),
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="behavior_validation", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储验证结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class LearningOptimizer(BaseAgentBehaviorTool):
    """学习优化机制"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="optimize_agent_learning",
            description="基于历史数据优化 Agent 学习和行为",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID",
                    },
                    "optimization_type": {
                        "type": "string",
                        "enum": [
                            "pattern_recognition",
                            "adaptive_adjustment",
                            "performance_optimization",
                            "behavior_refinement",
                        ],
                        "description": "优化类型",
                    },
                    "learning_data": {
                        "type": "object",
                        "properties": {
                            "successful_patterns": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "成功的行为模式",
                            },
                            "failed_patterns": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "失败的行为模式",
                            },
                            "performance_data": {
                                "type": "object",
                                "description": "性能数据",
                            },
                        },
                        "description": "学习数据",
                    },
                    "optimization_goals": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "efficiency",
                                "accuracy",
                                "consistency",
                                "speed",
                                "resource_usage",
                            ],
                        },
                        "description": "优化目标",
                        "default": ["efficiency", "accuracy"],
                    },
                },
                "required": ["session_id", "optimization_type"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行学习优化"""
        start_time = time.time()
        params = request.parameters

        try:
            session_id = params["session_id"]
            optimization_type = params["optimization_type"]
            learning_data = params.get("learning_data", {})
            goals = params.get("optimization_goals", ["efficiency", "accuracy"])

            # 执行相应的优化
            if optimization_type == "pattern_recognition":
                result = self._optimize_pattern_recognition(
                    session_id, learning_data, goals
                )
            elif optimization_type == "adaptive_adjustment":
                result = self._perform_adaptive_adjustment(
                    session_id, learning_data, goals
                )
            elif optimization_type == "performance_optimization":
                result = self._optimize_performance(session_id, learning_data, goals)
            elif optimization_type == "behavior_refinement":
                result = self._refine_behavior(session_id, learning_data, goals)
            else:
                return self._create_error_result(
                    "INVALID_TYPE", f"不支持的优化类型: {optimization_type}"
                )

            if not result["success"]:
                return self._create_error_result("OPTIMIZATION_FAILED", result["error"])

            # 存储优化结果
            self._store_optimization_result(
                session_id, optimization_type, result["data"]
            )

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=1,
            )

            return self._create_success_result(result["data"], metadata, resources)

        except Exception as e:
            print(f"学习优化执行异常: {e}")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _optimize_pattern_recognition(
        self, session_id: str, learning_data: Dict[str, Any], goals: List[str]
    ) -> Dict[str, Any]:
        """优化模式识别"""
        try:
            successful_patterns = learning_data.get("successful_patterns", [])
            failed_patterns = learning_data.get("failed_patterns", [])

            # 分析成功模式
            success_analysis = self._analyze_patterns(successful_patterns, "success")

            # 分析失败模式
            failure_analysis = self._analyze_patterns(failed_patterns, "failure")

            # 提取关键特征
            key_features = self._extract_key_features(
                success_analysis, failure_analysis
            )

            # 生成模式规则
            pattern_rules = self._generate_pattern_rules(key_features, goals)

            # 计算模式置信度
            confidence_scores = self._calculate_pattern_confidence(
                pattern_rules, successful_patterns, failed_patterns
            )

            optimization_result = {
                "session_id": session_id,
                "optimization_type": "pattern_recognition",
                "success_patterns_analyzed": len(successful_patterns),
                "failure_patterns_analyzed": len(failed_patterns),
                "key_features": key_features,
                "pattern_rules": pattern_rules,
                "confidence_scores": confidence_scores,
                "recommendations": self._generate_pattern_recommendations(
                    pattern_rules, confidence_scores
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": optimization_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _perform_adaptive_adjustment(
        self, session_id: str, learning_data: Dict[str, Any], goals: List[str]
    ) -> Dict[str, Any]:
        """执行自适应调整"""
        try:
            performance_data = learning_data.get("performance_data", {})

            # 分析当前性能
            current_performance = self._analyze_current_performance(performance_data)

            # 识别调整机会
            adjustment_opportunities = self._identify_adjustment_opportunities(
                current_performance, goals
            )

            # 生成调整策略
            adjustment_strategies = self._generate_adjustment_strategies(
                adjustment_opportunities, goals
            )

            # 预测调整效果
            predicted_improvements = self._predict_adjustment_effects(
                adjustment_strategies, current_performance
            )

            optimization_result = {
                "session_id": session_id,
                "optimization_type": "adaptive_adjustment",
                "current_performance": current_performance,
                "adjustment_opportunities": adjustment_opportunities,
                "adjustment_strategies": adjustment_strategies,
                "predicted_improvements": predicted_improvements,
                "recommendations": self._generate_adjustment_recommendations(
                    adjustment_strategies
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": optimization_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _optimize_performance(
        self, session_id: str, learning_data: Dict[str, Any], goals: List[str]
    ) -> Dict[str, Any]:
        """优化性能"""
        try:
            performance_data = learning_data.get("performance_data", {})

            # 分析性能瓶颈
            bottlenecks = self._analyze_performance_bottlenecks(performance_data)

            # 生成优化策略
            optimization_strategies = self._generate_performance_strategies(
                bottlenecks, goals
            )

            # 评估优化潜力
            optimization_potential = self._evaluate_optimization_potential(
                optimization_strategies, performance_data
            )

            # 制定实施计划
            implementation_plan = self._create_implementation_plan(
                optimization_strategies, optimization_potential
            )

            optimization_result = {
                "session_id": session_id,
                "optimization_type": "performance_optimization",
                "bottlenecks": bottlenecks,
                "optimization_strategies": optimization_strategies,
                "optimization_potential": optimization_potential,
                "implementation_plan": implementation_plan,
                "recommendations": self._generate_performance_optimization_recommendations(
                    optimization_strategies
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": optimization_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _refine_behavior(
        self, session_id: str, learning_data: Dict[str, Any], goals: List[str]
    ) -> Dict[str, Any]:
        """精炼行为"""
        try:
            successful_patterns = learning_data.get("successful_patterns", [])
            failed_patterns = learning_data.get("failed_patterns", [])

            # 分析行为有效性
            behavior_effectiveness = self._analyze_behavior_effectiveness(
                successful_patterns, failed_patterns
            )

            # 识别改进机会
            improvement_opportunities = self._identify_behavior_improvements(
                behavior_effectiveness, goals
            )

            # 生成精炼策略
            refinement_strategies = self._generate_refinement_strategies(
                improvement_opportunities
            )

            # 验证精炼效果
            refinement_validation = self._validate_refinement_strategies(
                refinement_strategies, successful_patterns
            )

            optimization_result = {
                "session_id": session_id,
                "optimization_type": "behavior_refinement",
                "behavior_effectiveness": behavior_effectiveness,
                "improvement_opportunities": improvement_opportunities,
                "refinement_strategies": refinement_strategies,
                "refinement_validation": refinement_validation,
                "recommendations": self._generate_refinement_recommendations(
                    refinement_strategies
                ),
                "timestamp": time.time(),
            }

            return {"success": True, "data": optimization_result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_patterns(
        self, patterns: List[Dict], pattern_type: str
    ) -> Dict[str, Any]:
        """分析模式"""
        if not patterns:
            return {"type": pattern_type, "count": 0, "features": {}}

        # 提取特征
        features: Dict[str, List[Any]] = {}
        for pattern in patterns:
            for key, value in pattern.items():
                if key not in features:
                    features[key] = []
                features[key].append(value)

        # 统计特征频率
        feature_stats = {}
        for key, values in features.items():
            if isinstance(values[0], str):
                # 字符串特征
                unique_values = list(set(values))
                feature_stats[key] = {
                    "type": "categorical",
                    "unique_count": len(unique_values),
                    "most_common": (
                        max(unique_values, key=values.count) if unique_values else None
                    ),
                    "frequency": {val: values.count(val) for val in unique_values},
                }
            elif isinstance(values[0], (int, float)):
                # 数值特征
                feature_stats[key] = {
                    "type": "numerical",
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "count": len(values),
                }

        return {"type": pattern_type, "count": len(patterns), "features": feature_stats}

    def _extract_key_features(
        self, success_analysis: Dict, failure_analysis: Dict
    ) -> List[Dict]:
        """提取关键特征"""
        key_features = []

        success_features = success_analysis.get("features", {})
        failure_features = failure_analysis.get("features", {})

        # 比较成功和失败模式的特征
        for feature_name in success_features:
            if feature_name in failure_features:
                success_feature = success_features[feature_name]
                failure_feature = failure_features[feature_name]

                # 分析特征差异
                if success_feature["type"] == "categorical":
                    success_common = success_feature.get("most_common")
                    failure_common = failure_feature.get("most_common")

                    if success_common != failure_common:
                        key_features.append(
                            {
                                "name": feature_name,
                                "type": "categorical",
                                "success_value": success_common,
                                "failure_value": failure_common,
                                "importance": "high",
                            }
                        )
                elif success_feature["type"] == "numerical":
                    success_avg = success_feature.get("avg", 0)
                    failure_avg = failure_feature.get("avg", 0)

                    if abs(success_avg - failure_avg) > 0.1:  # 阈值
                        key_features.append(
                            {
                                "name": feature_name,
                                "type": "numerical",
                                "success_avg": success_avg,
                                "failure_avg": failure_avg,
                                "difference": success_avg - failure_avg,
                                "importance": (
                                    "high"
                                    if abs(success_avg - failure_avg) > 0.5
                                    else "medium"
                                ),
                            }
                        )

        return key_features

    def _generate_pattern_rules(
        self, key_features: List[Dict], goals: List[str]
    ) -> List[Dict]:
        """生成模式规则"""
        rules = []

        for feature in key_features:
            if feature["type"] == "categorical":
                rules.append(
                    {
                        "type": "categorical_rule",
                        "feature": feature["name"],
                        "condition": f"{feature['name']} == '{feature['success_value']}'",
                        "action": "prefer",
                        "confidence": 0.8,
                        "goal_alignment": self._assess_goal_alignment(feature, goals),
                    }
                )
            elif feature["type"] == "numerical":
                if feature["difference"] > 0:
                    operator = ">"
                    threshold = feature["failure_avg"]
                else:
                    operator = "<"
                    threshold = feature["failure_avg"]

                rules.append(
                    {
                        "type": "numerical_rule",
                        "feature": feature["name"],
                        "condition": f"{feature['name']} {operator} {threshold}",
                        "action": "optimize",
                        "confidence": min(0.9, abs(feature["difference"])),
                        "goal_alignment": self._assess_goal_alignment(feature, goals),
                    }
                )

        return rules

    def _assess_goal_alignment(self, feature: Dict, goals: List[str]) -> float:
        """评估目标对齐度"""
        # 简化的目标对齐评估
        feature_name = feature["name"].lower()

        alignment_score = 0.5  # 默认分数

        if "efficiency" in goals and "time" in feature_name:
            alignment_score += 0.3
        if "accuracy" in goals and "error" in feature_name:
            alignment_score += 0.3
        if "speed" in goals and ("duration" in feature_name or "time" in feature_name):
            alignment_score += 0.3

        return min(1.0, alignment_score)

    def _calculate_pattern_confidence(
        self,
        rules: List[Dict],
        successful_patterns: List[Dict],
        failed_patterns: List[Dict],
    ) -> Dict[str, float]:
        """计算模式置信度"""
        confidence_scores = {}

        for rule in rules:
            rule_id = f"{rule['feature']}_{rule['type']}"

            # 简化的置信度计算
            success_matches = self._count_rule_matches(rule, successful_patterns)
            failure_matches = self._count_rule_matches(rule, failed_patterns)

            total_success = len(successful_patterns)
            total_failure = len(failed_patterns)

            if total_success + total_failure > 0:
                success_rate = success_matches / max(1, total_success)
                failure_rate = failure_matches / max(1, total_failure)

                confidence = success_rate - failure_rate
                confidence_scores[rule_id] = max(0.0, min(1.0, confidence))
            else:
                confidence_scores[rule_id] = 0.5

        return confidence_scores

    def _count_rule_matches(self, rule: Dict, patterns: List[Dict]) -> int:
        """计算规则匹配数"""
        matches = 0
        feature_name = rule["feature"]

        for pattern in patterns:
            if feature_name in pattern:
                value = pattern[feature_name]

                if rule["type"] == "categorical_rule":
                    if str(value) in rule["condition"]:
                        matches += 1
                elif rule["type"] == "numerical_rule":
                    # 简化的数值规则匹配
                    if isinstance(value, (int, float)):
                        matches += 1

        return matches

    def _generate_pattern_recommendations(
        self, rules: List[Dict], confidence_scores: Dict
    ) -> List[str]:
        """生成模式建议"""
        recommendations = []

        high_confidence_rules = [
            rule
            for rule in rules
            if confidence_scores.get(f"{rule['feature']}_{rule['type']}", 0) > 0.7
        ]

        if high_confidence_rules:
            recommendations.append(
                f"发现 {len(high_confidence_rules)} 个高置信度模式规则"
            )

            for rule in high_confidence_rules[:3]:  # 只显示前3个
                recommendations.append(f"建议优化 {rule['feature']} 特征")

        if len(rules) > len(high_confidence_rules):
            low_confidence_count = len(rules) - len(high_confidence_rules)
            recommendations.append(f"有 {low_confidence_count} 个规则需要更多数据验证")

        return recommendations

    def _analyze_current_performance(self, performance_data: Dict) -> Dict[str, Any]:
        """分析当前性能"""
        return {
            "efficiency": performance_data.get("efficiency", 0.8),
            "accuracy": performance_data.get("accuracy", 0.9),
            "speed": performance_data.get("speed", 0.7),
            "resource_usage": performance_data.get("resource_usage", 0.6),
            "overall_score": performance_data.get("overall_score", 0.75),
        }

    def _identify_adjustment_opportunities(
        self, performance: Dict, goals: List[str]
    ) -> List[Dict]:
        """识别调整机会"""
        opportunities = []

        for goal in goals:
            if goal in performance:
                current_value = performance[goal]
                if current_value < 0.8:  # 阈值
                    opportunities.append(
                        {
                            "metric": goal,
                            "current_value": current_value,
                            "target_value": 0.9,
                            "improvement_potential": 0.9 - current_value,
                            "priority": "high" if current_value < 0.6 else "medium",
                        }
                    )

        return opportunities

    def _generate_adjustment_strategies(
        self, opportunities: List[Dict], goals: List[str]
    ) -> List[Dict]:
        """生成调整策略"""
        strategies = []

        for opportunity in opportunities:
            metric = opportunity["metric"]

            if metric == "efficiency":
                strategies.append(
                    {
                        "metric": metric,
                        "strategy": "reduce_redundant_operations",
                        "description": "减少冗余操作以提高效率",
                        "expected_improvement": 0.1,
                        "implementation_difficulty": "medium",
                    }
                )
            elif metric == "speed":
                strategies.append(
                    {
                        "metric": metric,
                        "strategy": "optimize_critical_path",
                        "description": "优化关键路径以提高速度",
                        "expected_improvement": 0.15,
                        "implementation_difficulty": "high",
                    }
                )
            elif metric == "resource_usage":
                strategies.append(
                    {
                        "metric": metric,
                        "strategy": "implement_caching",
                        "description": "实现缓存机制以减少资源使用",
                        "expected_improvement": 0.2,
                        "implementation_difficulty": "medium",
                    }
                )

        return strategies

    def _predict_adjustment_effects(
        self, strategies: List[Dict], current_performance: Dict
    ) -> Dict[str, Any]:
        """预测调整效果"""
        predictions = {}

        for strategy in strategies:
            metric = strategy["metric"]
            current_value = current_performance.get(metric, 0.5)
            expected_improvement = strategy.get("expected_improvement", 0.1)

            predicted_value = min(1.0, current_value + expected_improvement)

            predictions[metric] = {
                "current": current_value,
                "predicted": predicted_value,
                "improvement": predicted_value - current_value,
                "confidence": 0.7,  # 简化的置信度
            }

        return predictions

    def _generate_adjustment_recommendations(self, strategies: List[Dict]) -> List[str]:
        """生成调整建议"""
        recommendations = []

        high_impact_strategies = [
            s for s in strategies if s.get("expected_improvement", 0) > 0.15
        ]
        if high_impact_strategies:
            recommendations.append(
                f"优先实施 {len(high_impact_strategies)} 个高影响策略"
            )

        easy_strategies = [
            s for s in strategies if s.get("implementation_difficulty") == "medium"
        ]
        if easy_strategies:
            recommendations.append(
                f"可以快速实施 {len(easy_strategies)} 个中等难度策略"
            )

        return recommendations

    def _analyze_performance_bottlenecks(self, performance_data: Dict) -> List[Dict]:
        """分析性能瓶颈"""
        bottlenecks = []

        # 简化的瓶颈分析
        for metric, value in performance_data.items():
            if isinstance(value, (int, float)) and value < 0.6:
                bottlenecks.append(
                    {
                        "metric": metric,
                        "current_value": value,
                        "severity": "high" if value < 0.4 else "medium",
                        "impact": "high",
                    }
                )

        return bottlenecks

    def _generate_performance_strategies(
        self, bottlenecks: List[Dict], goals: List[str]
    ) -> List[Dict]:
        """生成性能策略"""
        strategies = []

        for bottleneck in bottlenecks:
            metric = bottleneck["metric"]
            strategies.append(
                {
                    "target_metric": metric,
                    "strategy_type": "optimization",
                    "description": f"优化 {metric} 性能",
                    "priority": bottleneck["severity"],
                    "estimated_effort": "medium",
                }
            )

        return strategies

    def _evaluate_optimization_potential(
        self, strategies: List[Dict], performance_data: Dict
    ) -> Dict[str, Any]:
        """评估优化潜力"""
        return {
            "total_strategies": len(strategies),
            "high_priority": len(
                [s for s in strategies if s.get("priority") == "high"]
            ),
            "estimated_improvement": 0.2,  # 简化的估算
            "implementation_feasibility": 0.8,
        }

    def _create_implementation_plan(
        self, strategies: List[Dict], potential: Dict
    ) -> Dict[str, Any]:
        """创建实施计划"""
        return {
            "phases": [
                {
                    "phase": 1,
                    "strategies": [
                        s for s in strategies if s.get("priority") == "high"
                    ],
                    "duration": "1-2 weeks",
                    "expected_improvement": 0.1,
                },
                {
                    "phase": 2,
                    "strategies": [
                        s for s in strategies if s.get("priority") == "medium"
                    ],
                    "duration": "2-3 weeks",
                    "expected_improvement": 0.1,
                },
            ],
            "total_duration": "3-5 weeks",
            "total_improvement": potential.get("estimated_improvement", 0.2),
        }

    def _generate_performance_optimization_recommendations(
        self, strategies: List[Dict]
    ) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        if strategies:
            recommendations.append(f"制定了 {len(strategies)} 个性能优化策略")

            high_priority = [s for s in strategies if s.get("priority") == "high"]
            if high_priority:
                recommendations.append(f"优先实施 {len(high_priority)} 个高优先级策略")

        return recommendations

    def _analyze_behavior_effectiveness(
        self, successful_patterns: List[Dict], failed_patterns: List[Dict]
    ) -> Dict[str, Any]:
        """分析行为有效性"""
        total_patterns = len(successful_patterns) + len(failed_patterns)
        success_rate = len(successful_patterns) / max(1, total_patterns)

        return {
            "success_rate": success_rate,
            "total_patterns": total_patterns,
            "successful_count": len(successful_patterns),
            "failed_count": len(failed_patterns),
            "effectiveness_level": (
                "high"
                if success_rate > 0.8
                else "medium" if success_rate > 0.6 else "low"
            ),
        }

    def _identify_behavior_improvements(
        self, effectiveness: Dict, goals: List[str]
    ) -> List[Dict]:
        """识别行为改进机会"""
        improvements = []

        if effectiveness["success_rate"] < 0.8:
            improvements.append(
                {
                    "area": "success_rate",
                    "current_value": effectiveness["success_rate"],
                    "target_value": 0.9,
                    "improvement_type": "increase_success_patterns",
                    "priority": "high",
                }
            )

        return improvements

    def _generate_refinement_strategies(self, improvements: List[Dict]) -> List[Dict]:
        """生成精炼策略"""
        strategies = []

        for improvement in improvements:
            if improvement["area"] == "success_rate":
                strategies.append(
                    {
                        "strategy": "enhance_decision_logic",
                        "description": "增强决策逻辑以提高成功率",
                        "target_improvement": 0.1,
                        "implementation": "refine_pattern_matching",
                    }
                )

        return strategies

    def _validate_refinement_strategies(
        self, strategies: List[Dict], successful_patterns: List[Dict]
    ) -> Dict[str, Any]:
        """验证精炼策略"""
        return {
            "strategies_count": len(strategies),
            "validation_score": 0.8,  # 简化的验证分数
            "feasibility": "high",
            "expected_success": 0.85,
        }

    def _generate_refinement_recommendations(self, strategies: List[Dict]) -> List[str]:
        """生成精炼建议"""
        recommendations = []

        if strategies:
            recommendations.append(f"制定了 {len(strategies)} 个行为精炼策略")
            recommendations.append("建议逐步实施精炼策略并监控效果")

        return recommendations

    def _store_optimization_result(
        self, session_id: str, optimization_type: str, data: Dict[str, Any]
    ) -> None:
        """存储优化结果"""
        try:
            content = f"Learning optimization: {optimization_type} for {session_id}"
            metadata = {
                "session_id": session_id,
                "optimization_type": optimization_type,
                "timestamp": time.time(),
            }

            self.data_manager.store_data(
                data_type="learning_optimization", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储优化结果失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class AgentBehaviorTools:
    """Agent 行为工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有 Agent 行为工具"""
        return [
            StateMachineController(self.config),
            BehaviorValidator(self.config),
            LearningOptimizer(self.config),
        ]
