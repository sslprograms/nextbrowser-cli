from __future__ import annotations

import os
from pathlib import Path

from nextbrowser_harness.config import (
    AutomationChoice,
    BrowserChoice,
    HarnessConfig,
    ProxyChoice,
    UseCase,
)


def onboard_interactive() -> HarnessConfig:
    print("\n=== Nextbrowser Harness — onboarding ===\n")
    print("Target: under 5 minutes. Defaults are pre-selected; press Enter to accept.\n")

    use_raw = input("What do you want to do? [scrape/manage accounts] (default: scrape): ").strip().lower()
    use_case: UseCase = "accounts" if use_raw.startswith("m") or "account" in use_raw else "scrape"

    print("\nChoose browser:")
    print("  1) Native bundled browser (default)")
    print("  2) Multilogin")
    print("  3) GoLogin")
    print("  4) Octo Browser")
    browser_map = {"1": "native", "2": "multilogin", "3": "gologin", "4": "octo", "": "native"}
    browser_raw = input("Selection [1]: ").strip()
    browser: BrowserChoice = browser_map.get(browser_raw, "native")  # type: ignore[assignment]

    print("\nChoose proxy:")
    print("  1) NodeMaven residential (default)")
    print("  2) Bring your own proxies")
    proxy_map = {"1": "nodemaven", "2": "custom", "": "nodemaven"}
    proxy_raw = input("Selection [1]: ").strip()
    proxy: ProxyChoice = proxy_map.get(proxy_raw, "nodemaven")  # type: ignore[assignment]

    cfg = HarnessConfig(
        use_case=use_case,
        browser=browser,
        proxy=proxy,
        automation="playwright",
        headless=use_case == "scrape",
        llm_model=os.getenv("ANTHROPIC_MODEL") or os.getenv("OPENAI_MODEL") or None,
    )

    if proxy == "nodemaven":
        host = os.getenv("NODEMAVEN_PROXY_HOST", "")
        user = os.getenv("NODEMAVEN_PROXY_USER", "")
        password = os.getenv("NODEMAVEN_PROXY_PASSWORD", "")
        if host:
            cfg.nodemaven = {"host": host, "user": user, "password": password}
        else:
            print("\nTip: set NODEMAVEN_PROXY_HOST, NODEMAVEN_PROXY_USER, NODEMAVEN_PROXY_PASSWORD in .env")

    if proxy == "custom":
        raw = input("Proxy URLs (comma-separated, host:port:user:pass or http://...): ").strip()
        cfg.custom_proxies = [p.strip() for p in raw.split(",") if p.strip()]

    captcha = input("\nEnable CAPTCHA solver? [y/N]: ").strip().lower()
    if captcha == "y":
        cfg.captcha_enabled = True
        cfg.captcha_provider = input("Provider (2captcha, capmonster, ...): ").strip() or "2captcha"
        cfg.captcha_token = input("API token: ").strip() or None

    Path(cfg.profiles_dir).mkdir(parents=True, exist_ok=True)
    cfg.save()
    _print_summary(cfg)
    return cfg


def onboard_from_env() -> HarnessConfig:
    """Headless onboarding for agents — env vars override defaults."""
    use = os.getenv("NEXTBROWSER_USE_CASE", "scrape").lower()
    cfg = HarnessConfig(
        use_case="accounts" if use.startswith("account") else "scrape",
        browser=os.getenv("NEXTBROWSER_BROWSER", "native"),  # type: ignore[arg-type]
        proxy=os.getenv("NEXTBROWSER_PROXY", "nodemaven"),  # type: ignore[arg-type]
        automation=os.getenv("NEXTBROWSER_AUTOMATION", "playwright"),  # type: ignore[arg-type]
        headless=os.getenv("NEXTBROWSER_HEADLESS", "true").lower() in ("1", "true", "yes"),
        llm_model=os.getenv("NEXTBROWSER_LLM_MODEL") or os.getenv("ANTHROPIC_MODEL"),
    )
    if os.getenv("NODEMAVEN_PROXY_HOST"):
        cfg.nodemaven = {
            "host": os.getenv("NODEMAVEN_PROXY_HOST", ""),
            "user": os.getenv("NODEMAVEN_PROXY_USER", ""),
            "password": os.getenv("NODEMAVEN_PROXY_PASSWORD", ""),
        }
    if os.getenv("NEXTBROWSER_CUSTOM_PROXIES"):
        cfg.custom_proxies = [
            p.strip() for p in os.getenv("NEXTBROWSER_CUSTOM_PROXIES", "").split(",") if p.strip()
        ]
    _apply_multilogin_env(cfg)
    cfg.save()
    return cfg


def _apply_multilogin_env(cfg: HarnessConfig) -> None:
    """Persist MLX folder/profile UUIDs from env into config for agents."""
    folder = os.getenv("MULTILOGIN_FOLDER_ID", "").strip()
    default_profile = os.getenv("MULTILOGIN_PROFILE_ID", "").strip()
    profiles: dict[str, str] = {}
    for key, val in os.environ.items():
        if not key.startswith("MULTILOGIN_PROFILE_") or key == "MULTILOGIN_PROFILE_ID":
            continue
        if not val.strip():
            continue
        account_key = key[len("MULTILOGIN_PROFILE_") :].lower()
        profiles[account_key] = val.strip()
    if folder or default_profile or profiles:
        cfg.multilogin = {
            "folder_id": folder,
            "default_profile_id": default_profile,
            "profiles": profiles,
        }
    if os.getenv("NEXTBROWSER_BROWSER", "").strip().lower() == "multilogin":
        cfg.browser = "multilogin"  # type: ignore[assignment]


def _print_summary(cfg: HarnessConfig) -> None:
    print("\n--- Configuration saved ---")
    print(f"  Use case:    {cfg.use_case}")
    print(f"  Browser:     {cfg.browser}")
    print(f"  Proxy:       {cfg.proxy}")
    print(f"  Automation:  {cfg.automation}")
    print(f"  LLM model:   {cfg.llm_model or '(inherits from agent runtime)'}")
    print(f"  CAPTCHA:     {'on' if cfg.captcha_enabled else 'off'}")
    path = cfg.save()
    print(f"  Config file: {path}\n")
