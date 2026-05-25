from __future__ import annotations

import os
from pathlib import Path

from nextbrowser_harness.config import (
    AutomationChoice,
    BrowserChoice,
    DriverChoice,
    HarnessConfig,
    ProxyChoice,
    UseCase,
    resolve_config_path,
)

# Example / test placeholders — never write these into config.yaml
_PLACEHOLDER_MLX_IDS = frozenset(
    {"folder-1", "profile-1", "folder-uuid", "profile-uuid", "your-folder-id", "your-profile-id"}
)


def _is_placeholder_mlx_id(value: str) -> bool:
    v = (value or "").strip().lower()
    return not v or v in _PLACEHOLDER_MLX_IDS


def _prompt_proxy(browser: BrowserChoice) -> ProxyChoice:
    if browser == "multilogin":
        print("\nProxy: skipped — Multilogin profiles use their own proxies.")
        return "none"
    print("\nChoose proxy (optional):")
    print("  1) None (default)")
    print("  2) NodeMaven residential (recommended for native tier-3)")
    print("  3) Bring your own proxies")
    proxy_map = {"1": "none", "2": "nodemaven", "3": "custom", "": "none"}
    proxy_raw = input("Selection [1]: ").strip()
    return proxy_map.get(proxy_raw, "none")  # type: ignore[return-value]


def onboard_interactive(*, run_mlx_wizard: bool = False) -> HarnessConfig:
    print("\n=== Nextbrowser Harness — onboarding ===\n")
    print("Target: under 5 minutes. Defaults are pre-selected; press Enter to accept.\n")

    use_raw = input("What do you want to do? [scrape/manage accounts] (default: scrape): ").strip().lower()
    use_case: UseCase = "accounts" if use_raw.startswith("m") or "account" in use_raw else "scrape"

    print("\nChoose browser:")
    print("  1) Native undetectable Chrome (default)")
    print("  2) Multilogin X")
    print("  3) GoLogin")
    print("  4) Octo Browser")
    browser_map = {"1": "native", "2": "multilogin", "3": "gologin", "4": "octo", "": "native"}
    browser_raw = input("Selection [1]: ").strip()
    browser: BrowserChoice = browser_map.get(browser_raw, "native")  # type: ignore[assignment]

    proxy: ProxyChoice = _prompt_proxy(browser)

    driver: DriverChoice = "undetected" if browser == "native" else "playwright"

    cfg = HarnessConfig(
        use_case=use_case,
        browser=browser,
        proxy=proxy,
        driver=driver,
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

    if browser == "multilogin" or run_mlx_wizard:
        from nextbrowser_harness.integrations.multilogin.setup_wizard import run_setup_wizard

        run_setup_wizard(cfg=cfg)

    return cfg


def onboard_from_env() -> HarnessConfig:
    """Headless onboarding — merge env into existing config (never wipe MLX UUIDs)."""
    path = resolve_config_path()
    cfg = HarnessConfig.load() if path.exists() else HarnessConfig()

    use = os.getenv("NEXTBROWSER_USE_CASE", "").strip().lower()
    if use:
        cfg.use_case = "accounts" if use.startswith("account") else "scrape"  # type: ignore[assignment]

    browser = os.getenv("NEXTBROWSER_BROWSER", "").strip().lower()
    if browser:
        cfg.browser = browser  # type: ignore[assignment]

    proxy = os.getenv("NEXTBROWSER_PROXY", "").strip().lower()
    if proxy:
        cfg.proxy = proxy  # type: ignore[assignment]
    elif cfg.browser == "multilogin":
        cfg.proxy = "none"  # type: ignore[assignment]

    driver_raw = os.getenv("NEXTBROWSER_DRIVER", "").strip().lower()
    if driver_raw:
        cfg.driver = "playwright" if driver_raw == "playwright" else "undetected"  # type: ignore[assignment]
    if cfg.browser != "native":
        cfg.driver = "playwright"  # type: ignore[assignment]

    automation = os.getenv("NEXTBROWSER_AUTOMATION", "").strip().lower()
    if automation:
        cfg.automation = automation  # type: ignore[assignment]

    element_search = os.getenv("NEXTBROWSER_ELEMENT_SEARCH", "").strip().lower()
    if element_search in ("indexed", "index", "agent", "ai", "browser_use", "browser-use", "bu"):
        cfg.element_search = "indexed"  # type: ignore[assignment]
    elif element_search == "playwright":
        cfg.element_search = "playwright"  # type: ignore[assignment]

    headless_env = os.getenv("NEXTBROWSER_HEADLESS", "").strip().lower()
    if headless_env:
        cfg.headless = headless_env in ("1", "true", "yes")

    llm = os.getenv("NEXTBROWSER_LLM_MODEL") or os.getenv("ANTHROPIC_MODEL")
    if llm:
        cfg.llm_model = llm

    if cfg.proxy == "nodemaven" and os.getenv("NODEMAVEN_PROXY_HOST"):
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
    """Merge MLX folder/profile UUIDs from env into config (keep existing real UUIDs)."""
    folder = os.getenv("MULTILOGIN_FOLDER_ID", "").strip()
    default_profile = os.getenv("MULTILOGIN_PROFILE_ID", "").strip()
    if _is_placeholder_mlx_id(folder):
        folder = ""
    if _is_placeholder_mlx_id(default_profile):
        default_profile = ""

    profiles: dict[str, str] = dict((cfg.multilogin or {}).get("profiles") or {})
    for key, val in os.environ.items():
        if not key.startswith("MULTILOGIN_PROFILE_") or key == "MULTILOGIN_PROFILE_ID":
            continue
        pid = val.strip()
        if not pid or _is_placeholder_mlx_id(pid):
            continue
        account_key = key[len("MULTILOGIN_PROFILE_") :].lower()
        profiles[account_key] = pid

    mlx: dict[str, object] = dict(cfg.multilogin or {})
    if folder:
        mlx["folder_id"] = folder
    if default_profile:
        mlx["default_profile_id"] = default_profile
    if profiles:
        mlx["profiles"] = profiles
    if mlx:
        cfg.multilogin = mlx

    if os.getenv("NEXTBROWSER_BROWSER", "").strip().lower() == "multilogin":
        cfg.browser = "multilogin"  # type: ignore[assignment]
        cfg.proxy = "none"  # type: ignore[assignment]


def _print_summary(cfg: HarnessConfig) -> None:
    print("\n--- Configuration saved ---")
    print(f"  Use case:    {cfg.use_case}")
    print(f"  Browser:     {cfg.browser}")
    print(f"  Driver:      {cfg.driver}")
    print(f"  Proxy:       {cfg.proxy}")
    print(f"  Automation:  {cfg.automation}")
    print(f"  LLM model:   {cfg.llm_model or '(inherits from agent runtime)'}")
    print(f"  CAPTCHA:     {'on' if cfg.captcha_enabled else 'off'}")
    path = cfg.save()
    print(f"  Config file: {path}\n")
