# Troubleshooting

Same fixes on every agent host.

## Login closes between steps

- Use `nextbrowser login <name> --url <url>` (one command).
- For follow-ups use `nextbrowser ui state / click N / type N text`.
- **Never** `nextbrowser exec --action state` per click — that path is deprecated for UI.
- **Never** `browser-use close` or `multilogin stop-all` before `nextbrowser ui close`.

## Profile missing in Multilogin app

```bash
nextbrowser multilogin doctor          # launcher + token
nextbrowser account add <name> --create-mlx --display-name "Label"
```

JSON shows `mlx_profile_id`. Open the Multilogin X app → same folder → profile must be listed.

## Missing credentials

If you want the **AI agent** to log in like next-browser, you must store credentials for the account:

```bash
nextbrowser account set-credentials <account> --username U --password P
```

Or pass them inline on a run:

```bash
nextbrowser agent-run "<task>" --account <account> --url <url> --username U --password P
```

`nextbrowser login` fails with `placeholder credentials` if `--username` or `--password` look like placeholders (`USER`, `PASS`, empty, `$VAR`). Ask the user for real values.

If `agent-run` is logged out **and** has no credentials, it will fail fast with exit code 1 (this is intentional — no fake login).

## No CDP session

`nextbrowser ui <cmd>` returns `No browser session.` →

```bash
nextbrowser browser-use session     # check saved session
nextbrowser login <name> --url <url>
```

## MLX launcher issues

| Symptom | Fix |
|---------|-----|
| Launcher not reachable | Start the Multilogin X desktop app, then `multilogin doctor` |
| Token 401 | `multilogin signin` then `multilogin automation-token` |
| Linux launcher broken | `multilogin fix-linux-launcher` |
| Profile already running | `multilogin stop-all`, then `login` again |

## browser-use CLI missing

```bash
curl -fsSL https://browser-use.com/cli/install.sh | bash
browser-use doctor
```

## Playwright missing

```bash
pip install -e ".[playwright]"
playwright install chromium
playwright install-deps chromium    # Linux headless
```

## Agent wrote raw Playwright

Reload skill — UI is browser-use only.

## Sandboxed agent

Python, this package, Playwright, Chromium, and browser-use must all be inside the sandbox.
