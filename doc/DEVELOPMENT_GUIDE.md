# MCP工具集开发指导

## 📋 项目概述

MCP工具集是一个基于Model Context Protocol (MCP)的可扩展工具服务平台，支持动态服务注册、统一协议处理和模块化工具管理。

### 核心特性
- 🔧 **模块化架构**：支持动态服务注册和热插拔
- 🌐 **标准MCP协议**：完整支持MCP 2024-11-05规范
- 🛠️ **丰富工具集**：文件操作、终端执行、网络请求等基础工具
-  **统一日志**：基于Logloom的结构化日志系统
- 🚀 **轻量高效**：个人项目导向，专注核心功能

## 📚 设计文档索引

### 核心架构设计
- [`00_module_overview.md`](./module/00_module_overview.md) - 总体架构和模块分层
- [`01_core_interfaces.md`](./module/01_core_interfaces.md) - 核心接口规范和数据类型
- [`06_platform_architecture.md`](./module/06_platform_architecture.md) - 平台架构和服务模块设计

### 协议和工具设计
- [`02_protocol_handler.md`](./module/02_protocol_handler.md) - MCP协议处理和传输层
- [`03_tool_registry.md`](./module/03_tool_registry.md) - 工具注册管理和服务发现
- [`05_basic_tools.md`](./module/05_basic_tools.md) - 基础工具模块实现规范

### 配置和运维
- [`04_logloom_config.md`](./module/04_logloom_config.md) - 日志系统配置规范
- [`05_basic_tools_config.md`](./module/05_basic_tools_config.md) - 工具配置模板和示例

### 项目管理
- [`PROGRESS_TRACKING.md`](./PROGRESS_TRACKING.md) - 开发进度追踪和任务管理

## 🎯 开发里程碑规划

### 里程碑 1: 核心平台基础 (Milestone 1: Core Platform)

**目标**：建立MCP协议处理和基础服务框架

**实现内容**：
- [x] **核心接口实现** - 基于 [`01_core_interfaces.md`](./module/01_core_interfaces.md)
  - `ModuleInterface` 和 `ServiceModule` 基础接口
  - `ToolDefinition` 和 `ToolCallRequest/Response` 数据类型
  - 基础错误处理和结果包装

- [x] **MCP协议处理** - 基于 [`02_protocol_handler.md`](./module/02_protocol_handler.md)
  - HTTP传输处理器实现
  - JSON-RPC 2.0协议解析
  - 请求路由和响应格式化
  - 基础中间件链（日志、验证）

- [x] **服务注册框架** - 基于 [`03_tool_registry.md`](./module/03_tool_registry.md)
  - `ServiceRegistry` 核心实现
  - 服务发现和工具路由
  - 基础生命周期管理

- [x] **日志系统集成** - 基于 [`04_logloom_config.md`](./module/04_logloom_config.md)
  - Logloom初始化和配置
  - 模块化日志记录器
  - 国际化支持基础

**验收标准**：
- 能够启动MCP服务器并响应基础协议请求
- 支持工具注册和基本的工具调用
- 日志系统正常工作，支持中英文

**预计工期**：2-3周

---

### 里程碑 2: 基础工具实现 (Milestone 2: Basic Tools)

**目标**：实现核心基础工具，提供实用功能

**实现内容**：
- [x] **文件操作工具** - 基于 [`05_basic_tools.md`](./module/05_basic_tools.md)
  - `read_file`, `write_file`, `list_files`, `create_directory`
  - 路径安全验证和权限控制
  - 文件备份和恢复机制

- [x] **终端执行工具** - 基于 [`05_basic_tools.md`](./module/05_basic_tools.md)
  - `run_command`, `get_environment`, `set_working_directory`
  - 沙箱执行和安全限制
  - 命令白名单和超时控制

- [x] **网络请求工具** - 基于 [`05_basic_tools.md`](./module/05_basic_tools.md)
  - `http_request`, `websocket_connect`, `dns_lookup`
  - 域名白名单和请求限制
  - 响应缓存和错误重试

- [x] **搜索工具** - 基于 [`05_basic_tools.md`](./module/05_basic_tools.md)
  - `file_search`, `content_search`
  - 全文索引和正则匹配
  - 搜索结果分页和排序

- [x] **工具配置系统** - 基于 [`05_basic_tools_config.md`](./module/05_basic_tools_config.md)
  - 分层配置管理
  - 工具参数验证
  - 性能监控和缓存

