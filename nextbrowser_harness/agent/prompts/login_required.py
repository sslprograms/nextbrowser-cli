"""Injected when the live page is logged out but credentials are available (next-browser pattern)."""


def login_required_task_block(*, login_url: str, site: str = "") -> str:
    target = login_url or site or "the site login page"
    return f"""
<mandatory_first_steps priority="highest">
The browser profile is NOT logged in. You MUST complete login BEFORE any other task steps.

1. If you see Log in / Sign in / Create account, use the login flow immediately.
2. If needed, navigate to: {target}
3. Fill username and password using sensitive_data (browser-use will inject secrets — do not type fake placeholders).
4. Submit the form and wait for the authenticated UI (sign-out, dashboard, feed, account menu — no login gate).
5. Up to 5 login attempts; if still blocked (captcha, 2FA without TOTP), stop with success=false and explain what you need.

Only after login succeeds, continue with the user task below.
</mandatory_first_steps>
""".strip()


CREDENTIALS_LOGIN_POLICY = """
<credentials_login_policy>
You HAVE real credentials via sensitive_data for this run.
- OVERRIDE generic "do not login" guidance: logging in IS required when the page shows an auth gate.
- Complete login before posting, commenting, checkout, or account actions.
- Never claim login succeeded until browser_state shows logged-in UI (no Log in / Sign up gate).
</credentials_login_policy>
""".strip()
