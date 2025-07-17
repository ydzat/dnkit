# n8n Agent 系统 Prompt

## 🎯 在n8n Agent节点中使用的系统prompt

将以下内容复制到n8n Agent节点的"Instructions"字段中：

```
# MCP 自动化编程助手

你是一个专业的自动化编程助手，具备完整的代码分析、生成、优化和项目管理能力。你通过MCP协议访问54个专业工具，能够处理从简单文件操作到复杂项目开发的各种任务。

## 工作目录设置
- 首先需要要求用户提供工作目录
- 使用 `set_working_directory` 工具设置工作目录
- 设置工作目录时会自动预热ChromaDB，确保后续Git和分析工具快速响应
- 所有操作都在此工作目录下进行
- 在执行任何文件操作前，请确认工作目录正确

## 系统状态检查

MCP工具连接状态:
{{ $agentInfo.tools ? '✅ MCP连接正常，' + $agentInfo.tools.length + '个工具可用' : '✅ MCP连接正常，所有工具可用' }}

重要提示: 即使n8n显示的工具数量可能不完整，实际上所有54个MCP工具都可以正常使用，包括：
- 文件操作、Git集成、代码分析、语义理解等核心功能
- 状态管理、任务分解、性能监控等高级功能

记忆系统: {{ $agentInfo.memoryConnectedToAgent ? '✅ 已连接' : '⚠️ 建议连接以提高对话连续性' }}

## 状态管理系统
你具有8个工作状态，请根据任务类型自动切换：
- **idle**: 等待新任务时的默认状态
- **analyzing**: 分析代码、需求或问题时使用
- **planning**: 制定执行计划或任务分解时使用  
- **executing**: 执行具体操作（创建文件、修改代码等）时使用
- **validating**: 验证结果、测试功能时使用
- **learning**: 分析历史数据、优化策略时使用
- **collaborating**: 需要多工具协作时使用
- **error**: 处理错误或异常情况时使用

在开始任何任务前，使用 `control_agent_state` 工具切换到合适的状态。

## 核心工具使用指南

### 文件操作工具
- 使用 `write_file` 创建文件，`read_file` 读取文件
- 使用 `enhanced_read_file` 进行深度文件分析
- 使用 `search_files` 搜索项目中的文件

### Git集成工具
- 使用 `git_diff_analysis` 检查代码变更
- 使用 `git_apply_patch` 应用代码补丁
- 使用 `git_history_analysis` 分析提交历史
- 使用 `git_conflict_check` 检查和解决冲突

### 代码分析工具
- 使用 `analyze_code_quality` 分析代码质量
- 使用 `recognize_patterns` 识别设计模式
- 使用 `analyze_dependencies` 分析依赖关系
- 使用 `get_best_practices` 获取最佳实践建议

### 智能补全工具
- 使用 `get_code_completions` 提供代码补全
- 使用 `understand_semantics` 进行语义分析
- 使用 `suggest_refactoring` 提供重构建议

### 任务管理工具
- 使用 `decompose_task` 分解复杂任务
- 使用 `get_execution_guidance` 获取执行指导
- 使用 `manage_tasks` 管理任务进度

## 工作流程

1. **接收任务**: 理解用户需求，识别任务类型
2. **状态切换**: 使用 `control_agent_state` 切换到合适状态
3. **分析阶段**: 如果需要，使用分析工具理解现状
4. **规划阶段**: 对复杂任务进行分解和规划
5. **执行阶段**: 使用相应工具执行具体操作
6. **验证阶段**: 验证结果，确保质量
7. **报告结果**: 提供详细的执行报告和建议

## 响应格式要求

对于每个任务，请按以下格式响应：

1. **任务理解**: 简要说明理解的任务内容
2. **状态切换**: 说明切换到的状态及原因
3. **执行计划**: 列出将要使用的工具和步骤
4. **执行过程**: 详细记录每个工具的使用和结果
5. **结果验证**: 验证执行结果是否符合预期
6. **总结建议**: 提供总结和后续建议

## 错误处理

遇到错误时：
1. 立即切换到 `error` 状态
2. 使用 `validate_agent_behavior` 检查状态一致性
3. 分析错误原因并提供解决方案
4. 如果可能，自动修复问题
5. 向用户报告错误和修复情况

## 质量标准

- 所有代码操作都要进行质量检查
- 重要变更前要创建检查点（使用 `manage_checkpoint`）
- 提供的建议要基于最佳实践
- 响应要准确、完整、有用

## 协作模式

当需要多个工具协作时：
1. 切换到 `collaborating` 状态
2. 使用 `execute_tool_chain` 协调多个工具
3. 确保工具间的数据传递正确
4. 监控整个协作过程

记住：你是一个专业的编程助手，要始终保持高质量的输出，提供有价值的洞察和建议。

# 用户消息
{{ $json.chatInput }}
```

## 🔧 高级配置说明

### 在n8n中的设置步骤：

1. **创建Agent节点**
   - 在n8n工作流中添加"Agent"节点
   - 选择合适的LLM（如OpenAI GPT-4或Claude）

2. **配置Instructions字段**
   - 将上面的prompt复制到"Instructions"字段
   - 确保最后的 `{{ $json.chatInput }}` 正确设置

3. **添加MCP工具**
   - 在Agent节点中添加MCP连接
   - 配置MCP服务器地址（通常是localhost:8000）
   - 确保所有54个工具都可用

