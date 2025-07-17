# n8n Agent 高级配置参考

## 🎛️ Agent节点完整配置

### 基础设置
```yaml
Agent Node:
  Model: OpenAI GPT-4 / Claude-3.5-Sonnet
  Instructions: [使用完整的系统prompt]

  Options:
    Max Iterations: 30
    Return Intermediate Steps: true
    Require Specific Output Format: true
    System Message: "你是专业的MCP自动化编程助手"
```

### 输出格式Schema (JSON)
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "error", "in_progress"],
      "description": "执行状态"
    },
    "current_state": {
      "type": "string",
      "enum": ["idle", "analyzing", "planning", "executing", "validating", "learning", "collaborating", "error"],
      "description": "Agent当前状态"
    },
    "action_taken": {
      "type": "string",
      "description": "执行的具体操作描述"
    },
    "tools_used": {
      "type": "array",
      "items": {"type": "string"},
      "description": "使用的工具名称列表"
    },
    "result": {
      "type": "object",
      "description": "操作结果的详细信息"
    },
    "next_steps": {
      "type": "array",
      "items": {"type": "string"},
      "description": "建议的后续步骤"
    },
    "execution_time": {
      "type": "number",
      "description": "执行时间（秒）"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "结果置信度"
    }
  },
  "required": ["status", "current_state", "action_taken", "tools_used"]
}
```

### 备用模型配置
```yaml
Fallback Model:
  Primary Model:
    Provider: OpenAI
    Model: gpt-4
    Temperature: 0.1
    Max Tokens: 4000

  Fallback Model:
    Provider: OpenAI  
    Model: gpt-3.5-turbo
    Temperature: 0.2
    Max Tokens: 2000

  Trigger Conditions:
    - Rate limit exceeded
    - Model unavailable
    - Response timeout (>30s)
    - Invalid response format
```

## 🧠 Memory配置

### Vector Memory (推荐)
```yaml
Memory Type: Vector Memory
Vector Store: Pinecone
Embedding Model: text-embedding-3-small
Dimensions: 1536
Index Name: mcp-agent-memory
Namespace: user-sessions

Configuration:
  Max Memory Items: 1000
  Similarity Threshold: 0.7
  Memory Decay: 7 days
  Context Window: 10 messages
```

### Simple Memory (基础)
```yaml
Memory Type: Simple Memory
Max Items: 100
Context Window: 20 messages
Persistence: Session-based
```

## 🔧 工具验证表达式

### 系统prompt中的动态检查
```javascript
## 系统状态检查

工具可用性检查:
{{ $agentInfo.tools.length >= 50 ?
   '✅ 工具集完整(' + $agentInfo.tools.length + '个工具)' :
   '⚠️ 工具集不完整，当前仅' + $agentInfo.tools.length + '个工具' }}

关键工具检查:
{{ $agentInfo.tools.find(t => t.name === 'control_agent_state') ? '✅ 状态管理' : '❌ 状态管理' }}
{{ $agentInfo.tools.find(t => t.name === 'git_diff_analysis') ? '✅ Git集成' : '❌ Git集成' }}
{{ $agentInfo.tools.find(t => t.name === 'analyze_code_quality') ? '✅ 代码分析' : '❌ 代码分析' }}
{{ $agentInfo.tools.find(t => t.name === 'understand_semantics') ? '✅ 语义理解' : '❌ 语义理解' }}

记忆系统:
{{ $agentInfo.memoryConnectedToAgent ? '✅ 记忆系统已连接' : '⚠️ 建议连接记忆系统' }}

当前环境:
- 时间: {{ $now.toISO() }}
- 会话ID: {{ $execution.id }}
- 工作目录: 需要用户提供
```

### 条件化任务处理
```javascript
任务类型检测:
{{ $json.chatInput.toLowerCase().includes('创建') || $json.chatInput.toLowerCase().includes('生成') ?
   '🔨 检测到创建任务，准备执行模式' : '' }}
{{ $json.chatInput.toLowerCase().includes('分析') || $json.chatInput.toLowerCase().includes('检查') ?
   '🔍 检测到分析任务，准备分析模式' : '' }}
{{ $json.chatInput.toLowerCase().includes('git') || $json.chatInput.toLowerCase().includes('提交') ?
   '📝 检测到Git任务，准备版本控制模式' : '' }}
```

## 📊 监控和调试

### 调试模式配置
```javascript
// 在Variables中设置 DEBUG_MODE = true
{{ $vars.DEBUG_MODE ? `
🔍 调试模式已启用
- 详细日志: 开启
- 执行步骤: 显示
- 工具调用: 记录
- 状态转换: 追踪
` : '' }}
```

### 性能监控
```javascript
性能指标:
- 响应时间目标: < 5秒
- 工具调用成功率: > 95%
- 状态转换准确率: 100%
- 用户满意度: > 90%

当前会话统计:
- 执行时间: {{ $execution.startedAt ? ($now.toMillis() - $execution.startedAt.toMillis()) / 1000 : 0 }}秒
- 工具调用次数: [动态统计]
- 状态转换次数: [动态统计]
```

## 🚨 错误处理配置

### 错误恢复策略
```javascript
错误处理级别:
{{ $agentInfo.tools.find(t => t.name === 'validate_agent_behavior') ?
   '1. 自动状态验证和修复' : '1. 基础错误处理' }}
2. 工具调用重试机制 (最多3次)
3. 备用模型自动切换
4. 用户友好的错误说明

常见错误处理:
- 工具不可用: 提供替代方案
- 参数错误: 自动修正或请求澄清
- 超时错误: 分解任务或简化操作
- 权限错误: 指导用户解决权限问题
```

## 🎯 生产环境检查清单

### 部署前检查
- [ ] MCP服务器运行正常 (54个工具)
- [ ] 主模型和备用模型配置正确
- [ ] 输出格式Schema验证通过
- [ ] Memory系统连接正常
- [ ] 错误处理机制测试通过
- [ ] 性能基准测试完成
- [ ] 安全配置审查完成

### 运行时监控
- [ ] 响应时间 < 5秒
- [ ] 工具调用成功率 > 95%
- [ ] 内存使用 < 1GB
- [ ] 错误率 < 1%
- [ ] 用户满意度 > 90%

### 维护任务
- [ ] 定期清理Memory数据
- [ ] 更新工具定义
- [ ] 优化系统prompt
- [ ] 监控模型性能
- [ ] 备份配置和数据

这个高级配置将确保您的Agent在生产环境中稳定、高效、智能地运行！
