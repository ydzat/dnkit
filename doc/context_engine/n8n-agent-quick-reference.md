# n8n Agent 测试快速参考

## 🚀 快速开始对话

### 初始化测试
```
用户: 你好，请介绍一下你的能力，并显示当前状态。
```

### 环境验证
```
用户: 请检查 /home/ydzat/workspace/dnkit_demo 目录的状态，并验证Git仓库是否正常。
```

## 📋 核心测试对话模板

### 1. 文件操作测试
```
创建文件: 请在项目目录下创建一个名为 [文件名] 的文件，内容是 [具体内容]。

读取分析: 读取 [文件名] 并分析其代码结构和质量。

修改文件: 修改 [文件名]，添加 [具体功能]。
```

### 2. Git操作测试
```
状态检查: 检查Git仓库状态并显示未提交的更改。

提交操作: 将所有更改添加到Git并提交，提交信息为 "[提交信息]"。

历史分析: 分析Git提交历史并生成变更报告。

检查点管理: 创建一个检查点，然后演示回滚功能。
```

### 3. 代码分析测试
```
质量分析: 分析项目中所有代码文件的质量，识别潜在问题。

模式识别: 检查代码中使用的设计模式和编程模式。

性能分析: 分析代码性能瓶颈并提供优化建议。

最佳实践: 根据最佳实践标准评估代码并提供改进建议。
```

### 4. 智能补全测试
```
代码补全: 为这段代码提供智能补全建议：[代码片段]

语义理解: 分析这个项目的业务逻辑和架构设计意图。

依赖分析: 分析项目的依赖关系并生成调用图。
```

### 5. 任务管理测试
```
任务分解: 我想实现 [复杂功能]，请帮我分解任务并制定执行计划。

项目管理: 为当前项目创建任务管理和进度跟踪。

执行指导: 基于当前项目上下文，指导我如何实现 [具体功能]。
```

### 6. Agent行为测试
```
状态展示: 显示当前Agent状态和最近的操作历史。

状态控制: 切换到 [analyzing/planning/executing] 状态。

行为验证: 验证Agent行为是否符合预期规范。

学习优化: 分析执行历史并优化未来的行为模式。

错误处理: [故意提供无效输入] 测试错误处理能力。
```

## 🎯 Agent状态说明

- **idle**: 空闲状态，等待新任务
- **analyzing**: 分析任务和代码
- **planning**: 制定执行计划  
- **executing**: 执行具体操作
- **validating**: 验证执行结果
- **learning**: 学习和优化
- **collaborating**: 多Agent协作
- **error**: 错误处理状态

## 🛠️ 关键工具分类

### 文件操作 (5个)
- read_file, write_file, list_files, create_directory, enhanced_read_file

### Git集成 (4个)  
- git_diff_analysis, git_apply_patch, git_history_analysis, git_conflict_check

### 版本管理 (3个)
- undo_operation, rollback_to_checkpoint, manage_checkpoint

### 代码分析 (7个)
- analyze_code, analyze_code_quality, analyze_dependencies, build_call_graph, suggest_refactoring

### 语义智能 (4个)
- understand_semantics, get_code_completions, recognize_patterns, get_best_practices

### Agent控制 (3个)
- control_agent_state, validate_agent_behavior, optimize_agent_learning

### 任务管理 (6个)
- decompose_task, get_execution_guidance, manage_tasks, search_recent_tasks

## ⚡ 快速故障排除

### Agent无响应
```
用户: 请重置到初始状态并清理所有临时数据。
```

### 状态异常
```
用户: 显示当前状态机状态，如果异常请修复。
```

### 工具失败
```
用户: 列出所有可用工具并测试核心功能。
```

### 路径问题
```
用户: 设置工作目录为 /home/ydzat/workspace/dnkit_demo 并验证。
```

## 📊 成功指标

- ✅ Agent正确理解自然语言指令
- ✅ 状态转换逻辑清晰
- ✅ 工具选择准确合理
- ✅ 提供有价值的分析和建议
- ✅ 错误处理和恢复有效
- ✅ 响应时间 < 5秒
- ✅ 任务完成率 > 90%

## 🎪 高级测试场景

### 端到端工作流
```
用户: 从零开始创建一个Python Web API项目，包括项目结构、核心代码、测试用例和Git管理。
```

### 代码重构
```
用户: 分析现有代码，识别重构机会，并实施改进。
```

### 问题诊断
```
用户: 这段代码有性能问题，请帮我诊断并修复。
```

### 架构设计
```
用户: 为一个用户管理系统设计架构，并生成核心代码框架。
```

使用这个快速参考，您可以高效地测试Agent的各项能力！
