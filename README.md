# MCP Toolkit

A modular MCP (Model Context Protocol) toolkit for building extensible tool services.

## Features

- 🔧 **Modular Architecture**: Support for dynamic service registration and hot-swappable components
- 🌐 **Standard MCP Protocol**: Full support for MCP 2024-11-05 specification
- 🛠️ **Rich Tool Set**: File operations, terminal execution, network requests, and more
- 🚀 **Lightweight & Efficient**: Personal project focused on core functionality

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

## Quick Start

```bash
# Run the MCP server
mcp-toolkit --config config/development.yaml

# Health check
curl http://localhost:8080/health
```

## Development

This project follows a milestone-based development approach. See [DEVELOPMENT_GUIDE.md](doc/DEVELOPMENT_GUIDE.md) for detailed development instructions.

## License

MIT
