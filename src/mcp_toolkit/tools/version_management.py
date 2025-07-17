"""
轻量化版本管理系统

为 Agent 提供撤销更改、版本回滚等能力，无需完整的 Git 功能，
专注于 Agent 操作的可逆性和安全性。
"""

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
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


class BaseVersionTool(BaseTool):
    """版本管理工具基类"""

    # 类级别的共享实例缓存
    _shared_data_managers: Dict[str, Any] = {}
    _shared_backup_dirs: Dict[str, Any] = {}

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.max_history_size = self.config.get("max_history_size", 1000)
        self.auto_cleanup_days = self.config.get("auto_cleanup_days", 7)
        # 延迟初始化，在执行时根据工作目录设置
        self.data_manager: UnifiedDataManager | None = None
        self.backup_dir: str | None = None

    def _get_work_directory(
        self, request: Optional[ToolExecutionRequest] = None
    ) -> str:
        """获取工作目录，优先使用ExecutionContext中的工作目录"""
        if request:
            work_dir = self._get_working_directory(request)
            if work_dir:
                return os.path.abspath(work_dir)
        return os.path.abspath(os.getcwd())

    def _ensure_initialized(
        self, request: Optional[ToolExecutionRequest] = None
    ) -> None:
        """确保数据管理器和备份目录已初始化，优先使用SetWorkingDirectoryTool创建的实例"""
        if self.data_manager is None or self.backup_dir is None:
            work_dir = self._get_work_directory(request)
            # 规范化路径，确保路径一致性
            db_path = os.path.normpath(
                os.path.join(
                    work_dir, self.config.get("chromadb_path", "mcp_unified_db")
                )
            )

            # 首先检查SetWorkingDirectoryTool的全局缓存
            from .terminal import BaseTerminalTool

            existing_manager = None

            # 检查全局缓存中是否有匹配的数据管理器
            for cached_path, manager in BaseTerminalTool._global_data_managers.items():
                if os.path.normpath(cached_path) == db_path:
                    existing_manager = manager
                    self._logger.info(
                        f"复用SetWorkingDirectoryTool创建的数据管理器: {db_path}"
                    )
                    break

            # 如果全局缓存没有，再检查本地缓存
            if not existing_manager:
                for (
                    cached_path,
                    manager,
                ) in BaseVersionTool._shared_data_managers.items():
                    if os.path.normpath(cached_path) == db_path:
                        existing_manager = manager
                        self._logger.info(f"复用本地缓存的数据管理器: {db_path}")
                        break

            if existing_manager:
                self.data_manager = existing_manager
            else:
                # 只有在没有任何缓存时才创建新实例
                self._logger.warning(f"未找到已存在的数据管理器，创建新实例: {db_path}")
                self.data_manager = UnifiedDataManager(db_path)
                BaseVersionTool._shared_data_managers[db_path] = self.data_manager

            # 设置备份目录
            backup_dir = os.path.normpath(
                os.path.join(
                    work_dir, self.config.get("backup_directory", "mcp_backups")
                )
            )
            if backup_dir not in BaseVersionTool._shared_backup_dirs:
                BaseVersionTool._shared_backup_dirs[backup_dir] = backup_dir
                os.makedirs(backup_dir, exist_ok=True)
            self.backup_dir = backup_dir

    def _generate_operation_id(self) -> str:
        """生成操作ID"""
        timestamp = str(time.time())
        return f"op_{hashlib.md5(timestamp.encode(), usedforsecurity=False).hexdigest()[:8]}"

    def _create_file_snapshot(
        self,
        abs_path: str,
        operation_id: str,
        rel_path: Optional[str] = None,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Optional[str]:
        """创建文件快照，快照文件始终存储在self.backup_dir（记忆库文件夹）下，file_path存储为相对路径"""
        import os
        import shutil
        import uuid

        try:
            self._ensure_initialized(request)
            work_dir = self._get_work_directory(request)
            if rel_path is None:
                rel_path = os.path.relpath(abs_path, work_dir)
            if not os.path.exists(abs_path):
                return None
            # 使用时间戳+UUID确保唯一性，避免同一秒内多个文件快照ID重复
            unique_suffix = str(uuid.uuid4())[:8]
            snapshot_id = f"snap_{operation_id}_{int(time.time())}_{unique_suffix}"
            if self.backup_dir is None:
                raise ValueError("Backup directory not initialized")
            os.makedirs(self.backup_dir, exist_ok=True)
            snapshot_path = os.path.join(self.backup_dir, f"{snapshot_id}.backup")
            shutil.copy2(abs_path, snapshot_path)
            self._store_snapshot_info(
                snapshot_id, rel_path, operation_id, abs_path=abs_path, request=request
            )
            return snapshot_id
        except Exception as e:
            self._logger.warning(f"创建文件快照失败: {e}")
            return None

    def _store_snapshot_info(
        self,
        snapshot_id: str,
        file_path: str,
        operation_id: str,
        abs_path: Optional[str] = None,
        request: Optional[ToolExecutionRequest] = None,
    ) -> None:
        """存储快照信息，file_path 必须为相对路径"""
        import os

        try:
            self._ensure_initialized(request)
            work_dir = self._get_work_directory(request)
            if abs_path is None:
                abs_path = os.path.abspath(os.path.join(work_dir, file_path))
            content = f"File snapshot for {file_path}"
            metadata = {
                "snapshot_id": snapshot_id,
                "file_path": file_path,
                "operation_id": operation_id,
                "timestamp": time.time(),
                "file_size": (
                    os.path.getsize(abs_path) if os.path.exists(abs_path) else 0
                ),
                "file_hash": self._calculate_file_hash(abs_path),
            }
            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            self.data_manager.store_data(
                data_type="file_snapshot", content=content, metadata=metadata
            )
        except Exception as e:
            self._logger.warning(f"存储快照信息失败: {e}")

    def _calculate_file_hash(self, abs_path: str) -> str:
        """计算文件哈希，abs_path为绝对路径"""
        import hashlib
        import os

        try:
            if not os.path.exists(abs_path):
                return ""
            with open(abs_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _store_operation_record(self, operation_data: Dict[str, Any]) -> None:
        """存储操作记录"""
        try:
            content = (
                f"Agent operation: {operation_data.get('operation_type', 'unknown')}"
            )

            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            self.data_manager.store_data(
                data_type="agent_operation", content=content, metadata=operation_data
            )
        except Exception as e:
            self._logger.warning(f"存储操作记录失败: {e}")

    def _get_operation_history(
        self, limit: int = 50, request: Optional[ToolExecutionRequest] = None
    ) -> List[Dict[str, Any]]:
        """获取操作历史"""
        try:
            self._ensure_initialized(request)
            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            results = self.data_manager.query_data(
                query="agent operation", data_type="agent_operation", n_results=limit
            )

            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    # ChromaDB 返回的是列表的列表
                    if isinstance(metadatas[0], list):
                        return metadatas[0] if metadatas[0] else []
                    else:
                        return metadatas
            return []
        except Exception as e:
            print(f"获取操作历史失败: {e}")
            return []


class UndoTool(BaseVersionTool):
    """撤销工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="undo_operation",
            description="撤销 Agent 的操作",
            parameters={
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "integer",
                        "description": "撤销的步数",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "operation_type": {
                        "type": "string",
                        "enum": [
                            "file_edit",
                            "file_create",
                            "file_delete",
                            "config_change",
                            "all",
                        ],
                        "description": "撤销的操作类型",
                        "default": "all",
                    },
                    "target_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "指定撤销的文件列表（可选）",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "是否只预览撤销效果",
                        "default": False,
                    },
                    "confirm_required": {
                        "type": "boolean",
                        "description": "是否需要确认",
                        "default": True,
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行撤销操作"""
        start_time = time.time()
        params = request.parameters

        try:
            # 确保初始化
            self._ensure_initialized(request)

            steps = params.get("steps", 1)
            operation_type = params.get("operation_type", "all")
            target_files = params.get("target_files", [])
            dry_run = params.get("dry_run", False)
            confirm_required = params.get("confirm_required", True)

            # 获取操作历史
            history = self._get_operation_history(
                steps * 2, request
            )  # 获取更多历史以便筛选

            if not history:
                return self._create_error_result(
                    "NO_HISTORY", "没有找到可撤销的操作历史"
                )

            # 筛选符合条件的操作
            operations_to_undo = self._filter_operations(
                history, steps, operation_type, target_files
            )

            if not operations_to_undo:
                return self._create_error_result(
                    "NO_MATCHING_OPERATIONS", "没有找到符合条件的操作"
                )

            # 执行撤销
            undo_result = self._perform_undo(operations_to_undo, dry_run, request)

            if not undo_result["success"]:
                return self._create_error_result("UNDO_FAILED", undo_result["error"])

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(undo_result)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(operations_to_undo),
            )

            resources = ResourceUsage(
                memory_mb=len(str(undo_result)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(operations_to_undo),
            )

            return self._create_success_result(undo_result, metadata, resources)

        except Exception as e:
            self._logger.exception("撤销操作执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _filter_operations(
        self,
        history: List[Dict[str, Any]],
        steps: int,
        operation_type: str,
        target_files: List[str],
    ) -> List[Dict[str, Any]]:
        """筛选要撤销的操作"""
        filtered = []

        for op in history:
            # 类型筛选
            if operation_type != "all" and op.get("operation_type") != operation_type:
                continue

            # 文件筛选
            if target_files:
                op_file = op.get("file_path", "")
                if not any(target in op_file for target in target_files):
                    continue

            # 检查是否已经被撤销
            if op.get("undone", False):
                continue

            filtered.append(op)

            if len(filtered) >= steps:
                break

        return filtered

    def _perform_undo(
        self,
        operations: List[Dict[str, Any]],
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """执行撤销操作"""
        try:
            undone_operations = []

            for op in operations:
                operation_type = op.get("operation_type")
                file_path = op.get("file_path")
                operation_id = op.get("operation_id")

                if operation_type == "file_edit":
                    if file_path is None or operation_id is None:
                        result = {
                            "success": False,
                            "error": "Missing file_path or operation_id",
                        }
                    else:
                        result = self._undo_file_edit(
                            file_path, operation_id, dry_run, request
                        )
                elif operation_type == "file_create":
                    if file_path is None:
                        result = {"success": False, "error": "Missing file_path"}
                    else:
                        result = self._undo_file_create(file_path, dry_run, request)
                elif operation_type == "file_delete":
                    if file_path is None or operation_id is None:
                        result = {
                            "success": False,
                            "error": "Missing file_path or operation_id",
                        }
                    else:
                        result = self._undo_file_delete(
                            file_path, operation_id, dry_run, request
                        )
                else:
                    result = {
                        "success": False,
                        "error": f"不支持的操作类型: {operation_type}",
                    }

                if result["success"]:
                    undone_operations.append(
                        {
                            "operation_id": operation_id,
                            "type": operation_type,
                            "file_path": file_path,
                            "description": op.get("description", ""),
                            "timestamp": op.get("timestamp"),
                            "undo_result": result,
                        }
                    )

                    # 标记为已撤销（如果不是预览模式）
                    if not dry_run and operation_id is not None:
                        self._mark_operation_undone(operation_id)
                else:
                    return {"success": False, "error": result["error"]}

            return {
                "success": True,
                "undo_summary": {
                    "operations_undone": len(undone_operations),
                    "files_affected": list(
                        set(op["file_path"] for op in undone_operations)
                    ),
                    "timestamp": time.time(),
                },
                "undone_operations": undone_operations,
                "dry_run": dry_run,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _undo_file_edit(
        self,
        file_path: str,
        operation_id: str,
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """撤销文件编辑，file_path 必须为相对路径"""
        try:
            work_dir = self._get_work_directory(request)
            rel_path = (
                os.path.relpath(file_path, work_dir)
                if os.path.isabs(file_path)
                else file_path
            )
            abs_path = os.path.abspath(os.path.join(work_dir, rel_path))
            # 查找对应的快照
            snapshot_info = self._find_snapshot(rel_path, operation_id)
            if not snapshot_info:
                return {"success": False, "error": f"未找到文件 {rel_path} 的快照"}
            if self.backup_dir is None:
                return {"success": False, "error": "Backup directory not initialized"}
            snapshot_path = os.path.join(
                self.backup_dir, f"{snapshot_info['snapshot_id']}.backup"
            )
            if not os.path.exists(snapshot_path):
                return {"success": False, "error": f"快照文件不存在: {snapshot_path}"}
            if not dry_run:
                # 恢复文件
                shutil.copy2(snapshot_path, abs_path)
            return {
                "success": True,
                "action": "file_restored",
                "snapshot_used": snapshot_info["snapshot_id"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _undo_file_create(
        self,
        file_path: str,
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """撤销文件创建，file_path 必须为相对路径"""
        try:
            work_dir = self._get_work_directory(request)
            rel_path = (
                os.path.relpath(file_path, work_dir)
                if os.path.isabs(file_path)
                else file_path
            )
            abs_path = os.path.abspath(os.path.join(work_dir, rel_path))
            if not os.path.exists(abs_path):
                return {"success": True, "action": "file_already_deleted"}
            if not dry_run:
                os.remove(abs_path)
            return {"success": True, "action": "file_deleted"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _undo_file_delete(
        self,
        file_path: str,
        operation_id: str,
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """撤销文件删除，file_path 必须为相对路径"""
        try:
            work_dir = self._get_work_directory(request)
            rel_path = (
                os.path.relpath(file_path, work_dir)
                if os.path.isabs(file_path)
                else file_path
            )
            abs_path = os.path.abspath(os.path.join(work_dir, rel_path))
            # 查找删除前的快照
            snapshot_info = self._find_snapshot(rel_path, operation_id)
            if not snapshot_info:
                return {
                    "success": False,
                    "error": f"未找到文件 {rel_path} 的删除前快照",
                }
            if self.backup_dir is None:
                return {"success": False, "error": "Backup directory not initialized"}
            snapshot_path = os.path.join(
                self.backup_dir, f"{snapshot_info['snapshot_id']}.backup"
            )
            if not os.path.exists(snapshot_path):
                return {"success": False, "error": f"快照文件不存在: {snapshot_path}"}
            if not dry_run:
                # 恢复文件
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                shutil.copy2(snapshot_path, abs_path)
            return {
                "success": True,
                "action": "file_restored",
                "snapshot_used": snapshot_info["snapshot_id"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_snapshot(
        self, file_path: str, operation_id: str
    ) -> Optional[Dict[str, Any]]:
        """查找快照信息"""
        try:
            if self.data_manager is None:
                return None
            results = self.data_manager.query_data(
                query=f"snapshot for {file_path}",
                data_type="file_snapshot",
                n_results=50,
            )

            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                for metadata in metadatas:
                    if not isinstance(metadata, dict):
                        continue
                    if (
                        metadata.get("file_path") == file_path
                        and metadata.get("operation_id") == operation_id
                    ):
                        return metadata

            return None
        except Exception as e:
            print(f"查找快照失败: {e}")
            return None

    def _mark_operation_undone(self, operation_id: str) -> None:
        """标记操作为已撤销"""
        try:
            # 这里应该更新 ChromaDB 中的记录，标记为已撤销
            # 由于 ChromaDB 不支持直接更新，我们添加一个撤销记录
            content = f"Operation {operation_id} has been undone"
            metadata = {
                "operation_id": operation_id,
                "action": "undo_marker",
                "timestamp": time.time(),
            }

            if self.data_manager is None:
                self._logger.warning(
                    "Data manager not initialized, cannot mark operation as undone"
                )
                return
            self.data_manager.store_data(
                data_type="undo_marker", content=content, metadata=metadata
            )
        except Exception as e:
            self._logger.warning(f"标记操作撤销失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class RollbackTool(BaseVersionTool):
    """回滚工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="rollback_to_checkpoint",
            description="回滚到指定的检查点或时间点",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "object",
                        "properties": {
                            "checkpoint_id": {"type": "string"},
                            "timestamp": {"type": "string"},
                            "operation_id": {"type": "string"},
                        },
                        "description": "回滚目标（三选一）",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["project", "files", "config"],
                        "description": "回滚范围",
                        "default": "project",
                    },
                    "include_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "包含的文件列表",
                    },
                    "exclude_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "排除的文件列表",
                    },
                    "preview_changes": {
                        "type": "boolean",
                        "description": "是否预览变更",
                        "default": True,
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "是否在回滚前创建备份",
                        "default": True,
                    },
                },
                "required": ["target"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行回滚操作"""
        start_time = time.time()
        params = request.parameters

        try:
            # 确保初始化
            self._ensure_initialized(request)

            target = params["target"]
            scope = params.get("scope", "project")
            include_files = params.get("include_files", [])
            exclude_files = params.get("exclude_files", [])
            preview_changes = params.get("preview_changes", True)
            create_backup = params.get("create_backup", True)

            # 确定回滚目标
            rollback_target = self._determine_rollback_target(target)
            if not rollback_target["success"]:
                return self._create_error_result(
                    "INVALID_TARGET", rollback_target["error"]
                )

            # 获取回滚点信息
            target_info = rollback_target["target_info"]

            # 分析回滚影响
            impact_analysis = self._analyze_rollback_impact(
                target_info, scope, include_files, exclude_files
            )

            if preview_changes:
                # 只返回预览信息
                result_data = {
                    "rollback_target": target_info,
                    "impact_analysis": impact_analysis,
                    "preview_mode": True,
                    "estimated_changes": impact_analysis["estimated_changes"],
                }
            else:
                # 执行实际回滚
                if create_backup:
                    backup_result = self._create_rollback_backup()
                    if not backup_result["success"]:
                        return self._create_error_result(
                            "BACKUP_FAILED", backup_result["error"]
                        )

                rollback_result = self._perform_rollback(
                    target_info, scope, include_files, exclude_files, request
                )

                if not rollback_result["success"]:
                    return self._create_error_result(
                        "ROLLBACK_FAILED", rollback_result["error"]
                    )

                result_data = {
                    "rollback_target": target_info,
                    "rollback_summary": rollback_result["summary"],
                    "backup_created": (
                        backup_result.get("backup_id") if create_backup else None
                    ),
                    "files_affected": rollback_result["files_affected"],
                    "preview_mode": False,
                }

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,
                memory_used=len(str(result_data)) / 1024 / 1024,
                cpu_time=(time.time() - start_time) * 1000,
                io_operations=len(impact_analysis.get("files_to_change", [])),
            )

            resources = ResourceUsage(
                memory_mb=len(str(result_data)) / 1024 / 1024,
                cpu_time_ms=(time.time() - start_time) * 1000,
                io_operations=len(impact_analysis.get("files_to_change", [])),
            )

            return self._create_success_result(result_data, metadata, resources)

        except Exception as e:
            self._logger.exception("回滚操作执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _determine_rollback_target(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """确定回滚目标，支持 checkpoint_id 或 checkpoint_name"""
        try:
            if "checkpoint_id" in target:
                return self._find_checkpoint(target["checkpoint_id"])
            elif "checkpoint_name" in target:
                info = self._find_checkpoint_by_name_sync(target["checkpoint_name"])
                if info and info.get("checkpoint_id"):
                    return self._find_checkpoint(info["checkpoint_id"])
                else:
                    return {
                        "success": False,
                        "error": f"未找到检查点: {target['checkpoint_name']}",
                    }
            elif "timestamp" in target:
                return self._find_by_timestamp(target["timestamp"])
            elif "operation_id" in target:
                return self._find_by_operation(target["operation_id"])
            else:
                return {
                    "success": False,
                    "error": "必须指定 checkpoint_id、checkpoint_name、timestamp 或 operation_id",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_checkpoint_by_name_sync(self, name: str) -> Dict[str, Any]:
        try:
            if self.data_manager is None:
                return {}
            results = self.data_manager.query_data(
                query="checkpoint", data_type="checkpoint", n_results=50
            )
            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []
                for metadata in sorted(
                    metadatas, key=lambda x: x.get("timestamp", 0), reverse=True
                ):
                    if not isinstance(metadata, dict):
                        continue
                    if metadata.get("name") == name:
                        return metadata
            return {}
        except Exception:
            return {}

    def _find_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """查找检查点（排除已删除的）"""
        try:
            if self.data_manager is None:
                return {}
            results = self.data_manager.query_data(
                query="checkpoint", data_type="checkpoint", n_results=50
            )
            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []
                for metadata in metadatas:
                    if not isinstance(metadata, dict):
                        continue
                    if metadata.get("checkpoint_id") == checkpoint_id:
                        # 检查是否被删除
                        if hasattr(self, "_is_checkpoint_deleted") and callable(
                            self._is_checkpoint_deleted
                        ):
                            import asyncio

                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # 若在事件循环中，直接返回（无法await）
                                return {"success": True, "target_info": metadata}
                            else:
                                if loop.run_until_complete(
                                    self._is_checkpoint_deleted(checkpoint_id)
                                ):
                                    continue
                        return {"success": True, "target_info": metadata}
            return {"success": False, "error": f"未找到检查点: {checkpoint_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_by_timestamp(self, timestamp_str: str) -> Dict[str, Any]:
        """根据时间戳查找"""
        try:
            # 解析时间戳
            import datetime

            try:
                if timestamp_str.isdigit():
                    target_timestamp = float(timestamp_str)
                else:
                    # 尝试解析日期时间字符串
                    dt = datetime.datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    target_timestamp = dt.timestamp()
            except Exception:
                return {"success": False, "error": f"无效的时间戳格式: {timestamp_str}"}

            # 查找最接近的操作
            if self.data_manager is None:
                return {"success": False, "error": "Data manager not initialized"}
            results = self.data_manager.query_data(
                query="agent operation", data_type="agent_operation", n_results=100
            )

            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                closest_op = None
                min_diff = float("inf")

                for metadata in metadatas:
                    if not isinstance(metadata, dict):
                        continue
                    op_timestamp = metadata.get("timestamp", 0)
                    diff = abs(op_timestamp - target_timestamp)
                    if diff < min_diff:
                        min_diff = diff
                        closest_op = metadata

                if closest_op:
                    return {
                        "success": True,
                        "target_info": {
                            "type": "timestamp",
                            "operation_id": closest_op.get("operation_id"),
                            "timestamp": closest_op.get("timestamp"),
                            "description": f"最接近 {timestamp_str} 的操作",
                        },
                    }

            return {
                "success": False,
                "error": f"未找到时间戳 {timestamp_str} 附近的操作",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_by_operation(self, operation_id: str) -> Dict[str, Any]:
        """根据操作ID查找"""
        try:
            if self.data_manager is None:
                return {"success": False, "error": "Data manager not initialized"}
            results = self.data_manager.query_data(
                query=f"operation {operation_id}",
                data_type="agent_operation",
                n_results=10,
            )

            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                for metadata in metadatas:
                    if not isinstance(metadata, dict):
                        continue
                    if metadata.get("operation_id") == operation_id:
                        return {
                            "success": True,
                            "target_info": {
                                "type": "operation",
                                "operation_id": operation_id,
                                "timestamp": metadata.get("timestamp"),
                                "description": metadata.get("description", ""),
                            },
                        }

            return {"success": False, "error": f"未找到操作: {operation_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_rollback_impact(
        self,
        target_info: Dict[str, Any],
        scope: str,
        include_files: List[str],
        exclude_files: List[str],
    ) -> Dict[str, Any]:
        """分析回滚影响"""
        try:
            target_timestamp = target_info.get("timestamp", time.time())

            # 获取目标时间点之后的所有操作
            recent_operations = self._get_operations_since(target_timestamp)

            # 分析受影响的文件
            affected_files = set()
            for op in recent_operations:
                file_path = op.get("file_path")
                if file_path:
                    # 应用文件过滤
                    if include_files and not any(
                        inc in file_path for inc in include_files
                    ):
                        continue
                    if exclude_files and any(exc in file_path for exc in exclude_files):
                        continue

                    affected_files.add(file_path)

            return {
                "target_timestamp": target_timestamp,
                "operations_to_rollback": len(recent_operations),
                "files_to_change": list(affected_files),
                "estimated_changes": {
                    "files_affected": len(affected_files),
                    "operations_reversed": len(recent_operations),
                },
                "risk_assessment": self._assess_rollback_risk(recent_operations),
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_operations_since(self, timestamp: float) -> List[Dict[str, Any]]:
        """获取指定时间点之后的操作"""
        try:
            if self.data_manager is None:
                return []
            results = self.data_manager.query_data(
                query="agent operation", data_type="agent_operation", n_results=200
            )

            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                return [
                    op
                    for op in metadatas
                    if isinstance(op, dict) and op.get("timestamp", 0) > timestamp
                ]
            return []
        except Exception as e:
            print(f"获取操作历史失败: {e}")
            return []

    def _assess_rollback_risk(self, operations: List[Dict[str, Any]]) -> str:
        """评估回滚风险"""
        if len(operations) > 50:
            return "high"
        elif len(operations) > 10:
            return "medium"
        else:
            return "low"

    def _create_rollback_backup(self) -> Dict[str, Any]:
        """创建回滚前备份"""
        try:
            backup_id = f"rollback_backup_{int(time.time())}"
            # 这里应该创建当前状态的完整备份
            # 简化实现，只记录备份ID

            content = "Rollback backup created"
            metadata = {
                "backup_id": backup_id,
                "backup_type": "rollback_backup",
                "timestamp": time.time(),
            }

            if self.data_manager is None:
                return {"success": False, "error": "Data manager not initialized"}
            self.data_manager.store_data(
                data_type="rollback_backup", content=content, metadata=metadata
            )

            return {"success": True, "backup_id": backup_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _perform_rollback(
        self,
        target_info: Dict[str, Any],
        scope: str,
        include_files: List[str],
        exclude_files: List[str],
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """执行实际回滚，增加详细debug日志"""
        try:
            import json
            import logging
            import os

            logger = getattr(self, "_logger", None) or logging.getLogger(
                "mcp_toolkit.tools.version_management"
            )
            work_dir = self._get_work_directory(request)

            # 从检查点信息中获取patch_map
            patch_map = {}
            if "patch_map_str" in target_info:
                try:
                    patch_map = json.loads(target_info.get("patch_map_str", "{}"))
                    logger.info(f"[DEBUG] 从检查点获取到patch_map: {patch_map}")
                except Exception as e:
                    logger.error(f"[DEBUG] 解析patch_map失败: {e}")

            # 如果没有从检查点获取到patch_map，尝试从其他字段获取
            if not patch_map and "patch_map" in target_info:
                patch_map = target_info.get("patch_map", {})
                logger.info(f"[DEBUG] 从target_info.patch_map获取到: {patch_map}")

            # 处理操作历史
            target_timestamp = target_info.get("timestamp", time.time())
            operations_to_rollback = self._get_operations_since(target_timestamp)
            logger.info(
                f"[DEBUG] 回滚目标时间戳: {target_timestamp}, 获取到操作数: {len(operations_to_rollback)}"
            )

            # 按时间倒序排列，从最新的开始撤销
            operations_to_rollback.sort(
                key=lambda x: x.get("timestamp", 0), reverse=True
            )
            files_affected: List[str] = []
            rollback_summary: Dict[str, Any] = {
                "operations_rolled_back": 0,
                "files_restored": 0,
                "errors": [],
            }

            # 首先处理操作历史中的文件
            for op in operations_to_rollback:
                file_path = op.get("file_path")
                logger.info(
                    f"[DEBUG] 检查操作: {op.get('operation_id')} 路径: {file_path}"
                )
                if not file_path:
                    logger.info(f"[DEBUG] 跳过无 file_path 的操作: {op}")
                    continue

                # 应用文件过滤
                if include_files and not any(inc in file_path for inc in include_files):
                    logger.info(f"[DEBUG] 跳过未包含的文件: {file_path}")
                    continue
                if exclude_files and any(exc in file_path for exc in exclude_files):
                    logger.info(f"[DEBUG] 跳过被排除的文件: {file_path}")
                    continue

                # 执行单个操作的回滚
                result = self._rollback_single_operation(op, request)
                logger.info(f"[DEBUG] 回滚操作结果: {result}")
                if result["success"]:
                    rollback_summary["operations_rolled_back"] += 1
                    if file_path not in files_affected:
                        files_affected.append(file_path)
                        rollback_summary["files_restored"] += 1
                else:
                    rollback_summary["errors"].append(
                        {
                            "operation_id": op.get("operation_id"),
                            "error": result["error"],
                        }
                    )

            # 然后处理检查点中的文件快照
            for file_path, snapshot_id in patch_map.items():
                # 应用文件过滤
                if include_files and not any(inc in file_path for inc in include_files):
                    logger.info(f"[DEBUG] 跳过未包含的文件: {file_path}")
                    continue
                if exclude_files and any(exc in file_path for exc in exclude_files):
                    logger.info(f"[DEBUG] 跳过被排除的文件: {file_path}")
                    continue

                # 检查文件是否存在，如果不存在则从快照恢复
                abs_path = os.path.abspath(os.path.join(work_dir, file_path))
                if not os.path.exists(abs_path):
                    logger.info(f"[DEBUG] 文件不存在，尝试从快照恢复: {file_path}")
                    if self.backup_dir is None:
                        logger.error("Backup directory not initialized")
                        continue
                    snapshot_path = os.path.join(
                        self.backup_dir, f"{snapshot_id}.backup"
                    )

                    if os.path.exists(snapshot_path):
                        try:
                            # 确保目录存在
                            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                            # 从快照恢复文件
                            shutil.copy2(snapshot_path, abs_path)
                            logger.info(f"[DEBUG] 成功从快照恢复文件: {file_path}")

                            if file_path not in files_affected:
                                files_affected.append(file_path)
                                rollback_summary["files_restored"] += 1
                        except Exception as e:
                            logger.error(f"[DEBUG] 从快照恢复文件失败: {e}")
                            rollback_summary["errors"].append(
                                {
                                    "file_path": file_path,
                                    "error": f"从快照恢复失败: {str(e)}",
                                }
                            )
                    else:
                        logger.error(f"[DEBUG] 快照文件不存在: {snapshot_path}")
                        rollback_summary["errors"].append(
                            {
                                "file_path": file_path,
                                "error": f"快照文件不存在: {snapshot_path}",
                            }
                        )

            logger.info(
                f"[DEBUG] 回滚汇总: {rollback_summary}, 影响文件: {files_affected}"
            )
            return {
                "success": True,
                "summary": rollback_summary,
                "files_affected": files_affected,
            }
        except Exception as e:
            import logging

            logging.getLogger("mcp_toolkit.tools.version_management").error(
                f"[DEBUG] 回滚异常: {e}"
            )
            return {"success": False, "error": str(e)}

    def _rollback_single_operation(
        self, operation: Dict[str, Any], request: Optional[ToolExecutionRequest] = None
    ) -> Dict[str, Any]:
        """回滚单个操作，增加debug日志"""
        try:
            import logging

            logger = getattr(self, "_logger", None) or logging.getLogger(
                "mcp_toolkit.tools.version_management"
            )
            operation_type = operation.get("operation_type")
            file_path = operation.get("file_path")
            operation_id = operation.get("operation_id")
            logger.info(
                f"[DEBUG] 回滚单操作: type={operation_type}, file_path={file_path}, op_id={operation_id}"
            )
            if operation_type == "file_edit":
                if file_path is None or operation_id is None:
                    return {
                        "success": False,
                        "error": "Missing file_path or operation_id",
                    }
                return self._undo_file_edit(file_path, operation_id, False, request)
            elif operation_type == "file_create":
                if file_path is None:
                    return {"success": False, "error": "Missing file_path"}
                return self._undo_file_create(file_path, False, request)
            elif operation_type == "file_delete":
                if file_path is None or operation_id is None:
                    return {
                        "success": False,
                        "error": "Missing file_path or operation_id",
                    }
                return self._undo_file_delete(file_path, operation_id, False, request)
            else:
                logger.info(f"[DEBUG] 跳过不支持的操作类型: {operation_type}")
                return {"success": True, "action": "skipped_unsupported_operation"}
        except Exception as e:
            import logging

            logging.getLogger("mcp_toolkit.tools.version_management").error(
                f"[DEBUG] 回滚单操作异常: {e}"
            )
            return {"success": False, "error": str(e)}

    def _undo_file_edit(
        self,
        file_path: str,
        operation_id: str,
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """撤销文件编辑（复用 UndoTool 的逻辑），增加debug日志"""
        try:
            import logging

            logger = getattr(self, "_logger", None) or logging.getLogger(
                "mcp_toolkit.tools.version_management"
            )
            logger.info(
                f"[DEBUG] _undo_file_edit: file_path={file_path}, op_id={operation_id}, dry_run={dry_run}"
            )
            snapshot_info = self._find_snapshot(file_path, operation_id)
            logger.info(f"[DEBUG] _undo_file_edit: 查找快照结果: {snapshot_info}")
            if not snapshot_info:
                return {"success": False, "error": f"未找到文件 {file_path} 的快照"}
            if self.backup_dir is None:
                return {"success": False, "error": "Backup directory not initialized"}
            snapshot_path = os.path.join(
                self.backup_dir, f"{snapshot_info['snapshot_id']}.backup"
            )
            logger.info(f"[DEBUG] _undo_file_edit: snapshot_path={snapshot_path}")
            if not os.path.exists(snapshot_path):
                return {"success": False, "error": f"快照文件不存在: {snapshot_path}"}
            if not dry_run:
                shutil.copy2(snapshot_path, file_path)
            return {"success": True, "action": "file_restored"}
        except Exception as e:
            import logging

            logging.getLogger("mcp_toolkit.tools.version_management").error(
                f"[DEBUG] _undo_file_edit异常: {e}"
            )
            return {"success": False, "error": str(e)}

    def _undo_file_create(
        self,
        file_path: str,
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """撤销文件创建，增加debug日志"""
        try:
            import logging

            logger = getattr(self, "_logger", None) or logging.getLogger(
                "mcp_toolkit.tools.version_management"
            )
            logger.info(
                f"[DEBUG] _undo_file_create: file_path={file_path}, dry_run={dry_run}"
            )
            if not os.path.exists(file_path):
                logger.info(f"[DEBUG] _undo_file_create: 文件已不存在: {file_path}")
                return {"success": True, "action": "file_already_deleted"}
            if not dry_run:
                os.remove(file_path)
            return {"success": True, "action": "file_deleted"}
        except Exception as e:
            import logging

            logging.getLogger("mcp_toolkit.tools.version_management").error(
                f"[DEBUG] _undo_file_create异常: {e}"
            )
            return {"success": False, "error": str(e)}

    def _undo_file_delete(
        self,
        file_path: str,
        operation_id: str,
        dry_run: bool,
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """撤销文件删除，增加debug日志"""
        try:
            import logging

            logger = getattr(self, "_logger", None) or logging.getLogger(
                "mcp_toolkit.tools.version_management"
            )
            logger.info(
                f"[DEBUG] _undo_file_delete: file_path={file_path}, op_id={operation_id}, dry_run={dry_run}"
            )
            snapshot_info = self._find_snapshot(file_path, operation_id)
            logger.info(f"[DEBUG] _undo_file_delete: 查找快照结果: {snapshot_info}")
            if not snapshot_info:
                return {
                    "success": False,
                    "error": f"未找到文件 {file_path} 的删除前快照",
                }
            if self.backup_dir is None:
                return {"success": False, "error": "Backup directory not initialized"}
            snapshot_path = os.path.join(
                self.backup_dir, f"{snapshot_info['snapshot_id']}.backup"
            )
            logger.info(f"[DEBUG] _undo_file_delete: snapshot_path={snapshot_path}")
            if not os.path.exists(snapshot_path):
                return {"success": False, "error": f"快照文件不存在: {snapshot_path}"}
            if not dry_run:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                shutil.copy2(snapshot_path, file_path)
            return {"success": True, "action": "file_restored"}
        except Exception as e:
            import logging

            logging.getLogger("mcp_toolkit.tools.version_management").error(
                f"[DEBUG] _undo_file_delete异常: {e}"
            )
            return {"success": False, "error": str(e)}

    def _find_snapshot(
        self, file_path: str, operation_id: str
    ) -> Optional[Dict[str, Any]]:
        """查找快照信息（复用 UndoTool 的逻辑），增加debug日志"""
        try:
            import logging

            logger = getattr(self, "_logger", None) or logging.getLogger(
                "mcp_toolkit.tools.version_management"
            )
            logger.info(
                f"[DEBUG] _find_snapshot: file_path={file_path}, op_id={operation_id}"
            )
            if self.data_manager is None:
                return None
            results = self.data_manager.query_data(
                query=f"snapshot for {file_path}",
                data_type="file_snapshot",
                n_results=50,
            )
            if results and results.get("metadatas"):
                for metadata in results["metadatas"]:
                    logger.info(f"[DEBUG] _find_snapshot: 快照候选: {metadata}")
                    if (
                        isinstance(metadata, dict)
                        and metadata.get("file_path") == file_path
                        and metadata.get("operation_id") == operation_id
                    ):
                        logger.info(f"[DEBUG] _find_snapshot: 命中快照: {metadata}")
                        return metadata
            logger.info(
                f"[DEBUG] _find_snapshot: 未找到快照: file_path={file_path}, op_id={operation_id}"
            )
            return None
        except Exception as e:
            import logging

            logging.getLogger("mcp_toolkit.tools.version_management").error(
                f"[DEBUG] _find_snapshot异常: {e}"
            )
            return None

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class CheckpointTool(BaseVersionTool):
    """检查点管理工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="manage_checkpoint",
            description="管理版本检查点",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "list", "delete", "info"],
                        "description": "操作类型",
                    },
                    "checkpoint_name": {
                        "type": "string",
                        "description": "检查点名称（创建和删除时必需）",
                    },
                    "description": {
                        "type": "string",
                        "description": "检查点描述",
                    },
                    "include_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "包含的文件模式列表",
                    },
                    "exclude_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "排除的文件模式列表",
                    },
                    "auto_cleanup": {
                        "type": "boolean",
                        "description": "是否自动清理旧检查点",
                        "default": True,
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "是否包含详细元数据",
                        "default": False,
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行检查点管理操作"""
        start_time = time.time()
        params = request.parameters

        try:
            # 确保初始化
            self._ensure_initialized(request)

            action = params["action"]

            if action == "create":
                result = await self._create_checkpoint(params, request)
            elif action == "list":
                result = await self._list_checkpoints(params)
            elif action == "delete":
                result = await self._delete_checkpoint(params)
            elif action == "info":
                result = await self._get_checkpoint_info(params)
            else:
                return self._create_error_result(
                    "INVALID_ACTION", f"不支持的操作: {action}"
                )

            if not result["success"]:
                return self._create_error_result(
                    "CHECKPOINT_OPERATION_FAILED", result["error"]
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
            self._logger.exception("检查点管理操作执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    async def _create_checkpoint(
        self, params: Dict[str, Any], request: Optional[ToolExecutionRequest] = None
    ) -> Dict[str, Any]:
        """创建检查点（仅有内容变更时才创建，允许同名，存储patch），修复快照丢失和diff error"""
        import difflib
        import hashlib
        import json
        import mimetypes
        import os
        import time

        try:
            checkpoint_name = params.get("checkpoint_name")
            if not checkpoint_name:
                return {
                    "success": False,
                    "error": "创建检查点时必须提供 checkpoint_name",
                }
            description = params.get("description", "")
            include_files = params.get("include_files", [])
            exclude_files = params.get("exclude_files", [])
            auto_cleanup = params.get("auto_cleanup", True)
            checkpoint_id = f"checkpoint_{int(time.time())}_{hashlib.md5(checkpoint_name.encode(), usedforsecurity=False).hexdigest()[:8]}"
            project_state = self._analyze_project_state(
                include_files, exclude_files, request
            )
            # 路径基准统一为工作目录，所有相对路径都转为绝对路径
            work_dir = self._get_work_directory(request)
            all_files = project_state["files"]
            last_checkpoint = None
            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            results = self.data_manager.query_data(
                query="checkpoint", data_type="checkpoint", n_results=50
            )
            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []
                for metadata in sorted(
                    metadatas, key=lambda x: x.get("timestamp", 0), reverse=True
                ):
                    if not isinstance(metadata, dict):
                        continue
                    existing_checkpoint_id: Any = metadata.get("checkpoint_id")
                    if not isinstance(
                        existing_checkpoint_id, str
                    ) or await self._is_checkpoint_deleted(existing_checkpoint_id):
                        continue
                    try:
                        inc = json.loads(metadata.get("included_files_str", "[]"))
                        exc = json.loads(metadata.get("excluded_files_str", "[]"))
                    except (json.JSONDecodeError, ValueError):
                        inc, exc = [], []
                    if inc == include_files and exc == exclude_files:
                        last_checkpoint = metadata
                        break

            def is_text_file(path: str) -> bool:
                mime, _ = mimetypes.guess_type(path)
                if mime is None:
                    try:
                        with open(path, "rb") as f:
                            chunk = f.read(512)
                        if b"\0" in chunk:
                            return False
                        try:
                            chunk.decode("utf-8")
                            return True
                        except Exception:
                            return False
                    except Exception:
                        return False
                return mime.startswith("text") or mime in [
                    "application/json",
                    "application/xml",
                ]

            patch_map = {}
            has_changes = False
            snapshots_created = []
            # 先查找上一次快照
            last_snapshots = {}
            if last_checkpoint:
                last_id = last_checkpoint["checkpoint_id"]
                if self.data_manager is None:
                    raise ValueError("Data manager not initialized")
                snap_results = self.data_manager.query_data(
                    query="file snapshot", data_type="file_snapshot", n_results=1000
                )
                if snap_results and snap_results.get("metadatas"):
                    snaps = snap_results["metadatas"]
                    if isinstance(snaps, list) and len(snaps) > 0:
                        if isinstance(snaps[0], list):
                            snaps = snaps[0] if snaps[0] else []
                    for snap in snaps:
                        if not isinstance(snap, dict):
                            continue
                        if snap.get("operation_id") == last_id:
                            last_snapshots[snap.get("file_path")] = snap
            # 检查变更并创建快照
            for rel_path in all_files:
                # 统一将 rel_path 视为相对于当前工作目录的路径
                abs_path = os.path.abspath(os.path.join(work_dir, rel_path))
                prev_snap = last_snapshots.get(rel_path)
                changed = False

                # 如果没有上一个检查点，跳过这里的处理，在后面统一处理
                if last_checkpoint:
                    if prev_snap and os.path.exists(abs_path):
                        prev_hash = prev_snap.get("file_hash")
                        try:
                            now_hash = self._calculate_file_hash(abs_path)
                        except Exception:
                            now_hash = None
                        if now_hash != prev_hash:
                            changed = True
                    elif prev_snap is None and os.path.exists(abs_path):
                        changed = True
                    elif prev_snap and not os.path.exists(abs_path):
                        changed = True

                    if changed:
                        has_changes = True
                        snapshot_id = self._create_file_snapshot(
                            abs_path, checkpoint_id, rel_path=rel_path, request=request
                        )
                        if snapshot_id:
                            snapshots_created.append(
                                {"file_path": rel_path, "snapshot_id": snapshot_id}
                            )
                            patch_map[rel_path] = snapshot_id
            # 检查是否有被删除的文件
            if last_checkpoint:
                for rel_path in last_snapshots:
                    if rel_path not in all_files:
                        has_changes = True
                        # 只有快照实际存在才记录
                        snap_id = last_snapshots[rel_path].get("snapshot_id")
                        if snap_id:
                            patch_map[rel_path] = snap_id
            # 首次快照直接全部记录
            if not last_checkpoint:
                has_changes = True
                # 为所有文件创建快照
                for rel_path in all_files:
                    abs_path = os.path.abspath(os.path.join(work_dir, rel_path))
                    if os.path.exists(abs_path):
                        snapshot_id = self._create_file_snapshot(
                            abs_path, checkpoint_id, rel_path=rel_path, request=request
                        )
                        if snapshot_id:
                            snapshots_created.append(
                                {"file_path": rel_path, "snapshot_id": snapshot_id}
                            )
                            patch_map[rel_path] = snapshot_id
            if not has_changes:
                return {
                    "success": True,
                    "data": {"message": "无内容变更，不创建新检查点"},
                }
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "name": checkpoint_name,
                "description": description,
                "timestamp": time.time(),
                "created_by": "agent",
                "total_files": project_state["total_files"],
                "total_size": project_state["total_size"],
                "included_files_str": json.dumps(include_files),
                "excluded_files_str": json.dumps(exclude_files),
                "snapshots_count": len(snapshots_created),
                "patch_map_str": json.dumps(patch_map, ensure_ascii=False),
            }
            content = f"Checkpoint: {checkpoint_name}"
            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            self.data_manager.store_data(
                data_type="checkpoint", content=content, metadata=checkpoint_data
            )
            if auto_cleanup:
                await self._cleanup_old_checkpoints()
            return {
                "success": True,
                "data": {
                    "checkpoint_id": checkpoint_id,
                    "name": checkpoint_name,
                    "description": description,
                    "timestamp": checkpoint_data["timestamp"],
                    "files_included": len(snapshots_created),
                    "project_state": project_state,
                    "patch_map": patch_map,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _list_checkpoints(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出检查点"""
        try:
            include_metadata = params.get("include_metadata", False)

            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            results = self.data_manager.query_data(
                query="", data_type="checkpoint", n_results=100
            )

            checkpoints = []
            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                for metadata in metadatas:
                    if not isinstance(metadata, dict):
                        continue

                    checkpoint_info = {
                        "checkpoint_id": metadata.get("checkpoint_id"),
                        "name": metadata.get("name"),
                        "description": metadata.get("description", ""),
                        "timestamp": metadata.get("timestamp"),
                        "created_by": metadata.get("created_by", "unknown"),
                        "files_count": metadata.get("snapshots_count", 0),
                    }

                    if include_metadata:
                        checkpoint_info["total_files"] = metadata.get("total_files", 0)
                        checkpoint_info["total_size"] = metadata.get("total_size", 0)
                        # 解析 JSON 字符串
                        try:
                            checkpoint_info["included_files"] = json.loads(
                                metadata.get("included_files_str", "[]")
                            )
                            checkpoint_info["excluded_files"] = json.loads(
                                metadata.get("excluded_files_str", "[]")
                            )
                        except (json.JSONDecodeError, ValueError):
                            checkpoint_info["included_files"] = []
                            checkpoint_info["excluded_files"] = []

                    checkpoints.append(checkpoint_info)

            # 按时间排序
            checkpoints.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

            return {
                "success": True,
                "data": {
                    "total_checkpoints": len(checkpoints),
                    "checkpoints": checkpoints,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _delete_checkpoint(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除检查点"""
        try:
            checkpoint_name = params.get("checkpoint_name")
            if not checkpoint_name:
                return {
                    "success": False,
                    "error": "删除检查点时必须提供 checkpoint_name",
                }

            # 查找检查点
            checkpoint_info = await self._find_checkpoint_by_name(checkpoint_name)
            if not checkpoint_info:
                return {"success": False, "error": f"未找到检查点: {checkpoint_name}"}

            # 删除相关的快照文件（简化处理，因为快照信息存储方式已改变）
            deleted_snapshots = 0
            snapshots_count = checkpoint_info.get("snapshots_count", 0)

            # 尝试删除可能的快照文件
            checkpoint_id = checkpoint_info["checkpoint_id"]
            if self.backup_dir is None:
                raise ValueError("Backup directory not initialized")
            backup_files = [
                f
                for f in os.listdir(self.backup_dir)
                if f.startswith(f"snap_{checkpoint_id}")
            ]

            for backup_file in backup_files:
                backup_path = os.path.join(self.backup_dir, backup_file)
                try:
                    os.remove(backup_path)
                    deleted_snapshots += 1
                except Exception as e:
                    print(f"删除快照文件失败: {e}")

            # 标记检查点为已删除（由于 ChromaDB 不支持直接删除，我们添加删除标记）
            content = f"Checkpoint {checkpoint_name} deleted"
            metadata = {
                "checkpoint_id": checkpoint_info["checkpoint_id"],
                "action": "delete_marker",
                "timestamp": time.time(),
                "original_name": checkpoint_name,
            }

            if self.data_manager is None:
                raise ValueError("Data manager not initialized")
            self.data_manager.store_data(
                data_type="checkpoint_deletion", content=content, metadata=metadata
            )

            return {
                "success": True,
                "data": {
                    "checkpoint_name": checkpoint_name,
                    "checkpoint_id": checkpoint_info["checkpoint_id"],
                    "snapshots_deleted": deleted_snapshots,
                    "deletion_timestamp": time.time(),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_checkpoint_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取检查点详细信息"""
        try:
            checkpoint_name = params.get("checkpoint_name")
            if not checkpoint_name:
                return {
                    "success": False,
                    "error": "获取检查点信息时必须提供 checkpoint_name",
                }

            checkpoint_info = await self._find_checkpoint_by_name(checkpoint_name)
            if not checkpoint_info:
                return {"success": False, "error": f"未找到检查点: {checkpoint_name}"}

            # 解析 JSON 字符串
            try:
                included_files = json.loads(
                    checkpoint_info.get("included_files_str", "[]")
                )
                excluded_files = json.loads(
                    checkpoint_info.get("excluded_files_str", "[]")
                )
            except (json.JSONDecodeError, ValueError):
                included_files = []
                excluded_files = []

            return {
                "success": True,
                "data": {
                    "checkpoint_id": checkpoint_info["checkpoint_id"],
                    "name": checkpoint_info["name"],
                    "description": checkpoint_info.get("description", ""),
                    "timestamp": checkpoint_info.get("timestamp"),
                    "created_by": checkpoint_info.get("created_by", "unknown"),
                    "total_files": checkpoint_info.get("total_files", 0),
                    "total_size": checkpoint_info.get("total_size", 0),
                    "included_files": included_files,
                    "excluded_files": excluded_files,
                    "snapshots_count": checkpoint_info.get("snapshots_count", 0),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _find_checkpoint_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称查找检查点（返回最新未被删除的）"""
        try:
            if self.data_manager is None:
                return None
            results = self.data_manager.query_data(
                query="checkpoint", data_type="checkpoint", n_results=50
            )

            if results and results.get("metadatas"):
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                # 按时间倒序，优先返回最新的未被删除的同名检查点
                candidates = [
                    m
                    for m in metadatas
                    if isinstance(m, dict) and m.get("name") == name
                ]
                candidates.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                for metadata in candidates:
                    checkpoint_id = metadata.get("checkpoint_id")
                    if (
                        checkpoint_id is not None
                        and not await self._is_checkpoint_deleted(checkpoint_id)
                    ):
                        return metadata

            return None
        except Exception as e:
            self._logger.warning(f"查找检查点失败: {e}")
            return None

    async def _is_checkpoint_deleted(self, checkpoint_id: str) -> bool:
        """检查检查点是否已被删除"""
        try:
            if self.data_manager is None:
                return False
            results = self.data_manager.query_data(
                query=f"checkpoint {checkpoint_id} deleted",
                data_type="checkpoint_deletion",
                n_results=10,
            )

            if results and results.get("metadatas"):
                # 处理 ChromaDB 返回的数据结构
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    if isinstance(metadatas[0], list):
                        metadatas = metadatas[0] if metadatas[0] else []

                for metadata in metadatas:
                    if not isinstance(metadata, dict):
                        continue
                    if metadata.get("checkpoint_id") == checkpoint_id:
                        return True

            return False
        except Exception as e:
            return False

    def _analyze_project_state(
        self,
        include_files: List[str],
        exclude_files: List[str],
        request: Optional[ToolExecutionRequest] = None,
    ) -> Dict[str, Any]:
        """分析当前项目状态，自动排除记忆库目录，防止递归保存自身。遍历工作目录"""
        try:
            import os

            work_dir = self._get_work_directory(request)
            all_files = []

            # 自动排除记忆库相关目录，避免递归保存和重复创建
            memory_dirs = set()

            # 添加当前实例的备份目录
            if hasattr(self, "backup_dir") and self.backup_dir:
                memory_dirs.add(os.path.abspath(self.backup_dir))

            # 添加当前实例的数据库目录
            if (
                hasattr(self, "data_manager")
                and self.data_manager
                and hasattr(self.data_manager, "db_path")
            ):
                memory_dirs.add(os.path.abspath(self.data_manager.db_path))

            # 添加常见的记忆库目录名称（避免git相关指令误创建）
            common_memory_dirs = [
                "mcp_backups",
                "mcp_unified_db",
                ".git",
                "logs",
                "htmlcov",
                "__pycache__",
                "node_modules",
            ]
            for d in common_memory_dirs:
                memory_dirs.add(os.path.abspath(os.path.join(work_dir, d)))

            exclude_files = list(exclude_files) if exclude_files else []

            # 将记忆库目录添加到排除列表
            for mem_dir in memory_dirs:
                try:
                    rel_mem = os.path.relpath(mem_dir, work_dir)
                    # 避免添加重复的排除项
                    if rel_mem not in exclude_files and not rel_mem.startswith(".."):
                        exclude_files.append(rel_mem)
                except ValueError:
                    # 处理不同驱动器的情况（Windows）
                    continue

            for root, dirs, files in os.walk(work_dir):
                abs_root = os.path.abspath(root)
                if any(
                    abs_root == mem_dir or abs_root.startswith(mem_dir + os.sep)
                    for mem_dir in memory_dirs
                ):
                    dirs[:] = []
                    continue
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["__pycache__", "node_modules"]
                    and not any(
                        os.path.abspath(os.path.join(root, d)).startswith(mem_dir)
                        for mem_dir in memory_dirs
                    )
                ]

                for file in files:
                    if file.startswith("."):
                        continue

                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, work_dir)

                    abs_file_path = os.path.abspath(file_path)
                    if not abs_file_path.startswith(work_dir):
                        continue

                    if include_files:
                        if not any(pattern in rel_path for pattern in include_files):
                            continue

                    if exclude_files:
                        if any(pattern in rel_path for pattern in exclude_files):
                            continue

                    all_files.append(rel_path)

            total_size = 0
            file_types: Dict[str, int] = {}

            for file_path in all_files:
                try:
                    abs_path = os.path.abspath(os.path.join(work_dir, file_path))
                    size = os.path.getsize(abs_path)
                    total_size += size

                    ext = os.path.splitext(file_path)[1].lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
                except Exception:  # nosec B112
                    continue

            logger = getattr(self, "_logger", None)
            if logger:
                logger.info(
                    f"[DEBUG] _analyze_project_state: work_dir={work_dir}, all_files={all_files}"
                )
            else:
                print(
                    f"[DEBUG] _analyze_project_state: work_dir={work_dir}, all_files={all_files}"
                )

            return {
                "files": all_files,
                "total_files": len(all_files),
                "total_size": total_size,
                "file_types": file_types,
                "analysis_timestamp": time.time(),
            }

        except Exception as e:
            self._logger.warning(f"分析项目状态失败: {e}")
            return {
                "files": [],
                "total_files": 0,
                "total_size": 0,
                "file_types": {},
                "analysis_timestamp": time.time(),
                "error": str(e),
            }

    async def _cleanup_old_checkpoints(self) -> None:
        """清理旧检查点"""
        try:
            # 获取所有检查点
            if self.data_manager is None:
                return
            results = self.data_manager.query_data(
                query="checkpoint", data_type="checkpoint", n_results=200
            )

            if not results or not results.get("metadatas"):
                return

            # 处理 ChromaDB 返回的数据结构
            metadatas = results["metadatas"]
            if isinstance(metadatas, list) and len(metadatas) > 0:
                if isinstance(metadatas[0], list):
                    metadatas = metadatas[0] if metadatas[0] else []

            # 按时间排序，保留最新的检查点
            checkpoints = [m for m in metadatas if isinstance(m, dict)]
            checkpoints.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

            # 删除超过限制的旧检查点
            max_checkpoints = self.config.get("max_checkpoints", 20)
            if len(checkpoints) > max_checkpoints:
                old_checkpoints = checkpoints[max_checkpoints:]

                for checkpoint in old_checkpoints:
                    checkpoint_name = checkpoint.get("name")
                    if checkpoint_name:
                        await self._delete_checkpoint(
                            {"checkpoint_name": checkpoint_name}
                        )

        except Exception as e:
            print(f"清理旧检查点失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class VersionManagementTools:
    """版本管理工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有版本管理工具"""
        return [
            UndoTool(self.config),
            RollbackTool(self.config),
            CheckpointTool(self.config),
        ]
