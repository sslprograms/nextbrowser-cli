from __future__ import annotations

import os

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.proxy.base import ProxyEndpoint, ProxyLayer


class NodeMavenProxyLayer:
    """NodeMaven residential — default proxy integration."""

    def __init__(self, host: str, user: str = "", password: str = ""):
        self.host = host
        self.user = user
        self.password = password

    @classmethod
    def from_config(cls, config: HarnessConfig) -> NodeMavenProxyLayer:
        nm = config.nodemaven or {}
        host = nm.get("host") or os.getenv("NODEMAVEN_PROXY_HOST", "")
        user = nm.get("user") or os.getenv("NODEMAVEN_PROXY_USER", "")
        password = nm.get("password") or os.getenv("NODEMAVEN_PROXY_PASSWORD", "")
        if not host:
            raise ValueError(
                "NodeMaven proxy not configured. Set NODEMAVEN_PROXY_HOST (and user/pass) in .env"
            )
        return cls(host=host, user=user, password=password)

    def get_endpoint(self, session_id: str | None = None) -> ProxyEndpoint:
        # Sticky session: append session id to username when provider supports it
        user = self.user
        if session_id and user:
            user = f"{user}-session-{session_id}"
        return ProxyEndpoint(server=self.host, username=user or None, password=self.password or None)
