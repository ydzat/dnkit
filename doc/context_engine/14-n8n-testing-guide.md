# n8n Agent 测试指南

## 🎯 测试目标

本指南将帮助您在 n8n 中通过 ChatBox 与 Agent 进行自然语言交互，测试 MCP 工具集的所有功能，验证自动化编程服务的完整性和可靠性。

## 🤖 Agent 自动机系统概述

我们的 Agent 具有完整的状态机控制系统，包含以下状态：
- **idle** - 空闲状态，等待任务
- **analyzing** - 分析任务和代码
- **planning** - 制定执行计划
- **executing** - 执行具体操作
- **validating** - 验证执行结果
- **learning** - 学习和优化
- **collaborating** - 多Agent协作
- **error** - 错误处理状态

## 📁 测试环境

- **测试仓库**: `/home/ydzat/workspace/dnkit_demo` (GitHub空库已克隆)
- **MCP服务器**: 已启动并运行54个工具
- **Agent状态**: 通过 `control_agent_state` 工具管理

## � 自然语言测试指令

### 阶段1：基础功能测试 (30分钟)

#### 1.1 文件操作测试

**与Agent的对话示例：**

```
用户: 请在 /home/ydzat/workspace/dnkit_demo 目录下创建一个名为 hello.py 的文件，内容是一个简单的 Hello World 函数。

Agent预期行为:
1. 使用 control_agent_state 切换到 analyzing 状态
2. 使用 write_file 工具创建文件
3. 使用 read_file 验证文件创建成功
4. 使用 analyze_code 分析代码结构
5. 切换到 idle 状态并报告结果
```

**后续测试对话：**

```
用户: 读取刚才创建的 hello.py 文件内容，并分析其代码质量。

Agent预期行为:
1. 使用 read_file 读取文件
2. 使用 analyze_code_quality 分析代码质量
3. 提供改进建议
```

**高级测试对话：**

```
用户: 请搜索项目中所有的 Python 文件，并生成一个项目概览报告。

Agent预期行为:
1. 使用 search_files 搜索 .py 文件
2. 使用 get_project_overview 生成概览
3. 使用 analyze_dependencies 分析依赖关系
4. 生成结构化报告
```

#### 1.2 Git 操作测试

**基础Git操作对话：**

```
用户: 请检查当前Git仓库的状态，然后将刚才创建的hello.py文件添加到Git并提交。

Agent预期行为:
1. 切换到 analyzing 状态
2. 使用 git_diff_analysis 检查仓库状态
3. 使用 run_command 执行 git add hello.py
4. 使用 run_command 执行 git commit -m "Add hello.py"
5. 使用 git_history_analysis 验证提交
6. 报告操作结果
```

**版本管理测试对话：**

```
用户: 为当前状态创建一个检查点，然后修改hello.py文件，再演示如何回滚到检查点。

Agent预期行为:
1. 使用 manage_checkpoint 创建检查点
2. 修改文件内容 (使用 write_file)
3. 使用 git_diff_analysis 显示变更
4. 使用 rollback_to_checkpoint 回滚
5. 验证回滚结果
```

**冲突处理测试对话：**

```
用户: 模拟一个Git冲突场景，并演示如何解决冲突。

Agent预期行为:
1. 使用 git_conflict_check 检查冲突
2. 分析冲突内容
3. 提供解决方案
4. 使用相关工具解决冲突
```

### 阶段2：智能分析测试 (45分钟)

#### 2.1 代码质量分析

**复杂代码分析对话：**

```
用户: 请创建一个包含复杂逻辑的Python文件，然后分析其代码质量并提供改进建议。

Agent预期行为:
1. 切换到 planning 状态
2. 使用 write_file 创建复杂代码文件
3. 使用 analyze_code_quality 分析质量指标
4. 使用 get_best_practices 获取改进建议
5. 使用 recognize_patterns 识别代码模式
6. 提供详细的分析报告和重构建议
```

