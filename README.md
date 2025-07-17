# MCP Toolkit

A modular MCP (Model Context Protocol) toolkit for building extensible tool services with ChromaDB-powered semantic search and intelligent data management.

## ✨ Features

- 🔧 **Modular Architecture**: Support for dynamic service registration and hot-swappable components
- 🌐 **Standard MCP Protocol**: Full support for MCP 2024-11-05 specification with n8n compatibility
- 🛠️ **Rich Tool Set**: 54 tools including file operations, network requests, system management, intelligent code analysis, task management, memory system, visualization, Git integration, version management, agent automation, intelligent analysis, agent behavior control, deep context analysis, and semantic intelligence
- 🧠 **ChromaDB Integration**: Unified vector database for semantic search and intelligent data storage
- 🔍 **Semantic Search**: AI-powered search across files, web content, system information, code, tasks, and memories
- 🤖 **Context Engine**: Multi-language code analysis with intelligent query processing and similarity search
- 📋 **Task Management**: ChromaDB-based task storage with semantic search and specialized search tools
- 🧠 **Memory System**: Knowledge accumulation, conversation history, and intelligent memory retrieval
- 📊 **Visualization Tools**: Mermaid diagrams, Chart.js data visualization, and complex nested charts
- 🔗 **Tool Collaboration**: Chain execution, parallel processing, and data flow management
- 🚀 **Lightweight & Efficient**: Personal project focused on core functionality with enterprise-grade features

## 🎯 Current Status

**Phase 3 Complete** ✅ (July 2025)
- 54 tools available (12 basic + 6 enhanced + 4 context engine + 4 Git integration + 3 version management + 2 agent automation + 3 intelligent analysis + 3 agent behavior + 3 deep context + 4 semantic intelligence + 4 task management + 1 memory + 4 visualization + 1 collaboration)
- ChromaDB unified data storage across all intelligent tools
- Multi-language code analysis (Python, JavaScript, TypeScript, etc.)
- Task management system with semantic search and specialized search tools
- Memory system for knowledge accumulation and intelligent retrieval
- Visualization tools for Mermaid diagrams, data charts, and complex nested structures
- Tool collaboration framework with chain execution and parallel processing
- Intelligent semantic search and similarity matching across all data types
- Natural language query processing
- Full MCP protocol compatibility with n8n integration

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-toolkit.git
cd mcp-toolkit

# Install with uv
uv sync

# Activate virtual environment
source .venv/bin/activate
```

## 🚀 Quick Start

### Basic Mode
```bash
# Run the basic MCP server
mcp-toolkit --config config/development.yaml

# Health check
curl http://localhost:8080/health
```

### Enhanced Mode (Recommended)
```bash
# Run with ChromaDB and all intelligent tools
./scripts/run_mcp_daemon.sh

