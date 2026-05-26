"""
One-shot login workflow — the single reliable path for tier-3 account automation.

Wraps:
  1. Ensure account exists (create MLX profile if not)
  2. Connect Multilogin (CDP, keep-alive)
  3. Open URL via browser-use, capture initial element map
  4. Optionally run a credential chain (one shell pass — browser never closes)
  5. Return JSON: account, cdp_url, indexed elements, next_commands

Agents call this **once** per login. They do not need to chain manually.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

from nextbrowser_harness.accounts.registry import (
    AccountRegistry,
    SavedAccount,
    Tier3AccountError,
)
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import (
    browser_use_bin,
    connect_account,
    load_session,
)


@dataclass
class LoginResult:
    success: bool
    account_id: str
    mlx_profile_id: str = ""
    cdp_url: str = ""
    url: str = ""
    state: str = ""
    logged_in: bool | None = None
    actions_run: list[str] = field(default_factory=list)
    next_commands: list[str] = field(default_factory=list)
    agent_prompt: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PLACEHOLDER = re.compile(r"^(\$|USER|PASS|PASSWORD|USERNAME|FROM_USER|YOUR_)", re.I)


def _is_placeholder(val: str) -> bool:
    s = (val or "").strip()
    return not s or bool(_PLACEHOLDER.match(s))


def _ensure_account(
    config: HarnessConfig,
    account_id: str,
    *,
    site: str = "",
    create_if_missing: bool = True,
) -> SavedAccount:
    reg = AccountRegistry(config)
    existing = reg.get(account_id)
    if existing and existing.mlx_profile_id:
        return existing
    if not create_if_missing:
        raise Tier3AccountError(
            f"Account '{account_id}' not registered.",
            agent_prompt=(
                f"Run `nextbrowser account add {account_id} --create-mlx` "
                "or pass --create to login command."
            ),
            code="account_unknown",
        )
    return reg.register(
        account_id,
        display_name=account_id.replace("_", " ").title(),
        site=site,
        create_mlx=True,
    )


def _bu_call(cdp: str, args: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
    bin_path = browser_use_bin()
    if not bin_path:
        raise FileNotFoundError(
            "browser-use CLI not installed. Run: curl -fsSL https://browser-use.com/cli/install.sh | bash"
        )
    cmd = [bin_path, "--cdp-url", cdp, *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _bu_chain(cdp: str, steps: list[list[str]], *, timeout: int = 180) -> subprocess.CompletedProcess:
    """Run steps as ONE shell chain so daemon keeps the browser open."""
    bin_path = browser_use_bin()
    if not bin_path:
        raise FileNotFoundError("browser-use CLI not installed")
    segments = [
        shlex.join([bin_path, "--cdp-url", cdp, *step]) for step in steps
    ]
    script = " && ".join(segments)
    return subprocess.run(script, shell=True, capture_output=True, text=True, timeout=timeout)


def login(
    config: HarnessConfig,
    account_id: str,
    *,
    url: str,
    username: str | None = None,
    password: str | None = None,
    username_index: int | None = None,
    password_index: int | None = None,
    submit_index: int | None = None,
    recipe: str | None = None,
    recipe_vars: dict[str, str] | None = None,
    site: str = "",
    create_if_missing: bool = True,
    keep_open: bool = True,
) -> LoginResult:
    """
    Single reliable login. Steps:

      * ensure account (creates MLX profile if needed)
      * connect MLX → CDP (browser stays open)
      * open(url) and state() — agents read indices from result.state
      * if indices+creds supplied → chain input/click in one shell pass

    Always returns next_commands so the agent knows how to continue without
    breaking the keep-alive contract.
    """
    if not url:
        return LoginResult(success=False, account_id=account_id, error="url is required")

    if (username and _is_placeholder(username)) or (password and _is_placeholder(password)):
        return LoginResult(
            success=False,
            account_id=account_id,
            error="placeholder credentials",
            agent_prompt="Ask the user for real username and password — do not use placeholders.",
        )

    try:
        account = _ensure_account(
            config, account_id, site=site, create_if_missing=create_if_missing
        )
    except Tier3AccountError as e:
        return LoginResult(
            success=False, account_id=account_id, error=str(e), agent_prompt=e.agent_prompt
        )

    try:
        conn = connect_account(config, account.account_id)
    except Exception as e:
        return LoginResult(
            success=False,
            account_id=account.account_id,
            error=f"connect failed: {e}",
            agent_prompt="Check `nextbrowser multilogin doctor` then retry.",
        )

    cdp = conn["cdp_url"]
    result = LoginResult(
        success=True,
        account_id=account.account_id,
        mlx_profile_id=account.mlx_profile_id,
        cdp_url=cdp,
        url=url,
    )

    # Step 1: open + state in one chain so daemon stays alive
    try:
        proc = _bu_chain(cdp, [["open", url], ["state"]], timeout=120)
        result.actions_run.extend(["open", "state"])
        result.state = (proc.stdout or "")[-4000:]
        if proc.returncode != 0:
            result.error = (proc.stderr or "")[-2000:]
            result.agent_prompt = "browser-use failed to open URL — check `browser-use doctor`."
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        result.success = False
        result.error = str(e)
        result.agent_prompt = "Install browser-use CLI: curl -fsSL https://browser-use.com/cli/install.sh | bash"
        return result

    # Step 2: optional credential chain (single shell pass — browser stays open)
    has_indices = all(x is not None for x in (username_index, password_index, submit_index))
    has_creds = bool(username) and bool(password)
    if has_indices and has_creds:
        steps = [
            ["input", str(username_index), username],
            ["input", str(password_index), password],
            ["click", str(submit_index)],
            ["state"],
        ]
        try:
            proc = _bu_chain(cdp, steps, timeout=180)
            result.actions_run.extend(["input", "input", "click", "state"])
            result.state = (proc.stdout or "")[-4000:]
            result.logged_in = proc.returncode == 0 and "login" not in result.state.lower()[:200]
        except subprocess.TimeoutExpired as e:
            result.error = f"login chain timed out: {e}"
            result.logged_in = False
    elif recipe:
        result.agent_prompt = (
            f"Recipe '{recipe}' is not bundled in login yet. "
            "Use `nextbrowser browser-use chain open URL state \"input N val\" \"click M\"`."
        )

    # Always tell the agent how to continue without breaking keep-alive
    result.next_commands = [
        f'nextbrowser ui state',
        f'nextbrowser ui click <N>',
        f'nextbrowser ui type <N> "text"',
        f'nextbrowser ui close   # only when fully done',
    ]
    if not result.agent_prompt:
        result.agent_prompt = (
            f"MLX profile '{account.account_id}' is open (keep-alive). "
            "Continue with `nextbrowser ui ...` — do NOT close until task is done. "
            "Run `nextbrowser ui close` to disconnect when finished."
        )

    if not keep_open:
        from nextbrowser_harness.integrations.browser_use.bridge import disconnect_account

        disconnect_account(config, account.account_id)
        result.next_commands = []
        result.agent_prompt = "Login complete; profile stopped per --close."

    return result
