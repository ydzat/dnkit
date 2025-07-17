"""
操作追踪器

用于记录 Agent 的所有操作，为撤销和回滚功能提供历史数据。
"""

import hashlib
import json
import os
import shutil
import time
from typing import Any, Dict, List, Optional

from ..storage.unified_manager import UnifiedDataManager


class OperationTracker:
    """操作追踪器"""

    def __init__(
        self, data_manager: UnifiedDataManager, backup_dir: str = "./mcp_backups"
    ):
        self.data_manager = data_manager
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def track_file_operation(
        self,
        operation_type: str,
        file_path: str,
        description: str = "",
        content_before: Optional[str] = None,
        content_after: Optional[str] = None,
    ) -> str:
        """追踪文件操作"""
        operation_id = self._generate_operation_id()

        # 创建文件快照（如果需要）
        snapshot_id = None
        if operation_type in ["file_edit", "file_delete"] and os.path.exists(file_path):
            snapshot_id = self._create_file_snapshot(file_path, operation_id)

        # 记录操作
        operation_data = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "file_path": file_path,
            "description": description,
            "timestamp": time.time(),
            "snapshot_id": snapshot_id or "",
            "file_size_before": (
                os.path.getsize(file_path) if os.path.exists(file_path) else 0
            ),
            "file_hash_before": (
                self._calculate_file_hash(file_path)
                if os.path.exists(file_path)
                else ""
            ),
        }

        # 存储到 ChromaDB
        content = f"Agent operation: {operation_type} on {file_path}"
        self.data_manager.store_data(
            data_type="agent_operation", content=content, metadata=operation_data
        )

        return operation_id

    def _generate_operation_id(self) -> str:
        """生成操作ID"""
        timestamp = str(time.time())
        return f"op_{hashlib.md5(timestamp.encode(), usedforsecurity=False).hexdigest()[:8]}"

    def _create_file_snapshot(self, file_path: str, operation_id: str) -> Optional[str]:
        """创建文件快照"""
        try:
            if not os.path.exists(file_path):
                return None

            # 生成快照ID
            snapshot_id = f"snap_{operation_id}_{int(time.time())}"
            snapshot_path = os.path.join(self.backup_dir, f"{snapshot_id}.backup")

            # 复制文件
            shutil.copy2(file_path, snapshot_path)

            # 存储快照信息到 ChromaDB
            self._store_snapshot_info(snapshot_id, file_path, operation_id)

            return snapshot_id
        except Exception as e:
            print(f"创建文件快照失败: {e}")
            return None

    def _store_snapshot_info(
        self, snapshot_id: str, file_path: str, operation_id: str
    ) -> None:
        """存储快照信息"""
        try:
            content = f"File snapshot for {file_path}"
            metadata = {
                "snapshot_id": snapshot_id,
                "file_path": file_path,
                "operation_id": operation_id,
                "timestamp": time.time(),
                "file_size": (
                    os.path.getsize(file_path) if os.path.exists(file_path) else 0
                ),
                "file_hash": self._calculate_file_hash(file_path),
            }

            self.data_manager.store_data(
                data_type="file_snapshot", content=content, metadata=metadata
            )
        except Exception as e:
            print(f"存储快照信息失败: {e}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            if not os.path.exists(file_path):
                return ""

            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""


def create_test_operations(data_manager: UnifiedDataManager) -> List[str]:
    """创建测试操作历史"""
    tracker = OperationTracker(data_manager)
    operation_ids = []

    # 创建测试文件目录
    test_dir = "./test_files"
    os.makedirs(test_dir, exist_ok=True)

    # 操作1: 创建文件
    test_file1 = os.path.join(test_dir, "test1.py")
    with open(test_file1, "w") as f:
        f.write("def hello():\n    print('Hello, World!')\n")

    op_id1 = tracker.track_file_operation(
        "file_create", test_file1, "创建测试文件 test1.py"
    )
    operation_ids.append(op_id1)

    # 等待一秒确保时间戳不同
    time.sleep(1)

    # 操作2: 编辑文件
    with open(test_file1, "w") as f:
        f.write(
            "def hello():\n    print('Hello, Enhanced World!')\n\nif __name__ == '__main__':\n    hello()\n"
        )

    op_id2 = tracker.track_file_operation(
        "file_edit", test_file1, "修改 test1.py 添加主函数调用"
    )
    operation_ids.append(op_id2)

    time.sleep(1)

    # 操作3: 创建另一个文件
    test_file2 = os.path.join(test_dir, "test2.py")
    with open(test_file2, "w") as f:
        f.write("import test1\n\ntest1.hello()\n")

    op_id3 = tracker.track_file_operation(
        "file_create", test_file2, "创建测试文件 test2.py"
    )
    operation_ids.append(op_id3)

    time.sleep(1)

    # 操作4: 再次编辑第一个文件
    with open(test_file1, "w") as f:
        f.write(
            "def hello(name='World'):\n    print(f'Hello, {name}!')\n\nif __name__ == '__main__':\n    hello('Python')\n"
        )

    op_id4 = tracker.track_file_operation(
        "file_edit", test_file1, "修改 test1.py 添加参数支持"
    )
    operation_ids.append(op_id4)

    time.sleep(1)

    # 操作5: 创建配置文件
    config_file = os.path.join(test_dir, "config.json")
    with open(config_file, "w") as f:
        json.dump({"version": "1.0", "debug": True}, f, indent=2)

    op_id5 = tracker.track_file_operation(
        "file_create", config_file, "创建配置文件 config.json"
    )
    operation_ids.append(op_id5)

    print(f"创建了 {len(operation_ids)} 个测试操作:")
    for i, op_id in enumerate(operation_ids, 1):
        print(f"  {i}. {op_id}")

    return operation_ids
