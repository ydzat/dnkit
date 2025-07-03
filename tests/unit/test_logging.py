"""
测试日志系统
"""

import logging
import tempfile
from pathlib import Path

import pytest

from mcp_toolkit.core.logging import (
    LogConfig,
    LoggerManager,
    ModuleLogger,
    configure_logging,
    get_logger,
    set_module_level,
)


class TestLogConfig:
    """测试日志配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LogConfig()
        assert config.level == "INFO"
        assert config.enable_console is True
        assert config.enable_file is True
        assert config.max_bytes == 10 * 1024 * 1024


class TestModuleLogger:
    """测试模块日志记录器"""

    def test_logger_creation(self):
        """测试日志记录器创建"""
        config = LogConfig(level="DEBUG")
        logger = ModuleLogger("test.module", config)

        assert logger.name == "test.module"
        assert logger.config == config
        assert logger.logger.level == logging.DEBUG

    def test_log_methods(self):
        """测试日志方法"""
        config = LogConfig(enable_file=False)  # 只使用控制台
        logger = ModuleLogger("test.logger", config)

        # 这些方法应该可以调用而不出错
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_file_logging(self):
        """测试文件日志记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LogConfig(file_path=str(log_file), enable_console=False)
            logger = ModuleLogger("test.file", config)

            logger.info("Test file logging")

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test file logging" in content


class TestLoggerManager:
    """测试日志管理器"""

    def test_manager_creation(self):
        """测试管理器创建"""
        manager = LoggerManager()
        assert isinstance(manager.default_config, LogConfig)
        assert len(manager.loggers) == 0

    def test_get_logger(self):
        """测试获取日志记录器"""
        manager = LoggerManager()

        logger1 = manager.get_logger("module1")
        logger2 = manager.get_logger("module2")
        logger1_again = manager.get_logger("module1")

        assert isinstance(logger1, ModuleLogger)
        assert isinstance(logger2, ModuleLogger)
        assert logger1 is logger1_again  # 应该返回同一个实例
        assert len(manager.loggers) == 2

    def test_configure_from_dict(self):
        """测试从字典配置"""
        manager = LoggerManager()
        config_dict = {
            "logging": {"level": "WARNING", "module_levels": {"test.module": "DEBUG"}}
        }

        manager.configure_from_dict(config_dict)

        assert manager.default_config.level == "WARNING"
        assert manager.default_config.module_levels["test.module"] == "DEBUG"

    def test_set_level(self):
        """测试设置模块级别"""
        manager = LoggerManager()
        manager.set_level("test.module", "ERROR")

        assert manager.default_config.module_levels["test.module"] == "ERROR"


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_logger_function(self):
        """测试全局get_logger函数"""
        logger = get_logger("test.global")
        assert isinstance(logger, ModuleLogger)
        assert logger.name == "test.global"

    def test_configure_logging_function(self):
        """测试全局configure_logging函数"""
        config_dict = {"logging": {"level": "ERROR"}}
        configure_logging(config_dict)

        # 创建新的logger应该使用新配置
        logger = get_logger("test.config")
        # 注意：这里测试的是配置被应用了
        assert logger.config.level == "ERROR"

    def test_set_module_level_function(self):
        """测试全局set_module_level函数"""
        set_module_level("test.level", "CRITICAL")

        logger = get_logger("test.level")
        assert logger.logger.level == logging.CRITICAL


@pytest.fixture
def temp_log_dir():
    """临时日志目录fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_integration_logging(temp_log_dir):
    """集成测试：完整的日志功能"""
    log_file = temp_log_dir / "integration.log"

    # 配置日志系统
    config_dict = {
        "logging": {
            "level": "INFO",
            "file_path": str(log_file),
            "module_levels": {"integration.test": "DEBUG"},
        }
    }

    configure_logging(config_dict)

    # 获取不同模块的日志记录器
    logger1 = get_logger("integration.test")
    logger2 = get_logger("integration.other")

    # 记录日志
    logger1.debug("Debug from integration.test")
    logger1.info("Info from integration.test")
    logger2.debug("Debug from integration.other")  # 应该被过滤
    logger2.info("Info from integration.other")

    # 检查文件内容
    assert log_file.exists()
    content = log_file.read_text()

    assert "Debug from integration.test" in content
    assert "Info from integration.test" in content
    assert "Debug from integration.other" not in content  # 被过滤
    assert "Info from integration.other" in content
