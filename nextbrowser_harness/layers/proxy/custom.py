from __future__ import annotations

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.proxy.base import ProxyEndpoint, ProxyLayer


def _parse_proxy(raw: str) -> ProxyEndpoint:
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        from urllib.parse import urlparse

        u = urlparse(raw)
        server = f"{u.hostname}:{u.port or 80}"
        return ProxyEndpoint(server=server, username=u.username, password=u.password)
    parts = raw.split(":")
    if len(parts) >= 4:
        host, port, user, password = parts[0], parts[1], parts[2], ":".join(parts[3:])
        return ProxyEndpoint(server=f"{host}:{port}", username=user, password=password)
    if len(parts) == 2:
        return ProxyEndpoint(server=f"{parts[0]}:{parts[1]}")
    return ProxyEndpoint(server=raw)


class CustomProxyLayer:
    def __init__(self, proxies: list[str]):
        if not proxies:
            raise ValueError("No custom proxies configured")
        self.proxies = [_parse_proxy(p) for p in proxies]
        self._idx = 0

    @classmethod
    def from_config(cls, config: HarnessConfig) -> CustomProxyLayer:
        return cls(config.custom_proxies)

    def get_endpoint(self, session_id: str | None = None) -> ProxyEndpoint:
        ep = self.proxies[self._idx % len(self.proxies)]
        self._idx += 1
        return ep
