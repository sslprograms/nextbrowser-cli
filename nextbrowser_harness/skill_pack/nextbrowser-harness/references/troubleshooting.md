# Troubleshooting

Same fixes on every agent host.

## Login closes between steps

- Use `nextbrowser connect --account <name>` then `nextbrowser ui state` / `click` / `type`.
- Or one-shot: `nextbrowser login <name> --url <url>`.
- **Never** `nextbrowser exec --action state` per click — deprecated for UI.
- **Never** `multilogin stop-all` before `nextbrowser disconnect` or `ui close`.

## Profile missing in Multilogin app

```bash
nextbrowser multilogin doctor
nextbrowser account add <name> --create-mlx --display-name "Label"
```

## Missing credentials

Ask the user for username/password, then:

```bash
nextbrowser login <name> --url <url> --username U --password P --username-index N --password-index N --submit-index N
```

Or use indices from `ui state` manually with `ui type` / `ui click`.

`login` fails with `placeholder credentials` if values look like `USER`, `PASS`, empty, `$VAR`.

## No CDP session

`nextbrowser ui <cmd>` returns `No browser session.` →

```bash
nextbrowser connect --account <name>
```

## MLX launcher issues

| Symptom | Fix |
|---------|-----|
| Launcher not reachable | Start Multilogin X desktop app, then `multilogin doctor` |
| Token 401 | `multilogin signin` then `multilogin automation-token` |
| Linux launcher broken | `multilogin fix-linux-launcher` |
| Profile already running | `multilogin stop-all`, then `connect` again |

## Playwright missing

```bash
pip install -e ".[playwright]"
playwright install chromium
playwright install-deps chromium    # Linux headless
```

## Agent wrote raw Playwright

Reload skill — use `nextbrowser ui state` / `ui click` / `ui type` only.

## Sandboxed agent

Python, this package, Playwright, and Chromium must be inside the sandbox. MLX desktop app must run on the host.
