"""
AI-driven browser agent that runs browser-use over a Multilogin CDP session.

Architecture (ported from next-browser-main/task-runner):
  1. Start or reuse an MLX profile (CDP URL)
  2. Create a browser-use BrowserSession connected to CDP
  3. Create a browser-use Agent with system prompt + task
  4. Run the step loop: agent.take_step() until done or max_steps
  5. Return structured result

The agent uses the same prompt system as next-browser-main:
  - System prompt with indexed elements, reasoning rules, action format
  - Interactive element guidance for platform-specific patterns
  - Captcha, tab, and approval prompts appended as extensions
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from nextbrowser_harness.accounts.credentials import (
    AccountCredentials,
    build_sensitive_data,
    load_account_credentials,
)
from nextbrowser_harness.accounts.registry import AccountRegistry, Tier3AccountError
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import connect_account, load_session

from .preflight import probe_login_state
from .prompts.account_context import account_context_prompt
from .prompts.browser_agent_extended import BROWSER_AGENT_EXTENDED_PROMPT
from .prompts.login_required import CREDENTIALS_LOGIN_POLICY, login_required_task_block
from .prompts.captcha import CAPTCHA_PROMPT
from .prompts.interactive_elements import INTERACTIVE_ELEMENTS_GUIDANCE
from .prompts.system_prompt import SYSTEM_PROMPT
from .prompts.tabs import TAB_GUIDANCE

logger = logging.getLogger(__name__)

MAX_STEPS = int(os.getenv("NEXTBROWSER_AGENT_MAX_STEPS", "100"))
MAX_ACTIONS_PER_STEP = int(os.getenv("NEXTBROWSER_AGENT_MAX_ACTIONS", "10"))
MAX_FAILURES = int(os.getenv("NEXTBROWSER_AGENT_MAX_FAILURES", "10"))
LLM_TIMEOUT = int(os.getenv("NEXTBROWSER_AGENT_LLM_TIMEOUT", "150"))


@dataclass
class AgentRunResult:
    success: bool
    account_id: str
    task: str
    steps_taken: int = 0
    final_text: str = ""
    files: list[str] = field(default_factory=list)
    cdp_url: str = ""
    executed_actions: list[str] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    done_called: bool = False
    error: str | None = None
    agent_prompt: str = ""
    logged_in_live: bool | None = None
    had_credentials: bool = False
    preflight: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_llm(model_name: str):
    """Create an LLM instance compatible with browser-use."""
    if model_name.startswith("gpt-"):
        from browser_use.llm import ChatOpenAI

        return ChatOpenAI(model=model_name, timeout=LLM_TIMEOUT)
    elif model_name.startswith("gemini-"):
        from browser_use.llm import ChatGoogle

        return ChatGoogle(model=model_name)
    elif model_name.startswith("claude-"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, timeout=LLM_TIMEOUT)
    else:
        from browser_use.llm import ChatOpenAI

        return ChatOpenAI(model=model_name, timeout=LLM_TIMEOUT)


def _needs_reddit_guidance(*, task: str = "", url: str = "", site: str = "") -> bool:
    blob = f"{task} {url} {site}".lower()
    return "reddit.com" in blob or re.search(r"\breddit\b", blob) is not None


def _build_system_prompt(
    account_id: str | None = None,
    site: str = "",
    logged_in: bool = False,
    display_name: str = "",
    enable_captcha: bool = False,
    enable_approval: bool = False,
    task: str = "",
    url: str = "",
    *,
    has_credentials: bool = False,
    logged_in_live: bool | None = None,
    require_login: bool = False,
) -> tuple[str, str]:
    """Return (override_system_message, extend_system_message)."""
    extensions = [BROWSER_AGENT_EXTENDED_PROMPT, INTERACTIVE_ELEMENTS_GUIDANCE, TAB_GUIDANCE]

    if _needs_reddit_guidance(task=task, url=url, site=site):
        from .prompts.reddit import REDDIT_GUIDANCE

        extensions.append(REDDIT_GUIDANCE)

    if account_id:
        extensions.append(
            account_context_prompt(
                account_id,
                site=site,
                logged_in=logged_in,
                display_name=display_name,
                has_credentials=has_credentials,
                logged_in_live=logged_in_live,
            )
        )

    if has_credentials and require_login:
        extensions.append(CREDENTIALS_LOGIN_POLICY)

    if enable_captcha:
        extensions.append(CAPTCHA_PROMPT)

    if enable_approval:
        from .prompts.approval import APPROVAL_PROMPT

        extensions.append(APPROVAL_PROMPT)

    # Harden against fabricated action reporting.
    extensions.append(
        """