**示例复杂代码内容：**
```python
def complex_function(a, b, c, d, e, f):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return f
    return 0

class LargeClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
```

**性能监控对话：**

```
用户: 监控刚才创建的代码文件的性能指标，并分析潜在的性能瓶颈。

Agent预期行为:
1. 使用 monitor_performance 分析性能
2. 识别性能瓶颈
3. 提供优化建议
4. 生成性能报告
```

#### 2.2 模式识别测试

**设计模式识别对话：**

```
用户: 请创建一个单例模式的示例代码，然后识别其中使用的设计模式。

Agent预期行为:
1. 切换到 executing 状态
2. 使用 write_file 创建单例模式代码
3. 使用 recognize_patterns 识别设计模式
4. 分析模式的实现质量
5. 提供模式使用建议和最佳实践
```

**示例单例模式代码：**
```python
class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        pass
```

**多模式识别对话：**

```
用户: 创建一个包含多种设计模式的代码文件，然后识别所有的模式类型。

Agent预期行为:
1. 创建包含工厂模式、观察者模式等的代码
2. 使用 recognize_patterns 识别所有模式
3. 分析模式之间的关系
4. 评估模式使用的合理性
```

**反模式检测对话：**

```
用户: 检查项目中是否存在反模式或代码异味，并提供修复建议。

Agent预期行为:
1. 使用 recognize_patterns 检测反模式
2. 使用 analyze_code_quality 分析代码异味
3. 提供具体的修复方案
4. 生成重构计划
```

### 阶段3：语义理解测试 (30分钟)

#### 3.1 代码补全测试

**智能代码补全对话：**

```
用户: 请创建一个数据处理类的框架，然后为其中的方法提供智能代码补全建议。

Agent预期行为:
1. 切换到 analyzing 状态
2. 使用 write_file 创建类框架
3. 使用 get_code_completions 提供补全建议
4. 分析上下文和语义
5. 提供最相关的补全选项
```

**示例上下文代码：**
```python
class DataProcessor:
    def __init__(self):
        self.data = []
        self.cache = {}

    def process_data(self, input_data):
        result = # 在这里需要补全
```

**高级补全对话：**

```
用户: 基于项目的整体上下文，为这个数据处理类添加更多方法，并提供智能补全。

Agent预期行为:
1. 使用 analyze_dependencies 分析项目依赖
2. 使用 understand_semantics 理解业务逻辑
3. 使用 get_code_completions 提供上下文相关的补全
4. 考虑项目整体架构提供建议
```

#### 3.2 语义理解测试

**深度语义分析对话：**

```
用户: 请创建一个用户管理系统的业务逻辑代码，然后深度分析其语义结构和业务意图。

Agent预期行为:
1. 切换到 analyzing 状态
2. 使用 write_file 创建业务逻辑代码
3. 使用 understand_semantics 进行深度语义分析
4. 识别业务实体和操作
5. 分析代码意图和设计模式
6. 提供架构改进建议
```

**示例业务逻辑代码：**
```python
class UserManager:
    def create_user(self, user_data):
        # 创建新用户
        pass

    def update_user(self, user_id, data):
        # 更新用户信息
        pass

    def delete_user(self, user_id):
        # 删除用户
        pass
```

**项目级语义分析对话：**

```
用户: 分析整个项目的语义结构，识别主要的业务领域和架构模式。

Agent预期行为:
1. 使用 get_project_overview 获取项目概览
2. 使用 understand_semantics 分析项目级语义
3. 使用 build_call_graph 构建调用关系图
4. 识别领域边界和核心业务逻辑
5. 生成架构分析报告
```

### 阶段4：自动化工作流测试 (45分钟)

#### 4.1 任务分解测试

**复杂任务分解对话：**

