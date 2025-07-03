"""
模块化日志系统实现
为MCP工具集提供统一的日志记录功能
"""

import logging
import logging.handlers
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .types import ConfigDict


@dataclass
class LogConfig:
    """日志配置类"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_console: bool = True
    enable_file: bool = True
    module_levels: Dict[str, str] = field(default_factory=dict)


class ModuleLogger:
    """模块化日志记录器"""

    def __init__(self, name: str, config: Optional[LogConfig] = None):
        self.name = name
        self.config = config or LogConfig()
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        # 设置日志级别
        level = self.config.module_levels.get(self.name, self.config.level)
        self.logger.setLevel(getattr(logging, level.upper()))

        # 清除现有处理器
        self.logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter(
            self.config.format, datefmt=self.config.date_format
        )

        # 添加控制台处理器
        if self.config.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # 添加文件处理器
        if self.config.enable_file and self.config.file_path:
            file_path = Path(self.config.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # 防止日志传播到根记录器
        self.logger.propagate = False

    def debug(self, msg: str, **kwargs):
        """调试级日志"""
        self.logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """信息级日志"""
        self.logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """警告级日志"""
        self.logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        """错误级日志"""
        self.logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        """严重错误级日志"""
        self.logger.critical(msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        """异常日志（包含堆栈跟踪）"""
        self.logger.exception(msg, **kwargs)


class LoggerManager:
    """日志管理器"""

    def __init__(self, default_config: Optional[LogConfig] = None):
        self.default_config = default_config or LogConfig()
        self.loggers: Dict[str, ModuleLogger] = {}
        self._setup_default_config()

    def _setup_default_config(self):
        """设置默认配置"""
        # 从环境变量读取配置
        if "MCP_LOG_LEVEL" in os.environ:
            self.default_config.level = os.environ["MCP_LOG_LEVEL"]

        if "MCP_LOG_FILE" in os.environ:
            self.default_config.file_path = os.environ["MCP_LOG_FILE"]

        # 创建日志目录
        if self.default_config.file_path:
            log_dir = Path(self.default_config.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)

    def get_logger(self, name: str, config: Optional[LogConfig] = None) -> ModuleLogger:
        """获取指定模块的日志记录器"""
        if name not in self.loggers:
            logger_config = config or self.default_config
            self.loggers[name] = ModuleLogger(name, logger_config)
        return self.loggers[name]

    def configure_from_dict(self, config_dict: ConfigDict):
        """从配置字典设置日志配置"""
        log_config = config_dict.get("logging", {})

        # 更新默认配置
        if "level" in log_config:
            self.default_config.level = log_config["level"]

        if "format" in log_config:
            self.default_config.format = log_config["format"]

        if "file_path" in log_config:
            self.default_config.file_path = log_config["file_path"]

        if "max_bytes" in log_config:
            self.default_config.max_bytes = log_config["max_bytes"]

        if "backup_count" in log_config:
            self.default_config.backup_count = log_config["backup_count"]

        if "enable_console" in log_config:
            self.default_config.enable_console = log_config["enable_console"]

        if "enable_file" in log_config:
            self.default_config.enable_file = log_config["enable_file"]

        if "module_levels" in log_config:
            self.default_config.module_levels.update(log_config["module_levels"])

        # 重新配置所有现有日志记录器
        for logger in self.loggers.values():
            logger.config = self.default_config
            logger._setup_logger()

    def set_level(self, name: str, level: str):
        """设置指定模块的日志级别"""
        self.default_config.module_levels[name] = level
        if name in self.loggers:
            self.loggers[name].config.module_levels[name] = level
            self.loggers[name]._setup_logger()

    def get_all_loggers(self) -> Dict[str, ModuleLogger]:
        """获取所有日志记录器"""
        return self.loggers.copy()


# 全局日志管理器实例
_logger_manager = LoggerManager()


def get_logger(name: str, config: Optional[LogConfig] = None) -> ModuleLogger:
    """获取日志记录器的便捷函数"""
    return _logger_manager.get_logger(name, config)


def configure_logging(config_dict: ConfigDict):
    """配置日志系统的便捷函数"""
    _logger_manager.configure_from_dict(config_dict)


def set_module_level(name: str, level: str):
    """设置模块日志级别的便捷函数"""
    _logger_manager.set_level(name, level)


def setup_default_logging(
    level: str = "INFO", log_file: Optional[str] = None, enable_console: bool = True
):
    """设置默认日志配置的便捷函数"""
    config = LogConfig(level=level, file_path=log_file, enable_console=enable_console)

    global _logger_manager
    _logger_manager = LoggerManager(config)
