#!/bin/bash

# MCP Toolkit 后台运行脚本
# 支持第一阶段增强功能：ChromaDB 统一存储、增强工具集

set -e

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/mcp-toolkit.pid"
LOG_FILE="$PROJECT_ROOT/logs/mcp-toolkit.log"

# 配置文件优先级：增强配置 > 开发配置 > 默认配置
ENHANCED_CONFIG="$PROJECT_ROOT/config/enhanced_tools_config.yaml"
DEV_CONFIG="$PROJECT_ROOT/config/development.yaml"
DEFAULT_CONFIG="$PROJECT_ROOT/config/default.yaml"

# 选择配置文件
if [[ -f "$ENHANCED_CONFIG" ]]; then
    CONFIG_FILE="$ENHANCED_CONFIG"
    echo "使用增强工具配置: $ENHANCED_CONFIG"
elif [[ -f "$DEV_CONFIG" ]]; then
    CONFIG_FILE="$DEV_CONFIG"
    echo "使用开发配置: $DEV_CONFIG"
else
    CONFIG_FILE="$DEFAULT_CONFIG"
    echo "使用默认配置: $DEFAULT_CONFIG"
fi

# 默认配置
DEFAULT_HOST="0.0.0.0"  # 绑定到所有网络接口，允许局域网访问
DEFAULT_PORT="8080"
DEFAULT_WS_PORT="8081"
DEFAULT_SSE_PORT="8082"

# 增强功能标志
ENHANCED_MODE=false
if [[ -f "$ENHANCED_CONFIG" ]]; then
    ENHANCED_MODE=true
fi

# 创建必要目录
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/mcp_unified_db"  # ChromaDB 数据目录

# 检查虚拟环境
if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
    echo "错误: 虚拟环境不存在，请先运行: uv sync"
    exit 1
fi

# 检查增强功能依赖
check_enhanced_dependencies() {
    if [[ "$ENHANCED_MODE" == true ]]; then
        echo "检查增强功能依赖..."
        source "$PROJECT_ROOT/.venv/bin/activate"

        # 检查 ChromaDB
        if ! python -c "import chromadb" 2>/dev/null; then
            echo "警告: ChromaDB 未安装，正在安装..."
            pip install chromadb sentence-transformers beautifulsoup4 psutil
        fi

        # 检查其他依赖
        if ! python -c "import sentence_transformers, bs4, psutil" 2>/dev/null; then
            echo "警告: 增强功能依赖不完整，正在安装..."
            pip install sentence-transformers beautifulsoup4 psutil
        fi

        echo "✅ 增强功能依赖检查完成"
    fi
}

check_enhanced_dependencies

# 检查服务是否已运行
if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo "MCP 服务已在运行中 (PID: $pid)"
        echo "如需停止服务，请运行: kill $pid"
        exit 0
    else
        # 清理无效的 PID 文件
        rm -f "$PID_FILE"
    fi
fi

# 激活虚拟环境并启动服务
echo "启动 MCP Toolkit 服务..."
cd "$PROJECT_ROOT"
source .venv/bin/activate

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
export MCP_CONFIG_FILE="$CONFIG_FILE"

# 启动标准 MCP 服务器（兼容 n8n）
echo "🚀 启动 MCP 服务器"
if [[ "$ENHANCED_MODE" == true ]]; then
    echo "   模式: 增强模式 (ChromaDB + 增强工具集)"
    echo "   配置: $CONFIG_FILE"
    echo "   ChromaDB: $PROJECT_ROOT/mcp_unified_db"
else
    echo "   模式: 基础模式"
    echo "   配置: $CONFIG_FILE"
fi

# 启动标准 MCP 服务器（支持 WebSocket 和 SSE）
nohup mcp-toolkit --config "$CONFIG_FILE" --host "$DEFAULT_HOST" --port "$DEFAULT_PORT" --ws-port "$DEFAULT_WS_PORT" --sse-port "$DEFAULT_SSE_PORT" > "$LOG_FILE" 2>&1 &
pid=$!

# 保存 PID
echo "$pid" > "$PID_FILE"

echo "✅ MCP 服务已启动"
echo "   PID: $pid"
echo "   HTTP地址: http://$DEFAULT_HOST:$DEFAULT_PORT"
echo "   WebSocket地址: ws://$DEFAULT_HOST:$DEFAULT_WS_PORT"
echo "   SSE地址: http://$DEFAULT_HOST:$DEFAULT_SSE_PORT (用于n8n连接)"

if [[ "$ENHANCED_MODE" == true ]]; then
    echo "   增强功能:"
    echo "     - ChromaDB 统一数据存储"
    echo "     - 增强文件系统工具 (语义搜索)"
    echo "     - 增强网络工具 (网页内容存储)"
    echo "     - 增强系统工具 (系统信息管理)"
fi

echo "   日志: $LOG_FILE"
echo "   停止服务: kill $pid"
echo ""
echo "查看日志: tail -f $LOG_FILE"

# 如果是增强模式，显示额外信息
if [[ "$ENHANCED_MODE" == true ]]; then
    echo ""
    echo "💡 增强功能使用提示:"
    echo "   - 使用 enhanced_read_file 工具读取文件并存储到 ChromaDB"
    echo "   - 使用 search_files 工具进行语义搜索"
    echo "   - 使用 enhanced_fetch_web 工具获取网页并存储"
    echo "   - 使用 search_web_content 工具搜索网页内容"
    echo "   - 使用 get_system_info 工具获取系统信息"
    echo "   - 使用 manage_processes 工具管理进程"
fi
