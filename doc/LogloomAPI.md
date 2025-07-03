# Logloom Python API 完整参考文档

本文档提供 Logloom Python 绑定的详细 API 参考，包括所有公开函数、类、配置选项和使用示例。本文档适合想要在 Python 项目中集成 Logloom 的开发者。

---

## 目录

- [初始化与配置](#初始化与配置)
- [日志记录](#日志记录)
- [国际化支持](#国际化支持)
- [异常处理](#异常处理)
- [配置格式参考](#配置格式参考)
- [插件系统](#插件系统)
- [特殊功能](#特殊功能)
- [最佳实践](#最佳实践)
- [常见问题解答](#常见问题解答)

---

## 初始化与配置

### `initialize(config_path=None)`

初始化 Logloom 系统，可选择通过配置文件或配置字典进行配置。

**参数：**
- `config_path` (str 或 dict, 可选)：配置文件路径或配置字典
  - 如果是字符串，作为配置文件路径处理
  - 如果是字典，直接作为配置使用
  - 如果不提供，尝试使用环境变量 `LOGLOOM_CONFIG` 指定的配置文件

**返回值：**
- `True`：初始化成功
- `False`：初始化失败

**示例：**

使用配置文件初始化：
```python
import logloom_py as ll

# 通过配置文件初始化
if not ll.initialize("./config.yaml"):
    print("初始化失败")
    exit(1)
```

使用字典初始化：
```python
import logloom_py as ll

# 通过字典配置初始化
config_dict = {
    "logloom": {
        "language": "zh",
        "log": {
            "level": "DEBUG",
            "file": "app.log",
            "max_size": 1048576,  # 1MB
            "console": True
        }
    }
}

ll.initialize(config_dict)
```

### `cleanup()`

清理 Logloom 系统资源，应在程序退出前调用。

**参数：** 无

**返回值：**
- `True`：清理成功
- `False`：清理失败

**示例：**
```python
import logloom_py as ll

# 初始化和使用...

# 程序退出前清理资源
ll.cleanup()
```

### `set_log_level(level)`

设置全局日志级别，控制记录哪些级别的日志。

**参数：**
- `level` (LogLevel 或 str)：日志级别
  - 如果是 LogLevel 枚举值，直接使用
  - 如果是字符串，可以是 "DEBUG"、"INFO"、"WARN"、"ERROR" 或 "FATAL"

**返回值：**
- `True`：设置成功
- `False`：设置失败

**抛出异常：**
- `ValueError`：如果提供了无效的日志级别

**示例：**
```python
import logloom_py as ll
from logloom_py import LogLevel

# 使用枚举值设置
ll.set_log_level(LogLevel.DEBUG)

# 使用字符串设置
ll.set_log_level("INFO")
```

### `set_log_file(filepath)`

设置日志输出文件路径。

**参数：**
- `filepath` (str)：日志文件路径
  - 如果路径中包含不存在的目录，会自动创建

**返回值：**
- `True`：设置成功
- `False`：设置失败

**示例：**
```python
import logloom_py as ll

# 设置日志文件
ll.set_log_file("logs/app.log")
```

### `set_log_max_size(max_bytes)`

设置日志文件的最大大小，超出后将进行轮转。

**参数：**
- `max_bytes` (int)：最大文件大小（字节）

**返回值：**
- `True`：设置成功
- `False`：设置失败

**示例：**
```python
import logloom_py as ll

# 设置最大 2MB
ll.set_log_max_size(2 * 1024 * 1024)
```

### `set_output_console(enabled)`

设置是否输出日志到控制台。

**参数：**
- `enabled` (bool)：是否启用控制台输出
  - `True`：启用控制台输出
  - `False`：禁用控制台输出

**返回值：**
- `True`：设置成功
- `False`：设置失败

**示例：**
```python
import logloom_py as ll

# 禁用控制台输出
ll.set_output_console(False)
```

## 日志记录

### 类 `LogLevel`

日志级别枚举，用于指定日志记录的严重程度。

**属性：**
- `DEBUG`：调试信息，最详细级别
- `INFO`：常规信息
- `WARN`：警告信息（有潜在问题）
- `ERROR`：错误信息（操作失败）
- `FATAL`：致命错误（程序可能无法继续）

**示例：**
```python
import logloom_py as ll
from logloom_py import LogLevel

# 设置日志级别为 DEBUG
ll.set_log_level(LogLevel.DEBUG)

# 可以比较日志级别
current_level = ll.logger.get_level()
if current_level == "DEBUG":
    print("当前是调试级别")
```

### 类 `Logger`

记录器类，用于记录日志消息。

#### `__init__(name=None)`

创建一个新的日志记录器实例。

**参数：**
- `name` (str, 可选)：记录器名称
  - 如果不提供，将尝试自动检测调用者的模块名称

**示例：**
```python
import logloom_py as ll

# 创建命名记录器
auth_logger = ll.Logger("auth")
api_logger = ll.Logger("api")

# 使用默认名称（自动检测）
logger = ll.Logger()
```

#### `debug(message, *args, **kwargs)`

记录调试级别的日志消息。

**参数：**
- `message` (str)：日志消息模板
- `*args`：用于格式化消息的位置参数
- `**kwargs`：用于格式化消息的关键字参数
  - 可以使用特殊参数 `module` 覆盖模块名称

**返回值：** 无

**示例：**
```python
# 使用位置参数
logger.debug("处理请求 #{0} 从 {1}", req_id, client_ip)

# 使用关键字参数
logger.debug("用户 {username} 尝试访问 {resource}", username="admin", resource="/api/data")

# 覆盖模块名称
logger.debug("特殊情况", module="security")
```

#### `info(message, *args, **kwargs)`

记录信息级别的日志消息。

**参数：**
- `message` (str)：日志消息模板
- `*args`：用于格式化消息的位置参数
- `**kwargs`：用于格式化消息的关键字参数

**返回值：** 无

**示例：**
```python
# 简单消息
logger.info("应用程序已启动")

# 带参数的消息
logger.info("已处理 {} 个请求，耗时 {:.2f} 秒", count, duration)
```

#### `warn(message, *args, **kwargs)`

记录警告级别的日志消息。

**参数：**
- `message` (str)：日志消息模板
- `*args`：用于格式化消息的位置参数
- `**kwargs`：用于格式化消息的关键字参数

**返回值：** 无

**示例：**
```python
logger.warn("资源使用量过高：CPU {0}%, 内存 {1}%", cpu_usage, mem_usage)
```

#### `warning(message, *args, **kwargs)`

`warn` 的别名，提供与 Python 标准库日志兼容的接口。

#### `error(message, *args, **kwargs)`

记录错误级别的日志消息。

**参数：**
- `message` (str)：日志消息模板
- `*args`：用于格式化消息的位置参数
- `**kwargs`：用于格式化消息的关键字参数

**返回值：** 无

**示例：**
```python
try:
    # 某些操作
    pass
except Exception as e:
    logger.error("操作失败：{}", str(e))
    # 或者使用异常对象
    logger.error("操作失败", exc_info=e)
```

#### `fatal(message, *args, **kwargs)`

记录致命错误级别的日志消息。

**参数：**
- `message` (str)：日志消息模板
- `*args`：用于格式化消息的位置参数
- `**kwargs`：用于格式化消息的关键字参数

**返回值：** 无

**示例：**
```python
logger.fatal("系统无法恢复，即将关闭")
```

#### `critical(message, *args, **kwargs)`

`fatal` 的别名，提供与 Python 标准库日志兼容的接口。

#### `set_level(level)`

设置此记录器实例的日志级别。

**参数：**
- `level` (LogLevel 或 str)：日志级别

**返回值：** 无

**示例：**
```python
# 只对当前记录器设置级别
auth_logger.set_level(ll.LogLevel.WARN)
```

#### `set_file(file_path)`

设置此记录器实例的输出文件。

**参数：**
- `file_path` (str)：日志文件路径

**返回值：** 无

**示例：**
```python
# 分别记录到不同文件
auth_logger.set_file("logs/auth.log")
api_logger.set_file("logs/api.log")
```

#### `set_rotation_size(size)`

设置此记录器的日志文件轮转大小。

**参数：**
- `size` (int)：最大文件大小（字节）

**返回值：** 无

**示例：**
```python
# 设置 5MB 的轮转大小
logger.set_rotation_size(5 * 1024 * 1024)
```

#### `get_level()`

获取此记录器当前的日志级别。

**参数：** 无

**返回值：**
- (str)：当前日志级别，例如 "DEBUG"、"INFO" 等

**示例：**
```python
current = logger.get_level()
print(f"当前日志级别：{current}")
```

### 全局日志记录

Logloom 提供了全局级别的直接日志记录函数。

#### `debug(module, message)`

记录调试级别的日志消息。

**参数：**
- `module` (str)：模块名称
- `message` (str)：日志消息

**返回值：** 无

**示例：**
```python
import logloom_py as ll

ll.debug("main", "初始化连接")
```

#### `info(module, message)`

记录信息级别的日志消息。

**参数：**
- `module` (str)：模块名称
- `message` (str)：日志消息

**返回值：** 无

#### `warn(module, message)`

记录警告级别的日志消息。

**参数：**
- `module` (str)：模块名称
- `message` (str)：日志消息

**返回值：** 无

#### `error(module, message)`

记录错误级别的日志消息。

**参数：**
- `module` (str)：模块名称
- `message` (str)：日志消息

**返回值：** 无

#### `fatal(module, message)`

记录致命错误级别的日志消息。

**参数：**
- `module` (str)：模块名称
- `message` (str)：日志消息

**返回值：** 无

## 国际化支持

### `set_language(lang_code)`

设置当前使用的语言代码。

**参数：**
- `lang_code` (str)：语言代码，如 "zh" 或 "en"

**返回值：**
- `True`：设置成功
- `False`：设置失败（例如提供了不支持的语言代码）

**示例：**
```python
import logloom_py as ll

# 设置中文
ll.set_language("zh")

# 设置英文
ll.set_language("en")
```

### `get_current_language()`

获取当前使用的语言代码。

**参数：** 无

**返回值：**
- (str)：当前语言代码，如 "zh" 或 "en"

**示例：**
```python
import logloom_py as ll

current_lang = ll.get_current_language()
print(f"当前使用的语言：{current_lang}")
```

### `get_text(key, *args)`

获取指定键的翻译文本，可选地应用位置参数。

**参数：**
- `key` (str)：文本键名
- `*args`：可选的格式化参数

**返回值：**
- (str)：翻译后的文本
  - 如果找不到翻译，返回键名本身

**示例：**
```python
import logloom_py as ll

# 简单文本获取
welcome_text = ll.get_text("system.welcome")

# 带参数的文本获取
error_msg = ll.get_text("error.file_not_found", "/config.json")
```

### `format_text(key, *args, **kwargs)`

获取指定键的翻译文本并应用格式化，支持位置参数和关键字参数。

**参数：**
- `key` (str)：文本键名
- `*args`：位置格式化参数
- `**kwargs`：关键字格式化参数

**返回值：**
- (str)：格式化后的翻译文本
  - 如果找不到翻译，返回键名本身

**示例：**
```python
import logloom_py as ll

# 使用位置参数
msg1 = ll.format_text("greeting", "张三")  # "你好，张三！"

# 使用关键字参数
msg2 = ll.format_text("error.invalid_value", value="123", expected="数字")
# "无效的值: 123，期望: 数字"
```

### `register_locale_file(file_path, lang_code=None)`

注册额外的语言资源文件，实现应用级的翻译扩展。

**参数：**
- `file_path` (str)：YAML语言资源文件的路径
- `lang_code` (str, 可选)：语言代码（如果为None，则从文件名推断）

**返回值：**
- `True`：注册成功
- `False`：注册失败

**示例：**
```python
import logloom_py as ll

# 显式指定语言代码
success = ll.register_locale_file("/path/to/app_translations.yaml", "zh")

# 从文件名推断语言代码（如fr.yaml）
success = ll.register_locale_file("/path/to/fr.yaml")
```

### `register_locale_directory(dir_path, pattern="*.yaml")`

注册目录中所有匹配模式的语言资源文件。

**参数：**
- `dir_path` (str)：包含语言资源文件的目录路径
- `pattern` (str, 可选)：文件匹配模式，默认为"*.yaml"

**返回值：**
- (int)：成功注册的文件数量

**示例：**
```python
import logloom_py as ll

# 注册应用特定的翻译目录
count = ll.register_locale_directory("/app/translations")
print(f"已注册 {count} 个语言文件")

# 使用自定义模式
count = ll.register_locale_directory("/app/i18n", "lang_*.yaml")
```

### `get_supported_languages()`

获取当前支持的所有语言代码列表。

**参数：** 无

**返回值：**
- (list)：语言代码列表，如 `["en", "zh", "fr"]`

**示例：**
```python
import logloom_py as ll

languages = ll.get_supported_languages()
print(f"支持的语言: {', '.join(languages)}")
```

### `get_language_keys(lang_code=None)`

获取指定语言中所有可用的翻译键列表。

**参数：**
- `lang_code` (str, 可选)：语言代码，默认为当前语言

**返回值：**
- (list)：翻译键列表

**示例：**
```python
import logloom_py as ll

# 获取当前语言的所有键
keys = ll.get_language_keys()

# 获取特定语言的所有键
zh_keys = ll.get_language_keys("zh")
```

