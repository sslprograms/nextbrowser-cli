# Agent instructions — Nextbrowser Harness

**Tier 3 browser automation** = **Multilogin profile** + **CDP** + **named account** (`--account`).

## Start

```bash
nextbrowser status
```

Read `accounts`, `tier3_automation`, `how_to_automate`, use `platform.cli` as prefix.

## Ask the user first

- **Which account?** (`nextbrowser account list`)
- **New login?** → `nextbrowser account add <name> --create-mlx`
- **Credentials?** — if login needed and you don't have them, ask; never use placeholders.

## Automate

```bash
<cli> exec "<url>" --account <name> --action goto --action state
<cli> exec "<url>" --account <name> --action "click:N" --action "type:N|value"
```

## Read-only

```bash
<cli> scrape "<url>" --json
```

Skill: `skills/nextbrowser-harness/SKILL.md`
