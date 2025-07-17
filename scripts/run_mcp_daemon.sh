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
    echo "     - 上下文引擎工具 (代码分析)"
    echo "     - 任务管理系统 (智能任务跟踪)"
    echo "     - 记忆管理系统 (知识积累)"
    echo "     - 可视化工具 (图表生成)"
    echo "     - 工具协作框架 (链式调用)"
fi

echo "   日志: $LOG_FILE"
echo "   停止服务: kill $pid"
echo ""
echo "查看日志: tail -f $LOG_FILE"

# 如果是增强模式，显示额外信息
if [[ "$ENHANCED_MODE" == true ]]; then
    echo ""
    echo "💡 增强功能使用提示 (共54个工具):"
    echo ""
    echo "   📁 基础工具 (12个):"
    echo "     文件系统: read_file, write_file, list_files, create_directory"
    echo "     网络工具: http_request, dns_lookup"
    echo "     搜索工具: file_search, content_search"
    echo "     系统工具: run_command, get_environment, set_working_directory"
    echo "     实用工具: echo"
    echo ""
    echo "   🧠 增强工具 (6个):"
    echo "     智能文件: enhanced_read_file (ChromaDB存储), search_files (语义搜索)"
    echo "     智能网络: enhanced_fetch_web (网页存储), search_web_content (语义搜索)"
    echo "     智能系统: get_system_info (系统信息), manage_processes (进程管理)"
    echo ""
    echo "   🤖 上下文引擎 (4个):"
    echo "     代码分析: analyze_code (多语言代码分析+ChromaDB存储)"
    echo "     智能搜索: search_code (自然语言代码搜索)"
    echo "     相似搜索: find_similar_code (语义相似度搜索)"
    echo "     项目分析: get_project_overview (项目统计概览)"
    echo ""
    echo "   🔄 Git集成工具 (4个):"
    echo "     差异分析: git_diff_analysis (智能Git差异分析)"
    echo "     补丁管理: git_apply_patch (精确补丁应用)"
    echo "     历史分析: git_history_analysis (Git历史追踪)"
    echo "     冲突检测: git_conflict_check (合并冲突检测)"
    echo ""
    echo "   ⏱️  版本管理 (3个):"
    echo "     操作追踪: undo_operation (撤销代理操作)"
    echo "     检查点回滚: rollback_to_checkpoint (回滚到检查点)"
    echo "     检查点管理: manage_checkpoint (创建/列出/删除检查点)"
    echo ""
    echo "   🤝 Agent自动化 (2个):"
    echo "     任务分解: decompose_task (复杂任务分解为子任务)"
    echo "     执行指导: get_execution_guidance (任务执行指导和建议)"
    echo ""
    echo "   📈 智能分析 (3个):"
    echo "     代码质量: analyze_code_quality (代码质量分析和改进建议)"
    echo "     性能监控: monitor_performance (系统性能指标监控)"
    echo "     历史趋势: analyze_history_trends (历史数据趋势分析)"
    echo ""
    echo "   🎯 Agent行为 (3个):"
    echo "     状态控制: control_agent_state (Agent状态机控制)"
    echo "     行为验证: validate_agent_behavior (行为一致性验证)"
    echo "     学习优化: optimize_agent_learning (基于历史优化学习)"
    echo ""
    echo "   🔍 上下文引擎深度 (3个):"
    echo "     依赖分析: analyze_dependencies (代码依赖关系分析)"
    echo "     调用图: build_call_graph (函数调用关系图构建)"
    echo "     重构建议: suggest_refactoring (代码重构建议)"
    echo ""
    echo "   💡 语义智能 (4个):"
    echo "     语义理解: understand_semantics (业务逻辑和设计模式理解)"
    echo "     代码补全: get_code_completions (智能代码补全建议)"
    echo "     模式识别: recognize_patterns (设计模式和编程模式识别)"
    echo "     最佳实践: get_best_practices (最佳实践建议)"
    echo ""
    echo "   � 任务管理 (4个):"
    echo "     任务管理: manage_tasks (创建/更新/删除/查询+ChromaDB存储)"
    echo "     专项搜索: search_recent_tasks (最近任务搜索)"
    echo "     时间搜索: search_tasks_by_time (时间范围搜索)"
    echo "     语义搜索: search_tasks_semantic (内容语义搜索)"
    echo ""
    echo "   🧠 记忆系统 (1个):"
    echo "     记忆管理: manage_memory (知识/对话/经验/技能的存储与检索)"
    echo ""
    echo "   📊 可视化工具 (4个):"
    echo "     图表生成: generate_diagram (Mermaid流程图/时序图/思维导图)"
    echo "     数据图表: create_data_chart (Chart.js数据可视化)"
    echo "     复杂图表: generate_subgraph_diagram (嵌套子图)"
    echo "     状态机图: generate_state_machine (状态机和自动机图)"
    echo ""
    echo "   🔗 工具协作 (1个):"
    echo "     工作流执行: execute_tool_chain (链式执行/并行处理/数据流)"
    echo ""
    echo "   核心特性:"
    echo "     - ChromaDB统一向量数据库存储"
    echo "     - 多语言代码分析支持"
    echo "     - 自然语言查询处理"
    echo "     - AI驱动的语义搜索"
    echo "     - 完整的MCP协议兼容性"
    echo "     - Agent智能化和自动化支持"
    echo "     - 深度代码理解和分析能力"
fi
