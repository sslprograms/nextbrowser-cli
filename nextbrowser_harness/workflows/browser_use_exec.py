"""Shared browser-use CLI execution (Windows-safe quoting + per-account session)."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from typing import Any


def session_name_for_account(account_id: str | None) -> str:
    """Unique browser-use daemon session per MLX account (avoids 'default' conflicts)."""
    raw = (account_id or "default").strip()
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-")[:48]
    return safe or "nb-default"


def bu_argv(
    bin_path: str,
    cdp: str,
    args: list[str],
    *,
    account_id: str | None = None,
) -> list[str]:
    return [
        bin_path,
        "--cdp-url",
        cdp,
        "--session",
        session_name_for_account(account_id),
        *args,
    ]


def bu_call(
    bin_path: str,
    cdp: str,
    args: list[str],
    *,
    account_id: str | None = None,
    timeout: int = 60,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    cmd = bu_argv(bin_path, cdp, args, account_id=account_id)
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def bu_chain(
    bin_path: str,
    cdp: str,
    steps: list[list[str]],
    *,
    account_id: str | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess:
    """Run browser-use steps in one shell chain (daemon stays alive)."""
    sess = session_name_for_account(account_id)
    if os.name == "nt":
        segments: list[str] = []
        for step in steps:
            parts = bu_argv(bin_path, cdp, step, account_id=account_id)
            quoted: list[str] = []
            for p in parts:
                s = str(p)
                if any(c in s for c in ' "&()'):
                    quoted.append(f'"{s}"')
                else:
                    quoted.append(s)
            segments.append(" ".join(quoted))
        script = " && ".join(segments)
        return subprocess.run(
            ["cmd", "/c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

    segments = [
        shlex.join(bu_argv(bin_path, cdp, step, account_id=account_id)) for step in steps
    ]
    script = " && ".join(segments)
    return subprocess.run(script, shell=True, capture_output=True, text=True, timeout=timeout)


def capture_state(
    bin_path: str,
    cdp: str,
    *,
    account_id: str | None = None,
    timeout: int = 60,
) -> tuple[str, int, str]:
    """Return (stdout+stderr text, returncode, stderr_tail)."""
    proc = bu_call(bin_path, cdp, ["state"], account_id=account_id, timeout=timeout)
    text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return text, proc.returncode, (proc.stderr or "")[-1200:]
