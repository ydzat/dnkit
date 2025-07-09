"""
基础工具模块测试
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from mcp_toolkit.tools.base import ExecutionContext, ToolExecutionRequest
from mcp_toolkit.tools.file_operations import (
    CreateDirectoryTool,
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
)
from mcp_toolkit.tools.network import DnsLookupTool, HttpRequestTool
from mcp_toolkit.tools.search import ContentSearchTool, FileSearchTool
from mcp_toolkit.tools.terminal import (
    GetEnvironmentTool,
    RunCommandTool,
    SetWorkingDirectoryTool,
)


class TestFileOperationsTools:
    """文件操作工具测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def read_tool(self, temp_dir):
        """创建读取文件工具"""
        config = {"allowed_paths": [temp_dir]}
        return ReadFileTool(config)

    @pytest.fixture
    def write_tool(self, temp_dir):
        """创建写入文件工具"""
        config = {"allowed_paths": [temp_dir]}
        return WriteFileTool(config)

    @pytest.mark.asyncio
    async def test_read_file_success(self, read_tool, temp_dir):
        """测试读取文件成功"""
        # 创建测试文件
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Hello, World!")

        # 执行读取
        request = ToolExecutionRequest(
            tool_name="read_file",
            parameters={"path": test_file},
            execution_context=ExecutionContext(request_id="test-1"),
        )

        result = await read_tool.execute(request)

        assert result.success
        assert result.content["content"] == "Hello, World!"
        assert result.content["metadata"]["size"] == 13

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, read_tool, temp_dir):
        """测试读取不存在的文件"""
        request = ToolExecutionRequest(
            tool_name="read_file",
            parameters={"path": os.path.join(temp_dir, "nonexistent.txt")},
            execution_context=ExecutionContext(request_id="test-2"),
        )

        result = await read_tool.execute(request)

        assert not result.success
        assert result.error.code == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_write_file_success(self, write_tool, temp_dir):
        """测试写入文件成功"""
        test_file = os.path.join(temp_dir, "output.txt")

        request = ToolExecutionRequest(
            tool_name="write_file",
            parameters={"path": test_file, "content": "Test content", "mode": "create"},
            execution_context=ExecutionContext(request_id="test-3"),
        )

        result = await write_tool.execute(request)

        assert result.success
        assert result.content["bytes_written"] == 12

        # 验证文件内容
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "Test content"

    def test_parameter_validation(self, tmp_path):
        """测试参数验证"""
        # 获取临时目录的父路径，以确保包含所有pytest目录
        temp_root = str(tmp_path.parent.parent.parent)  # 获取 /tmp 目录

        # 创建工具并正确配置
        read_tool = ReadFileTool({"allowed_paths": [temp_root]})

        # 测试缺少必需参数 - 现在空路径会被解析为当前工作目录，这是被允许的
        validation = read_tool.validate_parameters({})
        assert validation.is_valid  # 智能路径验证允许当前工作目录

        # 测试真正无效的路径 - 系统敏感路径
        validation = read_tool.validate_parameters({"path": "/etc/passwd"})
        assert not validation.is_valid  # 系统敏感路径应该被禁止

        # 测试有效参数
        test_file = tmp_path / "test.txt"
        validation = read_tool.validate_parameters({"path": str(test_file)})
        assert validation.is_valid


class TestTerminalTools:
    """终端工具测试"""

    @pytest.fixture
    def run_command_tool(self):
        """创建命令执行工具"""
        config = {
            "allowed_commands": ["echo", "ls", "pwd"],
            "forbidden_commands": ["rm", "sudo"],
        }
        return RunCommandTool(config)

    @pytest.mark.asyncio
    async def test_run_command_success(self, run_command_tool):
        """测试命令执行成功"""
        request = ToolExecutionRequest(
            tool_name="run_command",
            parameters={"command": "echo", "args": ["Hello, World!"]},
            execution_context=ExecutionContext(request_id="test-4"),
        )

        result = await run_command_tool.execute(request)

        assert result.success
        assert result.content["exit_code"] == 0
        assert "Hello, World!" in result.content["stdout"]

    def test_command_validation_forbidden(self, run_command_tool):
        """测试禁止命令验证"""
        validation = run_command_tool._validate_command("rm -rf /")
        assert not validation.is_valid
        assert any(error.code == "FORBIDDEN_COMMAND" for error in validation.errors)

    def test_command_validation_allowed(self, run_command_tool):
        """测试允许命令验证"""
        validation = run_command_tool._validate_command("echo hello")
        assert validation.is_valid


