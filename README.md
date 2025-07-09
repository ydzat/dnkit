# MCP Toolkit

A modular MCP (Model Context Protocol) toolkit for building extensible tool services with ChromaDB-powered semantic search and intelligent data management.

## ✨ Features

- 🔧 **Modular Architecture**: Support for dynamic service registration and hot-swappable components
- 🌐 **Standard MCP Protocol**: Full support for MCP 2024-11-05 specification with n8n compatibility
- 🛠️ **Rich Tool Set**: 22 tools including file operations, network requests, system management, and intelligent code analysis
- 🧠 **ChromaDB Integration**: Unified vector database for semantic search and intelligent data storage
- 🔍 **Semantic Search**: AI-powered search across files, web content, system information, and code
- 🤖 **Context Engine**: Multi-language code analysis with intelligent query processing and similarity search
- 🚀 **Lightweight & Efficient**: Personal project focused on core functionality with enterprise-grade features

## 🎯 Current Status

**Phase 2 Complete** ✅ (July 2025)
- 22 tools available (12 basic + 6 enhanced + 4 context engine)
- ChromaDB unified data storage with context engine
- Multi-language code analysis (Python, JavaScript, TypeScript, etc.)
- Intelligent semantic search and similarity matching
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
# Run with ChromaDB and enhanced tools + context engine
./scripts/run_mcp_daemon.sh

# The server will automatically detect enhanced configuration
# and start with all 22 tools including semantic search and code analysis
```

### n8n Integration
```
Server URL: http://your-server:8082 (SSE endpoint)
Available Tools: 22 tools ready for use (including context engine)
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

### Core Features
- **ChromaDB Unified Storage**: All enhanced tools and context engine share a unified vector database
- **Multi-Language Code Analysis**: Support for Python, JavaScript, TypeScript, and more
- **Intelligent Query Processing**: Natural language understanding with intent parsing
- **Semantic Search**: AI-powered search using sentence-transformers across all data types
- **Code Understanding**: Function/class analysis, similarity matching, project overview
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
- **Phase 3** 📋: Task management + Memory system (Planned)
- **Phase 4** 📋: Visualization tools + Advanced features (Planned)

See [doc/basic_tools/README.md](doc/basic_tools/README.md) for detailed design documentation.

## 📊 Project Stats

- **Total Tools**: 22 (12 basic + 6 enhanced + 4 context engine)
- **Code Analysis**: Multi-language support (Python, JavaScript, TypeScript, etc.)
- **Database**: ChromaDB with sentence-transformers for unified vector storage
- **Protocol**: MCP 2024-11-05 compliant
- **Integration**: n8n compatible via SSE
- **Language**: Python 3.12+
- **Test Coverage**: 56 unit tests, full integration testing
- **Dependencies**: aiohttp, chromadb, sentence-transformers, beautifulsoup4, psutil

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details
