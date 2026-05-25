# browser-use + nextbrowser bridge

## Roles

| Tool | Role |
|------|------|
| **browser-use** | UI: `state`, `click`, `input`, `screenshot`, `eval` |
| **nextbrowser** | MLX accounts, `browser-use connect`, scrape, tiers |

Agents should load **both** skills:
- `nextbrowser agent install --force --with-browser-use`
- Or: `nextbrowser browser-use install-skill`

## Connect flow

```bash
nextbrowser browser-use connect --account my_account
# → writes ~/.nextbrowser/browser_use_session.json with cdp_url

nextbrowser browser-use run open "https://example.com"
nextbrowser browser-use run state
nextbrowser browser-use run click 5
```

Equivalent manual form (from connect JSON):

```bash
browser-use --cdp-url "http://127.0.0.1:PORT" state
```

## Why not nextbrowser exec?

`nextbrowser exec --action state` duplicates browser-use poorly. The official **browser-use** CLI keeps a persistent daemon, fast `state`, and is what agents already know. nextbrowser starts **Multilogin** and hands off **CDP** to browser-use.

## Account + credentials

Same as main skill — ask user for account name and login credentials before automating tier-3 sites.

## Official browser-use docs

https://github.com/browser-use/browser-use/blob/main/browser_use/skill_cli/README.md
