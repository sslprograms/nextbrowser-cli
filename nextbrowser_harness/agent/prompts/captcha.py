"""Captcha detection and solving guidance for the browser agent."""

CAPTCHA_PROMPT = """
<solve_captcha_guidance>
    If you have a captcha solving tool, call it **before you submit any form**.
    Even if captcha is not visible, there might be invisible captcha.

    Check for captcha presence first:
    - DOM markers like `<div class="g-recaptcha">`, `<div class="h-captcha">`,
      `iframe[src*="recaptcha"]`, `iframe[src*="hcaptcha.com"]`,
      or hidden inputs such as `g-recaptcha-response`.
    - Visible text prompts such as "verify you are human" or "verify you are not a robot".
    - Scripts loaded from captcha provider domains (Google reCAPTCHA, hCaptcha, Cloudflare Turnstile).

    If captcha is found and a solver tool is available, call it **before** triggering the submit button.
    If no solver tool is available, report to the user that a captcha is blocking progress.

    After captcha solving, a modal or popup can appear either before or after clicking submit.
    In both cases, close it immediately.
    If the modal hides the submit button, close it first before attempting to click submit.

    Do not attempt to solve captcha by clicking the challenge manually — always use the tool if available.
</solve_captcha_guidance>
"""
