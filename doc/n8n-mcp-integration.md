# n8n MCP 集成指南

本文档说明如何将 MCP Toolkit 与 n8n 集成，使 n8n 能够通过 MCP 协议访问本项目提供的工具。

## 概述

MCP Toolkit 现在支持三种传输协议：
- **HTTP** (端口 8080) - 标准 JSON-RPC over HTTP
- **WebSocket** (端口 8081) - WebSocket 连接
- **SSE** (端口 8082) - Server-Sent Events，专为 n8n MCP 客户端设计

## n8n MCP 连接要求

根据 n8n 官方文档，n8n 的 MCP 客户端需要：
1. **Server-Sent Events (SSE)** 或 **streamable HTTP** 支持
2. 长连接支持
3. 不支持标准的 stdio 传输

## 配置步骤

### 1. 启动 MCP Toolkit 服务

确保服务已启动并监听所有必要端口：

```bash
# 启动服务
./scripts/run_mcp_daemon.sh

# 检查服务状态
ps aux | grep mcp-toolkit
netstat -tlnp | grep -E ':(8080|8081|8082)'
```

### 2. 验证 SSE 端点

测试 SSE 端点是否正常工作：

```bash
# 测试 SSE 连接
curl -N -H "Accept: text/event-stream" http://localhost:8082/mcp

# 测试 HTTP POST (streamable HTTP)
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### 3. n8n MCP Server Trigger 配置

在 n8n 中创建 MCP Server Trigger 节点：

1. **MCP URL**: `http://your-server-ip:8082/mcp`
2. **Authentication**: 根据需要配置认证
3. **Path**: 使用默认路径或自定义

### 4. 网络配置

确保网络连接正常：

```bash
# 本地测试
curl http://127.0.0.1:8082/health

# 局域网测试 (替换为实际IP)
curl http://192.168.1.100:8082/health

# 防火墙配置 (如果需要)
sudo ufw allow 8082/tcp
```

## 连接示例

### 基本连接测试

```bash
# 1. 测试健康检查
curl http://localhost:8082/health

# 2. 测试工具列表
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# 3. 测试工具调用
curl -X POST http://localhost:8082/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {
        "path": "./README.md"
      }
    },
    "id": 2
  }'
```

### SSE 连接测试

```bash
# 使用 curl 测试 SSE 连接
curl -N -H "Accept: text/event-stream" \
  -H "Cache-Control: no-cache" \
  http://localhost:8082/mcp
```

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 检查服务是否启动：`ps aux | grep mcp-toolkit`
   - 检查端口是否监听：`netstat -tlnp | grep 8082`
   - 检查防火墙设置

2. **SSE 连接中断**
   - 检查网络稳定性
   - 查看服务日志：`tail -f logs/mcp-toolkit.log`
   - 确认没有代理服务器干扰

3. **工具调用失败**
   - 检查工具参数格式
   - 查看详细错误日志
   - 验证文件路径权限

### 调试命令

```bash
# 查看服务日志
tail -f logs/mcp-toolkit.log

# 检查端口占用
lsof -i :8082

# 测试网络连通性
telnet localhost 8082

# 查看进程状态
ps aux | grep mcp-toolkit
```

## 高级配置

### 反向代理配置

如果使用 nginx 等反向代理，需要特殊配置 SSE：

```nginx
location /mcp/ {
    proxy_pass http://localhost:8082/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;

    # SSE 特殊配置
    proxy_buffering off;
    proxy_read_timeout 24h;
    proxy_connect_timeout 5s;

    # 禁用 gzip 压缩
    gzip off;

    # 设置正确的 MIME 类型
    proxy_set_header Accept text/event-stream;
}
```

### 安全配置

```yaml
# config/development.yaml
security:
  allowed_origins:
    - "http://your-n8n-server:5678"
    - "https://your-n8n-domain.com"
  rate_limiting:
    enabled: true
    requests_per_minute: 100
```

## 参考资源

- [n8n MCP Server Trigger 文档](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/)
- [MCP 协议规范](https://modelcontextprotocol.io/specification/)
- [Server-Sent Events 规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)
