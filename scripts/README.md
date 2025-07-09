<!--
 * @Author: @ydzat
 * @Date: 2025-07-08 21:27:54
 * @LastEditors: @ydzat
 * @LastEditTime: 2025-07-08 22:20:22
 * @Description:
-->
# MCP Toolkit 后台运行脚本

## 使用方法

### 启动服务
```bash
./scripts/run_mcp_daemon.sh
```

### 查看日志
```bash
tail -f logs/mcp-toolkit.log
```

### 停止服务
```bash
# 方法1: 使用 PID 文件中的进程ID
kill $(cat logs/mcp-toolkit.pid)

# 方法2: 直接杀死进程
pkill -f mcp-toolkit
```

### 检查服务状态
```bash
# 检查进程是否运行
ps aux | grep mcp-toolkit

# 检查端口是否被占用
netstat -tlnp | grep :8080
```

## 文件说明

- `scripts/run_mcp_daemon.sh` - 后台启动脚本
- `logs/mcp-toolkit.pid` - 进程ID文件
- `logs/mcp-toolkit.log` - 服务日志文件
- `config/development.yaml` - 配置文件

## 网络访问

服务同时提供HTTP、WebSocket和SSE支持：

### HTTP服务 (端口8080)
- 本地访问: `http://127.0.0.1:8080`
- 局域网访问: `http://<设备IP>:8080`
- ZeroTier网络访问: `http://<ZeroTier IP>:8080`

### WebSocket服务 (端口8081)
- 本地访问: `ws://127.0.0.1:8081`
- 局域网访问: `ws://<设备IP>:8081`
- ZeroTier网络访问: `ws://<ZeroTier IP>:8081`

### SSE服务 (端口8082) - 用于n8n MCP连接
- 本地访问: `http://127.0.0.1:8082`
- 局域网访问: `http://<设备IP>:8082`
- ZeroTier网络访问: `http://<ZeroTier IP>:8082`

## 注意事项

1. 确保已安装依赖: `uv sync`
2. 脚本会自动检查虚拟环境是否存在
3. 重复运行脚本会检查服务是否已启动，避免重复启动
4. 服务绑定到所有网络接口，HTTP端口8080，WebSocket端口8081，SSE端口8082
5. 确保防火墙允许8080、8081和8082端口的访问