```
用户: 我想创建一个完整的用户管理系统，包括用户注册、登录、权限管理和数据持久化功能。请帮我分解这个任务并制定执行计划。

Agent预期行为:
1. 切换到 planning 状态
2. 使用 decompose_task 分解复杂任务
3. 使用 get_execution_guidance 获取执行指导
4. 分析任务依赖关系
5. 制定详细的执行计划
6. 提供技术选型建议
```

**渐进式开发对话：**

```
用户: 基于刚才的任务分解，请先实现用户注册功能，并创建相应的测试代码。

Agent预期行为:
1. 切换到 executing 状态
2. 根据任务分解结果创建用户注册模块
3. 使用 write_file 创建代码文件
4. 使用 get_best_practices 确保代码质量
5. 创建单元测试
6. 使用 validate_agent_behavior 验证实现
```

**项目管理对话：**

```
用户: 为这个用户管理系统项目创建任务管理和进度跟踪。

Agent预期行为:
1. 使用 manage_tasks 创建任务列表
2. 设置任务优先级和依赖关系
3. 跟踪开发进度
4. 生成项目状态报告
```

#### 4.2 Agent 行为测试

**Agent状态机控制对话：**

```
用户: 请演示Agent的状态机控制系统，展示不同状态之间的转换过程。

Agent预期行为:
1. 使用 control_agent_state 初始化状态机
2. 演示从 idle → analyzing → planning → executing 的状态转换
3. 使用 validate_agent_behavior 验证每个状态转换
4. 展示错误处理和恢复机制
5. 生成状态转换日志
```

**学习优化测试对话：**

```
用户: 让Agent分析自己的执行历史，并优化未来的行为模式。

Agent预期行为:
1. 使用 analyze_history_trends 分析执行历史
2. 使用 optimize_agent_learning 优化学习算法
3. 识别常见的执行模式
4. 调整决策策略
5. 生成学习报告
```

**多Agent协作测试对话：**

```
用户: 模拟多个Agent协作完成一个复杂任务的场景。

Agent预期行为:
1. 切换到 collaborating 状态
2. 使用 execute_tool_chain 协调多个工具
3. 分配子任务给不同的专业模块
4. 同步执行结果
5. 生成协作报告
```

**错误处理测试对话：**

```
用户: 故意提供一个无效的任务，测试Agent的错误处理能力。

Agent预期行为:
1. 检测到无效输入
2. 切换到 error 状态
3. 分析错误原因
4. 提供修复建议
5. 恢复到正常状态
```

## 📊 测试结果验证

### 成功标准

每个测试阶段都应该满足以下标准：

#### 阶段1：基础功能
- ✅ Agent能正确响应文件操作请求
- ✅ Git操作状态转换正确 (idle → analyzing → executing → idle)
- ✅ 检查点创建和回滚功能正常
- ✅ 自然语言理解准确率 > 90%

#### 阶段2：智能分析
- ✅ 代码质量问题检测准确，提供具体建议
- ✅ 设计模式识别置信度 > 0.8
- ✅ 反模式检测和修复建议合理
- ✅ Agent状态管理正确 (analyzing → validating)

#### 阶段3：语义理解
- ✅ 代码补全建议相关且实用 (>= 3个有效建议)
- ✅ 语义分析能识别业务逻辑和意图
- ✅ 项目级分析提供架构洞察
- ✅ 上下文理解准确率 > 85%

#### 阶段4：自动化工作流
- ✅ 任务分解逻辑清晰，依赖关系正确
- ✅ Agent状态转换完整 (planning → executing → validating)
- ✅ 多工具协作流畅
- ✅ 错误处理和恢复机制有效

### Agent行为验证指标

- **状态转换正确性**: 100% (所有状态转换符合预期)
- **自然语言理解**: > 90% (正确理解用户意图)
- **工具选择准确性**: > 95% (选择合适的工具完成任务)
- **响应完整性**: > 90% (提供完整的分析和建议)
- **错误处理能力**: 能正确识别和处理异常情况

## 🔧 故障排除

