# 语义智能工具使用指南

## 🎯 概述

语义智能工具集提供了四个核心工具，用于深度代码理解和智能推荐：

1. **SemanticUnderstanding** - 语义理解引擎
2. **CodeCompletionEngine** - 智能代码补全
3. **PatternRecognizer** - 模式识别器
4. **BestPracticeAdvisor** - 最佳实践建议器

## 🚀 快速开始

### 1. 语义理解 (understand_semantics)

分析代码的业务逻辑、设计模式和架构意图：

```json
{
  "tool": "understand_semantics",
  "parameters": {
    "target": {
      "type": "directory",
      "path": "./src",
      "patterns": ["*.py", "*.js"]
    },
    "understanding_types": ["business_logic", "design_patterns", "code_intent"],
    "analysis_depth": "deep",
    "include_suggestions": true
  }
}
```

**返回结果包含：**
- 业务实体和操作识别
- 设计模式检测结果
- 代码意图推断
- 架构模式分析
- 改进建议

### 2. 智能代码补全 (get_code_completions)

获取上下文感知的代码补全建议：

```json
{
  "tool": "get_code_completions",
  "parameters": {
    "file_path": "src/example.py",
    "position": {"line": 15, "column": 8},
    "context": "def process_data(data):\n    result = ",
    "completion_types": ["variables", "functions", "patterns"],
    "max_suggestions": 10
  }
}
```

**返回结果包含：**
- 变量名建议
- 函数调用建议
- 类实例化建议
- 常用代码模式
- 个性化排序

### 3. 模式识别 (recognize_patterns)

识别代码中的设计模式和编程模式：

```json
{
  "tool": "recognize_patterns",
  "parameters": {
    "target": {
      "type": "file",
      "path": "src/user_manager.py"
    },
    "pattern_types": ["design_patterns", "coding_patterns", "anti_patterns"],
    "confidence_threshold": 0.7
  }
}
```

**支持的模式类型：**
- **设计模式**: 单例、工厂、观察者、策略、装饰器、适配器、建造者、命令
- **编程模式**: 命名约定、错误处理、资源管理、迭代模式、函数模式
- **反模式**: 代码异味、性能问题、可维护性问题、安全风险

### 4. 最佳实践建议 (get_best_practices)

获取代码质量和最佳实践建议：

```json
{
  "tool": "get_best_practices",
  "parameters": {
    "target": {
      "type": "project",
      "path": "./src"
    },
    "advice_categories": ["code_quality", "performance", "security", "maintainability"],
    "language": "python",
    "priority_level": "medium"
  }
}
```

**分析类别：**
- **代码质量**: 函数长度、参数数量、文档完整性
- **性能**: 复杂度分析、优化建议
- **安全性**: 危险函数检测、安全实践
- **可维护性**: 代码结构、重构建议
- **测试**: 测试策略、覆盖率建议

## 📋 实际使用示例

### 示例 1: 项目代码质量分析

```python
# 分析整个项目的代码质量
{
  "tool": "get_best_practices",
  "parameters": {
    "target": {"type": "project", "path": "./"},
    "advice_categories": ["code_quality", "maintainability"],
    "priority_level": "high"
  }
}
```

### 示例 2: 设计模式识别

```python
# 识别特定文件中的设计模式
{
  "tool": "recognize_patterns",
  "parameters": {
    "target": {"type": "file", "path": "src/database.py"},
    "pattern_types": ["design_patterns"],
    "confidence_threshold": 0.8
  }
}
```

### 示例 3: 智能代码补全

```python
# 在编写代码时获取补全建议
{
  "tool": "get_code_completions",
  "parameters": {
    "file_path": "src/api.py",
    "position": {"line": 25, "column": 12},
    "context": "class UserAPI:\n    def create_user(self, data):\n        user = ",
    "completion_types": ["classes", "functions", "patterns"]
  }
}
```

## 🔧 配置选项

### 全局配置 (enhanced_tools_config.yaml)

```yaml
semantic_intelligence:
  enabled: true
  settings:
    code_completion:
      max_suggestions: 10
      context_window: 1000
      semantic_threshold: 0.7

    pattern_recognition:
      confidence_threshold: 0.7
      supported_patterns:
        - design_patterns
        - coding_patterns
        - anti_patterns

    best_practices:
      priority_levels: ["low", "medium", "high", "critical"]
      advice_categories:
        - code_quality
        - performance
        - security
        - maintainability
```

## 📈 性能特点

- **响应时间**: < 1秒 (大部分操作)
- **内存使用**: < 100MB (正常项目)
- **准确率**: > 90% (模式识别)
- **补全相关性**: > 85% (用户接受率)

## 🎯 最佳实践

1. **渐进式分析**: 从单个文件开始，逐步扩展到整个项目
2. **合理设置阈值**: 根据项目特点调整置信度阈值
3. **结合使用**: 多个工具配合使用效果更佳
4. **定期分析**: 在代码变更后定期运行分析
5. **关注建议**: 重视高优先级的改进建议

## 🔍 故障排除

### 常见问题

1. **分析结果为空**: 检查文件路径和权限
2. **模式识别不准确**: 调整置信度阈值
3. **补全建议不相关**: 提供更多上下文信息
4. **性能较慢**: 减少分析范围或调整深度

### 调试技巧

- 使用 `analysis_depth: "shallow"` 进行快速测试
- 检查 ChromaDB 数据存储状态
- 验证文件编码格式 (推荐 UTF-8)
- 确保项目结构清晰

## 📚 扩展阅读

- [语义智能系统设计文档](./11-semantic-intelligence.md)
- [上下文引擎架构](./05-enhanced-context.md)
- [项目进度追踪](./PROGRESS_TRACKING.md)
