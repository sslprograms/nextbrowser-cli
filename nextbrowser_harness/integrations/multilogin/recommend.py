"""When to suggest Multilogin X vs native browser."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.platform_hints import (
    mlx_install_check,
    mlx_setup_wizard_command,
)
from nextbrowser_harness.tiers.resolver import TierResolver


def _mlx_profile_configured(config: HarnessConfig) -> bool:
    mlx = config.multilogin or {}
    if mlx.get("folder_id") or mlx.get("default_profile_id") or mlx.get("profiles"):
        return True
    if os.getenv("MULTILOGIN_FOLDER_ID") and os.getenv("MULTILOGIN_PROFILE_ID"):
        return True
    return False


def _mlx_tokens_present() -> bool:
    path = Path.home() / ".nextbrowser" / "multilogin_tokens.yaml"
    if os.getenv("MULTILOGIN_AUTOMATION_TOKEN") or os.getenv("MULTILOGIN_TOKEN"):
        return True
    if not path.exists():
        return False
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return bool(data.get("automation_token") or data.get("token"))


def multilogin_recommendation(
    config: HarnessConfig,
    url: str | None = None,
    *,
    tier: int | None = None,
    cache_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """
    Suggest MLX when user runs tier 2/3 / account work but browser is still native.
    Returns None if already on multilogin or tier 1 HTTP is enough.
    """
    if config.browser == "multilogin":
        return None

    rec_tier = 1
    tier_source = "default"
    if url:
        resolver = TierResolver(Path(cache_path or config.tier_cache_path))
        tr = resolver.recommended_tier(url)
        rec_tier = int(tr.tier)
        tier_source = tr.source

    effective = tier if tier is not None else rec_tier
    needs_antidetect = config.use_case == "accounts" or effective >= 2

    if not needs_antidetect:
        return None

    install = mlx_install_check()
    configured = _mlx_profile_configured(config) and _mlx_tokens_present()

    reasons: list[str] = []
    if config.use_case == "accounts":
        reasons.append("use_case=accounts (persistent profiles)")
    if effective >= 3:
        reasons.append(f"tier {effective} site (anti-detect browser)")
    elif effective == 2:
        reasons.append("tier 2+ may escalate to tier 3 on hard sites")

    return {
        "recommend_multilogin": True,
        "reasons": reasons,
        "tier_recommended": rec_tier,
        "tier_source": tier_source,
        "mlx_installed": install.get("installed"),
        "mlx_configured": configured,
        "setup_command": mlx_setup_wizard_command(),
        "message": (
            "Multilogin X is recommended for this task (logged-in / anti-detect browsing). "
            f"Run: {mlx_setup_wizard_command()}"
            if not configured
            else "Multilogin is configured but NEXTBROWSER_BROWSER=native — set multilogin in config or --browser multilogin"
        ),
    }
