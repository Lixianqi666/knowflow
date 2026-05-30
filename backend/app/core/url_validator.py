"""URL 安全校验：防止 SSRF 攻击"""

import ipaddress
import socket
from urllib.parse import urlparse


class URLError(Exception):
    pass


def validate_webhook_url(url: str) -> None:
    """校验 Webhook URL，不安全则抛出 URLError"""
    # 仅允许 http/https
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise URLError("仅支持 http 和 https 协议")
    if not parsed.hostname:
        raise URLError("URL 格式无效")

    hostname = parsed.hostname

    # 禁止明显不安全的主机名
    blocked_names = {"localhost", "0.0.0.0", "::1", "metadata.google.internal"}
    if hostname.lower() in blocked_names:
        raise URLError("URL 指向不允许访问的地址")

    # DNS 解析后逐个校验 IP
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, OSError):
        raise URLError("URL 域名解析失败")

    if not infos:
        raise URLError("URL 域名解析失败")

    seen = set()
    for family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        _check_ip(ip_str)


def _check_ip(ip_str: str) -> None:
    """校验单个 IP 地址是否安全"""
    ip = ipaddress.ip_address(ip_str)
    if ip.is_loopback:
        raise URLError("URL 指向不允许访问的地址")
    if ip.is_link_local:
        raise URLError("URL 指向不允许访问的地址")
    if ip.is_multicast:
        raise URLError("URL 指向不允许访问的地址")
    if ip.is_reserved:
        raise URLError("URL 指向不允许访问的地址")
    if ip.is_private:
        raise URLError("URL 指向不允许访问的地址")
    if not ip.is_global:
        raise URLError("URL 指向不允许访问的地址")
