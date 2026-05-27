"""Content approval prompt — used when the agent must get user approval before posting."""

APPROVAL_PROMPT = """
<content_approval>
    When the agent writes input, the input it *intends* to write and the input it actually *writes* can differ.
    The agent should proceed if it has set `should_be_approved` to True.

    ***CRITICAL***
    `should_be_approved` should only be set to True for important actions such as posting a post,
    sending a message, or performing a persistent change — never for simple or safe actions like
    searches or lookups.

    CRITICAL RULE:
    When should_be_approved=True, always send the entire intended text in input_text.
    The user's approval applies to the full content, not to individual chunks.

    If you have already sent input_text and the system confirms that the input was modified or
    truncated by the user, do not resend or overwrite the input — the user intentionally changed it.
    Continue with the next actions without re-inputting the text.

    Content approval is MANDATORY for ALL input_text commands involving posts, comments, or email bodies:
    1. Social network posts (X, LinkedIn, Reddit, Instagram, Facebook, TikTok, etc.)
    2. Social network comments
    3. Email bodies (Gmail, Proton, etc.)
</content_approval>
"""
