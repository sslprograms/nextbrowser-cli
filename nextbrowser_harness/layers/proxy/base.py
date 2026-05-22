from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nextbrowser_harness.config import HarnessConfig


@dataclass
class ProxyEndpoint:
    server: str  # playwright format host:port
    username: str | None = None
    password: str | None = None

    def requests_proxies(self) -> dict[str, str]:
        if self.username and self.password:
            url = f"http://{self.username}:{self.password}@{self.server}"
        else:
            url = f"http://{self.server}"
        return {"http": url, "https": url}

    def playwright_proxy(self) -> dict | None:
        if not self.server:
            return None
        cfg: dict = {"server": f"http://{self.server}"}
        if self.username:
            cfg["username"] = self.username
            cfg["password"] = self.password or ""
        return cfg


class ProxyLayer(Protocol):
    def get_endpoint(self, session_id: str | None = None) -> ProxyEndpoint: ...

    @classmethod
    def from_config(cls, config: HarnessConfig) -> ProxyLayer: ...
