"""
网络操作工具集

提供HTTP请求、WebSocket连接、DNS查询等网络相关功能。
包含安全限制和访问控制机制。
"""

import asyncio
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceEstimate,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
    ValidationError,
    ValidationResult,
)


class BaseNetworkTool(BaseTool):
    """网络操作工具基类"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.allowed_domains = self.config.get("allowed_domains", [])
        self.forbidden_domains = self.config.get("forbidden_domains", [])
        self.allowed_ports = self.config.get("allowed_ports", [])
        self.forbidden_ports = self.config.get(
            "forbidden_ports", [22, 23, 25, 53, 135, 139, 445]
        )
        self.max_response_size = (
            self.config.get("max_response_size_mb", 50) * 1024 * 1024
        )  # 转换为字节
        self.default_timeout = self.config.get("default_timeout_seconds", 30)
        self.max_redirects = self.config.get("max_redirects", 5)

    def _validate_url(self, url: str) -> ValidationResult:
        """验证URL安全性"""
        errors = []

        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in ["http", "https"]:
                errors.append(
                    ValidationError(
                        field="url",
                        message=f"不支持的协议: {parsed.scheme}",
                        code="UNSUPPORTED_PROTOCOL",
                    )
                )

            # 检查域名
            hostname = parsed.hostname
            if hostname:
                # 检查禁止域名
                for forbidden in self.forbidden_domains:
                    if hostname.endswith(forbidden):
                        errors.append(
                            ValidationError(
                                field="url",
                                message=f"域名 {hostname} 被禁止访问",
                                code="FORBIDDEN_DOMAIN",
                            )
                        )

                # 检查允许域名（如果配置了白名单）
                if self.allowed_domains:
                    allowed = False
                    for allowed_domain in self.allowed_domains:
                        if hostname.endswith(allowed_domain):
                            allowed = True
                            break
                    if not allowed:
                        errors.append(
                            ValidationError(
                                field="url",
                                message=f"域名 {hostname} 不在允许列表中",
                                code="DOMAIN_NOT_ALLOWED",
                            )
                        )

                # 检查内网地址
                try:
                    ip = socket.gethostbyname(hostname)
                    if self._is_private_ip(ip):
                        errors.append(
                            ValidationError(
                                field="url",
                                message=f"不允许访问内网地址: {ip}",
                                code="PRIVATE_IP_FORBIDDEN",
                            )
                        )
                except socket.gaierror:
                    errors.append(
                        ValidationError(
                            field="url",
                            message=f"无法解析域名: {hostname}",
                            code="DNS_RESOLUTION_FAILED",
                        )
                    )

            # 检查端口
            port = parsed.port
            if port:
                if self.forbidden_ports and port in self.forbidden_ports:
                    errors.append(
                        ValidationError(
                            field="url",
                            message=f"端口 {port} 被禁止访问",
                            code="FORBIDDEN_PORT",
                        )
                    )
                elif self.allowed_ports and port not in self.allowed_ports:
                    errors.append(
                        ValidationError(
                            field="url",
                            message=f"端口 {port} 不在允许列表中",
                            code="PORT_NOT_ALLOWED",
                        )
                    )

        except Exception as e:
            errors.append(
                ValidationError(
                    field="url",
                    message=f"URL解析失败: {str(e)}",
                    code="URL_PARSE_ERROR",
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _is_private_ip(self, ip: str) -> bool:
        """检查是否为私有IP地址"""
        import ipaddress

        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return False


class HttpRequestTool(BaseNetworkTool):
    """HTTP请求工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="http_request",
            description="发送HTTP/HTTPS请求并返回响应",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "description": "请求URL",
                    },
                    "method": {
                        "type": "string",
                        "enum": [
                            "GET",
                            "POST",
                            "PUT",
                            "DELETE",
                            "PATCH",
                            "HEAD",
                            "OPTIONS",
                        ],
                        "default": "GET",
                        "description": "HTTP方法",
                    },
                    "headers": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "请求头",
                    },
                    "body": {
                        "type": "string",
                        "description": "请求体（JSON字符串或普通文本）",
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30,
                        "description": "超时时间（秒）",
                    },
                    "follow_redirects": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否跟随重定向",
                    },
                    "max_redirects": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                        "default": 5,
                        "description": "最大重定向次数",
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否验证SSL证书",
                    },
                    "proxy": {"type": "string", "description": "代理服务器地址"},
                    "auth": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["basic", "bearer", "custom"],
                            },
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "token": {"type": "string"},
                        },
                        "description": "认证信息",
                    },
                },
                "required": ["url"],
            },
        )

    def validate_parameters(self, params: Dict[str, Any]) -> ValidationResult:
        """验证参数"""
        errors: List[ValidationError] = []
        sanitized = {}

        # 验证URL
        url = params.get("url", "")
        url_validation = self._validate_url(url)
        if not url_validation.is_valid:
            errors.extend(url_validation.errors or [])
        sanitized["url"] = url

        # 验证HTTP方法
        method = params.get("method", "GET").upper()
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if method not in valid_methods:
            errors.append(
                ValidationError(
                    field="method",
                    message=f"不支持的HTTP方法: {method}",
                    code="INVALID_METHOD",
                )
            )
        sanitized["method"] = method

        # 验证请求头
        headers = params.get("headers", {})
        if not isinstance(headers, dict):
            errors.append(
                ValidationError(
                    field="headers",
                    message="headers 必须是对象",
                    code="INVALID_HEADERS_TYPE",
                )
            )
        else:
            for key, value in headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    errors.append(
                        ValidationError(
                            field="headers",
                            message="请求头的键和值都必须是字符串",
                            code="INVALID_HEADER_TYPE",
                        )
                    )
        sanitized["headers"] = headers

        # 验证请求体
        body = params.get("body")
        if body is not None and not isinstance(body, str):
            errors.append(
                ValidationError(
                    field="body", message="body 必须是字符串", code="INVALID_BODY_TYPE"
                )
            )
        sanitized["body"] = body

        # 验证超时时间
        timeout = params.get("timeout", self.default_timeout)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
            errors.append(
                ValidationError(
                    field="timeout",
                    message="timeout 必须在 1 到 300 之间",
                    code="INVALID_TIMEOUT",
                )
            )
        sanitized["timeout"] = timeout

        # 验证重定向参数
        follow_redirects = params.get("follow_redirects", True)
        if not isinstance(follow_redirects, bool):
            errors.append(
                ValidationError(
                    field="follow_redirects",
                    message="follow_redirects 必须是布尔值",
                    code="INVALID_FOLLOW_REDIRECTS_TYPE",
                )
            )
        sanitized["follow_redirects"] = follow_redirects

        max_redirects = params.get("max_redirects", 5)
        if (
            not isinstance(max_redirects, int)
            or max_redirects < 0
            or max_redirects > 10
        ):
            errors.append(
                ValidationError(
                    field="max_redirects",
                    message="max_redirects 必须在 0 到 10 之间",
                    code="INVALID_MAX_REDIRECTS",
                )
            )
        sanitized["max_redirects"] = max_redirects

        # 验证SSL选项
        verify_ssl = params.get("verify_ssl", True)
        if not isinstance(verify_ssl, bool):
            errors.append(
                ValidationError(
                    field="verify_ssl",
                    message="verify_ssl 必须是布尔值",
                    code="INVALID_VERIFY_SSL_TYPE",
                )
            )
        sanitized["verify_ssl"] = verify_ssl

        # 验证代理
        proxy = params.get("proxy")
        if proxy is not None and not isinstance(proxy, str):
            errors.append(
                ValidationError(
                    field="proxy",
                    message="proxy 必须是字符串",
                    code="INVALID_PROXY_TYPE",
                )
            )
        sanitized["proxy"] = proxy

        # 验证认证信息
        auth = params.get("auth")
        if auth is not None:
            if not isinstance(auth, dict):
                errors.append(
                    ValidationError(
                        field="auth",
                        message="auth 必须是对象",
                        code="INVALID_AUTH_TYPE",
                    )
                )
            else:
                auth_type = auth.get("type")
                if auth_type not in ["basic", "bearer", "custom"]:
                    errors.append(
                        ValidationError(
                            field="auth.type",
                            message="auth.type 必须是 'basic', 'bearer' 或 'custom'",
                            code="INVALID_AUTH_TYPE_VALUE",
                        )
                    )
        sanitized["auth"] = auth

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized if len(errors) == 0 else None,
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行HTTP请求"""
        params = request.parameters
        url = params["url"]
        method = params.get("method", "GET")
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout", self.default_timeout)
        follow_redirects = params.get("follow_redirects", True)
        max_redirects = params.get("max_redirects", 5)
        verify_ssl = params.get("verify_ssl", True)
        proxy = params.get("proxy")
        auth = params.get("auth")

        start_time = time.time()
        redirects: List[str] = []

        try:
            # 构建请求
            req = urllib.request.Request(url, method=method)

            # 添加请求头
            for key, value in headers.items():
                req.add_header(key, value)

            # 添加认证
            if auth:
                auth_type = auth.get("type")
                if auth_type == "basic":
                    import base64

                    username = auth.get("username", "")
                    password = auth.get("password", "")
                    credentials = base64.b64encode(
                        f"{username}:{password}".encode()
                    ).decode()
                    req.add_header("Authorization", f"Basic {credentials}")
                elif auth_type == "bearer":
                    req.add_header("Authorization", f"Bearer {auth.get('token', '')}")

            # 添加请求体
            if body and method in ["POST", "PUT", "PATCH"]:
                req.data = body.encode("utf-8")

            # 配置opener
            opener = urllib.request.build_opener()

            if not follow_redirects:
                # 禁用重定向
                opener.add_handler(urllib.request.HTTPRedirectHandler())

            if proxy:
                proxy_handler = urllib.request.ProxyHandler(
                    {"http": proxy, "https": proxy}
                )
                opener.add_handler(proxy_handler)

            # 发送请求
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: opener.open(req, timeout=timeout)
                )

                # 读取响应
                response_body = response.read().decode("utf-8", errors="replace")

                # 检查响应大小
                if len(response_body.encode()) > self.max_response_size:
                    return self._create_error_result(
                        "RESPONSE_TOO_LARGE",
                        f"响应过大, 超过限制 ({self.max_response_size} bytes)",
                    )

                response_time = (time.time() - start_time) * 1000  # 转换为毫秒

                result_content = {
                    "status_code": response.getcode(),
                    "headers": dict(response.headers),
                    "body": response_body,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": len(response_body.encode()),
                    "response_time": response_time / 1000,  # 转换回秒
                    "redirects": redirects,
                }

                metadata = ExecutionMetadata(
                    execution_time=response_time,
                    memory_used=len(response_body.encode()) / 1024 / 1024,
                    cpu_time=response_time * 0.1,  # 估算
                    io_operations=1,
                    cache_hit=False,
                )

                resources = ResourceUsage(
                    memory_mb=len(response_body.encode()) / 1024 / 1024,
                    cpu_time_ms=response_time * 0.1,
                    io_operations=1,
                    network_requests=1,
                )

                return self._create_success_result(result_content, metadata, resources)

            except urllib.error.HTTPError as e:
                # HTTP错误响应也需要处理
                error_body = (
                    e.read().decode("utf-8", errors="replace")
                    if hasattr(e, "read")
                    else ""
                )
                response_time = (time.time() - start_time) * 1000

                result_content = {
                    "status_code": e.code,
                    "headers": dict(e.headers) if hasattr(e, "headers") else {},
                    "body": error_body,
                    "content_type": (
                        e.headers.get("Content-Type", "")
                        if hasattr(e, "headers")
                        else ""
                    ),
                    "content_length": len(error_body.encode()),
                    "response_time": response_time / 1000,
                    "redirects": redirects,
                }

                metadata = ExecutionMetadata(
                    execution_time=response_time,
                    memory_used=len(error_body.encode()) / 1024 / 1024,
                    cpu_time=response_time * 0.1,
                    io_operations=1,
                )

                resources = ResourceUsage(
                    memory_mb=len(error_body.encode()) / 1024 / 1024,
                    cpu_time_ms=response_time * 0.1,
                    io_operations=1,
                    network_requests=1,
                )

                return self._create_success_result(result_content, metadata, resources)

        except urllib.error.URLError as e:
            if "timeout" in str(e).lower():
                return self._create_error_result(
                    "REQUEST_TIMEOUT", f"请求超时 (>{timeout}秒)"
                )
            else:
                return self._create_error_result(
                    "CONNECTION_ERROR", f"连接错误: {str(e)}"
                )
        except Exception as e:
            self._logger.exception("HTTP请求时发生异常")
            return self._create_error_result("REQUEST_ERROR", f"请求失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class DnsLookupTool(BaseNetworkTool):
    """DNS查询工具"""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dns_lookup",
            description="执行DNS查询获取域名解析信息",
            parameters={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "要查询的主机名或域名",
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "PTR"],
                        "default": "A",
                        "description": "DNS记录类型",
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 60,
                        "default": 10,
                        "description": "查询超时时间（秒）",
                    },
                },
                "required": ["hostname"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行DNS查询"""
        params = request.parameters
        hostname = params["hostname"]
        record_type = params.get("record_type", "A")
        timeout = params.get("timeout", 10)

        try:
            start_time = time.time()

            # 执行DNS查询
            if record_type == "A":
                # IPv4地址查询
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, socket.gethostbyname_ex, hostname
                    ),
                    timeout=timeout,
                )

                records = {
                    "hostname": result[0],
                    "aliases": result[1],
                    "addresses": result[2],
                }

            elif record_type == "AAAA":
                # IPv6地址查询
                try:
                    # 直接调用而不使用 executor，避免类型复杂性
                    ipv6_result = socket.getaddrinfo(hostname, None, socket.AF_INET6)
                    addresses = [str(info[4][0]) for info in ipv6_result]
                    records = {"hostname": hostname, "addresses": addresses}
                except socket.gaierror as e:
                    records = {"hostname": hostname, "error": str(e)}

            else:
                # 其他记录类型需要更专业的DNS库
                return self._create_error_result(
                    "UNSUPPORTED_RECORD_TYPE", f"暂不支持 {record_type} 记录类型的查询"
                )

            query_time = (time.time() - start_time) * 1000  # 转换为毫秒

            result_content = {
                "hostname": hostname,
                "record_type": record_type,
                "records": records,
                "query_time": query_time / 1000,  # 转换回秒
                "server": "system_default",  # 简化实现
            }

            metadata = ExecutionMetadata(
                execution_time=query_time,
                memory_used=0.01,
                cpu_time=query_time * 0.1,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=0.01,
                cpu_time_ms=query_time * 0.1,
                io_operations=1,
                network_requests=1,
            )

            return self._create_success_result(result_content, metadata, resources)

        except socket.gaierror as e:
            return self._create_error_result(
                "DNS_RESOLUTION_FAILED", f"DNS解析失败: {str(e)}"
            )
        except asyncio.TimeoutError:
            return self._create_error_result(
                "DNS_TIMEOUT", f"DNS查询超时 (>{timeout}秒)"
            )
        except Exception as e:
            self._logger.exception("DNS查询时发生异常")
            return self._create_error_result("DNS_ERROR", f"DNS查询失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


class NetworkTools:
    """网络操作工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        self.config = config or {}

    def create_tools(self) -> List[BaseTool]:
        """创建所有网络工具"""
        tools_config = self.config.get("network", {})

        return [HttpRequestTool(tools_config), DnsLookupTool(tools_config)]
