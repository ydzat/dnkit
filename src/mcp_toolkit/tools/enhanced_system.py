"""
增强的系统工具集

基于 ChromaDB 统一存储的系统工具，支持进程管理、系统信息获取等功能。
扩展现有的系统工具，添加 ChromaDB 集成。
"""

import json
import platform
import subprocess  # nosec B404
import time
from typing import Any, Dict, List, Optional

import psutil

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from ..storage.unified_manager import UnifiedDataManager
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
    ValidationError,
    ValidationResult,
)


class SystemInfoTool(BaseTool):
    """系统信息获取工具 - 支持 ChromaDB 存储"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()
        self.auto_store = self.config.get("auto_store_to_chromadb", True)

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_system_info",
            description="获取系统信息并可选择存储到 ChromaDB",
            parameters={
                "type": "object",
                "properties": {
                    "include_processes": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否包含进程信息",
                    },
                    "include_network": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否包含网络信息",
                    },
                    "include_disk": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否包含磁盘信息",
                    },
                    "store_to_chromadb": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否将信息存储到 ChromaDB",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行系统信息获取"""
        params = request.parameters
        include_processes = params.get("include_processes", False)
        include_network = params.get("include_network", False)
        include_disk = params.get("include_disk", True)
        store_to_chromadb = params.get("store_to_chromadb", True)

        try:
            start_time = time.time()

            # 基础系统信息
            system_info: Dict[str, Any] = {
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "architecture": platform.architecture(),
                    "hostname": platform.node(),
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "count_logical": psutil.cpu_count(logical=True),
                    "usage_percent": psutil.cpu_percent(interval=1),
                    "frequency": (
                        psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                    ),
                },
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "used": psutil.virtual_memory().used,
                    "percentage": psutil.virtual_memory().percent,
                },
                "timestamp": time.time(),
            }

            # 磁盘信息
            if include_disk:
                disk_info = []
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_info.append(
                            {
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "fstype": partition.fstype,
                                "total": usage.total,
                                "used": usage.used,
                                "free": usage.free,
                                "percentage": (usage.used / usage.total) * 100,
                            }
                        )
                    except PermissionError:
                        continue
                system_info["disk"] = disk_info

            # 网络信息
            if include_network:
                network_info: Dict[str, Any] = {
                    "interfaces": {},
                    "connections": (
                        len(psutil.net_connections())
                        if hasattr(psutil, "net_connections")
                        else 0
                    ),
                }
                for interface, addrs in psutil.net_if_addrs().items():
                    network_info["interfaces"][interface] = [
                        {
                            "family": addr.family.name,
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast,
                        }
                        for addr in addrs
                    ]
                system_info["network"] = network_info

            # 进程信息
            if include_processes:
                processes = []
                for proc in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent"]
                ):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                system_info["processes"] = sorted(
                    processes, key=lambda x: x.get("cpu_percent", 0), reverse=True
                )[:20]

            # 存储到 ChromaDB
            if store_to_chromadb and self.auto_store:
                try:
                    # 创建可搜索的文本内容
                    searchable_content = f"""
                    系统信息报告
                    操作系统: {system_info['platform']['system']} {system_info['platform']['release']}
                    主机名: {system_info['platform']['hostname']}
                    处理器: {system_info['platform']['processor']}
                    CPU核心数: {system_info['cpu']['count']}
                    CPU使用率: {system_info['cpu']['usage_percent']}%
                    内存总量: {system_info['memory']['total'] / 1024 / 1024 / 1024:.2f} GB
                    内存使用率: {system_info['memory']['percentage']}%
                    """

                    data_id = f"system_info_{int(time.time())}"

                    metadata: Dict[str, Any] = {
                        "info_type": "system_info",
                        "hostname": system_info["platform"]["hostname"],
                        "os_system": system_info["platform"]["system"],
                        "cpu_count": system_info["cpu"]["count"],
                        "memory_total_gb": system_info["memory"]["total"]
                        / 1024
                        / 1024
                        / 1024,
                        "timestamp": system_info["timestamp"],
                    }

                    stored_id = self.data_manager.store_data(
                        data_type="system_info",
                        content=searchable_content,
                        metadata=metadata,
                        data_id=data_id,
                    )

                    system_info["chromadb_id"] = stored_id
                    system_info["stored_to_chromadb"] = True

                except Exception as e:
                    system_info["chromadb_error"] = str(e)
                    system_info["stored_to_chromadb"] = False

            execution_time = (time.time() - start_time) * 1000

            exec_metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=0.1,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(system_info, exec_metadata)

        except Exception as e:
            self._logger.exception("获取系统信息时发生异常")
            return self._create_error_result(
                "SYSTEM_INFO_ERROR", f"获取系统信息失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class ProcessManagerTool(BaseTool):
    """进程管理工具"""

    def __init__(
        self,
        config: Optional[ConfigDict] = None,
        data_manager: Optional[UnifiedDataManager] = None,
    ):
        super().__init__(config)
        self.data_manager = data_manager or UnifiedDataManager()

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="manage_processes",
            description="管理系统进程（查看、搜索进程信息）",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "search", "info"],
                        "description": "操作类型：list(列出进程), search(搜索进程), info(进程详情)",
                    },
                    "process_name": {
                        "type": "string",
                        "description": "进程名称（用于搜索和获取详情）",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                        "description": "返回结果数量限制",
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行进程管理"""
        params = request.parameters
        action = params["action"]
        process_name = params.get("process_name", "")
        limit = params.get("limit", 20)

        try:
            start_time = time.time()

            if action == "list":
                # 列出所有进程
                processes = []
                for proc in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent", "status"]
                ):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # 按CPU使用率排序
                processes = sorted(
                    processes, key=lambda x: x.get("cpu_percent", 0), reverse=True
                )[:limit]
                result_content = {
                    "action": "list",
                    "processes": processes,
                    "total_count": len(processes),
                }

            elif action == "search":
                if not process_name:
                    return self._create_error_result(
                        "MISSING_PARAMETER", "搜索进程需要提供 process_name 参数"
                    )

                # 搜索进程
                matching_processes = []
                for proc in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent", "status"]
                ):
                    try:
                        if process_name.lower() in proc.info["name"].lower():
                            matching_processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                result_content = {
                    "action": "search",
                    "search_term": process_name,
                    "processes": matching_processes[:limit],
                    "total_found": len(matching_processes),
                }

            elif action == "info":
                if not process_name:
                    return self._create_error_result(
                        "MISSING_PARAMETER", "获取进程详情需要提供 process_name 参数"
                    )

                # 获取进程详细信息
                process_details = []
                for proc in psutil.process_iter():
                    try:
                        if process_name.lower() in proc.name().lower():
                            proc_info = {
                                "pid": proc.pid,
                                "name": proc.name(),
                                "status": proc.status(),
                                "cpu_percent": proc.cpu_percent(),
                                "memory_percent": proc.memory_percent(),
                                "create_time": proc.create_time(),
                                "num_threads": proc.num_threads(),
                                "cmdline": proc.cmdline(),
                            }
                            process_details.append(proc_info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                result_content = {
                    "action": "info",
                    "process_name": process_name,
                    "processes": process_details[:limit],
                    "total_found": len(process_details),
                }

            else:
                return self._create_error_result(
                    "INVALID_ACTION", f"不支持的操作: {action}"
                )

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=0.1,
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(result_content, metadata)

        except Exception as e:
            self._logger.exception("管理进程时发生异常")
            return self._create_error_result(
                "PROCESS_MANAGEMENT_ERROR", f"进程管理失败: {str(e)}"
            )

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class EnhancedSystemTools:
    """增强的系统工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}
        self.data_manager = UnifiedDataManager()

    def create_tools(self) -> List[BaseTool]:
        """创建所有增强的系统工具"""
        tools_config = self.config.get("enhanced_system", {})

        return [
            SystemInfoTool(tools_config, self.data_manager),
            ProcessManagerTool(tools_config, self.data_manager),
        ]
