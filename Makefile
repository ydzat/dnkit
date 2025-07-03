# Makefile for MCP Toolkit development
.PHONY: help install test lint format check security clean all

# 默认目标
help:
	@echo "MCP Toolkit 开发工具"
	@echo ""
	@echo "可用命令:"
	@echo "  install     - 安装开发依赖"
	@echo "  test        - 运行测试"
	@echo "  lint        - 运行代码质量检查"
	@echo "  format      - 格式化代码"
	@echo "  check       - 运行所有检查但不修改代码"
	@echo "  security    - 运行安全检查"
	@echo "  clean       - 清理缓存文件"
	@echo "  all         - 运行完整的检查流程"
	@echo ""

# 安装开发依赖
install:
	@echo "安装开发依赖..."
	uv sync --dev
	uv run pre-commit install

# 运行测试
test:
	@echo "运行测试套件..."
	uv run pytest

# 代码质量检查
lint:
	@echo "运行代码质量检查..."
	@echo "1. flake8 检查..."
	uv run flake8 src/ tests/
	@echo "2. mypy 类型检查..."
	uv run mypy src/
	@echo "3. bandit 安全检查..."
	uv run bandit -r src/ -f json -ll || true

# 格式化代码
format:
	@echo "格式化代码..."
	@echo "1. isort 排序 imports..."
	uv run isort src/ tests/
	@echo "2. black 格式化..."
	uv run black src/ tests/
	@echo "代码格式化完成!"

# 检查代码格式但不修改
check:
	@echo "检查代码格式和质量..."
	@echo "1. black 格式检查..."
	uv run black --check --diff src/ tests/
	@echo "2. isort 检查..."
	uv run isort --check-only --diff src/ tests/
	@echo "3. flake8 质量检查..."
	uv run flake8 src/ tests/
	@echo "4. mypy 类型检查..."
	uv run mypy src/

# 安全检查
security:
	@echo "运行安全检查..."
	@echo "1. bandit 安全扫描..."
	uv run bandit -r src/ -f json -ll || true
	@echo "2. safety 依赖安全检查..."
	uv run safety scan || true

# 清理缓存文件
clean:
	@echo "清理缓存文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage
	@echo "清理完成!"

# 运行完整的检查流程
all: clean format lint test security
	@echo ""
	@echo "✅ 所有检查完成!"
	@echo "建议在提交前运行: make check"

# Pre-commit 相关命令
pre-commit-install:
	@echo "安装 pre-commit hooks..."
	uv run pre-commit install

pre-commit-run:
	@echo "运行 pre-commit 检查..."
	uv run pre-commit run --all-files

pre-commit-update:
	@echo "更新 pre-commit hooks..."
	uv run pre-commit autoupdate
