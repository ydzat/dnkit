"""基于Logloom的模块化日志系统实现.

为MCP工具集提供统一的日志记录功能。
"""

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import logloom_py as ll
import yaml

from .types import ConfigDict


@dataclass
class LogConfig:
    """日志配置类 - 兼容Logloom配置格式。"""

    level: str = "INFO"
    language: str = "zh"
    file_path: Optional[str] = None
    max_size: int = 10 * 1024 * 1024  # 10MB
    max_bytes: int = 10 * 1024 * 1024  # 兼容性别名
    console: bool = True
    enable_console: bool = True  # 兼容性别名
    enable_file: bool = True  # 兼容性属性
    modules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    module_levels: Dict[str, str] = field(default_factory=dict)  # 兼容性别名

    def __post_init__(self) -> None:
        """后初始化处理，同步兼容性属性。"""
        # 同步enable_console和console
        if hasattr(self, "enable_console") and not self.enable_console:
            self.console = False

        # 同步max_bytes和max_size
        if hasattr(self, "max_bytes"):
            self.max_size = self.max_bytes

        # 同步module_levels到modules
        for module_name, level in self.module_levels.items():
            if module_name not in self.modules:
                self.modules[module_name] = {}
            self.modules[module_name]["level"] = level

    def to_logloom_config(self) -> Dict[str, Any]:
        """转换为Logloom配置格式。"""
        # 计算最低的日志级别（包括模块级别）
        min_level = self.level
        for module_level in self.module_levels.values():
            if self._level_to_int(module_level) < self._level_to_int(min_level):
                min_level = module_level

        config = {
            "logloom": {
                "language": self.language,
                "log": {
                    "level": min_level,  # 使用最低级别，让单个Logger控制具体级别
                    "console": self.console,
                    "format": "[{timestamp}][{level}][{module}] {message}",
                    "timestamp_format": "%Y-%m-%d %H:%M:%S",
                },
            }
        }

        if self.file_path:
            log_config = config["logloom"]["log"]
            log_config["file"] = self.file_path  # type: ignore[index]
            log_config["max_size"] = self.max_size  # type: ignore[index]

        # 如果禁用了控制台且有文件路径，确保只输出到文件
        if not self.console and self.file_path:
            log_config = config["logloom"]["log"]
            log_config["console"] = False  # type: ignore[index]

        return config

    def _level_to_int(self, level: str) -> int:
        """将日志级别转换为数字，用于比较。"""
        level_map = {
            "DEBUG": 10,
            "INFO": 20,
            "WARN": 30,
            "WARNING": 30,
            "ERROR": 40,
            "FATAL": 50,
            "CRITICAL": 50,
        }
        return level_map.get(level.upper(), 20)


