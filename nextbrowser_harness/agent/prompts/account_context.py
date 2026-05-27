"""
Account-aware context injected into the system prompt when running with a Multilogin profile.

Mirrors next-browser-main: persistent MLX profile + optional sensitive_data credentials.
"""


def account_context_prompt(
    account_id: str,
    site: str = "",
    logged_in: bool = False,
    display_name: str = "",
    *,
    has_credentials: bool = False,
    logged_in_live: bool | None = None,
) -> str:
    if logged_in_live is True:
        status = "verified logged in (live page check before this run)"
    elif logged_in_live is False:
        status = "verified NOT logged in (live page check) — login required first"
    elif logged_in:
        status = "registry marked logged in (confirm in browser_state)"
    else:
        status = "NOT logged in — login required before account actions"

    site_line = f"Target site: {site}" if site else ""
    cred_line = ""
    if has_credentials:
        cred_line = (
            "- Credentials: available via sensitive_data (username/password). "
            "You MUST use them to log in when an auth gate is visible."
        )
    else:
        cred_line = (
            "- Credentials: NOT loaded. If login is required, call done with success=false "
            "and ask the user to run: "
            f"`nextbrowser account set-credentials {account_id} --username ... --password ...`"
        )

    return f"""
<account_context>
You are operating inside a Multilogin anti-detect browser profile (same model as next-browser + MLX CDP).
- Account name: {account_id}
- Display name: {display_name or account_id}
{f'- {site_line}' if site_line else ''}
- Login status: {status}
{cred_line}
- Browser fingerprint, cookies, and proxy are managed by Multilogin — do not change proxy settings.
- Sessions persist across runs; stale cookies may still show a login wall — always trust current browser_state.
- NEVER use placeholder credentials (USER, PASS, xxx, changeme, etc.).
</account_context>
"""