<execution_verification>
Before claiming any action was completed, verify it from browser state/screenshot and action results.
Never state an action as completed if it is missing from executed action results.
If uncertain, explicitly say uncertain.
</execution_verification>
""".strip()
    )

    return SYSTEM_PROMPT, "\n".join(extensions)


def _resolve_credentials(
    config: HarnessConfig,
    account_id: str,
    *,
    username: str | None = None,
    password: str | None = None,
) -> AccountCredentials | None:
    if username and password:
        from nextbrowser_harness.accounts.credentials import is_real_credential, save_account_credentials

        if is_real_credential(username) and is_real_credential(password):
            return save_account_credentials(
                config, account_id, username=username, password=password
            )
    return load_account_credentials(config, account_id)


def _build_task_with_login(
    task: str,
    *,
    url: str = "",
    login_url: str = "",
    site: str = "",
    logged_in_live: bool | None,
    has_credentials: bool,
) -> str:
    parts: list[str] = []
    nav = url or login_url
    if nav and "navigate to" not in task.lower()[:200]:
        parts.append(f"If not already on the right page, go to {nav}.")
    if has_credentials and logged_in_live is not True:
        parts.append(
            login_required_task_block(login_url=login_url or url, site=site)
        )
    parts.append(task.strip())
    return "\n\n".join(parts)


def _collect_executed_actions(history: Any) -> list[str]:
    """
    Best-effort extraction of executed action names from browser-use history.
    Works across browser-use versions by probing common structures.
    """
    out: list[str] = []
    if history is None:
        return out

    # Newer APIs may expose model_actions()
    model_actions_fn = getattr(history, "model_actions", None)
    if callable(model_actions_fn):
        try:
            action_steps = model_actions_fn() or []
            for step in action_steps:
                if isinstance(step, list):
                    for a in step:
                        if isinstance(a, dict):
                            out.extend([str(k) for k in a.keys()])
                        else:
                            out.append(str(a))
                elif isinstance(step, dict):
                    out.extend([str(k) for k in step.keys()])
                else:
                    out.append(str(step))
        except Exception:
            pass

    # Fallback: inspect raw history entries
    raw_steps = getattr(history, "history", None) or []
    for step in raw_steps:
        try:
            model_output = getattr(step, "model_output", None)
            actions = getattr(model_output, "action", None)
            if isinstance(actions, list):
                for a in actions:
                    if isinstance(a, dict):
                        out.extend([str(k) for k in a.keys()])
                    else:
                        out.append(str(a))
        except Exception:
            continue

    # normalize + dedupe while preserving order
    seen = set()
    deduped: list[str] = []
    for a in out:
        s = a.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        deduped.append(s)
    return deduped


def _safe_str(value: Any, max_len: int = 400) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _extract_url_from_step(step: Any) -> str:
    # Try common browser-use history paths
    for attr in ("url",):
        val = getattr(step, attr, None)
        if val:
            return _safe_str(val, 1000)
    browser_state = getattr(step, "browser_state", None)
    if browser_state is not None:
        for attr in ("url", "current_url"):
            val = getattr(browser_state, attr, None)
            if val:
                return _safe_str(val, 1000)
    state = getattr(step, "state", None)
    if state is not None:
        for attr in ("url", "current_url"):
            val = getattr(state, attr, None)
            if val:
                return _safe_str(val, 1000)
    return ""


def _extract_actions_from_step(step: Any) -> list[str]:
    actions: list[str] = []
    model_output = getattr(step, "model_output", None)
    action_list = getattr(model_output, "action", None)
    if isinstance(action_list, list):
        for a in action_list:
            if isinstance(a, dict):
                actions.extend([str(k) for k in a.keys()])
            else:
                actions.append(str(a))
    return actions


def _extract_step_error(step: Any) -> str:
    # action_results may contain errors
    action_results = getattr(step, "result", None) or getattr(step, "action_results", None)
    if isinstance(action_results, list):
        for r in action_results:
            err = getattr(r, "error", None)
            if err:
                return _safe_str(err, 1000)
    return ""


def _extract_step_result_preview(step: Any) -> str:
    action_results = getattr(step, "result", None) or getattr(step, "action_results", None)
    if isinstance(action_results, list):
        chunks: list[str] = []
        for r in action_results:
            extracted = getattr(r, "extracted_content", None)
            if extracted:
                chunks.append(_safe_str(extracted, 200))
        if chunks:
            return " | ".join(chunks[:3])
    return ""


def _build_audit_trail(history: Any) -> list[dict[str, Any]]:
    """
    Build a per-step audit trail from raw history.
    Each row is "verified" only when no per-step error is present.
    """
    trail: list[dict[str, Any]] = []
    if history is None:
        return trail
    raw_steps = getattr(history, "history", None) or []
    prev_url = ""
    for idx, step in enumerate(raw_steps, start=1):
        actions = _extract_actions_from_step(step)
        error = _extract_step_error(step)
        current_url = _extract_url_from_step(step)
        url_changed = bool(prev_url and current_url and prev_url != current_url)
        trail.append(
            {
                "step": idx,
                "planned_actions": actions,
                "verified": bool(actions) and not bool(error),
                "error": error,
                "url": current_url,
                "url_changed": url_changed,
                "result_preview": _extract_step_result_preview(step),
            }
        )
        if current_url:
            prev_url = current_url
    return trail


async def _run_agent_async(
    cdp_url: str,
    task: str,
    model_name: str,
    *,
    account_id: str = "",
    site: str = "",
    logged_in: bool = False,
    display_name: str = "",
    enable_captcha: bool = False,
    enable_approval: bool = False,
    max_steps: int = MAX_STEPS,
    downloads_dir: str | None = None,
    url: str = "",
    sensitive_data: dict[str, dict[str, str]] | None = None,
    logged_in_live: bool | None = None,
    require_login: bool = False,
) -> AgentRunResult:
    """Core async agent loop — connects to CDP and runs browser-use Agent."""
    from browser_use import Agent, BrowserProfile, BrowserSession

    override_prompt, extend_prompt = _build_system_prompt(
        account_id=account_id,
        site=site,
        logged_in=logged_in,
        display_name=display_name,
        enable_captcha=enable_captcha,
        enable_approval=enable_approval,
        task=task,
        url=url,
        has_credentials=bool(sensitive_data),
        logged_in_live=logged_in_live,
        require_login=require_login,
    )

    dl_dir = downloads_dir or os.path.join(
        os.path.expanduser("~"), ".nextbrowser", "downloads", str(int(time.time()))
    )
    os.makedirs(dl_dir, exist_ok=True)

    browser_session = BrowserSession(
        cdp_url=cdp_url,
        browser_profile=BrowserProfile(
            highlight_elements=False,
            downloads_path=dl_dir,
        ),
        no_viewport=True,
    )

    llm = _get_llm(model_name)

    agent_kwargs: dict[str, Any] = {
        "task": task,
        "llm": llm,
        "browser_session": browser_session,
        "override_system_message": override_prompt,
        "extend_system_message": extend_prompt,
        "max_failures": MAX_FAILURES,
        "max_history_items": 100,
        "llm_timeout": LLM_TIMEOUT,
    }
    if sensitive_data:
        agent_kwargs["sensitive_data"] = sensitive_data

    agent = Agent(**agent_kwargs)

    result = AgentRunResult(
        success=False,
        account_id=account_id,
        task=task,
        cdp_url=cdp_url,
    )

    try:
        history = await agent.run(max_steps=max_steps)
        result.steps_taken = len(history.history) if history else 0
        result.success = history.is_successful() if history else False
        result.final_text = history.final_result() if history else ""
        result.executed_actions = _collect_executed_actions(history)
        result.audit_trail = _build_audit_trail(history)
        result.done_called = bool(result.final_text)
        # Guardrail: don't claim success without any observed executed actions.
        if result.success and not result.executed_actions:
            result.success = False
            if not result.error:
                result.error = "No verified executed actions found in run history."
        # Stronger guardrail: require at least one verified step.
        if result.success and result.audit_trail and not any(
            bool(row.get("verified")) for row in result.audit_trail
        ):
            result.success = False
            if not result.error:
                result.error = "Run has no verified successful steps."
    except Exception as e:
        logger.error(f"Agent run failed: {e}", exc_info=True)
        result.error = str(e)
    finally:
        try:
            await agent.close()
        except Exception:
            pass

    return result


def run_agent(
    config: HarnessConfig,
    task: str,
    *,
    account_id: str | None = None,
    model: str | None = None,
    url: str | None = None,
    login_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    enable_captcha: bool = False,
    enable_approval: bool = False,
    max_steps: int = MAX_STEPS,
    headless: bool = False,
    keep_open: bool = False,
    skip_preflight: bool = False,
) -> AgentRunResult:
    """
    Synchronous entry point — start MLX profile, connect CDP, run the AI agent.

    If account_id is provided, uses Multilogin. Otherwise uses any existing
    browser-use session (if available).
    """
    model_name = model or os.getenv("NEXTBROWSER_LLM_MODEL", "gpt-4o")

    site = ""
    logged_in = False
    display_name = ""
    cdp_url = ""

    if account_id:
        try:
            conn = connect_account(config, account_id, headless=headless)
            cdp_url = conn["cdp_url"]
        except Tier3AccountError as e:
            return AgentRunResult(
                success=False,
                account_id=account_id or "",
                task=task,
                error=str(e),
                agent_prompt=e.agent_prompt,
            )
        except Exception as e:
            return AgentRunResult(
                success=False,
                account_id=account_id or "",
                task=task,
                error=f"MLX connect failed: {e}",
                agent_prompt="Check `nextbrowser multilogin doctor` then retry.",
            )

        acc = AccountRegistry(config).get(account_id)
        if acc:
            site = acc.site
            logged_in = acc.logged_in
            display_name = acc.display_name
    else:
        sess = load_session()
        if sess and sess.get("cdp_url"):
            cdp_url = sess["cdp_url"]
            account_id = sess.get("account_id", "")
        else:
            return AgentRunResult(
                success=False,
                account_id="",
                task=task,
                error="No CDP session. Run `nextbrowser login <account> --url <url>` first.",
            )

    nav_url = url or ""
    login_target = login_url or url or ""
    creds: AccountCredentials | None = None
    sensitive_data: dict[str, dict[str, str]] | None = None
    logged_in_live: bool | None = None
    preflight_dict: dict[str, Any] = {}

    if account_id:
        creds = _resolve_credentials(
            config, account_id, username=username, password=password
        )
        if creds:
            sensitive_data = build_sensitive_data(
                creds, url=nav_url or login_target, site=site
            )

        if not skip_preflight and cdp_url:
            pf = probe_login_state(
                cdp_url,
                account_id,
                open_url=nav_url or login_target or None,
                timeout=120,
            )
            preflight_dict = pf.to_dict()
            logged_in_live = pf.logged_in_likely
            if pf.logged_in_likely is True:
                AccountRegistry(config).mark_logged_in(account_id, logged_in=True)
            elif pf.logged_in_likely is False:
                AccountRegistry(config).mark_logged_in(account_id, logged_in=False)

    require_login = bool(sensitive_data) and logged_in_live is not True

    if not sensitive_data and logged_in_live is False:
        return AgentRunResult(
            success=False,
            account_id=account_id or "",
            task=task,
            cdp_url=cdp_url,
            logged_in_live=False,
            preflight=preflight_dict,
            error="Not logged in and no credentials available for the agent.",
            agent_prompt=(
                f"Store credentials: nextbrowser account set-credentials {account_id} "
                "--username U --password P\n"
                "Or pass --username/--password on agent-run.\n"
                "Or run: nextbrowser login <account> --url <url> with indices, then retry."
            ),
        )

    agent_task = _build_task_with_login(
        task,
        url=nav_url,
        login_url=login_target,
        site=site,
        logged_in_live=logged_in_live,
        has_credentials=bool(sensitive_data),
    )

    try:
        result = asyncio.run(
            _run_agent_async(
                cdp_url,
                agent_task,
                model_name,
                account_id=account_id or "",
                site=site,
                logged_in=logged_in,
                display_name=display_name,
                enable_captcha=enable_captcha,
                enable_approval=enable_approval,
                max_steps=max_steps,
                url=nav_url,
                sensitive_data=sensitive_data,
                logged_in_live=logged_in_live,
                require_login=require_login,
            )
        )
        result.logged_in_live = logged_in_live
        result.had_credentials = bool(sensitive_data)
        result.preflight = preflight_dict
    except Exception as e:
        result = AgentRunResult(
            success=False,
            account_id=account_id or "",
            task=task,
            cdp_url=cdp_url,
            error=str(e),
        )
    finally:
        # Like next-browser task-runner: stop MLX when the task ends (unless --keep-open).
        if not keep_open and account_id:
            from nextbrowser_harness.integrations.browser_use.bridge import disconnect_account

            try:
                disconnect_account(config, account_id)
            except Exception as e:
                logger.warning("disconnect after agent-run failed: %s", e)

    if not keep_open and account_id:
        result.agent_prompt = (
            (result.agent_prompt or "")
            + " Multilogin profile was stopped after this run (default). "
            "Use --keep-open to leave the browser running for manual follow-up."
        ).strip()

    return result
