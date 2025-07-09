# n8n MCP 连接配置示例

## 服务器信息

你的MCP Toolkit服务器现在已经支持n8n连接：

- **SSE端点**: `http://your-server-ip:8082/mcp`
- **健康检查**: `http://your-server-ip:8082/health`
- **支持的传输**: Server-Sent Events (SSE) 和 streamable HTTP

## n8n MCP Server Trigger 配置

### 1. 基本配置

在n8n中创建MCP Server Trigger节点，使用以下配置：

```
MCP URL: http://your-server-ip:8082/mcp
Path: /mcp (或保持默认)
Authentication: 根据需要配置
```

### 2. 本地测试配置

如果n8n和MCP Toolkit在同一台机器上：

```
MCP URL: http://localhost:8082/mcp
```

### 3. 局域网配置

如果n8n在局域网的另一台机器上：

```
MCP URL: http://192.168.1.100:8082/mcp
```
（替换为你的实际IP地址）

### 4. 远程配置

如果需要通过互联网访问，建议使用反向代理或VPN。

## 可用工具

你的MCP服务器提供以下工具：

1. **read_file** - 读取文件内容
2. **write_file** - 写入文件内容
3. **list_files** - 列出目录文件
4. **create_directory** - 创建目录
5. **run_command** - 执行系统命令
6. **get_environment** - 获取环境变量
7. **set_working_directory** - 设置工作目录
8. **http_request** - 发送HTTP请求
9. **dns_lookup** - DNS查询
10. **file_search** - 搜索文件
11. **content_search** - 搜索文件内容

## 测试连接

### 1. 健康检查

```bash
curl http://your-server-ip:8082/health
```

预期响应：
```json
{"status": "healthy", "connections": 0, "max_connections": 100}
```

### 2. 工具列表

```bash
curl -X POST http://your-server-ip:8082/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### 3. SSE连接测试

```bash
curl -N -H "Accept: text/event-stream" \
  -H "Cache-Control: no-cache" \
  http://your-server-ip:8082/mcp
```

预期看到连接事件：
```
event: connected
data: {"connection_id": "uuid-here"}
```

## 故障排除

### 连接问题

1. **检查服务状态**:
   ```bash
   ps aux | grep mcp-toolkit
   netstat -tlnp | grep 8082
   ```

2. **检查防火墙**:
   ```bash
   sudo ufw status
   sudo ufw allow 8082/tcp
   ```

3. **查看日志**:
   ```bash
   tail -f logs/mcp-toolkit.log
   ```

### 常见错误

- **连接被拒绝**: 检查服务是否启动，端口是否正确
- **超时**: 检查网络连接和防火墙设置
- **认证失败**: 确认认证配置正确

## 高级配置

### 反向代理 (nginx)

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

在 `config/development.yaml` 中：

```yaml
security:
  allowed_origins:
    - "http://your-n8n-server:5678"
    - "https://your-n8n-domain.com"
  rate_limiting:
    enabled: true
    requests_per_minute: 100
```

## 使用示例

在n8n工作流中，你可以：

1. 使用 `read_file` 工具读取配置文件
2. 使用 `http_request` 工具调用API
3. 使用 `run_command` 工具执行系统命令
4. 使用 `file_search` 工具查找特定文件
5. 使用 `content_search` 工具在文件中搜索内容

这些工具可以帮助你在n8n工作流中实现复杂的自动化任务。