# The server will automatically detect enhanced configuration
# and start with all 32 tools including semantic search, code analysis,
# task management, memory system, and visualization tools
```

### n8n Integration
```
Server URL: http://your-server:8082 (SSE endpoint)
Available Tools: 54 tools ready for use (including context engine, task management, memory system, visualization, agent automation, and semantic intelligence)
```

## 🛠️ Available Tools

### Basic Tools (12)
| Category | Tool | Description |
|----------|------|-------------|
| **File System** | `read_file` | Read file contents |
| | `write_file` | Write file contents |
| | `list_files` | List directory files |
| | `create_directory` | Create directories |
| **Network** | `http_request` | HTTP requests |
| | `dns_lookup` | DNS queries |
| **Search** | `file_search` | File name search |
| | `content_search` | File content search |
| **System** | `run_command` | Execute commands |
| | `get_environment` | Get environment variables |
| | `set_working_directory` | Set working directory |
| **Utility** | `echo` | Echo test tool |

### Enhanced Tools (6) 🧠
| Category | Tool | Description |
|----------|------|-------------|
| **Smart File System** | `enhanced_read_file` | Read files + ChromaDB storage + metadata |
| | `search_files` | Semantic file search |
| **Smart Network** | `enhanced_fetch_web` | Fetch web pages + ChromaDB storage |
| | `search_web_content` | Semantic web content search |
| **Smart System** | `get_system_info` | System info + ChromaDB storage |
| | `manage_processes` | Process management |

### Context Engine Tools (4) 🤖
| Category | Tool | Description |
|----------|------|-------------|
| **Code Analysis** | `analyze_code` | Multi-language code analysis + ChromaDB storage |
| **Intelligent Search** | `search_code` | Natural language code search |
| | `find_similar_code` | Semantic similarity code search |
| **Project Analysis** | `get_project_overview` | Project statistics and overview |

### Git Integration Tools (4) 🔄
| Category | Tool | Description |
|----------|------|-------------|
| **Diff Analysis** | `git_diff_analysis` | Smart Git diff analysis with multi-level insights |
| **Patch Management** | `git_apply_patch` | Precise patch application with line-level editing |
| **History Analysis** | `git_history_analysis` | Git history and change tracking analysis |
| **Conflict Detection** | `git_conflict_check` | Potential merge conflict detection and analysis |

### Version Management Tools (3) ⏱️
| Category | Tool | Description |
|----------|------|-------------|
| **Operation Tracking** | `undo_operation` | Undo agent operations with fine-grained control |
| **Checkpoint Management** | `rollback_to_checkpoint` | Rollback to specific checkpoints or time points |
| **Checkpoint Control** | `manage_checkpoint` | Create, list, delete and manage version checkpoints |

### Agent Automation Tools (2) 🤖
| Category | Tool | Description |
|----------|------|-------------|
| **Task Decomposition** | `decompose_task` | Decompose complex tasks into subtasks |
| **Execution Guidance** | `get_execution_guidance` | Task execution guidance and suggestions |

### Intelligent Analysis Tools (3) 📈
| Category | Tool | Description |
|----------|------|-------------|
| **Code Quality** | `analyze_code_quality` | Code quality analysis and improvement suggestions |
| **Performance Monitoring** | `monitor_performance` | System performance metrics monitoring |
| **History Trends** | `analyze_history_trends` | Historical data trend analysis |

### Agent Behavior Tools (3) 🎯
| Category | Tool | Description |
|----------|------|-------------|
| **State Control** | `control_agent_state` | Agent state machine control |
| **Behavior Validation** | `validate_agent_behavior` | Behavior consistency validation |
| **Learning Optimization** | `optimize_agent_learning` | History-based learning optimization |

### Deep Context Engine Tools (3) 🔍
| Category | Tool | Description |
|----------|------|-------------|
| **Dependency Analysis** | `analyze_dependencies` | Code dependency relationship analysis |
| **Call Graph** | `build_call_graph` | Function call relationship graph construction |
| **Refactoring Suggestions** | `suggest_refactoring` | Code refactoring suggestions |

### Semantic Intelligence Tools (4) 💡
| Category | Tool | Description |
|----------|------|-------------|
| **Semantic Understanding** | `understand_semantics` | Business logic and design pattern understanding |
| **Code Completion** | `get_code_completions` | Intelligent code completion suggestions |
| **Pattern Recognition** | `recognize_patterns` | Design pattern and programming pattern recognition |
| **Best Practices** | `get_best_practices` | Best practice suggestions |

### Task Management Tools (4) 📋
| Category | Tool | Description |
|----------|------|-------------|
| **Task Management** | `manage_tasks` | Task creation, update, delete, query + ChromaDB storage |
| **Specialized Search** | `search_recent_tasks` | Search recently created tasks |
| | `search_tasks_by_time` | Search tasks by time range |
| | `search_tasks_semantic` | Semantic task search by content |

### Memory Management Tools (1) 🧠
| Category | Tool | Description |
|----------|------|-------------|
| **Memory System** | `manage_memory` | Knowledge storage, retrieval, search (knowledge, conversation, experience, skills) |

### Visualization Tools (4) 📊
| Category | Tool | Description |
|----------|------|-------------|
| **Chart Generation** | `generate_diagram` | Mermaid diagrams (flowcharts, sequence, mind maps) |
| | `create_data_chart` | Data visualization (Chart.js format) |
| **Complex Charts** | `generate_subgraph_diagram` | Complex nested subgraph diagrams |
| | `generate_state_machine` | State machine and automaton diagrams |

### Tool Collaboration (1) 🔗
| Category | Tool | Description |
|----------|------|-------------|
| **Workflow Execution** | `execute_tool_chain` | Chain execution, parallel processing, data flow |

### Core Features
- **ChromaDB Unified Storage**: All intelligent tools share a unified vector database for seamless data integration
- **Multi-Language Code Analysis**: Support for Python, JavaScript, TypeScript, and more
- **Intelligent Query Processing**: Natural language understanding with intent parsing
- **Semantic Search**: AI-powered search using sentence-transformers across files, code, tasks, and memories
- **Code Understanding**: Function/class analysis, similarity matching, project overview
- **Task Management**: ChromaDB-based task storage with specialized search tools and semantic search
- **Memory System**: Knowledge accumulation, conversation history, and intelligent memory retrieval
- **Visualization Capabilities**: Mermaid diagrams, Chart.js data visualization, complex nested charts
- **Tool Collaboration**: Chain execution, parallel processing, and data flow management
- **Agent Automation**: Complex task decomposition and intelligent execution guidance
- **Intelligent Analysis**: Code quality analysis, performance monitoring, and history trend analysis
- **Agent Behavior Control**: State machine control, behavior validation, and learning optimization
- **Deep Context Analysis**: Code dependency analysis, call graph construction, and refactoring suggestions
- **Semantic Intelligence**: Business logic understanding, intelligent code completion, and pattern recognition
- **Intelligent Metadata**: Automatic language detection, content analysis, complexity scoring
- **MCP Compatible**: Full protocol compliance for seamless integration with n8n and other clients

## 📋 Configuration

### Enhanced Mode Configuration
Create `config/enhanced_tools_config.yaml`:
```yaml
# ChromaDB Configuration
chromadb:
  persist_directory: "./mcp_unified_db"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