class ModuleLogger:
    """模块化日志记录器 - 基于Logloom实现。"""

    _global_initialized = False

    def __init__(self, name: str, config: Optional[LogConfig] = None):
        """初始化模块日志记录器。

        Args:
            name: 日志记录器名称，通常是模块名。
            config: 日志配置，如果为None则使用默认配置。
        """
        self.name = name
        self.config = config or LogConfig()
        self._logger: Optional[ll.Logger] = None

        # 创建标准logging.Logger以提供兼容性
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, self.config.level.upper(), logging.INFO))

        # 初始化Logloom
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """确保Logloom已初始化。"""
        # 只在第一次时初始化全局Logloom
        if not ModuleLogger._global_initialized:
            # 使用基础配置初始化Logloom（使用DEBUG级别以允许所有日志）
            config_dict = {
                "logloom": {
                    "language": self.config.language,
                    "log": {
                        "level": "DEBUG",  # 始终使用DEBUG以允许所有级别
                        "console": self.config.console,
                        "format": "[{timestamp}][{level}][{module}] {message}",
                        "timestamp_format": "%Y-%m-%d %H:%M:%S",
                    },
                }
            }

            # 如果有文件配置，添加到配置中
            if self.config.file_path:
                log_config = config_dict["logloom"]["log"]
                log_config["file"] = self.config.file_path  # type: ignore
                log_config["max_size"] = self.config.max_size  # type: ignore

            # 创建临时配置文件
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(config_dict, f)
                config_path = f.name

            try:
                # 清理之前的Logloom状态
                try:
                    ll.cleanup()
                except Exception:  # nosec B110
                    pass  # 忽略清理错误，这是可接受的

                # 初始化Logloom
                ll.initialize(config_path)

                # 显式设置全局文件输出
                if self.config.file_path:
                    ll.set_log_file(self.config.file_path)
                    ll.set_log_max_size(self.config.max_size)

                ModuleLogger._global_initialized = True
            finally:
                # 清理临时文件
                os.unlink(config_path)

        # 创建logger实例
        self._logger = ll.Logger(self.name)

        # 验证logger创建是否成功
        if not self._logger:
            # 如果失败，尝试重新创建
            self._logger = ll.Logger(self.name)

    def _should_log(self, level: str) -> bool:
        """检查是否应该记录指定级别的日志。"""
        level_values = {
            "DEBUG": 10,
            "INFO": 20,
            "WARN": 30,
            "WARNING": 30,
            "ERROR": 40,
            "FATAL": 50,
            "CRITICAL": 50,
        }

        current_level_value = level_values.get(self.config.level.upper(), 20)
        log_level_value = level_values.get(level.upper(), 20)

        return log_level_value >= current_level_value

    def debug(self, message: str, *args: Any) -> None:
        """记录调试级别日志。"""
        if self._logger and self._should_log("DEBUG"):
            formatted_msg = message.format(*args) if args else message
            self._logger.debug(formatted_msg)

    def info(self, message: str, *args: Any) -> None:
        """记录信息级别日志。"""
        if self._logger and self._should_log("INFO"):
            formatted_msg = message.format(*args) if args else message
            self._logger.info(formatted_msg)

    def warning(self, message: str, *args: Any) -> None:
        """记录警告级别日志。"""
        if self._logger and self._should_log("WARN"):
            formatted_msg = message.format(*args) if args else message
            self._logger.warn(formatted_msg)

    def error(self, message: str, *args: Any) -> None:
        """记录错误级别日志。"""
        if self._logger and self._should_log("ERROR"):
            formatted_msg = message.format(*args) if args else message
            self._logger.error(formatted_msg)

    def critical(self, message: str, *args: Any) -> None:
        """记录严重错误级别日志"""
        if self._logger and self._should_log("FATAL"):
            formatted_msg = message.format(*args) if args else message
            self._logger.fatal(formatted_msg)

    def exception(self, message: str, *args: Any) -> None:
        """记录异常级别日志，包含堆栈信息"""
        import traceback

        if self._logger and self._should_log("ERROR"):
            formatted_msg = message.format(*args) if args else message
            # 添加异常堆栈信息
            exc_info = traceback.format_exc()
            if exc_info and exc_info.strip() != "NoneType: None":
                formatted_msg = f"{formatted_msg}\n{exc_info}"
            self._logger.error(formatted_msg)

    def flush(self) -> None:
        """刷新日志输出，确保写入到文件"""
        # Logloom会自动处理刷新，这里添加一个延迟确保文件写入
        import time

        time.sleep(0.2)  # 增加延迟确保文件写入

        # 如果有文件路径，尝试强制刷新文件系统缓存
        if self.config.file_path:
            try:
                import os

                os.sync()  # 强制写入磁盘
            except (OSError, AttributeError):
                pass  # 忽略同步错误，某些系统可能不支持

    def set_level(self, level: str) -> None:
        """设置日志级别"""
        self.config.level = level.upper()
        # 同步标准logger级别
        if hasattr(self, "logger"):
            self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        # 同步Logloom logger级别
        if self._logger:
            self._logger.set_level(level.upper())
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        # 重新初始化以应用新级别
        self._initialized = False
        self._ensure_initialized()

    def get_effective_level(self) -> str:
        """获取当前有效的日志级别"""
        return self.config.level


