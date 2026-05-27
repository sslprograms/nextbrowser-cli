"""Bridge Multilogin CDP sessions to the browser-use CLI (official agent skill)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from nextbrowser_harness.accounts.registry import AccountRegistry, Tier3AccountError
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient, MultiloginXError
from nextbrowser_harness.integrations.multilogin.platform_hints import ensure_mlx_launcher_running

SESSION_PATH = Path.home() / ".nextbrowser" / "browser_use_session.json"
BROWSER_USE_SKILL_URL = (
    "https://raw.githubusercontent.com/browser-use/browser-use/main/skills/browser-use/SKILL.md"
)


def _session_path() -> Path:
    p = Path(os.getenv("NEXTBROWSER_BROWSER_USE_SESSION", str(SESSION_PATH)))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_session(data: dict[str, Any]) -> Path:
    path = _session_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_session() -> dict[str, Any] | None:
    path = _session_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def browser_use_bin() -> str | None:
    for name in ("browser-use", "bu", "browseruse"):
        found = shutil.which(name)
        if found:
            return found
    return None


def browser_use_doctor() -> dict[str, Any]:
    bin_path = browser_use_bin()
    out: dict[str, Any] = {
        "browser_use_on_path": bool(bin_path),
        "browser_use_bin": bin_path,
        "session_file": str(_session_path()),
        "session": load_session(),
        "skill_url": BROWSER_USE_SKILL_URL,
        "install_hint": "curl -fsSL https://browser-use.com/cli/install.sh | bash && browser-use doctor",
    }
    if bin_path:
        try:
            proc = subprocess.run(
                [bin_path, "doctor"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            out["doctor_exit"] = proc.returncode
            out["doctor_stdout"] = (proc.stdout or "")[:4000]
            out["doctor_stderr"] = (proc.stderr or "")[:2000]
        except Exception as e:
            out["doctor_error"] = str(e)
    return out


def connect_account(
    config: HarnessConfig,
    account_id: str,
    *,
    headless: bool = False,
) -> dict[str, Any]:
    """
    Start MLX profile for account, return CDP URL for browser-use --cdp-url.
    Does not attach Playwright — browser-use owns the CDP session.
    """
    account = AccountRegistry(config).require_for_tier3(account_id)
    layer_cfg = dict(config.multilogin or {})
    layer_cfg.setdefault("profiles", {})[account_id] = account.mlx_profile_id
    if account.mlx_folder_id:
        layer_cfg.setdefault("folder_id", account.mlx_folder_id)

    from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer

    layer = MultiloginBrowserLayer.from_config(config)
    folder_id, mlx_profile_id = layer.resolve_profile_id(account_id)

    launcher = ensure_mlx_launcher_running()
    if not launcher.get("launcher_reachable_after"):
        raise MultiloginXError(
            "Multilogin launcher not reachable. Run: nextbrowser multilogin doctor"
        )

    client = MultiloginXClient()
    started = client.start_profile(
        folder_id,
        mlx_profile_id,
        automation_type="playwright",
        headless=headless,
    )
    cdp = started.cdp_url
    if not cdp:
        raise MultiloginXError(f"No CDP port from MLX for profile {mlx_profile_id}")

    bu = browser_use_bin()
    prefix = f'browser-use --cdp-url "{cdp}"'
    session = {
        "account_id": account_id,
        "mlx_profile_id": mlx_profile_id,
        "folder_id": folder_id,
        "cdp_url": cdp,
        "browser_use_prefix": prefix,
        "browser_use_bin": bu,
    }
    session["keep_alive"] = True
    save_session(session)

    from nextbrowser_harness.integrations.multilogin.session import mark_keep_alive

    mark_keep_alive(
        account_id,
        mlx_profile_id=mlx_profile_id,
        folder_id=folder_id,
        cdp_url=cdp,
        reason="browser-use",
    )
    AccountRegistry(config).touch_run(account_id)

    return {
        "success": True,
        "account_id": account_id,
        "mlx_profile_id": mlx_profile_id,
        "cdp_url": cdp,
        "connection": "cdp",
        "keep_alive": True,
        "browser_use_prefix": prefix,
        "browser_use_bin": bu,
        "next_commands": [
            f'{prefix} open "<url>" && {prefix} state && {prefix} input N "text" && {prefix} click N',
            'nextbrowser browser-use chain open "<url>" state "input 3 user" "click 5"',
        ],
        "agent_must_know": [
            "MLX browser is open for this session until you disconnect or a task finishes.",
            "Login chains: one browser-use chain — do not split per field.",
            "When done with manual steps: nextbrowser ui close (stops Multilogin).",
            "Autonomous tasks: nextbrowser agent-run stops Multilogin when done (default).",
            f"Emergency stop all profiles: nextbrowser multilogin stop-all",
        ],
        "agent_prompt": (
            f"MLX profile '{account_id}' is running (keep_alive). "
            f"Login in ONE chain: `nextbrowser browser-use chain open \"<url>\" state \"input N user\" \"click M\"`. "
            "Do NOT split into separate exec/run steps. Do NOT browser-use close until done. "
            f"Then: `nextbrowser browser-use disconnect --account {account_id}`"
        ),
    }


def disconnect_account(
    config: HarnessConfig,
    account_id: str,
) -> dict[str, Any]:
    """Stop MLX profile and clear keep-alive (call when login flow is fully done)."""
    from nextbrowser_harness.integrations.multilogin.session import clear_keep_alive

    sess = load_session() or {}
    mlx_id = sess.get("mlx_profile_id") or ""
    if account_id:
        acc = AccountRegistry(config).get(account_id)
        if acc:
            mlx_id = acc.mlx_profile_id
    if mlx_id:
        try:
            MultiloginXClient().stop_profile(mlx_id)
        except Exception:
            pass
    clear_keep_alive(account_id or None)
    path = _session_path()
    if path.is_file():
        path.unlink(missing_ok=True)
    return {"success": True, "account_id": account_id, "stopped_mlx_profile": mlx_id}


def run_browser_use_chain(
    parts: list[str],
    *,
    session: dict[str, Any] | None = None,
) -> subprocess.CompletedProcess:
    """Run multiple browser-use subcommands in one shell chain (browser stays open)."""
    import shlex

    sess = session or load_session()
    if not sess or not sess.get("cdp_url"):
        raise Tier3AccountError(
            "No browser-use CDP session. Run: nextbrowser browser-use connect --account <name>",
            agent_prompt="Run browser-use connect first.",
            code="browser_use_session_missing",
        )
    bin_path = browser_use_bin()
    if not bin_path:
        raise FileNotFoundError("browser-use CLI not found")
    cdp = sess["cdp_url"]
    segments = []
    for part in parts:
        tokens = shlex.split(part, posix=(os.name != "nt"))
        segments.append(shlex.join([bin_path, "--cdp-url", cdp, *tokens]))
    script = " && ".join(segments)
    return subprocess.run(script, shell=True)


def run_browser_use(
    args: list[str],
    *,
    session: dict[str, Any] | None = None,
) -> subprocess.CompletedProcess:
    """Run browser-use with --cdp-url from saved MLX session."""
    sess = session or load_session()
    if not sess or not sess.get("cdp_url"):
        raise Tier3AccountError(
            "No browser-use CDP session. Run: nextbrowser browser-use connect --account <name>",
            agent_prompt=(
                "Connect Multilogin to browser-use first:\n"
                "  nextbrowser browser-use connect --account <name>\n"
                "Then use browser-use state / click / input (see browser-use skill)."
            ),
            code="browser_use_session_missing",
        )
    bin_path = browser_use_bin()
    if not bin_path:
        raise FileNotFoundError(
            "browser-use CLI not found. Install: https://browser-use.com/cli/install.sh"
        )
    cdp = sess["cdp_url"]
    cmd = [bin_path, "--cdp-url", cdp, *args]
    return subprocess.run(cmd, capture_output=False, text=True)


def install_browser_use_skill(dest: Path | None = None) -> Path:
    """Download official browser-use SKILL.md for the agent host."""
    import urllib.request

    root = dest or (Path.home() / ".cursor" / "skills" / "browser-use")
    root.mkdir(parents=True, exist_ok=True)
    target = root / "SKILL.md"
    req = urllib.request.Request(
        BROWSER_USE_SKILL_URL,
        headers={"User-Agent": "nextbrowser-harness/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        target.write_bytes(resp.read())
    return target
