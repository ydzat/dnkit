#!/bin/bash

# MCP 工具集第一阶段增强服务器启动脚本
# 启动基于 ChromaDB 统一存储的增强 MCP 服务器

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查 Python 环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    local python_version=$(python3 --version | cut -d' ' -f2)
    log_info "Python 版本: $python_version"
}

# 检查依赖
check_dependencies() {
    log_info "检查项目依赖..."

    cd "$PROJECT_ROOT"

    # 检查是否在虚拟环境中
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        log_info "使用虚拟环境: $VIRTUAL_ENV"
    else
        log_warn "未检测到虚拟环境，建议使用虚拟环境"
    fi

    # 安装依赖
    if [[ -f "pyproject.toml" ]]; then
        log_info "安装项目依赖..."
        pip install -e . || {
            log_error "依赖安装失败"
            exit 1
        }
    else
        log_error "未找到 pyproject.toml 文件"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    local config_file="$PROJECT_ROOT/config/enhanced_tools_config.yaml"

    if [[ -f "$config_file" ]]; then
        log_info "使用配置文件: $config_file"
    else
        log_warn "未找到配置文件，将使用默认配置"
    fi
}

# 创建必要目录
create_directories() {
    local db_dir="$PROJECT_ROOT/mcp_unified_db"
    local log_dir="$PROJECT_ROOT/logs"

    mkdir -p "$db_dir"
    mkdir -p "$log_dir"

    log_info "创建数据目录: $db_dir"
    log_info "创建日志目录: $log_dir"
}

# 启动服务器
start_server() {
    local host="${1:-localhost}"
    local port="${2:-8000}"
    local config_file="$PROJECT_ROOT/config/enhanced_tools_config.yaml"

    log_info "启动增强 MCP 服务器..."
    log_info "服务器地址: http://$host:$port"
    log_info "按 Ctrl+C 停止服务器"

    cd "$PROJECT_ROOT"

    # 设置环境变量
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    export MCP_CONFIG_FILE="$config_file"

    # 启动服务器
    python3 -m mcp_toolkit.enhanced_server || {
        log_error "服务器启动失败"
        exit 1
    }
}

# 显示帮助信息
show_help() {
    echo "MCP 工具集第一阶段增强服务器启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示帮助信息"
    echo "  -H, --host HOST         服务器主机地址 (默认: localhost)"
    echo "  -p, --port PORT         服务器端口 (默认: 8000)"
    echo "  -c, --config FILE       配置文件路径"
    echo "  --check-only            仅检查环境，不启动服务器"
    echo "  --install-deps          安装依赖后退出"
    echo ""
    echo "示例:"
    echo "  $0                      # 使用默认设置启动"
    echo "  $0 -H 0.0.0.0 -p 8080   # 指定主机和端口"
    echo "  $0 --check-only         # 仅检查环境"
}

# 主函数
main() {
    local host="localhost"
    local port="8000"
    local config_file=""
    local check_only=false
    local install_deps=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -H|--host)
                host="$2"
                shift 2
                ;;
            -p|--port)
                port="$2"
                shift 2
                ;;
            -c|--config)
                config_file="$2"
                shift 2
                ;;
            --check-only)
                check_only=true
                shift
                ;;
            --install-deps)
                install_deps=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_info "=== MCP 工具集第一阶段增强服务器 ==="

    # 检查环境
    check_python
    check_dependencies
    check_config
    create_directories

    if [[ "$install_deps" == true ]]; then
        log_info "依赖安装完成，退出"
        exit 0
    fi

    if [[ "$check_only" == true ]]; then
        log_info "环境检查完成，退出"
        exit 0
    fi

    # 启动服务器
    start_server "$host" "$port"
}

# 捕获中断信号
trap 'log_info "正在停止服务器..."; exit 0' INT TERM

# 运行主函数
main "$@"
