# ChromaDB 纯统一架构实现指南

## 🎯 核心理念

**一个 ChromaDB 实例，一个集合，所有数据**

所有组件（文件系统、任务管理、上下文引擎、记忆系统、配置管理）共享同一个 ChromaDB 实例和集合，通过元数据字段区分数据类型，实现真正的统一数据管理。

## 🏗️ 核心架构

### 统一数据管理器
```python
import chromadb
import time
import uuid
import json
from typing import Dict, List, Any, Optional

class UnifiedDataManager:
    """ChromaDB 统一数据管理器 - 所有组件的数据访问层"""

    def __init__(self, persist_directory: str = "./mcp_unified_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="mcp_unified_storage",
            embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        )

    def store_data(self, data_type: str, content: str, metadata: Dict[str, Any], data_id: str = None) -> str:
        """统一数据存储接口"""
        if data_id is None:
            data_id = f"{data_type}_{uuid.uuid4()}"

        # 添加通用元数据
        enhanced_metadata = {
            "data_type": data_type,
            "created_time": time.time(),
            "updated_time": time.time(),
            **metadata
        }

        self.collection.add(
            documents=[content],
            metadatas=[enhanced_metadata],
            ids=[data_id]
        )

        return data_id

    def query_data(self, query: str, data_type: str = None, filters: Dict[str, Any] = None, n_results: int = 10) -> Dict:
        """统一数据查询接口"""
        where_clause = {}

        if data_type:
            where_clause["data_type"] = data_type

        if filters:
            where_clause.update(filters)

        return self.collection.query(
            query_texts=[query],
            where=where_clause if where_clause else None,
            n_results=n_results
        )

    def get_by_id(self, data_id: str) -> Dict:
        """根据ID获取数据"""
        return self.collection.get(
            ids=[data_id],
            include=["documents", "metadatas"]
        )

    def update_data(self, data_id: str, content: str = None, metadata: Dict[str, Any] = None):
        """更新数据"""
        if content or metadata:
            current_data = self.get_by_id(data_id)
            if not current_data["ids"]:
                raise ValueError(f"Data with ID {data_id} not found")

            new_content = content if content is not None else current_data["documents"][0]

            if metadata:
                current_metadata = current_data["metadatas"][0]
                current_metadata.update(metadata)
                current_metadata["updated_time"] = time.time()
                new_metadata = current_metadata
            else:
                new_metadata = current_data["metadatas"][0]
                new_metadata["updated_time"] = time.time()

            # ChromaDB 需要先删除再添加来更新
            self.collection.delete(ids=[data_id])
            self.collection.add(
                documents=[new_content],
                metadatas=[new_metadata],
                ids=[data_id]
            )

    def delete_data(self, data_id: str):
        """删除数据"""
        self.collection.delete(ids=[data_id])

    def get_stats(self) -> Dict[str, int]:
        """获取数据统计"""
        all_data = self.collection.get(include=["metadatas"])
        stats = {}

        for metadata in all_data["metadatas"]:
            data_type = metadata.get("data_type", "unknown")
            stats[data_type] = stats.get(data_type, 0) + 1

        return stats
```

## 🛠️ 各组件实现

### 1. 文件系统工具
```python
class FileSystemManager:
    def __init__(self, unified_manager: UnifiedDataManager):
        self.data_manager = unified_manager

    def store_file(self, file_path: str, content: str, language: str = None) -> str:
        """存储文件内容到 ChromaDB"""
        metadata = {
            "file_path": file_path,
            "file_size": len(content),
            "language": language or self._detect_language(file_path),
            "file_extension": file_path.split('.')[-1] if '.' in file_path else ""
        }

        return self.data_manager.store_data(
            data_type="file",
            content=content,
            metadata=metadata,
            data_id=f"file_{hash(file_path)}"
        )

    def search_files(self, query: str, language: str = None) -> List[Dict]:
        """搜索文件内容"""
        filters = {}
        if language:
            filters["language"] = language

        return self.data_manager.query_data(
            query=query,
            data_type="file",
            filters=filters
        )

    def _detect_language(self, file_path: str) -> str:
        """简单的语言检测"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust"
        }
        ext = "." + file_path.split('.')[-1] if '.' in file_path else ""
        return ext_map.get(ext, "text")
```

