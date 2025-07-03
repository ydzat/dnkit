# Logloom日志系统配置规范

## 1. 配置文件结构

MCP工具集采用Logloom作为统一日志系统，配置文件为`config/runtime/logloom.yaml`。

### 1.1 基础配置格式
```yaml
logloom:
  # 语言设置
  language: "zh"  # 支持 "zh", "en" 等

  # 日志配置
  log:
    level: "INFO"           # DEBUG, INFO, WARN, ERROR, FATAL
    file: "logs/mcp-toolkit.log"
    max_size: 10485760      # 10MB，字节数
    console: true           # 是否输出到控制台

  # 国际化资源
  locale:
    directory: "i18n"       # 翻译文件目录
    pattern: "*.yaml"       # 文件匹配模式
```

### 1.2 模块化日志配置
```yaml
logloom:
  language: "zh"

  # 全局默认配置
  log:
    level: "INFO"
    console: true

  # 模块特定配置
  modules:
    protocol_handler:
      file: "logs/protocol.log"
      level: "DEBUG"
      max_size: 5242880     # 5MB

    tool_registry:
      file: "logs/tools.log"
      level: "INFO"
      max_size: 5242880

    contextengine:
      file: "logs/context.log"
      level: "WARN"
      max_size: 2097152     # 2MB

    security:
      file: "logs/security.log"
      level: "INFO"
      max_size: 10485760    # 10MB（安全日志保留更多）
```

## 2. 日志使用规范

### 2.1 Python集成示例
```python
import logloom_py as ll

# 系统启动时初始化
def initialize_logging():
    config_path = "config/runtime/logloom.yaml"
    if not ll.initialize(config_path):
        print("日志系统初始化失败")
        return False
    return True

# 创建模块日志记录器
class ProtocolHandler:
    def __init__(self):
        self.logger = ll.Logger("protocol_handler")

    def handle_request(self, request):
        self.logger.info("收到请求: {}", request.id)
        try:
            # 处理逻辑
            result = self.process_request(request)
            self.logger.debug("请求处理完成: {} -> {}", request.id, result.status)
            return result
        except Exception as e:
            self.logger.error("请求处理失败: {}", str(e), exc_info=e)
            raise

# 全局日志记录
def log_system_event(event_type, message):
    ll.info("system", f"{event_type}: {message}")

# 程序退出时清理
def cleanup_logging():
    ll.cleanup()
```

### 2.2 日志级别使用指南

- **DEBUG**: 详细的调试信息，包括函数调用、变量值等
- **INFO**: 重要的业务流程信息，如请求开始/结束、操作成功等
- **WARN**: 潜在问题或异常情况，不影响正常流程
- **ERROR**: 错误情况，操作失败但系统可继续运行
- **FATAL**: 致命错误，系统无法继续运行

### 2.3 国际化日志消息
```python
# 使用翻译键记录日志
logger.info(ll.get_text("system.startup_complete"))
logger.error(ll.format_text("error.tool_not_found", tool_name="example"))

# 自定义翻译资源注册
ll.register_locale_directory("config/i18n")
```

## 3. 翻译资源格式

### 3.1 中文翻译文件 (i18n/zh.yaml)
```yaml
system:
  startup_complete: "MCP工具集启动完成"
  shutdown_begin: "正在关闭MCP工具集"
  config_loaded: "配置文件加载成功: {0}"

protocol:
  request_received: "收到MCP请求: {method} from {client}"
  response_sent: "发送MCP响应: {status} ({duration}ms)"
  connection_established: "建立新连接: {client_id}"
  connection_closed: "连接已关闭: {client_id}"

tools:
  tool_registered: "工具注册成功: {tool_name}"
  tool_unregistered: "工具注销: {tool_name}"
  tool_execution_start: "开始执行工具: {tool_name}"
  tool_execution_complete: "工具执行完成: {tool_name} ({duration}ms)"

error:
  tool_not_found: "工具未找到: {tool_name}"
  permission_denied: "权限不足: {operation}"
  invalid_request: "无效请求: {reason}"
  system_error: "系统错误: {message}"
```

### 3.2 英文翻译文件 (i18n/en.yaml)
```yaml
system:
  startup_complete: "MCP Toolkit startup complete"
  shutdown_begin: "Shutting down MCP Toolkit"
  config_loaded: "Configuration loaded successfully: {0}"

protocol:
  request_received: "MCP request received: {method} from {client}"
  response_sent: "MCP response sent: {status} ({duration}ms)"
  connection_established: "New connection established: {client_id}"
  connection_closed: "Connection closed: {client_id}"

tools:
  tool_registered: "Tool registered successfully: {tool_name}"
  tool_unregistered: "Tool unregistered: {tool_name}"
  tool_execution_start: "Tool execution started: {tool_name}"
  tool_execution_complete: "Tool execution completed: {tool_name} ({duration}ms)"

error:
  tool_not_found: "Tool not found: {tool_name}"
  permission_denied: "Permission denied: {operation}"
  invalid_request: "Invalid request: {reason}"
  system_error: "System error: {message}"
```

## 4. 监控和运维

### 4.1 日志文件管理
- 自动轮转：文件达到max_size时自动轮转
- 文件命名：原文件重命名为`.1`, `.2`等
- 保留策略：建议保留最近7天的日志文件

### 4.2 性能考虑
- 异步日志写入，减少对主线程的影响
- 批量写入策略，提高I/O效率
- 合理设置日志级别，避免过多DEBUG日志

### 4.3 故障排查
- 检查配置文件格式和路径
- 确认日志目录写权限
- 监控日志文件大小和磁盘空间
- 定期清理旧日志文件

## 5. 与现有系统集成

### 5.1 ContextEngine集成
```python
# contextengine/demo_llm_integration.py 中的使用
import logloom_py as ll

class ContextEngineDemo:
    def __init__(self):
        self.logger = ll.Logger("contextengine")

    def process_context(self, context):
        self.logger.info(ll.get_text("contextengine.processing_start"))
        # 处理逻辑...
        self.logger.debug("上下文处理完成: {} tokens", context.token_count)
```

### 5.2 MCP协议处理集成
```python
# 协议处理器中的日志记录
class MCPProtocolHandler:
    def __init__(self):
        self.logger = ll.Logger("protocol")

    def handle_tools_list(self, request):
        self.logger.info(ll.get_text("protocol.request_received",
                                   method="tools/list", client=request.client_id))
        # 处理逻辑...
```

此配置规范确保MCP工具集的所有组件使用统一的日志系统，便于运维管理和故障排查。