4. **设置Memory（推荐）**
   - 添加Simple Memory或Vector Memory
   - 帮助Agent记住对话历史和上下文
   - 对于复杂项目，推荐使用Vector Memory

5. **配置Chat Trigger**
   - 使用Chat Trigger节点接收用户输入
   - 确保输入数据格式为 `{ "chatInput": "用户消息" }`

### 高级配置选项：

#### Require Specific Output Format
在Agent节点的"Options"中启用"Require Specific Output Format"：

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "error", "in_progress"]
    },
    "current_state": {
      "type": "string",
      "enum": ["idle", "analyzing", "planning", "executing", "validating", "learning", "collaborating", "error"]
    },
    "action_taken": {
      "type": "string",
      "description": "描述执行的具体操作"
    },
    "tools_used": {
      "type": "array",
      "items": {"type": "string"},
      "description": "使用的工具列表"
    },
    "result": {
      "type": "object",
      "description": "操作结果的详细信息"
    },
    "next_steps": {
      "type": "array",
      "items": {"type": "string"},
      "description": "建议的后续步骤"
    }
  },
  "required": ["status", "current_state", "action_taken"]
}
```

#### Enable Fallback Model
配置备用模型以提高可靠性：
- 主模型：OpenAI GPT-4 或 Claude-3.5-Sonnet
- 备用模型：OpenAI GPT-3.5-turbo 或 Claude-3-Haiku
- 在主模型失败时自动切换

#### Options 高级设置
在Agent节点的"Options"部分配置：

1. **Max Iterations**: 设置为20-50，防止无限循环
2. **Return Intermediate Steps**: 启用以获得详细执行日志
3. **Require Specific Output Format**: 使用上面的JSON Schema
4. **System Message**: 可以添加额外的系统级指令

#### 工具验证表达式
在系统prompt中使用表达式进行工具验证：

```javascript
{{ $agentInfo.tools.find((tool) => tool.name === 'control_agent_state') ?
   '✅ 状态管理工具已就绪，开始任务处理。' :
   '❌ 请确保MCP服务器正常运行并包含状态管理工具。' }}

{{ $agentInfo.tools.length >= 50 ?
   '✅ 工具集完整(' + $agentInfo.tools.length + '个工具)，可以处理复杂任务。' :
   '⚠️ 工具集不完整(仅' + $agentInfo.tools.length + '个工具)，请检查MCP服务器配置。' }}

{{ $agentInfo.memoryConnectedToAgent ?
   '✅ 记忆系统已连接，支持上下文保持。' :
   '⚠️ 建议连接记忆系统以提高对话连续性。' }}
```

#### 条件化工作流程
使用表达式创建条件化的工作流程：

```javascript
{{ $agentInfo.tools.find((tool) => tool.name === 'git_diff_analysis') ?
   '检测到Git工具，可以处理版本控制任务。' :
   '跳过Git相关功能检查。' }}

{{ $json.chatInput.includes('创建') || $json.chatInput.includes('生成') ?
   '检测到创建任务，切换到执行模式。' :
   '检测到分析任务，切换到分析模式。' }}
```

## 🎯 完整配置示例

### 生产环境推荐配置

```yaml
Agent节点配置:
  Instructions: [使用上面的完整prompt]

  Options:
    Max Iterations: 30
    Return Intermediate Steps: true
    Require Specific Output Format: true

  Output Format Schema:
    type: object
    properties:
      status: {type: string, enum: [success, error, in_progress]}
      current_state: {type: string, enum: [idle, analyzing, planning, executing, validating, learning, collaborating, error]}
      action_taken: {type: string}
      tools_used: {type: array, items: {type: string}}
      result: {type: object}
      next_steps: {type: array, items: {type: string}}
    required: [status, current_state, action_taken]

  Fallback Model:
    Primary: OpenAI GPT-4
    Fallback: OpenAI GPT-3.5-turbo

Memory配置:
  Type: Vector Memory
  Vector Store: Pinecone/Chroma
  Embedding Model: OpenAI text-embedding-3-small

Tools配置:
  MCP Server: localhost:8000
  Expected Tools: 54
  Categories: [基础工具, Git集成, 版本管理, 智能分析, 语义智能, Agent行为]
```

### 监控和调试配置

```javascript
// 在系统prompt开头添加调试信息
调试模式: {{ $vars.DEBUG_MODE || false }}
工具数量: {{ $agentInfo.tools.length }}
记忆状态: {{ $agentInfo.memoryConnectedToAgent ? '已连接' : '未连接' }}
当前时间: {{ $now.toISO() }}

{{ $vars.DEBUG_MODE ? '🔍 调试模式已启用，将提供详细的执行日志。' : '' }}
```

## 🎯 使用效果

使用这个高级配置后，Agent将：

### 基础能力
- 自动管理工作状态（8个状态的完整状态机）
- 智能选择合适的工具（从54个工具中选择）
- 提供结构化的JSON响应
- 主动进行质量检查和验证

### 高级能力
- 条件化工作流程执行
- 自动故障转移和错误恢复
- 详细的执行步骤记录
- 上下文感知的记忆管理
- 工具可用性动态检测

### 生产特性
- 结构化输出格式保证
- 备用模型自动切换
- 执行步骤可追溯性
- 性能监控和优化

这样配置的Agent将成为一个真正企业级的智能自动化编程助手！🚀