# Enhanced Tools Settings
enhanced_file_operations:
  max_file_size_mb: 10
  auto_store_to_chromadb: true

enhanced_network:
  timeout: 30
  max_content_size_mb: 5
  auto_store_to_chromadb: true

enhanced_system:
  auto_store_to_chromadb: true
```

## 🔧 Development

This project follows a milestone-based development approach:

- **Phase 1** ✅: Basic tools + ChromaDB integration (Complete)
- **Phase 2** ✅: Context engine + Multi-language code analysis (Complete)
- **Phase 3** ✅: Task management + Memory system + Visualization + Tool collaboration (Complete)
- **Phase 4** 📋: Advanced features + Performance optimization (Planned)

See [doc/basic_tools/README.md](doc/basic_tools/README.md) for detailed design documentation.

## 📊 Project Stats

- **Total Tools**: 54 (12 basic + 6 enhanced + 4 context engine + 4 Git integration + 3 version management + 2 agent automation + 3 intelligent analysis + 3 agent behavior + 3 deep context + 4 semantic intelligence + 4 task management + 1 memory + 4 visualization + 1 collaboration)
- **Code Analysis**: Multi-language support (Python, JavaScript, TypeScript, etc.)
- **Task Management**: ChromaDB-based with semantic search and specialized search tools
- **Memory System**: Knowledge accumulation with intelligent retrieval
- **Visualization**: Mermaid diagrams, Chart.js data visualization, complex nested charts
- **Tool Collaboration**: Chain execution, parallel processing, data flow management
- **Agent Automation**: Task decomposition and execution guidance
- **Intelligent Analysis**: Code quality, performance monitoring, history trends
- **Agent Behavior**: State control, behavior validation, learning optimization
- **Deep Context**: Dependency analysis, call graphs, refactoring suggestions
- **Semantic Intelligence**: Business logic understanding, code completion, pattern recognition
- **Database**: ChromaDB with sentence-transformers for unified vector storage
- **Protocol**: MCP 2024-11-05 compliant
- **Integration**: n8n compatible via SSE
- **Language**: Python 3.12+
- **Test Coverage**: Full integration testing with n8n, all tools verified
- **Dependencies**: aiohttp, chromadb, sentence-transformers, beautifulsoup4, psutil

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

AGPL-3.0 License - see [LICENSE](LICENSE) for details