class TestNetworkTools:
    """网络工具测试"""

    @pytest.fixture
    def http_tool(self):
        """创建HTTP请求工具"""
        config = {
            "allowed_domains": ["httpbin.org", "example.com"],
            "forbidden_domains": ["malicious.com"],
        }
        return HttpRequestTool(config)

    @pytest.fixture
    def dns_tool(self):
        """创建DNS查询工具"""
        return DnsLookupTool()

    def test_url_validation_allowed(self, http_tool):
        """测试允许的URL验证"""
        validation = http_tool._validate_url("https://httpbin.org/get")
        assert validation.is_valid

    def test_url_validation_forbidden(self, http_tool):
        """测试禁止的URL验证"""
        validation = http_tool._validate_url("https://malicious.com/evil")
        assert not validation.is_valid

    @pytest.mark.asyncio
    async def test_dns_lookup_success(self, dns_tool):
        """测试DNS查询成功"""
        request = ToolExecutionRequest(
            tool_name="dns_lookup",
            parameters={"hostname": "example.com"},
            execution_context=ExecutionContext(request_id="test-5"),
        )

        result = await dns_tool.execute(request)

        assert result.success
        assert "records" in result.content
        assert result.content["hostname"] == "example.com"


class TestSearchTools:
    """搜索工具测试"""

    @pytest.fixture
    def temp_dir_with_files(self):
        """创建包含测试文件的临时目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            files = [
                ("test1.txt", "This is a test file"),
                ("test2.py", 'print("Hello World")'),
                ("data.json", '{"key": "value"}'),
                ("subdir/nested.txt", "Nested file content"),
            ]

            for file_path, content in files:
                full_path = os.path.join(temp_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            yield temp_dir

    @pytest.fixture
    def file_search_tool(self, temp_dir_with_files):
        """创建文件搜索工具"""
        config = {"allowed_paths": [temp_dir_with_files]}
        return FileSearchTool(config)

    @pytest.fixture
    def content_search_tool(self, temp_dir_with_files):
        """创建内容搜索工具"""
        config = {"allowed_paths": [temp_dir_with_files]}
        return ContentSearchTool(config)

    @pytest.mark.asyncio
    async def test_file_search_glob_pattern(
        self, file_search_tool, temp_dir_with_files
    ):
        """测试文件搜索glob模式"""
        request = ToolExecutionRequest(
            tool_name="file_search",
            parameters={
                "search_path": temp_dir_with_files,
                "pattern": "*.txt",
                "pattern_type": "glob",
            },
            execution_context=ExecutionContext(request_id="test-6"),
        )

        result = await file_search_tool.execute(request)

        assert result.success
        assert result.content["total_found"] >= 2  # test1.txt and nested.txt

        # 检查结果包含txt文件
        txt_files = [r for r in result.content["results"] if r["name"].endswith(".txt")]
        assert len(txt_files) >= 2

    @pytest.mark.asyncio
    async def test_content_search_text(self, content_search_tool, temp_dir_with_files):
        """测试内容搜索文本"""
        request = ToolExecutionRequest(
            tool_name="content_search",
            parameters={
                "search_path": temp_dir_with_files,
                "query": "test",
                "query_type": "text",
                "case_sensitive": False,
            },
            execution_context=ExecutionContext(request_id="test-7"),
        )

        result = await content_search_tool.execute(request)

        assert result.success
        assert result.content["total_files_found"] >= 1
        assert result.content["total_matches"] >= 1

        # 检查匹配结果
        matches = result.content["results"]
        assert len(matches) >= 1
        assert any(
            "test" in match["matches"][0]["line_content"].lower() for match in matches
        )


class TestToolRegistry:
    """工具注册中心测试"""

    @pytest.fixture
    def registry(self):
        """创建工具注册中心"""
        from mcp_toolkit.tools.base import ToolRegistry

        return ToolRegistry()

    @pytest.fixture
    def sample_tool(self, tmp_path):
        """创建示例工具"""
        config = {"allowed_paths": [str(tmp_path)]}
        return ReadFileTool(config)

    def test_register_tool(self, registry, sample_tool):
        """测试注册工具"""
        registry.register_tool(sample_tool, "file_operations")

        assert sample_tool.get_name() in registry.list_tools()
        assert sample_tool.get_name() in registry.list_tools("file_operations")

    def test_unregister_tool(self, registry, sample_tool):
        """测试注销工具"""
        tool_name = sample_tool.get_name()
        registry.register_tool(sample_tool, "file_operations")

        success = registry.unregister_tool(tool_name)

        assert success
        assert tool_name not in registry.list_tools()

    def test_get_tool(self, registry, sample_tool):
        """测试获取工具"""
        registry.register_tool(sample_tool)

        retrieved_tool = registry.get_tool(sample_tool.get_name())

        assert retrieved_tool is sample_tool

    @pytest.mark.asyncio
    async def test_execute_tool(self, registry, sample_tool, tmp_path):
        """测试执行工具"""
        # 工具已经在fixture中配置了allowed_paths
        registry.register_tool(sample_tool)

        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 执行工具
        request = ToolExecutionRequest(
            tool_name=sample_tool.get_name(),
            parameters={"path": str(test_file)},
            execution_context=ExecutionContext(request_id="test-8"),
        )

        result = await registry.execute_tool(request)

        assert result.success
        assert result.content["content"] == "test content"
