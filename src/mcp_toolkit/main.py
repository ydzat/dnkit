"""
MCP Toolkit main entry point.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

from .core import (
    I18nConfig,
    LogConfig,
    configure_i18n,
    configure_logging,
    get_logger,
    set_locale,
)
from .protocols.http_handler import HTTPTransportHandler
from .protocols.middleware import MiddlewareChain
from .protocols.router import RequestRouter
from .protocols.sse_handler import SSETransportHandler
from .protocols.websocket_handler import WebSocketTransportHandler
from .services.basic_tools import BasicToolsService


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/development.yaml",
    help="Configuration file path",
)
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind the server")
@click.option(
    "--port", "-p", type=int, default=8080, help="HTTP port to bind the server"
)
@click.option(
    "--ws-port", type=int, default=8081, help="WebSocket port to bind the server"
)
@click.option("--sse-port", type=int, default=8082, help="SSE port to bind the server")
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode")
@click.option(
    "--locale", "-l", default="zh_CN", help="Interface language (zh_CN/en_US)"
)
def main(
    config: Path,
    host: str,
    port: int,
    ws_port: int,
    sse_port: int,
    debug: bool,
    locale: str,
) -> None:
    """Start the MCP Toolkit server."""
    # 初始化国际化
    configure_i18n(I18nConfig(default_locale=locale))
    set_locale(locale)

    # 加载配置
    config_data = {}
    if config.exists():
        with open(config, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

    # 配置日志系统
    log_config = LogConfig(
        level="DEBUG" if debug else "INFO",
        file_path="logs/mcp_toolkit.log",
        console=True,
    )
    configure_logging(config_data)

    # 获取主日志记录器
    logger = get_logger("mcp_toolkit.main")

    logger.info("� 启动MCP工具集服务器...")
    logger.info(f"📁 配置文件: {config}")
    logger.info(f"🌐 HTTP服务器地址: http://{host}:{port}")
    logger.info(f"🔌 WebSocket服务器地址: ws://{host}:{ws_port}")
    logger.info(f"📡 SSE服务器地址: http://{host}:{sse_port}")
    logger.info(f"🔧 调试模式: {debug}")
    logger.info(f"🌍 界面语言: {locale}")

    # 启动服务器
    try:
        asyncio.run(start_server(host, port, ws_port, sse_port, debug))
    except KeyboardInterrupt:
        logger.info("👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")


async def start_server(
    host: str, port: int, ws_port: int, sse_port: int, debug: bool
) -> None:
    """启动HTTP、WebSocket和SSE服务器"""
    logger = get_logger("mcp_toolkit.server")

    # 创建路由器和中间件
    router = RequestRouter()
    middleware = MiddlewareChain()

    # 创建HTTP、WebSocket和SSE处理器
    http_handler = HTTPTransportHandler(host=host, port=port)
    ws_handler = WebSocketTransportHandler(host=host, port=ws_port)
    sse_handler = SSETransportHandler(host=host, port=sse_port)

    # 初始化基础工具服务
    logger.info("🔧 初始化基础工具服务...")
    basic_tools_service = BasicToolsService()
    await basic_tools_service.initialize()

    # 注册服务到路由器
    await router.register_service(basic_tools_service)

    # 为两个处理器注册相同的MCP方法
    def setup_jsonrpc_methods(jsonrpc_processor: Any) -> None:
        # MCP初始化方法
        async def handle_initialize(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            # 验证协议版本
            if params is None:
                params = {}
            client_protocol_version = params.get("protocolVersion", "2024-11-05")
            client_capabilities = params.get("capabilities", {})
            client_info = params.get("clientInfo", {})

            logger.info(
                f"MCP客户端初始化: {client_info.get('name', 'Unknown')} v{client_info.get('version', 'Unknown')}"
            )
            logger.info(f"客户端协议版本: {client_protocol_version}")
            logger.info(f"客户端能力: {client_capabilities}")

            # 支持客户端请求的协议版本（向前兼容）
            supported_versions = ["2024-11-05", "2025-03-26"]
            server_protocol_version = (
                client_protocol_version
                if client_protocol_version in supported_versions
                else "2024-11-05"
            )

            logger.info(f"使用协议版本: {server_protocol_version}")

            # 返回服务器能力
            return {
                "protocolVersion": server_protocol_version,
                "capabilities": {"tools": {"listChanged": True}, "logging": {}},
                "serverInfo": {
                    "name": "dnkit-mcp-toolkit",
                    "title": "DNKit MCP Toolkit Server",
                    "version": "1.0.0",
                },
                "instructions": "DNKit MCP工具集服务器，提供文件操作、终端执行、网络请求等工具功能",
            }

        # 初始化完成通知处理
        async def handle_initialized(params: Optional[Dict[str, Any]] = None) -> None:
            logger.info("MCP客户端初始化完成，服务器准备就绪")
            return None  # 通知不需要返回值

        # 注册tools/list方法
        async def handle_tools_list(
            params: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            tools = basic_tools_service.get_tools()
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.parameters,
                    }
                    for tool in tools
                ]
            }

        # 注册tools/call方法
        async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
            if not params or "name" not in params:
                raise ValueError("Missing required parameter: name")

            tool_name = params["name"]
            arguments = params.get("arguments", {})

            # 创建工具调用请求
            from .core.types import ToolCallRequest

            request = ToolCallRequest(
                tool_name=tool_name,
                arguments=arguments,
                request_id=f"req_{asyncio.get_event_loop().time()}",
            )

            # 执行工具调用
            response = await basic_tools_service.call_tool(request)

            if response.success:
                return {"content": [{"type": "text", "text": str(response.result)}]}
            else:
                raise Exception(response.error or "Tool execution failed")

        # 注册MCP协议方法
        jsonrpc_processor.register_method("initialize", handle_initialize)
        jsonrpc_processor.register_method(
            "notifications/initialized", handle_initialized
        )
        jsonrpc_processor.register_method("tools/list", handle_tools_list)
        jsonrpc_processor.register_method("tools/call", handle_tools_call)

    # 为HTTP、WebSocket和SSE处理器设置方法
    setup_jsonrpc_methods(http_handler.jsonrpc_processor)
    setup_jsonrpc_methods(ws_handler.jsonrpc_processor)
    setup_jsonrpc_methods(sse_handler.jsonrpc_processor)

    logger.info(f"📋 已注册 {len(basic_tools_service.get_tools())} 个工具")

    # 启动HTTP、WebSocket和SSE服务器
    await http_handler.start()
    await ws_handler.start()
    await sse_handler.start()
    logger.info(f"✅ HTTP服务器已启动: http://{host}:{port}")
    logger.info(f"✅ WebSocket服务器已启动: ws://{host}:{ws_port}")
    logger.info(f"✅ SSE服务器已启动: http://{host}:{sse_port}")

    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 正在停止服务器...")
        await basic_tools_service.cleanup()
        await http_handler.stop()
        await ws_handler.stop()
        await sse_handler.stop()


if __name__ == "__main__":
    main()