### 常见Agent行为问题

1. **Agent无响应或响应不当**
   - 检查Agent状态：询问 "请显示当前状态"
   - 重置状态机：说 "请重置到初始状态"
   - 验证工具可用性：说 "列出所有可用工具"

2. **状态转换异常**
   - 使用 `validate_agent_behavior` 检查状态一致性
   - 查看状态转换日志
   - 手动控制状态：说 "切换到分析状态"

3. **工具执行失败**
   - 检查文件路径：确保使用 `/home/ydzat/workspace/dnkit_demo`
   - 验证Git仓库状态：说 "检查Git状态"
   - 重试机制：说 "请重试上一个操作"

4. **语义理解偏差**
   - 提供更具体的上下文信息
   - 使用技术术语而非模糊描述
   - 分步骤描述复杂任务

### 调试对话示例

**检查Agent状态：**
```
用户: 请显示当前的Agent状态和最近的操作历史。

预期响应: Agent应该报告当前状态、最近执行的工具、状态转换历史
```

**重置Agent：**
```
用户: 系统出现异常，请重置Agent到初始状态并清理临时数据。

预期响应: Agent切换到idle状态，清理会话数据，准备接受新任务
```

**验证工具功能：**
```
用户: 测试所有Git相关工具是否正常工作。

预期响应: Agent依次测试git_diff_analysis、git_apply_patch等工具
```

## 📈 Agent测试报告模板

完成测试后，请填写以下报告：

```markdown
# n8n Agent 集成测试报告

## 测试环境
- 操作系统: Linux
- Python 版本: 3.11+
- n8n 版本:
- MCP服务器版本: 1.0.0
- 测试仓库: /home/ydzat/workspace/dnkit_demo
- 测试时间:

## Agent行为测试结果
- 阶段1 (基础功能): ✅/❌
  - 文件操作响应: ✅/❌
  - Git集成功能: ✅/❌
  - 状态转换正确性: ✅/❌

- 阶段2 (智能分析): ✅/❌
  - 代码质量分析: ✅/❌
  - 模式识别准确性: ✅/❌
  - 性能监控功能: ✅/❌

- 阶段3 (语义理解): ✅/❌
  - 代码补全质量: ✅/❌
  - 语义分析深度: ✅/❌
  - 业务逻辑理解: ✅/❌

- 阶段4 (自动化工作流): ✅/❌
  - 任务分解逻辑: ✅/❌
  - Agent协作能力: ✅/❌
  - 错误处理机制: ✅/❌

## Agent性能指标
- 自然语言理解准确率: ___%
- 工具选择准确率: ___%
- 状态转换成功率: ___%
- 平均响应时间: ___秒
- 任务完成率: ___%

## 发现的问题
1. Agent状态管理问题:
2. 工具执行异常:
3. 语义理解偏差:
4. 其他问题:

## Agent行为优化建议
1. 状态机优化:
2. 工具选择策略:
3. 错误处理改进:
4. 学习算法调整:

## 测试用例执行情况
- 成功执行的对话数: ___
- 失败的对话数: ___
- 需要人工干预的情况: ___
- Agent自主解决问题的次数: ___

## 总体评价
Agent在n8n环境中的表现: 优秀/良好/一般/需改进
推荐投入生产使用: 是/否
```

## 🎯 测试完成检查清单

- [ ] Agent能正确理解自然语言指令
- [ ] 状态机转换逻辑正确
- [ ] 所有54个工具都能正常调用
- [ ] Git操作在测试仓库中正常工作
- [ ] 代码分析和生成功能准确
- [ ] 错误处理和恢复机制有效
- [ ] Agent能提供有价值的建议和洞察
- [ ] 多工具协作流程顺畅
- [ ] 性能指标满足要求
- [ ] 测试报告完整填写

通过这个Agent测试指南，您可以全面验证MCP工具集在n8n中的Agent行为和智能化程度。
