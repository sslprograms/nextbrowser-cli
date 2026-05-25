from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

UseCase = Literal["scrape", "accounts"]
BrowserChoice = Literal["native", "multilogin", "gologin", "octo"]
ProxyChoice = Literal["none", "nodemaven", "custom"]
AutomationChoice = Literal["browser_use", "playwright", "custom"]
DriverChoice = Literal["undetected", "playwright"]
TierLevel = Literal[1, 2, 3]

CONFIG_ENV = "NEXTBROWSER_CONFIG"
DEFAULT_CONFIG_PATH = Path.home() / ".nextbrowser" / "config.yaml"


@dataclass
class HarnessConfig:
    """Persisted harness configuration from onboarding."""

    use_case: UseCase = "scrape"
    browser: BrowserChoice = "native"
    proxy: ProxyChoice = "none"
    driver: DriverChoice = "undetected"
    automation: AutomationChoice = "playwright"
    headless: bool = True
    captcha_enabled: bool = False
    captcha_provider: str | None = None
    captcha_token: str | None = None
    llm_model: str | None = None  # inherits from agent runtime when unset
    nodemaven: dict[str, str] = field(default_factory=dict)
    multilogin: dict[str, object] = field(default_factory=dict)
    custom_proxies: list[str] = field(default_factory=list)
    profiles_dir: str = str(Path.home() / ".nextbrowser" / "profiles")
    tier_cache_path: str = str(Path.home() / ".nextbrowser" / "tier_cache.yaml")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessConfig:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | None = None) -> Path:
        target = path or resolve_config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path | None = None) -> HarnessConfig:
        target = path or resolve_config_path()
        if not target.exists():
            return cls()
        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)


def resolve_config_path() -> Path:
    env = os.getenv(CONFIG_ENV)
    if env:
        return Path(env)
    local = Path.cwd() / ".nextbrowser.yaml"
    if local.exists():
        return local
    return DEFAULT_CONFIG_PATH