### 2. 任务管理工具
```python
class TaskManager:
    def __init__(self, unified_manager: UnifiedDataManager):
        self.data_manager = unified_manager

    def create_task(self, title: str, description: str, **kwargs) -> str:
        """创建任务"""
        metadata = {
            "task_title": title,
            "task_status": kwargs.get("status", "NOT_STARTED"),
            "task_priority": kwargs.get("priority", "MEDIUM"),
            "task_assignee": kwargs.get("assignee", ""),
            "task_due_date": kwargs.get("due_date", ""),
            "task_tags": kwargs.get("tags", []),
            "task_dependencies": kwargs.get("dependencies", [])
        }

        content = f"{title}\n\n{description}"

        return self.data_manager.store_data(
            data_type="task",
            content=content,
            metadata=metadata
        )

    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """根据状态获取任务"""
        return self.data_manager.query_data(
            query=f"tasks with status {status}",
            data_type="task",
            filters={"task_status": status}
        )

    def search_tasks(self, query: str) -> List[Dict]:
        """搜索任务"""
        return self.data_manager.query_data(
            query=query,
            data_type="task"
        )

    def update_task_status(self, task_id: str, new_status: str):
        """更新任务状态"""
        self.data_manager.update_data(
            data_id=task_id,
            metadata={"task_status": new_status}
        )
```

### 3. 配置管理工具
```python
class ConfigManager:
    def __init__(self, unified_manager: UnifiedDataManager):
        self.data_manager = unified_manager

    def set_config(self, key: str, value: Any, category: str = "general", scope: str = "global") -> str:
        """设置配置"""
        metadata = {
            "config_key": key,
            "config_category": category,
            "config_scope": scope,
            "config_type": type(value).__name__
        }

        content = json.dumps(value) if not isinstance(value, str) else value

        return self.data_manager.store_data(
            data_type="config",
            content=content,
            metadata=metadata,
            data_id=f"config_{category}_{key}"
        )

    def get_config(self, key: str, category: str = "general") -> Any:
        """获取配置"""
        result = self.data_manager.query_data(
            query=f"config {key}",
            data_type="config",
            filters={"config_key": key, "config_category": category},
            n_results=1
        )

        if result["documents"]:
            content = result["documents"][0]
            config_type = result["metadatas"][0].get("config_type", "str")

            if config_type != "str":
                return json.loads(content)
            return content

        return None
```

### 4. 记忆系统
```python
class MemoryManager:
    def __init__(self, unified_manager: UnifiedDataManager):
        self.data_manager = unified_manager

    def store_memory(self, content: str, memory_type: str = "knowledge", importance: float = 0.5) -> str:
        """存储记忆"""
        metadata = {
            "memory_type": memory_type,
            "importance_score": importance,
            "access_count": 0,
            "last_accessed": time.time()
        }

        return self.data_manager.store_data(
            data_type="memory",
            content=content,
            metadata=metadata
        )

    def recall_memory(self, query: str, memory_type: str = None) -> List[Dict]:
        """回忆记忆"""
        filters = {}
        if memory_type:
            filters["memory_type"] = memory_type

        results = self.data_manager.query_data(
            query=query,
            data_type="memory",
            filters=filters
        )

        # 更新访问计数
        for i, memory_id in enumerate(results["ids"]):
            current_count = results["metadatas"][i].get("access_count", 0)
            self.data_manager.update_data(
                data_id=memory_id,
                metadata={
                    "access_count": current_count + 1,
                    "last_accessed": time.time()
                }
            )

        return results
```

## 🚀 使用示例

```python
# 初始化统一数据管理器
unified_manager = UnifiedDataManager()

# 初始化各个组件
file_manager = FileSystemManager(unified_manager)
task_manager = TaskManager(unified_manager)
config_manager = ConfigManager(unified_manager)
memory_manager = MemoryManager(unified_manager)

# 存储文件
file_id = file_manager.store_file(
    file_path="/path/to/example.py",
    content="def hello_world():\n    print('Hello, World!')",
    language="python"
)

# 创建任务
task_id = task_manager.create_task(
    title="Implement file reader",
    description="Create a function to read files safely",
    priority="HIGH",
    tags=["development", "file-io"]
)

# 设置配置
config_manager.set_config(
    key="max_file_size",
    value=10485760,  # 10MB
    category="file_system"
)

# 存储记忆
memory_manager.store_memory(
    content="Always validate file paths before reading to prevent security issues",
    memory_type="knowledge",
    importance=0.8
)

# 统一搜索 - 可以搜索所有类型的数据
all_results = unified_manager.query_data("file reading")
print(f"Found {len(all_results['documents'])} results across all data types")

# 查看数据统计
stats = unified_manager.get_stats()
print(f"Data statistics: {stats}")
```

---

这个纯 ChromaDB 架构彻底解决了数据一致性和记忆混乱问题，所有数据都在一个地方，查询简单统一，维护成本最低。
