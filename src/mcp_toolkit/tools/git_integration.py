"""
Git 集成工具集

提供精确的文件修改、差异分析、历史管理和冲突解决等 Git 相关功能。
解决当前只能整文件替换的核心问题，实现行级精确编辑。
"""

import hashlib
import json
import os
import re
import subprocess  # nosec B404
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from ..storage.unified_manager import UnifiedDataManager
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceEstimate,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
    ValidationError,
    ValidationResult,
)


class BaseGitTool(BaseTool):
    """Git 工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.data_manager = UnifiedDataManager(
            self.config.get("chromadb_path", "./mcp_unified_db")
        )
        self.git_timeout = self.config.get("git_timeout", 30)
        self.max_diff_size = self.config.get("max_diff_size", 1024 * 1024)  # 1MB

    def _run_git_command(
        self, cmd: List[str], cwd: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """执行 Git 命令"""
        try:
            result = subprocess.run(  # nosec B603
                ["git"] + cmd,
                cwd=cwd or os.getcwd(),
                capture_output=True,
                text=True,
                timeout=self.git_timeout,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Git command timeout"
        except Exception as e:
            return False, "", str(e)

    def _is_git_repository(self, path: Optional[str] = None) -> bool:
        """检查是否为 Git 仓库"""
        success, _, _ = self._run_git_command(["rev-parse", "--git-dir"], cwd=path)
        return success

    def _get_file_content(self, file_path: str) -> Optional[str]:
        """获取文件内容"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def _write_file_content(self, file_path: str, content: str) -> bool:
        """写入文件内容"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    def _create_backup(self, file_path: str) -> Optional[str]:
        """创建文件备份"""
        try:
            backup_path = f"{file_path}.backup.{int(time.time())}"
            content = self._get_file_content(file_path)
            if content is not None:
                self._write_file_content(backup_path, content)
                return backup_path
        except Exception:  # nosec B110
            pass
        return None


class GitDiffTool(BaseGitTool):
    """Git 差异分析工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_diff_analysis",
            description="智能分析文件或项目的 Git 差异，支持多层次分析",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "分析目标：文件路径、提交哈希或分支名",
                    },
                    "comparison_base": {
                        "type": "string",
                        "description": "比较基准：HEAD、特定提交或分支",
                        "default": "HEAD",
                    },
                    "analysis_level": {
                        "type": "string",
                        "enum": ["line", "semantic", "structural"],
                        "description": "分析级别",
                        "default": "semantic",
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "是否包含上下文信息",
                        "default": True,
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["unified", "side-by-side", "json", "mermaid"],
                        "description": "输出格式",
                        "default": "unified",
                    },
                },
                "required": ["target"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行差异分析"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params["target"]
            comparison_base = params.get("comparison_base", "HEAD")
            analysis_level = params.get("analysis_level", "semantic")
            include_context = params.get("include_context", True)
            output_format = params.get("output_format", "unified")

            # 获取工作目录
            working_dir = (
                request.execution_context.working_directory
                if request.execution_context
                else None
            )
            self._logger.info(f"Git diff analysis working directory: {working_dir}")

            # 检查是否为 Git 仓库
            if not self._is_git_repository(working_dir):
                return self._create_error_result(
                    "NOT_GIT_REPO", f"目录 {working_dir or 'current'} 不是 Git 仓库"
                )

            # 检查仓库状态
            repo_status = self._check_repository_status(working_dir)
            if repo_status["is_empty"]:
                return self._create_success_result(
                    {
                        "has_changes": False,
                        "message": "这是一个空的Git仓库，没有提交历史",
                        "diff_summary": {
                            "files_changed": 0,
                            "lines_added": 0,
                            "lines_deleted": 0,
                        },
                        "repository_status": repo_status,
                        "suggestion": "请先进行初始提交，然后再进行差异分析",
                    }
                )

            # 执行差异分析
            diff_result = self._analyze_diff(
                target, comparison_base, analysis_level, include_context, working_dir
            )

            if not diff_result["success"]:
                return self._create_error_result(
                    "DIFF_ANALYSIS_FAILED", diff_result["error"]
                )

            # 格式化输出
            formatted_output = self._format_diff_output(
                diff_result["data"], output_format
            )

            # 存储分析结果到 ChromaDB (异步，避免超时)
            try:
                self._store_diff_analysis(target, diff_result["data"])
            except Exception as e:
                self._logger.warning(f"ChromaDB存储失败，但不影响主要功能: {e}")

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                memory_used=len(str(formatted_output)) / 1024,  # KB 转 MB
                cpu_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(formatted_output)) / 1024 / 1024,  # 转换为 MB
                cpu_time_ms=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=1,
            )

            return self._create_success_result(formatted_output, metadata, resources)

        except Exception as e:
            self._logger.exception("Git 差异分析执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _analyze_diff(
        self,
        target: str,
        base: str,
        level: str,
        include_context: bool,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行差异分析"""
        try:
            # 智能处理比较基准
            resolved_base = self._resolve_comparison_base(base, cwd)
            if not resolved_base:
                return {
                    "success": True,
                    "data": {
                        "has_changes": False,
                        "message": f"无法解析比较基准 '{base}'，可能是新仓库或分支不存在",
                        "diff_summary": {
                            "files_changed": 0,
                            "lines_added": 0,
                            "lines_deleted": 0,
                        },
                        "suggestion": "尝试使用 'HEAD' 或具体的提交哈希作为比较基准",
                    },
                }

            # 获取 Git diff
            success, stdout, stderr = self._run_git_command(
                ["diff", resolved_base, "--", target], cwd=cwd
            )

            if not success:
                # 尝试更智能的错误处理
                if "bad revision" in stderr.lower():
                    return self._handle_bad_revision_error(base, target, cwd)
                elif "not a git repository" in stderr.lower():
                    return {"success": False, "error": "当前目录不是Git仓库"}
                else:
                    return {"success": False, "error": stderr}

            if not stdout.strip():
                return {
                    "success": True,
                    "data": {
                        "has_changes": False,
                        "message": "没有检测到变更",
                        "diff_summary": {
                            "files_changed": 0,
                            "lines_added": 0,
                            "lines_deleted": 0,
                        },
                    },
                }

            # 解析差异
            parsed_diff = self._parse_diff(stdout, level, include_context)

            return {"success": True, "data": parsed_diff}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_diff(
        self, diff_text: str, level: str, include_context: bool
    ) -> Dict[str, Any]:
        """解析差异文本"""
        lines = diff_text.split("\n")
        result: Dict[str, Any] = {
            "has_changes": True,
            "diff_summary": {"files_changed": 0, "lines_added": 0, "lines_deleted": 0},
            "file_changes": [],
            "raw_diff": diff_text if include_context else None,
        }

        current_file: Optional[Dict[str, Any]] = None
        current_hunk: Optional[Dict[str, Any]] = None

        for line in lines:
            if line.startswith("diff --git"):
                # 新文件开始
                if current_file:
                    result["file_changes"].append(current_file)

                file_path = (
                    line.split(" b/")[-1] if " b/" in line else line.split(" ")[-1]
                )
                current_file = {
                    "file_path": file_path,
                    "change_type": "modified",
                    "hunks": [],
                    "lines_added": 0,
                    "lines_deleted": 0,
                }
                result["diff_summary"]["files_changed"] += 1

            elif line.startswith("@@"):
                # 新的代码块
                if current_hunk and current_file:
                    current_file["hunks"].append(current_hunk)

                # 解析行号信息
                match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
                if match:
                    old_start, old_count, new_start, new_count = match.groups()
                    current_hunk = {
                        "old_start": int(old_start),
                        "old_count": int(old_count) if old_count else 1,
                        "new_start": int(new_start),
                        "new_count": int(new_count) if new_count else 1,
                        "changes": [],
                        "context": line if include_context else None,
                    }

            elif line.startswith("+") and not line.startswith("+++"):
                # 新增行
                if current_hunk:
                    current_hunk["changes"].append({"type": "add", "content": line[1:]})
                if current_file:
                    current_file["lines_added"] += 1
                    result["diff_summary"]["lines_added"] += 1

            elif line.startswith("-") and not line.startswith("---"):
                # 删除行
                if current_hunk:
                    current_hunk["changes"].append(
                        {"type": "delete", "content": line[1:]}
                    )
                if current_file:
                    current_file["lines_deleted"] += 1
                    result["diff_summary"]["lines_deleted"] += 1

            elif line.startswith(" ") and current_hunk:
                # 上下文行
                if include_context:
                    current_hunk["changes"].append(
                        {"type": "context", "content": line[1:]}
                    )

        # 添加最后的文件和代码块
        if current_hunk and current_file:
            current_file["hunks"].append(current_hunk)
        if current_file:
            result["file_changes"].append(current_file)

        # 语义分析增强
        if level == "semantic":
            result = self._enhance_semantic_analysis(result)

        return result

    def _enhance_semantic_analysis(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """增强语义分析"""
        for file_change in diff_data["file_changes"]:
            file_path = file_change["file_path"]

            # 分析变更类型
            semantic_impact = self._analyze_semantic_impact(file_change)
            file_change["semantic_impact"] = semantic_impact

            # 风险评估
            risk_level = self._assess_change_risk(file_change)
            file_change["risk_level"] = risk_level

        return diff_data

    def _analyze_semantic_impact(self, file_change: Dict[str, Any]) -> str:
        """分析语义影响"""
        # 简单的语义分析逻辑
        file_path = file_change["file_path"]

        if file_path.endswith((".py", ".js", ".ts", ".java")):
            # 检查是否有函数签名变更
            for hunk in file_change["hunks"]:
                for change in hunk["changes"]:
                    if change["type"] in ["add", "delete"]:
                        content = change["content"].strip()
                        if any(
                            keyword in content
                            for keyword in ["def ", "function ", "class ", "interface "]
                        ):
                            return "function_signature_change"
                        elif "import " in content or "from " in content:
                            return "import_change"

            return "code_content_change"

        elif file_path.endswith((".json", ".yaml", ".yml", ".toml")):
            return "configuration_change"

        elif file_path.endswith((".md", ".txt", ".rst")):
            return "documentation_change"

        return "file_content_change"

    def _assess_change_risk(self, file_change: Dict[str, Any]) -> str:
        """评估变更风险"""
        lines_changed = file_change["lines_added"] + file_change["lines_deleted"]

        if lines_changed > 100:
            return "high"
        elif lines_changed > 20:
            return "medium"
        else:
            return "low"

    def _format_diff_output(
        self, diff_data: Dict[str, Any], format_type: str
    ) -> Dict[str, Any]:
        """格式化差异输出"""
        if format_type == "json":
            return diff_data
        elif format_type == "unified":
            return self._format_unified_diff(diff_data)
        elif format_type == "side-by-side":
            return self._format_side_by_side_diff(diff_data)
        elif format_type == "mermaid":
            return self._format_mermaid_diff(diff_data)
        else:
            return diff_data

    def _format_unified_diff(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化为统一差异格式"""
        formatted = {
            "format": "unified",
            "summary": diff_data.get("diff_summary", {}),
            "has_changes": diff_data.get("has_changes", False),
            "changes": [],
        }

        # 检查是否有文件变更
        if not diff_data.get("has_changes", False) or "file_changes" not in diff_data:
            formatted["message"] = diff_data.get("message", "没有检测到变更")
            return formatted

        for file_change in diff_data["file_changes"]:
            file_formatted = {
                "file": file_change["file_path"],
                "type": file_change["change_type"],
                "hunks": [],
            }

            for hunk in file_change["hunks"]:
                hunk_formatted: Dict[str, Any] = {
                    "header": f"@@ -{hunk['old_start']},{hunk['old_count']} +{hunk['new_start']},{hunk['new_count']} @@",
                    "lines": [],
                }

                for change in hunk["changes"]:
                    prefix = {"add": "+", "delete": "-", "context": " "}[change["type"]]
                    hunk_formatted["lines"].append(f"{prefix}{change['content']}")

                file_formatted["hunks"].append(hunk_formatted)

            formatted["changes"].append(file_formatted)

        return formatted

    def _format_side_by_side_diff(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化为并排差异格式"""
        # 简化实现，实际可以更复杂
        result = {
            "format": "side-by-side",
            "summary": diff_data.get("diff_summary", {}),
            "has_changes": diff_data.get("has_changes", False),
            "note": "Side-by-side format not fully implemented yet",
            "data": diff_data,
        }

        if not diff_data.get("has_changes", False):
            result["message"] = diff_data.get("message", "没有检测到变更")

        return result

    def _format_mermaid_diff(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化为 Mermaid 图表格式"""
        # 检查是否有变更
        if not diff_data.get("has_changes", False) or "file_changes" not in diff_data:
            return {
                "format": "mermaid",
                "summary": diff_data.get("diff_summary", {}),
                "has_changes": False,
                "message": diff_data.get("message", "没有检测到变更"),
                "mermaid_code": "graph TD\n    A[没有变更] --> B[仓库状态正常]",
            }

        mermaid_code = "graph TD\n"

        for i, file_change in enumerate(diff_data["file_changes"]):
            file_node = f"F{i}[{file_change['file_path']}]"
            mermaid_code += f"    {file_node}\n"

            if file_change["lines_added"] > 0:
                add_node = f"A{i}[+{file_change['lines_added']} lines]"
                mermaid_code += f"    {file_node} --> {add_node}\n"
                mermaid_code += f"    style {add_node} fill:#90EE90\n"

            if file_change["lines_deleted"] > 0:
                del_node = f"D{i}[-{file_change['lines_deleted']} lines]"
                mermaid_code += f"    {file_node} --> {del_node}\n"
                mermaid_code += f"    style {del_node} fill:#FFB6C1\n"

        return {
            "format": "mermaid",
            "summary": diff_data["diff_summary"],
            "mermaid_code": mermaid_code,
        }

    def _store_diff_analysis(self, target: str, diff_data: Dict[str, Any]) -> None:
        """存储差异分析结果到 ChromaDB"""
        try:
            content = f"Git diff analysis for {target}"
            metadata = {
                "target": target,
                "analysis_timestamp": time.time(),
                "files_changed": diff_data["diff_summary"]["files_changed"],
                "lines_added": diff_data["diff_summary"]["lines_added"],
                "lines_deleted": diff_data["diff_summary"]["lines_deleted"],
                "has_changes": diff_data["has_changes"],
            }

            self.data_manager.store_data(
                data_type="git_diff_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            self._logger.warning(f"Failed to store diff analysis: {e}")

    def _resolve_comparison_base(
        self, base: str, cwd: Optional[str] = None
    ) -> Optional[str]:
        """智能解析比较基准"""
        # 1. 检查是否有提交
        success, _, _ = self._run_git_command(["rev-parse", "HEAD"], cwd=cwd)
        if not success:
            # 没有提交的新仓库
            return None

        # 2. 如果是HEAD，直接返回
        if base == "HEAD":
            return "HEAD"

        # 3. 检查指定的分支/提交是否存在
        success, _, _ = self._run_git_command(["rev-parse", "--verify", base], cwd=cwd)
        if success:
            return base

        # 4. 如果是origin/xxx格式，尝试找到对应的本地分支
        if base.startswith("origin/"):
            local_branch = base.replace("origin/", "")
            success, _, _ = self._run_git_command(
                ["rev-parse", "--verify", local_branch], cwd=cwd
            )
            if success:
                return local_branch

        # 5. 尝试获取默认分支
        success, stdout, _ = self._run_git_command(
            ["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=cwd
        )
        if success and stdout.strip():
            default_branch = stdout.strip().replace("refs/remotes/origin/", "")
            success, _, _ = self._run_git_command(
                ["rev-parse", "--verify", default_branch], cwd=cwd
            )
            if success:
                return default_branch

        # 6. 尝试常见的分支名
        common_branches = ["main", "master", "develop", "dev"]
        for branch in common_branches:
            success, _, _ = self._run_git_command(
                ["rev-parse", "--verify", branch], cwd=cwd
            )
            if success:
                return branch

        # 7. 最后尝试HEAD
        return "HEAD"

    def _check_repository_status(self, cwd: Optional[str] = None) -> Dict[str, Any]:
        """检查仓库状态"""
        status: Dict[str, Any] = {
            "is_empty": False,
            "has_commits": False,
            "current_branch": None,
            "remote_branches": [],
            "untracked_files": [],
            "staged_files": [],
            "modified_files": [],
        }

        # 检查是否有提交
        success, _, _ = self._run_git_command(["rev-parse", "HEAD"], cwd=cwd)
        status["has_commits"] = success
        status["is_empty"] = not success

        # 获取当前分支
        success, stdout, _ = self._run_git_command(
            ["branch", "--show-current"], cwd=cwd
        )
        if success and stdout.strip():
            status["current_branch"] = stdout.strip()

        # 获取远程分支
        success, stdout, _ = self._run_git_command(["branch", "-r"], cwd=cwd)
        if success:
            status["remote_branches"] = [
                line.strip()
                for line in stdout.split("\n")
                if line.strip() and not line.strip().startswith("origin/HEAD")
            ]

        # 获取文件状态
        success, stdout, _ = self._run_git_command(["status", "--porcelain"], cwd=cwd)
        if success:
            for line in stdout.split("\n"):
                if not line.strip():
                    continue
                status_code = line[:2]
                filename = line[3:]

                if status_code.startswith("??"):
                    status["untracked_files"].append(filename)
                elif status_code[0] in "MADRC":
                    status["staged_files"].append(filename)
                elif status_code[1] in "MD":
                    status["modified_files"].append(filename)

        return status

    def _handle_bad_revision_error(
        self, base: str, target: str, cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理bad revision错误"""
        # 获取可用的分支和标签
        branches_success, branches_out, _ = self._run_git_command(
            ["branch", "-a"], cwd=cwd
        )
        tags_success, tags_out, _ = self._run_git_command(["tag", "-l"], cwd=cwd)

        available_refs = []
        if branches_success:
            available_refs.extend(
                [
                    line.strip().replace("* ", "").replace("remotes/", "")
                    for line in branches_out.split("\n")
                    if line.strip()
                ]
            )
        if tags_success:
            available_refs.extend(
                [line.strip() for line in tags_out.split("\n") if line.strip()]
            )

        return {
            "success": False,
            "error": f"分支或提交 '{base}' 不存在",
            "available_refs": available_refs[:10],  # 只显示前10个
            "suggestion": f"请使用有效的分支名、标签或提交哈希。可用的引用: {', '.join(available_refs[:5])}",
        }

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class GitPatchTool(BaseGitTool):
    """Git 精确补丁应用工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_apply_patch",
            description="精确应用代码补丁到指定文件，支持行级编辑",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "目标文件路径",
                    },
                    "patch_operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "enum": ["insert", "delete", "replace"],
                                    "description": "补丁操作类型",
                                },
                                "line_number": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "description": "目标行号",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "操作内容",
                                },
                                "context_lines": {
                                    "type": "integer",
                                    "default": 3,
                                    "description": "上下文行数",
                                },
                            },
                            "required": ["operation", "line_number"],
                        },
                        "description": "补丁操作列表",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "是否只进行预检查",
                        "default": False,
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "是否创建备份",
                        "default": True,
                    },
                    "verify_context": {
                        "type": "boolean",
                        "description": "是否验证上下文匹配",
                        "default": True,
                    },
                },
                "required": ["file_path", "patch_operations"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行补丁应用"""
        start_time = time.time()
        params = request.parameters

        try:
            file_path = params["file_path"]
            patch_operations = params["patch_operations"]
            dry_run = params.get("dry_run", False)
            create_backup = params.get("create_backup", True)
            verify_context = params.get("verify_context", True)

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return self._create_error_result(
                    "FILE_NOT_FOUND", f"文件不存在: {file_path}"
                )

            # 读取原始文件内容
            original_content = self._get_file_content(file_path)
            if original_content is None:
                return self._create_error_result(
                    "READ_ERROR", f"无法读取文件: {file_path}"
                )

            # 验证补丁操作
            validation_result = self._validate_patch_operations(
                original_content, patch_operations, verify_context
            )

            if not validation_result["valid"]:
                return self._create_error_result(
                    "PATCH_VALIDATION_FAILED", validation_result["error"]
                )

            # 应用补丁
            patch_result = self._apply_patch_operations(
                original_content, patch_operations, dry_run
            )

            if not patch_result["success"]:
                return self._create_error_result(
                    "PATCH_APPLICATION_FAILED", patch_result["error"]
                )

            result_data = {
                "file_path": file_path,
                "dry_run": dry_run,
                "operations_applied": len(patch_operations),
                "backup_created": None,
                "changes_summary": patch_result["summary"],
            }

            # 如果不是预检查，实际写入文件
            if not dry_run:
                # 创建备份
                backup_path = None
                if create_backup:
                    backup_path = self._create_backup(file_path)
                    result_data["backup_created"] = backup_path

                # 写入修改后的内容
                if not self._write_file_content(file_path, patch_result["content"]):
                    return self._create_error_result(
                        "WRITE_ERROR", f"无法写入文件: {file_path}"
                    )

                # 存储补丁应用记录
                self._store_patch_application(file_path, patch_operations, patch_result)

            else:
                result_data["preview_content"] = patch_result["content"]

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                memory_used=len(patch_result["content"]) / 1024 / 1024,  # 转换为 MB
                cpu_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=2 if not dry_run else 1,
            )

            resources = ResourceUsage(
                memory_mb=len(patch_result["content"]) / 1024 / 1024,  # 转换为 MB
                cpu_time_ms=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=2 if not dry_run else 1,
            )

            return self._create_success_result(result_data, metadata, resources)

        except Exception as e:
            self._logger.exception("Git 补丁应用执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _validate_patch_operations(
        self, content: str, operations: List[Dict[str, Any]], verify_context: bool
    ) -> Dict[str, Any]:
        """验证补丁操作"""
        lines = content.split("\n")
        total_lines = len(lines)

        for i, op in enumerate(operations):
            operation = op["operation"]
            line_number = op["line_number"]

            # 检查行号范围
            if operation in ["delete", "replace"]:
                if line_number > total_lines:
                    return {
                        "valid": False,
                        "error": f"操作 {i+1}: 行号 {line_number} 超出文件范围 (总行数: {total_lines})",
                    }
            elif operation == "insert":
                if line_number > total_lines + 1:
                    return {
                        "valid": False,
                        "error": f"操作 {i+1}: 插入行号 {line_number} 超出有效范围",
                    }

            # 上下文验证（如果启用）
            if verify_context and "expected_context" in op:
                context_lines = op.get("context_lines", 3)
                if not self._verify_context_match(
                    lines, line_number, op["expected_context"], context_lines
                ):
                    return {
                        "valid": False,
                        "error": f"操作 {i+1}: 上下文不匹配，行号 {line_number} 附近的内容已发生变化",
                    }

        return {"valid": True}

    def _verify_context_match(
        self,
        lines: List[str],
        line_number: int,
        expected_context: str,
        context_lines: int,
    ) -> bool:
        """验证上下文匹配"""
        start_line = max(0, line_number - context_lines - 1)
        end_line = min(len(lines), line_number + context_lines)

        actual_context = "\n".join(lines[start_line:end_line])
        return expected_context.strip() in actual_context

    def _apply_patch_operations(
        self, content: str, operations: List[Dict[str, Any]], dry_run: bool
    ) -> Dict[str, Any]:
        """应用补丁操作"""
        try:
            lines = content.split("\n")
            changes_summary = {
                "lines_inserted": 0,
                "lines_deleted": 0,
                "lines_modified": 0,
            }

            # 按行号排序操作（从后往前处理，避免行号偏移）
            sorted_operations = sorted(
                operations, key=lambda x: x["line_number"], reverse=True
            )

            for op in sorted_operations:
                operation = op["operation"]
                line_number = op["line_number"]
                content_text = op.get("content", "")

                if operation == "insert":
                    # 插入行
                    if line_number <= len(lines):
                        lines.insert(line_number - 1, content_text)
                        changes_summary["lines_inserted"] += 1
                    else:
                        lines.append(content_text)
                        changes_summary["lines_inserted"] += 1

                elif operation == "delete":
                    # 删除行
                    if 1 <= line_number <= len(lines):
                        lines.pop(line_number - 1)
                        changes_summary["lines_deleted"] += 1

                elif operation == "replace":
                    # 替换行
                    if 1 <= line_number <= len(lines):
                        lines[line_number - 1] = content_text
                        changes_summary["lines_modified"] += 1

            modified_content = "\n".join(lines)

            return {
                "success": True,
                "content": modified_content,
                "summary": changes_summary,
            }

        except Exception as e:
            return {"success": False, "error": f"应用补丁时发生错误: {str(e)}"}

    def _store_patch_application(
        self, file_path: str, operations: List[Dict[str, Any]], result: Dict[str, Any]
    ) -> None:
        """存储补丁应用记录"""
        try:
            content = f"Applied patch to {file_path}"
            metadata = {
                "file_path": file_path,
                "application_timestamp": time.time(),
                "operations_count": len(operations),
                "operations": operations,
                "changes_summary": result["summary"],
            }

            self.data_manager.store_data(
                data_type="git_patch_application", content=content, metadata=metadata
            )
        except Exception as e:
            self._logger.warning(f"Failed to store patch application: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class GitHistoryTool(BaseGitTool):
    """Git 变更历史管理工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_history_analysis",
            description="分析 Git 历史和变更追踪",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "分析目标：文件路径、函数名或项目路径",
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "since": {
                                "type": "string",
                                "description": "开始时间或提交",
                            },
                            "until": {
                                "type": "string",
                                "description": "结束时间或提交",
                            },
                        },
                        "description": "时间范围",
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": [
                            "commits",
                            "file_changes",
                            "function_evolution",
                            "author_stats",
                        ],
                        "description": "分析类型",
                        "default": "commits",
                    },
                    "include_diffs": {
                        "type": "boolean",
                        "description": "是否包含详细差异",
                        "default": False,
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 50,
                        "description": "最大结果数量",
                    },
                },
                "required": ["target"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行历史分析"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params["target"]
            time_range = params.get("time_range", {})
            analysis_type = params.get("analysis_type", "commits")
            include_diffs = params.get("include_diffs", False)
            max_results = params.get("max_results", 50)

            # 获取工作目录
            working_dir = (
                request.execution_context.working_directory
                if request.execution_context
                else None
            )
            self._logger.info(f"Git history analysis working directory: {working_dir}")

            # 检查是否为 Git 仓库
            if not self._is_git_repository(working_dir):
                return self._create_error_result(
                    "NOT_GIT_REPO", f"目录 {working_dir or 'current'} 不是 Git 仓库"
                )

            # 执行历史分析
            history_result = self._analyze_history(
                target, time_range, analysis_type, include_diffs, max_results
            )

            if not history_result["success"]:
                return self._create_error_result(
                    "HISTORY_ANALYSIS_FAILED", history_result["error"]
                )

            # 存储分析结果
            self._store_history_analysis(target, history_result["data"])

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                memory_used=len(str(history_result["data"])) / 1024 / 1024,  # 转换为 MB
                cpu_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(history_result["data"])) / 1024 / 1024,  # 转换为 MB
                cpu_time_ms=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=1,
            )

            return self._create_success_result(
                history_result["data"], metadata, resources
            )

        except Exception as e:
            self._logger.exception("Git 历史分析执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _analyze_history(
        self,
        target: str,
        time_range: Dict[str, str],
        analysis_type: str,
        include_diffs: bool,
        max_results: int,
    ) -> Dict[str, Any]:
        """执行历史分析"""
        try:
            if analysis_type == "commits":
                return self._analyze_commits(
                    target, time_range, include_diffs, max_results
                )
            elif analysis_type == "file_changes":
                return self._analyze_file_changes(target, time_range, max_results)
            elif analysis_type == "function_evolution":
                return self._analyze_function_evolution(target, time_range, max_results)
            elif analysis_type == "author_stats":
                return self._analyze_author_stats(target, time_range)
            else:
                return {"success": False, "error": f"不支持的分析类型: {analysis_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_commits(
        self,
        target: str,
        time_range: Dict[str, str],
        include_diffs: bool,
        max_results: int,
    ) -> Dict[str, Any]:
        """分析提交历史"""
        cmd = [
            "log",
            f"-{max_results}",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso",
        ]

        # 添加时间范围
        if time_range.get("since"):
            cmd.append(f"--since={time_range['since']}")
        if time_range.get("until"):
            cmd.append(f"--until={time_range['until']}")

        # 添加目标文件或路径
        if target != ".":
            cmd.extend(["--", target])

        success, stdout, stderr = self._run_git_command(cmd)

        if not success:
            return {"success": False, "error": stderr}

        commits = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split("|", 4)
                if len(parts) == 5:
                    commit_hash, author_name, author_email, date, message = parts
                    commit_data = {
                        "hash": commit_hash,
                        "author": {"name": author_name, "email": author_email},
                        "date": date,
                        "message": message,
                    }

                    # 如果需要包含差异
                    if include_diffs:
                        diff_success, diff_stdout, _ = self._run_git_command(
                            ["show", "--pretty=format:", commit_hash, "--", target]
                        )
                        if diff_success:
                            commit_data["diff"] = diff_stdout

                    commits.append(commit_data)

        return {
            "success": True,
            "data": {
                "analysis_type": "commits",
                "target": target,
                "total_commits": len(commits),
                "commits": commits,
            },
        }

    def _analyze_file_changes(
        self, target: str, time_range: Dict[str, str], max_results: int
    ) -> Dict[str, Any]:
        """分析文件变更"""
        cmd = [
            "log",
            f"-{max_results}",
            "--pretty=format:%H|%ad",
            "--date=iso",
            "--name-status",
        ]

        if time_range.get("since"):
            cmd.append(f"--since={time_range['since']}")
        if time_range.get("until"):
            cmd.append(f"--until={time_range['until']}")

        if target != ".":
            cmd.extend(["--", target])

        success, stdout, stderr = self._run_git_command(cmd)

        if not success:
            return {"success": False, "error": stderr}

        changes: List[Dict[str, Any]] = []
        current_commit: Optional[Dict[str, Any]] = None

        for line in stdout.strip().split("\n"):
            if "|" in line:
                # 提交信息行
                commit_hash, date = line.split("|", 1)
                current_commit = {"hash": commit_hash, "date": date, "files": []}
                changes.append(current_commit)
            elif line.strip() and current_commit:
                # 文件变更行
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    status, file_path = parts[0], parts[1]
                    current_commit["files"].append(
                        {"status": status, "path": file_path}
                    )

        return {
            "success": True,
            "data": {
                "analysis_type": "file_changes",
                "target": target,
                "total_changes": len(changes),
                "changes": changes,
            },
        }

    def _analyze_function_evolution(
        self, target: str, time_range: Dict[str, str], max_results: int
    ) -> Dict[str, Any]:
        """分析函数演化（简化实现）"""
        # 这是一个简化的实现，实际可以更复杂
        return {
            "success": True,
            "data": {
                "analysis_type": "function_evolution",
                "target": target,
                "note": "Function evolution analysis not fully implemented yet",
                "suggestion": "Use commits or file_changes analysis for detailed history",
            },
        }

    def _analyze_author_stats(
        self, target: str, time_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """分析作者统计"""
        cmd = ["shortlog", "-sn"]

        if time_range.get("since"):
            cmd.append(f"--since={time_range['since']}")
        if time_range.get("until"):
            cmd.append(f"--until={time_range['until']}")

        if target != ".":
            cmd.extend(["--", target])

        success, stdout, stderr = self._run_git_command(cmd)

        if not success:
            return {"success": False, "error": stderr}

        authors = []
        for line in stdout.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t", 1)
                if len(parts) == 2:
                    commit_count, author_name = parts
                    authors.append({"name": author_name, "commits": int(commit_count)})

        return {
            "success": True,
            "data": {
                "analysis_type": "author_stats",
                "target": target,
                "total_authors": len(authors),
                "authors": authors,
            },
        }

    def _store_history_analysis(self, target: str, data: Dict[str, Any]) -> None:
        """存储历史分析结果"""
        try:
            content = f"Git history analysis for {target}"
            metadata = {
                "target": target,
                "analysis_type": data["analysis_type"],
                "analysis_timestamp": time.time(),
                "total_results": data.get("total_commits")
                or data.get("total_changes")
                or data.get("total_authors", 0),
            }

            self.data_manager.store_data(
                data_type="git_history_analysis", content=content, metadata=metadata
            )
        except Exception as e:
            self._logger.warning(f"Failed to store history analysis: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class GitConflictTool(BaseGitTool):
    """Git 冲突解决助手工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_conflict_check",
            description="检测和分析潜在的 Git 合并冲突",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "检查目标：文件路径或分支名",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "基准分支",
                        "default": "main",
                    },
                    "check_type": {
                        "type": "string",
                        "enum": ["potential", "existing", "resolution"],
                        "description": "检查类型",
                        "default": "potential",
                    },
                    "provide_suggestions": {
                        "type": "boolean",
                        "description": "是否提供解决建议",
                        "default": True,
                    },
                },
                "required": ["target"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行冲突检查"""
        start_time = time.time()
        params = request.parameters

        try:
            target = params["target"]
            base_branch = params.get("base_branch", "main")
            check_type = params.get("check_type", "potential")
            provide_suggestions = params.get("provide_suggestions", True)

            # 检查是否为 Git 仓库
            if not self._is_git_repository():
                return self._create_error_result(
                    "NOT_GIT_REPO", "当前目录不是 Git 仓库"
                )

            # 执行冲突检查
            conflict_result = self._check_conflicts(
                target, base_branch, check_type, provide_suggestions
            )

            if not conflict_result["success"]:
                return self._create_error_result(
                    "CONFLICT_CHECK_FAILED", conflict_result["error"]
                )

            # 存储检查结果
            self._store_conflict_check(target, conflict_result["data"])

            # 创建执行元数据
            metadata = ExecutionMetadata(
                execution_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                memory_used=len(str(conflict_result["data"]))
                / 1024
                / 1024,  # 转换为 MB
                cpu_time=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(str(conflict_result["data"])) / 1024 / 1024,  # 转换为 MB
                cpu_time_ms=(time.time() - start_time) * 1000,  # 转换为毫秒
                io_operations=1,
            )

            return self._create_success_result(
                conflict_result["data"], metadata, resources
            )

        except Exception as e:
            self._logger.exception("Git 冲突检查执行异常")
            return self._create_error_result("EXECUTION_ERROR", f"执行异常: {str(e)}")

    def _check_conflicts(
        self, target: str, base_branch: str, check_type: str, provide_suggestions: bool
    ) -> Dict[str, Any]:
        """执行冲突检查"""
        try:
            if check_type == "potential":
                return self._check_potential_conflicts(
                    target, base_branch, provide_suggestions
                )
            elif check_type == "existing":
                return self._check_existing_conflicts(target, provide_suggestions)
            elif check_type == "resolution":
                return self._suggest_conflict_resolution(target)
            else:
                return {"success": False, "error": f"不支持的检查类型: {check_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _check_potential_conflicts(
        self, target: str, base_branch: str, provide_suggestions: bool
    ) -> Dict[str, Any]:
        """检查潜在冲突"""
        # 获取当前分支
        success, current_branch, _ = self._run_git_command(["branch", "--show-current"])
        if not success:
            return {"success": False, "error": "无法获取当前分支"}

        current_branch = current_branch.strip()

        # 比较两个分支的差异
        success, diff_output, stderr = self._run_git_command(
            ["diff", f"{base_branch}...{current_branch}", "--", target]
        )

        if not success:
            return {"success": False, "error": stderr}

        # 分析潜在冲突
        potential_conflicts = self._analyze_potential_conflicts(diff_output, target)

        result = {
            "check_type": "potential",
            "target": target,
            "base_branch": base_branch,
            "current_branch": current_branch,
            "has_potential_conflicts": len(potential_conflicts) > 0,
            "conflicts": potential_conflicts,
        }

        if provide_suggestions and potential_conflicts:
            result["suggestions"] = self._generate_conflict_suggestions(
                potential_conflicts
            )

        return {"success": True, "data": result}

    def _check_existing_conflicts(
        self, target: str, provide_suggestions: bool
    ) -> Dict[str, Any]:
        """检查现有冲突"""
        # 检查是否有未解决的冲突
        success, status_output, _ = self._run_git_command(["status", "--porcelain"])

        if not success:
            return {"success": False, "error": "无法获取 Git 状态"}

        conflicts = []
        for line in status_output.split("\n"):
            if (
                line.startswith("UU ")
                or line.startswith("AA ")
                or line.startswith("DD ")
            ):
                file_path = line[3:].strip()
                if target == "." or file_path == target:
                    conflicts.append(
                        {
                            "file": file_path,
                            "status": line[:2],
                            "type": "merge_conflict",
                        }
                    )

        result = {
            "check_type": "existing",
            "target": target,
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
        }

        if provide_suggestions and conflicts:
            result["suggestions"] = self._generate_resolution_suggestions(conflicts)

        return {"success": True, "data": result}

    def _suggest_conflict_resolution(self, target: str) -> Dict[str, Any]:
        """建议冲突解决方案"""
        # 简化实现
        return {
            "success": True,
            "data": {
                "check_type": "resolution",
                "target": target,
                "general_suggestions": [
                    "使用 git status 查看冲突文件",
                    "手动编辑冲突文件，解决冲突标记",
                    "使用 git add 标记冲突已解决",
                    "使用 git commit 完成合并",
                ],
                "note": "具体的冲突解决需要根据实际情况进行",
            },
        }

    def _analyze_potential_conflicts(
        self, diff_output: str, target: str
    ) -> List[Dict[str, Any]]:
        """分析潜在冲突"""
        conflicts: List[Dict[str, Any]] = []

        if not diff_output.strip():
            return conflicts

        # 简单的冲突检测逻辑
        lines = diff_output.split("\n")
        current_file = None

        for line in lines:
            if line.startswith("diff --git"):
                current_file = line.split(" b/")[-1] if " b/" in line else target
            elif line.startswith("@@"):
                # 检测到修改区域，可能存在冲突
                if current_file:
                    conflicts.append(
                        {
                            "file": current_file,
                            "type": "modification_overlap",
                            "description": "两个分支都修改了相同区域",
                            "line_info": line,
                        }
                    )

        return conflicts

    def _generate_conflict_suggestions(
        self, conflicts: List[Dict[str, Any]]
    ) -> List[str]:
        """生成冲突解决建议"""
        suggestions = []

        for conflict in conflicts:
            if conflict["type"] == "modification_overlap":
                suggestions.append(
                    f"文件 {conflict['file']} 存在修改重叠，建议仔细检查合并结果"
                )

        suggestions.extend(
            [
                "在合并前创建备份分支",
                "使用三方合并工具辅助解决冲突",
                "与团队成员沟通确认修改意图",
            ]
        )

        return suggestions

    def _generate_resolution_suggestions(
        self, conflicts: List[Dict[str, Any]]
    ) -> List[str]:
        """生成解决方案建议"""
        suggestions = []

        for conflict in conflicts:
            suggestions.append(f"解决文件 {conflict['file']} 中的冲突标记")

        suggestions.extend(
            [
                "使用编辑器搜索 <<<<<<< 标记定位冲突",
                "保留需要的代码，删除冲突标记",
                "测试修改后的代码确保功能正常",
            ]
        )

        return suggestions

    def _store_conflict_check(self, target: str, data: Dict[str, Any]) -> None:
        """存储冲突检查结果"""
        try:
            content = f"Git conflict check for {target}"
            metadata = {
                "target": target,
                "check_type": data["check_type"],
                "check_timestamp": time.time(),
                "has_conflicts": data.get("has_conflicts")
                or data.get("has_potential_conflicts", False),
                "conflicts_count": len(data.get("conflicts", [])),
            }

            self.data_manager.store_data(
                data_type="git_conflict_check", content=content, metadata=metadata
            )
        except Exception as e:
            self._logger.warning(f"Failed to store conflict check: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class GitIntegrationTools:
    """Git 集成工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有 Git 集成工具"""
        return [
            GitDiffTool(self.config),
            GitPatchTool(self.config),
            GitHistoryTool(self.config),
            GitConflictTool(self.config),
        ]