**验收标准**：
- 所有基础工具可以通过MCP协议正常调用
- 工具配置系统完整，支持热更新
- 安全限制生效，异常处理完善

**预计工期**：3-4周

---

### 里程碑 3: 平台服务化 (Milestone 3: Platform Services)

**目标**：实现平台化架构，支持服务模块动态管理

**实现内容**：
- [x] **服务模块架构** - 基于 [`06_platform_architecture.md`](./module/06_platform_architecture.md)
  - `ServiceModule` 接口完整实现
  - 服务生命周期协调器
  - 服务依赖管理和启动顺序

- [x] **服务路由层** - 基于 [`06_platform_architecture.md`](./module/06_platform_architecture.md)
  - 智能路由决策
  - 负载均衡和故障转移
  - 工具命名空间管理

- [x] **平台事件系统** - 基于 [`06_platform_architecture.md`](./module/06_platform_architecture.md)
  - 事件总线实现
  - 服务间通信机制
  - 事件历史和统计

- [x] **配置管理服务** - 基于 [`06_platform_architecture.md`](./module/06_platform_architecture.md)
  - 分布式配置管理
  - 配置版本控制
  - 热更新和回滚

**验收标准**：
- 支持多个服务模块同时运行
- 服务发现和路由工作正常
- 事件系统能够协调服务间通信

**预计工期**：3-4周

---

### 里程碑 4: 测试和文档完善 (Milestone 4: Testing & Documentation)

**目标**：完善测试覆盖和项目文档

**实现内容**：
- [x] **单元测试完善**
  - 核心接口和协议处理测试
  - 基础工具功能测试
  - 服务注册和路由测试
  - 错误处理和边界情况测试

- [x] **集成测试**
  - MCP协议合规性测试
  - 端到端工具调用测试
  - 服务模块集成测试
  - 性能基准测试

- [x] **API文档生成**
  - 自动生成API文档
  - 工具使用示例
  - 配置参数说明
  - 故障排查指南

- [x] **用户文档**
  - 快速开始指南
  - 工具使用教程
  - 扩展开发指南
  - 常见问题解答

**验收标准**：
- 测试覆盖率达到80%以上
- 所有公共API有完整文档
- 用户可以通过文档快速上手

**预计工期**：2-3周

---

### 里程碑 0: DevOps基础设施 (Milestone 0: DevOps Infrastructure)

**目标**：建立CI/CD基础设施，支持自动化测试和部署

**实现内容**：
- [x] **持续集成 (CI)** 
  - GitHub Actions工作流配置
  - 自动化测试运行 (单元测试 + 集成测试)
  - 代码质量检查 (flake8, mypy)
  - 测试覆盖率报告 (codecov)
  - MCP协议合规性测试

- [x] **持续部署 (CD)**
  - 自动化发布流程
  - 版本标签管理
  - 构建产物生成
  - 发布资产上传

- [x] **代码质量保证**
  - 代码格式化检查 (black, isort)  
  - 静态类型检查 (mypy)
  - 安全扫描 (bandit)
  - 依赖漏洞检查

**验收标准**：
- 推送代码时自动运行测试
- 测试失败时阻止合并
- 标签发布时自动创建GitHub Release
- 代码质量检查全部通过

**实施时机**：在里程碑2开发前完成，作为基础设施支撑

**预计工期**：1-2天

## 🌿 分支管理策略

### 主分支说明
- **`main`** - 主分支，保持稳定可发布状态
- **`develop`** - 开发分支，集成最新功能
- **`feature/*`** - 功能分支，用于开发具体功能
- **`release/*`** - 发布分支，用于发布准备
- **`hotfix/*`** - 热修复分支，用于紧急修复

### 分支工作流

```mermaid
gitgraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Core Interfaces"
    
    branch feature/protocol-handler
    checkout feature/protocol-handler
    commit id: "HTTP Handler"
    commit id: "JSON-RPC Parser"
    
    checkout develop
    merge feature/protocol-handler
    commit id: "Protocol Handler Done"
    
    branch feature/basic-tools
    checkout feature/basic-tools
    commit id: "File Operations"
    commit id: "Terminal Tools"
    
    checkout develop
    merge feature/basic-tools
    commit id: "Basic Tools Done"
    
    branch release/v1.0
    checkout release/v1.0
    commit id: "Release Prep"
    
    checkout main
    merge release/v1.0
    tag: "v1.0.0"
    
    checkout develop
    merge release/v1.0
    commit id: "Back to Develop"
```

