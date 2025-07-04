"""
测试main模块的功能
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from mcp_toolkit.main import main, start_server


class TestMainCommand:
    """测试主命令行功能"""

    def test_main_with_default_config(self):
        """测试使用默认配置启动"""
        runner = CliRunner()

        with patch("mcp_toolkit.main.asyncio.run") as mock_run:
            with patch("mcp_toolkit.main.Path.exists", return_value=False):
                result = runner.invoke(main, ["--help"])
                assert result.exit_code == 0
                assert "Start the MCP Toolkit server" in result.output

    def test_main_with_custom_config(self):
        """测试使用自定义配置文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {"logging": {"level": "INFO", "console": True}}
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            runner = CliRunner()

            # 模拟asyncio.run，确保传入的协程被正确关闭

            def mock_asyncio_run(coro):
                # 关闭协程以避免警告
                if hasattr(coro, "close"):
                    coro.close()
                return None

            with patch(
                "mcp_toolkit.main.asyncio.run", side_effect=mock_asyncio_run
            ) as mock_run:
                with patch("mcp_toolkit.main.configure_i18n") as mock_i18n:
                    with patch("mcp_toolkit.main.configure_logging") as mock_logging:
                        with patch("mcp_toolkit.main.get_logger") as mock_logger:
                            mock_logger.return_value = MagicMock()
                            result = runner.invoke(
                                main,
                                [
                                    "--config",
                                    config_path,
                                    "--host",
                                    "0.0.0.0",
                                    "--port",
                                    "9090",
                                    "--debug",
                                    "--locale",
                                    "en_US",
                                ],
                            )

                            # 验证函数被正确调用
                            mock_i18n.assert_called_once()
                            mock_logging.assert_called_once_with(config_data)
                            mock_run.assert_called_once()
        finally:
            Path(config_path).unlink()

    def test_main_with_keyboard_interrupt(self):
        """测试键盘中断处理"""
        runner = CliRunner()

        # 模拟asyncio.run，确保传入的协程被正确关闭
        def mock_asyncio_run(coro):
            # 关闭协程以避免警告
            if hasattr(coro, "close"):
                coro.close()
            raise KeyboardInterrupt()

        with patch("mcp_toolkit.main.asyncio.run", side_effect=mock_asyncio_run):
            with patch("mcp_toolkit.main.Path.exists", return_value=False):
                with patch("mcp_toolkit.main.configure_i18n"):
                    with patch("mcp_toolkit.main.configure_logging"):
                        with patch("mcp_toolkit.main.get_logger") as mock_logger:
                            mock_logger.return_value = MagicMock()
                            result = runner.invoke(main, [])
                            # 应该正常退出，不应该有错误
                            assert result.exit_code == 0

    def test_main_with_exception(self):
        """测试异常处理"""
        runner = CliRunner()

        # 模拟asyncio.run，确保传入的协程被正确关闭
        def mock_asyncio_run(coro):
            # 关闭协程以避免警告
            if hasattr(coro, "close"):
                coro.close()
            raise Exception("Test error")

        with patch("mcp_toolkit.main.asyncio.run", side_effect=mock_asyncio_run):
            with patch("mcp_toolkit.main.Path.exists", return_value=False):
                with patch("mcp_toolkit.main.configure_i18n"):
                    with patch("mcp_toolkit.main.configure_logging"):
                        with patch("mcp_toolkit.main.get_logger") as mock_logger:
                            mock_logger_instance = MagicMock()
                            mock_logger.return_value = mock_logger_instance
                            result = runner.invoke(main, [])

                            # 验证错误被记录
                            mock_logger_instance.error.assert_called_once()


class TestStartServer:
    """测试服务器启动功能"""

    @pytest.mark.asyncio
    async def test_start_server_success(self):
        """测试服务器成功启动"""
        with patch("mcp_toolkit.main.RequestRouter") as mock_router:
            with patch("mcp_toolkit.main.MiddlewareChain") as mock_middleware:
                with patch("mcp_toolkit.main.HTTPTransportHandler") as mock_handler:
                    with patch("mcp_toolkit.main.get_logger") as mock_logger:
                        # 设置mock
                        mock_handler_instance = AsyncMock()
                        mock_handler.return_value = mock_handler_instance
                        mock_logger_instance = MagicMock()
                        mock_logger.return_value = mock_logger_instance

                        # 模拟立即停止
                        async def mock_sleep(duration):
                            raise KeyboardInterrupt()

                        with patch("asyncio.sleep", side_effect=mock_sleep):
                            await start_server("127.0.0.1", 8080, False)

                        # 验证调用
                        mock_handler_instance.start.assert_called_once()
                        mock_handler_instance.stop.assert_called_once()
                        mock_logger_instance.info.assert_called()

    @pytest.mark.asyncio
    async def test_start_server_with_debug(self):
        """测试调试模式下的服务器启动"""
        with patch("mcp_toolkit.main.RequestRouter"):
            with patch("mcp_toolkit.main.MiddlewareChain"):
                with patch("mcp_toolkit.main.HTTPTransportHandler") as mock_handler:
                    with patch("mcp_toolkit.main.get_logger") as mock_logger:
                        mock_handler_instance = AsyncMock()
                        mock_handler.return_value = mock_handler_instance
                        mock_logger.return_value = MagicMock()

                        # 模拟立即停止
                        with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
                            await start_server("0.0.0.0", 9090, True)

                        # 验证处理器被正确创建
                        mock_handler.assert_called_once_with(host="0.0.0.0", port=9090)

    @pytest.mark.asyncio
    async def test_start_server_handler_creation(self):
        """测试服务器组件创建"""
        with patch("mcp_toolkit.main.RequestRouter") as mock_router:
            with patch("mcp_toolkit.main.MiddlewareChain") as mock_middleware:
                with patch("mcp_toolkit.main.HTTPTransportHandler") as mock_handler:
                    with patch("mcp_toolkit.main.get_logger") as mock_logger:
                        mock_handler_instance = AsyncMock()
                        mock_handler.return_value = mock_handler_instance
                        mock_logger.return_value = MagicMock()

                        # 模拟立即停止
                        with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
                            await start_server("127.0.0.1", 8080, False)

                        # 验证所有组件都被创建
                        mock_router.assert_called_once()
                        mock_middleware.assert_called_once()
                        mock_handler.assert_called_once_with(
                            host="127.0.0.1", port=8080
                        )


class TestMainIntegration:
    """集成测试"""

    def test_config_file_loading(self):
        """测试配置文件加载"""
        config_data = {
            "logging": {"level": "DEBUG", "console": True, "file_path": "test.log"},
            "server": {"host": "0.0.0.0", "port": 9090},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            runner = CliRunner()

            # 模拟asyncio.run，确保传入的协程被正确关闭

            def mock_asyncio_run(coro):
                # 关闭协程以避免警告
                if hasattr(coro, "close"):
                    coro.close()
                return None

            with patch("mcp_toolkit.main.asyncio.run", side_effect=mock_asyncio_run):
                with patch("mcp_toolkit.main.configure_i18n"):
                    with patch("mcp_toolkit.main.configure_logging") as mock_logging:
                        with patch("mcp_toolkit.main.get_logger") as mock_logger:
                            mock_logger.return_value = MagicMock()

                            result = runner.invoke(main, ["--config", config_path])

                            # 验证配置数据被正确传递
                            mock_logging.assert_called_once_with(config_data)
        finally:
            Path(config_path).unlink()