class LoggerManager:
    """日志管理器 - 管理多个模块的日志记录器"""

    def __init__(self) -> None:
        self._loggers: Dict[str, ModuleLogger] = {}
        self._global_config: Optional[LogConfig] = None
        self.default_config = LogConfig()  # 兼容性属性

    @property
    def loggers(self) -> Dict[str, ModuleLogger]:
        """获取所有日志记录器的字典 - 兼容性属性"""
        return self._loggers

    def get_logger(self, name: str) -> ModuleLogger:
        """获取或创建指定模块的日志记录器"""
        if name not in self._loggers:
            base_config = self._global_config or self.default_config

            # 应用模块特定的配置
            if base_config and name in base_config.modules:
                module_config = base_config.modules[name]
                final_config = LogConfig(
                    level=module_config.get("level", base_config.level),
                    language=module_config.get("language", base_config.language),
                    file_path=module_config.get("file_path", base_config.file_path),
                    max_size=module_config.get("max_size", base_config.max_size),
                    console=module_config.get("console", base_config.console),
                    modules=base_config.modules,
                    module_levels=base_config.module_levels,
                )
            elif base_config and name in base_config.module_levels:
                # 如果在module_levels中有配置，使用该级别
                final_config = LogConfig(
                    level=base_config.module_levels[name],
                    language=base_config.language,
                    file_path=base_config.file_path,
                    max_size=base_config.max_size,
                    console=base_config.console,
                    modules=base_config.modules,
                    module_levels=base_config.module_levels,
                )
            else:
                final_config = base_config

            self._loggers[name] = ModuleLogger(name, final_config)

        return self._loggers[name]

    def configure_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """从字典配置日志系统 - 兼容性方法"""
        self.configure(config_dict)

    def configure(self, config: Union[ConfigDict, str]) -> None:
        """配置全局日志设置"""
        if isinstance(config, str):
            # 从YAML文件读取配置
            with open(config, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
        else:
            config_dict = config

        # 解析配置
        log_config = config_dict.get("logging", {})

        self._global_config = LogConfig(
            level=log_config.get("level", "INFO"),
            language=log_config.get("language", "zh"),
            file_path=log_config.get("file_path"),
            max_size=log_config.get("max_size", 10 * 1024 * 1024),
            console=log_config.get("console", True),
            modules=log_config.get("modules", {}),
            module_levels=log_config.get("module_levels", {}),
        )

        # 更新default_config
        self.default_config = self._global_config

        # 重新配置所有现有的日志记录器
        for name, logger in self._loggers.items():
            # 应用模块特定的配置
            if name in self._global_config.modules:
                module_config = self._global_config.modules[name]
                new_config = LogConfig(
                    level=module_config.get("level", self._global_config.level),
                    language=module_config.get(
                        "language", self._global_config.language
                    ),
                    file_path=module_config.get(
                        "file_path", self._global_config.file_path
                    ),
                    max_size=module_config.get(
                        "max_size", self._global_config.max_size
                    ),
                    console=module_config.get("console", self._global_config.console),
                    modules=self._global_config.modules,
                    module_levels=self._global_config.module_levels,
                )
            elif name in self._global_config.module_levels:
                # 如果在module_levels中有配置，使用该级别
                new_config = LogConfig(
                    level=self._global_config.module_levels[name],
                    language=self._global_config.language,
                    file_path=self._global_config.file_path,
                    max_size=self._global_config.max_size,
                    console=self._global_config.console,
                    modules=self._global_config.modules,
                    module_levels=self._global_config.module_levels,
                )
            else:
                new_config = self._global_config

            # 重置logger配置
            logger.config = new_config
            logger._ensure_initialized()

    def set_level(self, module: str, level: str) -> None:
        """设置特定模块的日志级别"""
        if module in self._loggers:
            self._loggers[module].set_level(level)

        # 更新全局配置中的模块设置
        if self._global_config:
            if module not in self._global_config.modules:
                self._global_config.modules[module] = {}
            self._global_config.modules[module]["level"] = level.upper()
            # 同时更新module_levels
            self._global_config.module_levels[module] = level.upper()

        # 更新default_config
        if module not in self.default_config.modules:
            self.default_config.modules[module] = {}
        self.default_config.modules[module]["level"] = level.upper()
        self.default_config.module_levels[module] = level.upper()

    def cleanup(self) -> None:
        """清理所有日志记录器"""
        self._loggers.clear()
        try:
            ll.cleanup()
        except Exception:  # nosec B110
            pass  # 忽略清理错误


# 全局日志管理器实例
_logger_manager = LoggerManager()


def get_logger(name: str) -> ModuleLogger:
    """获取日志记录器的全局函数"""
    return _logger_manager.get_logger(name)


def configure_logging(config: Union[ConfigDict, str]) -> None:
    """配置日志系统的全局函数"""
    _logger_manager.configure(config)


def set_module_level(module: str, level: str) -> None:
    """设置模块日志级别的全局函数"""
    _logger_manager.set_level(module, level)


def cleanup_logging() -> None:
    """清理日志系统的全局函数"""
    _logger_manager.cleanup()


# 导出主要接口
__all__ = [
    "LogConfig",
    "ModuleLogger",
    "LoggerManager",
    "get_logger",
    "configure_logging",
    "set_module_level",
    "cleanup_logging",
]
