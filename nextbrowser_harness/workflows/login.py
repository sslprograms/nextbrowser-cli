"""
Log a Multilogin X account into a site over raw CDP.

Flow: ensure account → start MLX profile → if credentials are available, run the
deterministic CDP login (fill + submit + verify); otherwise navigate + survey and
ask the user/agent for credentials. No ``ui`` / indexed-click shortcuts.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from nextbrowser_harness.accounts.credentials import (
    is_real_credential,
    load_account_credentials,
    save_account_credentials,
)
from nextbrowser_harness.accounts.registry import (
    AccountRegistry,
    SavedAccount,
    Tier3AccountError,
)
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.mlx_cdp.bridge import connect_account, disconnect_account
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_with_reason
from nextbrowser_harness.workflows.cdp_control import cdp_login, cdp_send, page_survey


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
    used_credentials: bool = False
    fields_found: dict[str, Any] = field(default_factory=dict)
    filled: list[str] = field(default_factory=list)
    submitted: bool = False
    obstacle: str | None = None
    screenshots: dict[str, Any] = field(default_factory=dict)
    actions_run: list[str] = field(default_factory=list)
    next_commands: list[str] = field(default_factory=list)
    survey: dict[str, Any] = field(default_factory=dict)
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


def _cdp_next_commands(account_id: str, url: str) -> list[str]:
    esc = json.dumps(url)
    return [
        f"nextbrowser cdp survey --account {account_id}",
        f"nextbrowser cdp send --account {account_id} Page.navigate --params '{{\"url\":{esc}}}'",
        f"nextbrowser cdp send --account {account_id} <Domain.method> --params '<json>'",
        f"nextbrowser disconnect --account {account_id}",
    ]


def _resolve_credentials(
    config: HarnessConfig,
    account_id: str,
    *,
    username: str | None,
    password: str | None,
    site: str,
) -> tuple[str, str] | None:
    """Use explicit username/password (and persist them), else load stored creds."""
    if username and password and is_real_credential(username) and is_real_credential(password):
        try:
            save_account_credentials(
                config, account_id, username=username, password=password, service=site
            )
        except ValueError:
            pass
        return username, password
    stored = load_account_credentials(config, account_id)
    if stored:
        return stored.username, stored.password
    return None


def login(
    config: HarnessConfig,
    account_id: str,
    *,
    url: str,
    username: str | None = None,
    password: str | None = None,
    site: str = "",
    create_if_missing: bool = True,
    keep_open: bool = True,
    run_survey: bool = True,
) -> LoginResult:
    if not url:
        return LoginResult(success=False, account_id=account_id, error="url is required")

    if (username and _is_placeholder(username)) or (password and _is_placeholder(password)):
        return LoginResult(
            success=False,
            account_id=account_id,
            error="placeholder credentials",
            agent_prompt="Ask the user for real username and password.",
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
            error=f"MLX connect failed: {e}",
            agent_prompt="Check `nextbrowser multilogin doctor` then retry.",
        )

    creds = _resolve_credentials(
        config, account.account_id, username=username, password=password, site=site
    )

    result = LoginResult(
        success=True,
        account_id=account.account_id,
        mlx_profile_id=account.mlx_profile_id,
        cdp_url=conn.get("cdp_url", ""),
        url=url,
        actions_run=["connect"],
        next_commands=_cdp_next_commands(account.account_id, url),
    )

    if creds:
        out = cdp_login(
            config,
            account_id=account.account_id,
            url=url,
            username=creds[0],
            password=creds[1],
        )
        result.used_credentials = True
        result.actions_run.append("cdp:login")
        result.success = bool(out.get("success"))
        result.logged_in = out.get("logged_in")
        result.logged_in_reason = out.get("logged_in_reason", "")
        result.fields_found = out.get("fields_found", {})
        result.filled = out.get("filled", [])
        result.submitted = bool(out.get("submitted"))
        result.obstacle = out.get("obstacle")
        result.screenshots = out.get("screenshots", {})
        result.state = out.get("state", "")
        result.cdp_url = out.get("cdp_url", result.cdp_url)
        result.error = out.get("error")
        result.agent_prompt = out.get("agent_prompt", "")
    else:
        # No credentials: open the page, survey it, and ask for credentials.
        nav = cdp_send(config, "Page.navigate", {"url": url}, account_id=account.account_id)
        result.actions_run.append("cdp:Page.navigate")
        if not nav.success:
            result.success = False
            result.error = nav.error or "Page.navigate failed"
            return result
        if run_survey:
            survey = page_survey(config, account_id=account.account_id, wait_ms=400)
            result.survey = survey
            result.actions_run.append("cdp:survey")
            if survey.get("success"):
                texts = []
                for seg in survey.get("segments") or []:
                    texts.append(str(seg.get("visible_text") or ""))
                    hint = seg.get("logged_in_hint")
                    if hint is True:
                        result.logged_in = True
                    elif hint is False and result.logged_in is not True:
                        result.logged_in = False
                blob = f"Current URL: {url}\n" + "\n".join(texts)
                reason, inferred = infer_logged_in_with_reason(blob[:12000])
                if result.logged_in is None:
                    result.logged_in = inferred
                result.logged_in_reason = reason
                result.state = blob[-4000:]
        result.success = result.logged_in is True
        result.agent_prompt = (
            f"No stored credentials for '{account.account_id}'. To auto-login, run "
            f"`nextbrowser account set-credentials {account.account_id} --username U --password P` "
            f"then `nextbrowser login {account.account_id} --url {url}`. "
            "Or complete login in the MLX window."
        )

    if not keep_open:
        disconnect_account(config, account.account_id)
        result.actions_run.append("disconnect")
        result.next_commands = []

    return result
