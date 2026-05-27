"""
One-shot login — MLX profile + Playwright CDP (no browser-use).

Opens URL, returns indexed element map, optional credential fill by index.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from nextbrowser_harness.accounts.registry import (
    AccountRegistry,
    SavedAccount,
    Tier3AccountError,
)
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import connect_account
from nextbrowser_harness.integrations.multilogin.playwright_session import (
    capture_state_text,
    mlx_page,
)
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_with_reason


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
    if result.error and result.logged_in is not True:
        result.success = False
        return result
    if attempted_credential_login:
        result.success = result.logged_in is True
        if not result.success:
            result.agent_prompt = (
                "Login submitted but page still looks logged out. "
                "Run `nextbrowser ui require-login`."
            )
    elif result.logged_in is False:
        result.success = False
        result.agent_prompt = (
            "Page shows logged OUT. Use indices from `ui state` with "
            "`ui type` / `ui click`, or ask user to log in in the MLX window."
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

    result = LoginResult(
        success=True,
        account_id=account.account_id,
        mlx_profile_id=account.mlx_profile_id,
        cdp_url=conn["cdp_url"],
        url=url,
    )
    attempted_creds = False

    try:
        from nextbrowser_harness.element_search.indexed import IndexedElementSearch

        with mlx_page(config, account_id=account.account_id) as page:
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            result.actions_run.append("open")
            driver = IndexedElementSearch(page)
            result.state = capture_state_text(page)[-4000:]
            result.actions_run.append("state")
            explanation, inferred = infer_logged_in_with_reason(result.state)
            result.logged_in = inferred
            result.logged_in_reason = explanation

            has_indices = all(
                x is not None for x in (username_index, password_index, submit_index)
            )
            has_creds = bool(username) and bool(password)
            if has_indices and has_creds:
                attempted_creds = True
                driver.input_text(username_index, username)  # type: ignore[arg-type]
                driver.input_text(password_index, password)  # type: ignore[arg-type]
                driver.click(submit_index)  # type: ignore[arg-type]
                result.actions_run.extend(["input", "input", "click", "state"])
                page.wait_for_timeout(1500)
                result.state = capture_state_text(page)[-4000:]
                explanation, inferred = infer_logged_in_with_reason(result.state)
                result.logged_in = inferred
                result.logged_in_reason = explanation
                if result.logged_in is True:
                    AccountRegistry(config).mark_logged_in(account.account_id, logged_in=True)
                elif result.logged_in is False:
                    AccountRegistry(config).mark_logged_in(account.account_id, logged_in=False)
    except Exception as e:
        result.success = False
        result.error = str(e)
        result.agent_prompt = "MLX/Playwright error — run multilogin doctor."
        return result

    result.next_commands = [
        "nextbrowser ui require-login",
        "nextbrowser ui state",
        "nextbrowser ui click <N>",
        'nextbrowser ui type <N> "text"',
        f"nextbrowser disconnect --account {account.account_id}",
    ]

    result = _finalize_success(result, attempted_credential_login=attempted_creds)

    if not keep_open:
        from nextbrowser_harness.integrations.browser_use.bridge import disconnect_account

        disconnect_account(config, account.account_id)
        result.next_commands = []

    return result
