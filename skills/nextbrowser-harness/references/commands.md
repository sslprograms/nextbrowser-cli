# nextbrowser CLI — CDP only

## MLX account automation

| Command | Purpose |
|---------|---------|
| `nextbrowser connect --account <name>` | Start MLX profile (CDP) |
| `nextbrowser disconnect --account <name>` | Stop profile |
| `nextbrowser cdp navigate --account <name> <url>` | `Page.navigate` + full-page `survey` |
| `nextbrowser cdp survey --account <name>` | Scroll page; PNG + text per viewport (open screenshots with vision) |
| `nextbrowser cdp snapshot --account <name> [path.png]` | Single viewport PNG (verify after actions) |
| `nextbrowser cdp send --account <name> <Method> --params '<json>'` | Raw CDP |
| `nextbrowser cdp session --account <name>` | CDP URL + tabs |
| `nextbrowser login <name> --url <url>` | Auto-login: navigate, fill creds, submit, verify |
| `nextbrowser account set-credentials <name> --username U --password P` | Store creds for `login` |

## Login (deterministic)

```bash
nextbrowser account set-credentials alice --username "alice@example.com" --password "secret"
nextbrowser login alice --url "https://example.com/login"
```

`login` connects MLX, finds the username/password/submit controls, types with **trusted CDP
Input events** (works in the anti-detect browser), submits, then verifies and returns
`logged_in` + before/after screenshots. Credentials can be stored first (above) or passed
with `--username/--password`. If no credentials exist it just opens + surveys the page and
tells you to add them. Never echoes the password.

## Disabled (return error — do not use)

`ui`, `ui close`, `state`, `click`, `type`, indexed shortcuts.

## Open Reddit example

```bash
nextbrowser disconnect --account Pale-Accident-6750
nextbrowser connect --account Pale-Accident-6750
nextbrowser cdp navigate --account Pale-Accident-6750 "https://www.reddit.com/r/sidehustle/"
```

## Scrape (no browser)

`nextbrowser scrape "<url>" --json`
