"""
测试国际化系统
"""

import pytest
import tempfile
import json
from pathlib import Path

from mcp_toolkit.core.i18n import (
    I18nConfig, TranslationManager,
    get_text, set_locale, _, configure_i18n
)


class TestI18nConfig:
    """测试国际化配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = I18nConfig()
        assert config.default_locale == "zh_CN"
        assert config.fallback_locale == "en_US"
        assert config.locale_dir == "locales"
        assert config.auto_reload is False


class TestTranslationManager:
    """测试翻译管理器"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            assert manager.current_locale == "zh_CN"
            assert isinstance(manager.translations, dict)
    
    def test_create_default_translations(self):
        """测试创建默认翻译"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            # 检查翻译文件是否创建
            zh_file = Path(tmpdir) / "zh_CN.json"
            en_file = Path(tmpdir) / "en_US.json"
            
            assert zh_file.exists()
            assert en_file.exists()
            
            # 检查翻译内容
            with open(zh_file, 'r', encoding='utf-8') as f:
                zh_data = json.load(f)
            
            assert "core" in zh_data
            assert "errors" in zh_data["core"]
            assert "module_not_found" in zh_data["core"]["errors"]
    
    def test_get_text_basic(self):
        """测试基本文本获取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            # 获取存在的翻译
            text = manager.get_text("core.errors.module_not_found", module_name="test")
            assert "test" in text
            assert "模块未找到" in text or "Module not found" in text
    
    def test_get_text_fallback(self):
        """测试回退语言"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(
                locale_dir=tmpdir,
                default_locale="fr_FR",  # 不存在的语言
                fallback_locale="en_US"
            )
            manager = TranslationManager(config)
            
            # 应该回退到英文
            text = manager.get_text("core.errors.module_not_found", module_name="test")
            assert "Module not found" in text
    
    def test_get_text_missing_key(self):
        """测试缺失的键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            # 不存在的键应该返回键名
            text = manager.get_text("nonexistent.key")
            assert text == "nonexistent.key"
    
    def test_set_locale(self):
        """测试设置语言"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            manager.set_locale("en_US")
            assert manager.current_locale == "en_US"
    
    def test_add_translation(self):
        """测试添加翻译"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            manager.add_translation("zh_CN", "test.new.key", "新测试文本")
            text = manager.get_text("test.new.key")
            assert text == "新测试文本"
    
    def test_nested_value_access(self):
        """测试嵌套值访问"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = I18nConfig(locale_dir=tmpdir)
            manager = TranslationManager(config)
            
            # 测试深层嵌套
            data = {"a": {"b": {"c": "deep_value"}}}
            result = manager._get_nested_value(data, ["a", "b", "c"])
            assert result == "deep_value"
            
            # 测试不存在的路径
            result = manager._get_nested_value(data, ["a", "x", "c"])
            assert result is None


class TestGlobalFunctions:
    """测试全局函数"""
    
    def test_global_get_text(self):
        """测试全局get_text函数"""
        # 这将使用默认的翻译管理器
        text = get_text("core.errors.module_not_found", module_name="test")
        assert "test" in text
    
    def test_global_alias(self):
        """测试全局别名函数"""
        text1 = get_text("core.errors.module_not_found", module_name="test")
        text2 = _("core.errors.module_not_found", module_name="test")
        assert text1 == text2
    
    def test_set_locale_global(self):
        """测试全局设置语言"""
        set_locale("en_US")
        text = get_text("core.errors.module_not_found", module_name="test")
        # 应该是英文
        assert "Module not found" in text
        
        # 切换回中文
        set_locale("zh_CN")
        text = get_text("core.errors.module_not_found", module_name="test")
        # 应该是中文
        assert "模块未找到" in text


@pytest.fixture
def custom_locale_dir():
    """自定义locale目录fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        locale_dir = Path(tmpdir)
        
        # 创建自定义翻译文件
        custom_zh = {
            "test": {
                "message": "测试消息: {name}",
                "greeting": "你好"
            }
        }
        
        custom_en = {
            "test": {
                "message": "Test message: {name}",
                "greeting": "Hello"
            }
        }
        
        with open(locale_dir / "zh_CN.json", 'w', encoding='utf-8') as f:
            json.dump(custom_zh, f, ensure_ascii=False)
        
        with open(locale_dir / "en_US.json", 'w', encoding='utf-8') as f:
            json.dump(custom_en, f, ensure_ascii=False)
        
        yield locale_dir


def test_custom_translations(custom_locale_dir):
    """测试自定义翻译"""
    config = I18nConfig(locale_dir=str(custom_locale_dir))
    manager = TranslationManager(config)
    
    # 测试中文
    text = manager.get_text("test.message", name="世界")
    assert text == "测试消息: 世界"
    
    # 测试英文
    manager.set_locale("en_US")
    text = manager.get_text("test.message", name="World")
    assert text == "Test message: World"


def test_text_formatting():
    """测试文本格式化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = I18nConfig(locale_dir=tmpdir)
        manager = TranslationManager(config)
        
        # 测试正常格式化
        text = manager.get_text("core.errors.module_not_found", module_name="TestModule")
        assert "TestModule" in text
        
        # 测试缺失参数
        text = manager.get_text("core.errors.module_not_found")  # 没有提供module_name
        # 应该返回原始文本（格式化失败时）
        assert "{module_name}" in text or "module_not_found" in text


def test_integration_i18n():
    """集成测试：完整的国际化功能"""
    # 使用默认配置
    original_locale = "zh_CN"
    set_locale(original_locale)
    
    # 测试中文消息
    zh_text = _("core.errors.tool_not_found", tool_name="测试工具")
    assert "测试工具" in zh_text
    assert "工具未找到" in zh_text or "Tool not found" in zh_text
    
    # 切换到英文
    set_locale("en_US")
    en_text = _("core.errors.tool_not_found", tool_name="TestTool")
    assert "TestTool" in en_text
    assert "Tool not found" in en_text
    
    # 恢复原始语言
    set_locale(original_locale)