### 分支命名规范

**功能分支** (feature/*)：
- `feature/milestone-1-core-platform` - 里程碑1核心平台
- `feature/milestone-2-basic-tools` - 里程碑2基础工具
- `feature/protocol-http-handler` - HTTP协议处理器
- `feature/tool-file-operations` - 文件操作工具

**发布分支** (release/*)：
- `release/v1.0` - 版本1.0发布
- `release/v1.1` - 版本1.1发布

**热修复分支** (hotfix/*)：
- `hotfix/security-fix-auth` - 安全修复
- `hotfix/critical-memory-leak` - 关键内存泄漏修复

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**类型说明**：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建工具、依赖管理等

**示例**：
```
feat(protocol): implement HTTP transport handler

- Add HTTP server with async request handling
- Support CORS and request validation
- Include comprehensive error handling

Closes #123
```

## 🚀 CI/CD 配置指导

### 简化的GitHub Actions工作流

为个人项目优化的轻量级CI/CD配置：

#### 持续集成 (CI) - `.github/workflows/ci.yml`

```yaml
name: Continuous Integration

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.11
    
    - name: Install dependencies
      run: |
        uv sync
        uv pip install pytest pytest-cov flake8 mypy
    
    - name: Lint with flake8
      run: |
        uv run flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
        uv run flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Type check with mypy
      run: |
        uv run mypy src/ --ignore-missing-imports
    
    - name: Test with pytest
      run: |
        uv run pytest tests/ --cov=src/ --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  mcp-compliance:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
    
    - name: Set up Python
      run: uv python install 3.11
    
    - name: Install dependencies
      run: uv sync
    
    - name: Test MCP protocol compliance
      run: |
        uv run python scripts/test_mcp_compliance.py
```

#### 发布工作流 - `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
    
    - name: Set up Python
      run: uv python install 3.11
    
    - name: Build package
      run: |
        uv build
    
    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        draft: false
        prerelease: false
    
    - name: Upload Release Assets
      run: |
        echo "Upload dist files to release"
```



## 🔧 开发环境配置

### 1. Python版本管理

检查并设置Python版本（你的系统应该有pyenv或类似工具）：

```bash
# 检查当前Python版本管理工具
which pyenv || which python-launcher || which py

# 如果使用pyenv
pyenv versions
pyenv install 3.11.9  # 安装Python 3.11.9
pyenv local 3.11.9    # 设置项目本地版本

# 如果使用其他工具，确保Python 3.11+可用
python --version  # 应该显示 3.11.x
```

### 2. 使用uv进行项目配置

```bash
# 安装uv（如果还没安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或者使用pip
pip install uv

# 克隆仓库
git clone https://github.com/yourusername/dnkit.git
cd dnkit

# 初始化uv项目
uv init --python 3.11

# 创建并激活虚拟环境
uv venv --python 3.11
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装项目依赖
uv add logloom-py  # 添加生产依赖
uv add --dev pytest pytest-cov flake8 mypy black  # 添加开发依赖

# 安装项目本身（开发模式）
uv pip install -e .
```

### 3. 项目结构创建

```bash
# 创建基本项目结构
mkdir -p src/mcp_toolkit/{core,protocols,services,tools,utils}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p config/{modules,runtime}
mkdir -p scripts docs logs

# 创建基础配置文件
touch pyproject.toml
touch uv.lock
touch .gitignore
touch README.md
```

### 4. pyproject.toml 配置

创建 `pyproject.toml` 文件：

```toml
[project]
name = "mcp-toolkit"
version = "0.1.0"
description = "A modular MCP (Model Context Protocol) toolkit"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
dependencies = [
    "logloom-py>=0.1.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "click>=8.0.0",
]
requires-python = ">=3.11"
readme = "README.md"
license = {text = "MIT"}

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
]

[project.scripts]
mcp-toolkit = "mcp_toolkit.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=src/mcp_toolkit",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80",
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
exclude = ["tests/", "build/", "dist/"]

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.git
    | \.venv
    | build
    | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
```

### 5. .gitignore 配置

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.coverage
.pytest_cache/
coverage.xml
htmlcov/
.tox/

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# Project specific
config/local/
data/
temp/
```

### 6. 开发工作流

```bash
# 1. 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/milestone-1-core-platform

# 2. 开发和测试
# 编写代码...
uv run pytest tests/
uv run flake8 src/
uv run mypy src/

# 3. 代码格式化
uv run black src/ tests/
uv run isort src/ tests/

# 4. 提交代码
git add .
git commit -m "feat(core): implement basic service module interface"

# 5. 推送和创建PR
git push origin feature/milestone-1-core-platform
# 在GitHub上创建Pull Request

# 6. 合并后清理
git checkout develop
git pull origin develop
git branch -d feature/milestone-1-core-platform
```

## 📊 进度管理

### 开发进度追踪
项目使用专门的进度追踪文档来管理开发进度：

- **进度追踪文档**: [`PROGRESS_TRACKING.md`](./PROGRESS_TRACKING.md)
- **更新频率**: 每周更新，重大进展随时更新
- **追踪内容**: 里程碑进度、任务完成度、技术债务、开发日志

### 任务管理方式
- **GitHub Issues**: 用于跟踪具体的bug和功能请求
- **GitHub Projects**: 用于看板式任务管理
- **进度文档**: 用于详细的开发进度记录和分析

## 📊 质量保证

### 代码质量标准
- **测试覆盖率**: >= 80%
- **代码复杂度**: <= 10 (McCabe)
- **文档覆盖率**: >= 90%
- **类型检查**: 100% (mypy)

### 测试策略

```bash
# 单元测试
uv run pytest tests/unit/ -v

# 集成测试
uv run pytest tests/integration/ -v

# 测试覆盖率
uv run pytest tests/ --cov=src/mcp_toolkit --cov-report=html

# MCP协议合规性测试
uv run python scripts/test_mcp_compliance.py

# 性能测试
uv run pytest tests/performance/ -v --benchmark-only
```

### 代码审查清单

- [ ] 代码符合PEP 8规范
- [ ] 所有公共接口有类型注解
- [ ] 所有函数有docstring
- [ ] 测试覆盖新功能
- [ ] 更新相关文档
- [ ] 性能测试通过
- [ ] 安全扫描无问题

## 🚀 快速开始

### 本地开发运行

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行开发服务器
uv run python -m mcp_toolkit.main --config config/development.yaml

# 或者使用脚本命令（如果已安装）
mcp-toolkit --config config/development.yaml

# 健康检查
curl http://localhost:8080/health
```

### 基础配置文件

创建 `config/development.yaml`：

```yaml
server:
  host: "127.0.0.1"
  port: 8080
  debug: true

logging:
  level: "DEBUG"
  console: true
  file: "logs/mcp-toolkit.log"

tools:
  basic_tools:
    enabled: true
    max_file_size_mb: 10
    allowed_paths:
      - "./data"
      - "./workspace"
```

## 📈 基础监控

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8080/health

# 详细健康检查（包含服务状态）
curl http://localhost:8080/health/detailed

# 获取服务指标
curl http://localhost:8080/metrics
```

### 日志管理

```bash
# 查看实时日志
tail -f logs/mcp-toolkit.log

# 按级别过滤
grep "ERROR" logs/mcp-toolkit.log

# 查看特定模块日志
grep "protocol_handler" logs/mcp-toolkit.log
```

## 🤝 贡献指南

### 开发规范

1. **遵循设计文档**: 所有实现必须符合对应的设计文档规范
2. **测试驱动开发**: 新功能先写测试，再写实现
3. **文档同步更新**: 代码变更时同步更新相关文档
4. **代码审查**: 所有代码都需要经过审查才能合并

### 问题报告

使用GitHub Issues报告问题，包含：
- 问题描述和重现步骤
- 环境信息（操作系统、Python版本等）
- 相关日志和错误信息
- 预期行为和实际行为

### 功能请求

提交功能请求时，请说明：
- 功能的使用场景和价值
- 与现有架构的契合度
- 实现的复杂度评估

---

**注意**: 这是一个个人项目，专注于核心MCP工具集功能。开发节奏可以根据实际情况灵活调整，重要的是保持代码质量和文档的同步更新。ContextEngine等扩展功能将在后续根据项目重构需求进行设计和集成。

更多详细信息请参考项目的各个设计文档和代码注释。
