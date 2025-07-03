"""
国际化(i18n)支持系统
为MCP工具集提供多语言支持
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union


@dataclass
class I18nConfig:
    """国际化配置"""

    default_locale: str = "zh_CN"
    fallback_locale: str = "en_US"
    locale_dir: str = "locales"
    auto_reload: bool = False


class TranslationManager:
    """翻译管理器"""

    def __init__(self, config: Optional[I18nConfig] = None):
        self.config = config or I18nConfig()
        self.current_locale = self.config.default_locale
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.fallback_translations: Dict[str, Any] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """加载翻译文件"""
        locale_path = Path(self.config.locale_dir)

        # 检查当前语言文件
        current_file = locale_path / f"{self.current_locale}.json"
        fallback_file = locale_path / f"{self.config.fallback_locale}.json"

        # 如果翻译文件不存在，创建默认翻译文件
        if not current_file.exists() or not fallback_file.exists():
            self._create_default_translations()

        # 加载当前语言
        if current_file.exists():
            with open(current_file, "r", encoding="utf-8") as f:
                self.translations[self.current_locale] = json.load(f)

        # 加载回退语言
        if fallback_file.exists():
            with open(fallback_file, "r", encoding="utf-8") as f:
                self.fallback_translations = json.load(f)

    def _create_default_translations(self) -> None:
        """创建默认翻译文件"""
        locale_dir = Path(self.config.locale_dir)
        locale_dir.mkdir(parents=True, exist_ok=True)

        # 中文翻译
        zh_translations = {
            "core": {
                "errors": {
                    "module_not_found": "模块未找到: {module_name}",
                    "tool_not_found": "工具未找到: {tool_name}",
                    "invalid_parameters": "无效参数: {details}",
                    "execution_failed": "执行失败: {error}",
                    "permission_denied": "权限被拒绝: {action}",
                    "rate_limit_exceeded": "速率限制超出: {limit}",
                    "service_unavailable": "服务不可用: {service}",
                    "validation_error": "验证错误: {field}",
                },
                "messages": {
                    "module_loaded": "模块已加载: {module_name}",
                    "module_unloaded": "模块已卸载: {module_name}",
                    "tool_executed": "工具已执行: {tool_name}",
                    "service_started": "服务已启动: {service_name}",
                    "service_stopped": "服务已停止: {service_name}",
                    "request_received": "收到请求: {method}",
                    "response_sent": "响应已发送: {status}",
                },
            },
            "protocols": {
                "jsonrpc": {
                    "invalid_request": "无效的JSON-RPC请求",
                    "method_not_found": "方法未找到: {method}",
                    "invalid_params": "无效参数",
                    "internal_error": "内部错误",
                    "parse_error": "解析错误",
                },
                "http": {
                    "invalid_content_type": "无效的内容类型: {content_type}",
                    "method_not_allowed": "方法不被允许: {method}",
                    "cors_blocked": "CORS被阻止",
                    "health_check_ok": "健康检查通过",
                    "server_starting": "HTTP服务器启动中...",
                },
            },
            "tools": {
                "file": {
                    "file_not_found": "文件未找到: {path}",
                    "permission_denied": "文件权限被拒绝: {path}",
                    "read_success": "文件读取成功: {path}",
                    "write_success": "文件写入成功: {path}",
                },
                "network": {
                    "connection_failed": "连接失败: {host}",
                    "timeout": "连接超时: {timeout}s",
                    "request_sent": "请求已发送: {url}",
                    "response_received": "收到响应: {status}",
                },
            },
        }

        # 英文翻译
        en_translations = {
            "core": {
                "errors": {
                    "module_not_found": "Module not found: {module_name}",
                    "tool_not_found": "Tool not found: {tool_name}",
                    "invalid_parameters": "Invalid parameters: {details}",
                    "execution_failed": "Execution failed: {error}",
                    "permission_denied": "Permission denied: {action}",
                    "rate_limit_exceeded": "Rate limit exceeded: {limit}",
                    "service_unavailable": "Service unavailable: {service}",
                    "validation_error": "Validation error: {field}",
                },
                "messages": {
                    "module_loaded": "Module loaded: {module_name}",
                    "module_unloaded": "Module unloaded: {module_name}",
                    "tool_executed": "Tool executed: {tool_name}",
                    "service_started": "Service started: {service_name}",
                    "service_stopped": "Service stopped: {service_name}",
                    "request_received": "Request received: {method}",
                    "response_sent": "Response sent: {status}",
                },
            },
            "protocols": {
                "jsonrpc": {
                    "invalid_request": "Invalid JSON-RPC request",
                    "method_not_found": "Method not found: {method}",
                    "invalid_params": "Invalid parameters",
                    "internal_error": "Internal error",
                    "parse_error": "Parse error",
                },
                "http": {
                    "invalid_content_type": "Invalid content type: {content_type}",
                    "method_not_allowed": "Method not allowed: {method}",
                    "cors_blocked": "CORS blocked",
                    "health_check_ok": "Health check OK",
                    "server_starting": "HTTP server starting...",
                },
            },
            "tools": {
                "file": {
                    "file_not_found": "File not found: {path}",
                    "permission_denied": "File permission denied: {path}",
                    "read_success": "File read success: {path}",
                    "write_success": "File write success: {path}",
                },
                "network": {
                    "connection_failed": "Connection failed: {host}",
                    "timeout": "Connection timeout: {timeout}s",
                    "request_sent": "Request sent: {url}",
                    "response_received": "Response received: {status}",
                },
            },
        }

        # 保存翻译文件
        with open(locale_dir / "zh_CN.json", "w", encoding="utf-8") as f:
            json.dump(zh_translations, f, ensure_ascii=False, indent=2)

        with open(locale_dir / "en_US.json", "w", encoding="utf-8") as f:
            json.dump(en_translations, f, ensure_ascii=False, indent=2)

        # 根据当前locale加载到内存
        if self.current_locale == "zh_CN":
            self.translations[self.current_locale] = zh_translations
        elif self.current_locale == "en_US":
            self.translations[self.current_locale] = en_translations

        # 根据fallback locale设置fallback
        if self.config.fallback_locale == "zh_CN":
            self.fallback_translations = zh_translations
        elif self.config.fallback_locale == "en_US":
            self.fallback_translations = en_translations

    def set_locale(self, locale: str) -> None:
        """设置当前语言"""
        self.current_locale = locale
        if self.config.auto_reload:
            self._load_translations()

    def get_text(self, key: str, **kwargs: Any) -> str:
        """
        获取翻译文本

        Args:
            key: 翻译键，使用点号分隔，如 'core.errors.module_not_found'
            **kwargs: 格式化参数

        Returns:
            翻译后的文本
        """
        # 分解键路径
        keys = key.split(".")

        # 首先尝试当前语言
        current_translations = self.translations.get(self.current_locale, {})
        text = self._get_nested_value(current_translations, keys)

        # 如果没找到，使用回退语言
        if text is None:
            text = self._get_nested_value(self.fallback_translations, keys)

        # 如果还是没找到，返回键名
        if text is None:
            text = key

        # 格式化文本
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text

    def _get_nested_value(self, data: Dict[str, Any], keys: list) -> Optional[str]:
        """从嵌套字典中获取值"""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current if isinstance(current, str) else None

    def add_translation(self, locale: str, key: str, text: str) -> None:
        """添加翻译"""
        if locale not in self.translations:
            self.translations[locale] = {}

        keys = key.split(".")
        current = self.translations[locale]

        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # 设置值
        current[keys[-1]] = text

    def get_available_locales(self) -> list:
        """获取可用的语言列表"""
        locale_dir = Path(self.config.locale_dir)
        if not locale_dir.exists():
            return [self.config.default_locale, self.config.fallback_locale]

        locales = []
        for file in locale_dir.glob("*.json"):
            locales.append(file.stem)

        return locales


# 全局翻译管理器实例
_translation_manager = TranslationManager()


def set_locale(locale: str) -> None:
    """设置当前语言的便捷函数"""
    _translation_manager.set_locale(locale)


def get_text(key: str, **kwargs: Any) -> str:
    """获取翻译文本的便捷函数"""
    return _translation_manager.get_text(key, **kwargs)


def _(key: str, **kwargs: Any) -> str:
    """获取翻译文本的简短别名"""
    return get_text(key, **kwargs)


def configure_i18n(config: I18nConfig) -> None:
    """配置国际化系统"""
    global _translation_manager
    _translation_manager = TranslationManager(config)


def get_available_locales() -> list:
    """获取可用语言列表"""
    return _translation_manager.get_available_locales()
