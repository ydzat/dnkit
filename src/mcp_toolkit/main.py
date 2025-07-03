"""
MCP Toolkit main entry point.
"""

import asyncio
import click
import yaml
from pathlib import Path

from .core import get_logger, configure_logging, set_locale, configure_i18n, I18nConfig, LogConfig
from .protocols.http_handler import HTTPTransportHandler
from .protocols.router import RequestRouter
from .protocols.middleware import MiddlewareChain


@click.command()
@click.option('--config', '-c', 
              type=click.Path(exists=True, path_type=Path),
              default='config/development.yaml',
              help='Configuration file path')
@click.option('--host', '-h', 
              default='127.0.0.1',
              help='Host to bind the server')
@click.option('--port', '-p', 
              type=int, 
              default=8080,
              help='Port to bind the server')
@click.option('--debug', '-d',
              is_flag=True,
              help='Enable debug mode')
@click.option('--locale', '-l',
              default='zh_CN',
              help='Interface language (zh_CN/en_US)')
def main(config: Path, host: str, port: int, debug: bool, locale: str):
    """Start the MCP Toolkit server."""
    # 初始化国际化
    configure_i18n(I18nConfig(default_locale=locale))
    set_locale(locale)
    
    # 加载配置
    config_data = {}
    if config.exists():
        with open(config, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    
    # 配置日志系统
    log_config = LogConfig(
        level="DEBUG" if debug else "INFO",
        file_path="logs/mcp_toolkit.log",
        enable_console=True,
        enable_file=True
    )
    configure_logging(config_data)
    
    # 获取主日志记录器
    logger = get_logger('mcp_toolkit.main')
    
    logger.info("� 启动MCP工具集服务器...")
    logger.info(f"📁 配置文件: {config}")
    logger.info(f"🌐 服务器地址: http://{host}:{port}")
    logger.info(f"🔧 调试模式: {debug}")
    logger.info(f"🌍 界面语言: {locale}")
    
    # 启动服务器
    try:
        asyncio.run(start_server(host, port, debug))
    except KeyboardInterrupt:
        logger.info("👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")


async def start_server(host: str, port: int, debug: bool):
    """启动HTTP服务器"""
    logger = get_logger('mcp_toolkit.server')
    
    # 创建路由器和中间件
    router = RequestRouter()
    middleware = MiddlewareChain()
    
    # 创建HTTP处理器
    handler = HTTPTransportHandler(router, middleware)
    
    # 启动服务器
    await handler.start_server(host, port)
    logger.info(f"✅ HTTP服务器已启动: http://{host}:{port}")
    
    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 正在停止服务器...")
        await handler.stop_server()


if __name__ == "__main__":
    main()
