"""
Account-aware context injected into the system prompt when running with a Multilogin profile.

This is nextbrowser-harness specific — tells the AI it's operating inside an
anti-detect browser with a persistent identity, and how to handle credentials.
"""


def account_context_prompt(
    account_id: str,
    site: str = "",
    logged_in: bool = False,
    display_name: str = "",
) -> str:
    status = "already logged in" if logged_in else "NOT logged in yet — login may be required"
    site_line = f"Target site: {site}" if site else ""
    return f"""
<account_context>
You are operating inside a Multilogin anti-detect browser profile.
- Account name: {account_id}
- Display name: {display_name or account_id}
{f'- {site_line}' if site_line else ''}- Login status: {status}
- Browser fingerprint, cookies, and proxy are managed by Multilogin — do not change proxy settings.
- Sessions persist across runs. If you logged in before, cookies should still be valid.
- If you need credentials and don't have them, call `done` with success=false and ask the user.
- NEVER use placeholder credentials (USER, PASS, xxx, changeme, etc.).
</account_context>
"""
