# Agent instructions

Run **`nextbrowser status`** first — follow **`agent_must_know`** in the JSON.

## Rules

1. Load **browser-use** skill + **nextbrowser-harness** skill.
2. Ask user: which account / new login / credentials?
3. `nextbrowser account add <name> --create-mlx` if new profile needed.
4. `nextbrowser browser-use connect --account <name>` — browser stays open.
5. **One chain** for login: `nextbrowser browser-use chain open "URL" state "input N user" "click M"`.
6. Do **not** `browser-use close` or `multilogin stop-all` until done.
7. `nextbrowser browser-use disconnect --account <name>` when finished.

## Not for UI

Do not use `nextbrowser exec --action state` for clicks/types — use browser-use after connect.

Skill: `skills/nextbrowser-harness/SKILL.md`
