# Troubleshooting (agents)

## Tier 3: missing account

**Symptom:** `success: false`, `agent_prompt` about “Which saved account” or “named account”.

```bash
nextbrowser account list
nextbrowser account add <name> --create-mlx
```

Ask the user which name to use or whether to create a new login.

## Tier 3: missing credentials

**Symptom:** `agent_prompt` about username/password or placeholders.

Ask the user for real credentials. Retry with:

```bash
<cli> exec "<url>" --account <name> --var username=REAL --var password=REAL
# or
<cli> exec "<url>" --account <name> --action "type:N|REAL"
```

Do not use `USER`, `PASS`, or empty `--var` values.

## CLI not found

```bash
nextbrowser status
```

Use `platform.cli` from JSON. `pip install -e .` and activate venv.

## Skill not loading

```bash
nextbrowser agent install --force
nextbrowser agent doctor
```

New agent session after install.

## Element clicks fail (SPA / shadow DOM)

Tier 3 — always include account and use indices:

```bash
<cli> exec "<url>" --account <name> --action goto --action state
<cli> exec "<url>" --account <name> --action "click:N"
```

## MLX / CDP

| Symptom | Fix |
|---------|-----|
| Launcher not reachable | Start MLX desktop; `multilogin doctor` |
| Signin 400 | MLX app credentials at multilogin.com |
| Token 400 | `multilogin automation-token` after signin |
| Profile already running | `multilogin stop-all` |
| Linux launcher broken | `multilogin fix-linux-launcher` |
| No CDP port | Launcher must be running; check doctor |

## Playwright missing

```bash
pip install -e ".[playwright]"
playwright install chromium
```

## Agent wrote Playwright Python

Reload skill — use `exec` / `scrape` / `account` only.
