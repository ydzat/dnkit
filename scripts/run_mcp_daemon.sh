#!/bin/bash

# MCP Toolkit 后台运行脚本
# 简单的后台启动脚本

set -e

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/mcp-toolkit.pid"
LOG_FILE="$PROJECT_ROOT/logs/mcp-toolkit.log"
CONFIG_FILE="$PROJECT_ROOT/config/development.yaml"

# 默认配置
DEFAULT_HOST="0.0.0.0"  # 绑定到所有网络接口，允许局域网访问
DEFAULT_PORT="8080"
DEFAULT_WS_PORT="8081"
DEFAULT_SSE_PORT="8082"

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

# 检查虚拟环境
if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
    echo "错误: 虚拟环境不存在，请先运行: uv sync"
    exit 1
fi

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

# 后台启动服务
nohup mcp-toolkit --config "$CONFIG_FILE" --host "$DEFAULT_HOST" --port "$DEFAULT_PORT" --ws-port "$DEFAULT_WS_PORT" --sse-port "$DEFAULT_SSE_PORT" > "$LOG_FILE" 2>&1 &
pid=$!

# 保存 PID
echo "$pid" > "$PID_FILE"

echo "✅ MCP 服务已启动"
echo "   PID: $pid"
echo "   HTTP地址: http://$DEFAULT_HOST:$DEFAULT_PORT"
echo "   WebSocket地址: ws://$DEFAULT_HOST:$DEFAULT_WS_PORT"
echo "   SSE地址: http://$DEFAULT_HOST:$DEFAULT_SSE_PORT (用于n8n连接)"
echo "   日志: $LOG_FILE"
echo "   停止服务: kill $pid"
echo ""
echo "查看日志: tail -f $LOG_FILE"
