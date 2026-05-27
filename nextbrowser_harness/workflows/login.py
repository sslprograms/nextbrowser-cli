"""
One-shot login workflow — the single reliable path for tier-3 account automation.

Wraps:
  1. Ensure account exists (create MLX profile if not)
  2. Connect Multilogin (CDP, keep-alive)
  3. Open URL via browser-use, capture initial element map
  4. Optionally run a credential chain (one shell pass — browser never closes)
  5. Return JSON: account, cdp_url, indexed elements, logged_in (fail-closed)

Agents call this **once** per login. They do not need to chain manually.
"""

from __future__ import annotations

import re
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
)
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_with_reason
from nextbrowser_harness.workflows.browser_use_exec import bu_chain


@dataclass
class LoginResult:
    success: bool
    account_id: str
    mlx_profile_id: str = ""
    cdp_url: str = ""
    url: str = ""
    state: str = ""
    logged_in: bool | None = None
    logged_in_reason: str = ""
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


def _finalize_success(
    result: LoginResult,
    *,
    attempted_credential_login: bool,
) -> LoginResult:
    """Fail closed: do not report success when the live page still shows a login/auth gate."""
    if result.error and result.logged_in is not True:
        result.success = False
        return result
    if attempted_credential_login:
        result.success = result.logged_in is True
        if not result.success:
            result.agent_prompt = (
                "Login form was submitted but the live page does NOT look logged in. "
                "Run `nextbrowser ui situation` — if logged_in_verified is false, ask the user "
                "for credentials or complete 2FA manually. Do NOT claim you are logged in."
            )
    elif result.logged_in is False:
        result.success = False
        result.agent_prompt = (
            "Browser opened but page shows logged OUT (Log in / Sign up). "
            "Run login with --username/--password and indices from `ui state`, or complete login "
            "with `ui click` / `ui type` then `nextbrowser ui require-login`."
        )
    return result


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

    `success` is True only when logged_in is True (after creds) or unknown/open-only
    without a definite logged-out signal.
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
    bin_path = browser_use_bin()
    if not bin_path:
        return LoginResult(
            success=False,
            account_id=account.account_id,
            error="browser-use CLI not installed",
            agent_prompt="Install browser-use CLI: curl -fsSL https://browser-use.com/cli/install.sh | bash",
        )

    result = LoginResult(
        success=True,
        account_id=account.account_id,
        mlx_profile_id=account.mlx_profile_id,
        cdp_url=cdp,
        url=url,
    )
    attempted_creds = False

    # Step 1: open + state in one chain so daemon stays alive
    try:
        proc = bu_chain(
            bin_path,
            cdp,
            [["open", url], ["state"]],
            account_id=account.account_id,
            timeout=120,
        )
        result.actions_run.extend(["open", "state"])
        result.state = (proc.stdout or "")[-4000:]
        explanation, inferred = infer_logged_in_with_reason(result.state)
        result.logged_in = inferred
        result.logged_in_reason = explanation
        if proc.returncode != 0:
            result.success = False
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
        attempted_creds = True
        steps = [
            ["input", str(username_index), username],
            ["input", str(password_index), password],
            ["click", str(submit_index)],
            ["state"],
        ]
        try:
            proc = bu_chain(
                bin_path,
                cdp,
                steps,
                account_id=account.account_id,
                timeout=180,
            )
            result.actions_run.extend(["input", "input", "click", "state"])
            result.state = (proc.stdout or "")[-4000:]
            if proc.returncode == 0:
                explanation, inferred = infer_logged_in_with_reason(result.state)
                result.logged_in = inferred
                result.logged_in_reason = explanation
            else:
                result.logged_in = False
                result.logged_in_reason = "Submit flow failed (browser-use non-zero exit)."
            if result.logged_in is True:
                AccountRegistry(config).mark_logged_in(account.account_id, logged_in=True)
            elif result.logged_in is False:
                AccountRegistry(config).mark_logged_in(account.account_id, logged_in=False)
        except subprocess.TimeoutExpired as e:
            result.error = f"login chain timed out: {e}"
            result.logged_in = False
    elif recipe:
        result.agent_prompt = (
            f"Recipe '{recipe}' is not bundled in login yet. "
            "Use `nextbrowser browser-use chain open URL state \"input N val\" \"click M\"`."
        )

    result.next_commands = [
        "nextbrowser ui require-login   # exit 0 = logged in verified; exit 1 = STOP",
        "nextbrowser ui situation",
        "nextbrowser ui state",
        "nextbrowser ui click <N>",
        'nextbrowser ui type <N> "text"',
        'nextbrowser ui verify --text "<exact text after submit>"',
        "nextbrowser ui close",
    ]
    if not result.agent_prompt and result.logged_in is True:
        result.agent_prompt = (
            f"MLX profile '{account.account_id}' is open and looks logged in. "
            "Before authenticated actions, run `nextbrowser ui require-login`. After submit, "
            "`nextbrowser ui verify --text \"...\"` — exit 0 only means that text is on the page."
        )
    elif not result.agent_prompt:
        result.agent_prompt = (
            f"MLX profile '{account.account_id}' is open. "
            "Run `nextbrowser ui require-login` before claiming logged in. "
            "Do NOT tell the user content was posted until `ui verify --text` exits 0."
        )

    result = _finalize_success(result, attempted_credential_login=attempted_creds)

    if not keep_open:
        from nextbrowser_harness.integrations.browser_use.bridge import disconnect_account

        disconnect_account(config, account.account_id)
        result.next_commands = []
        result.agent_prompt = "Login complete; profile stopped per --close."

    return result
