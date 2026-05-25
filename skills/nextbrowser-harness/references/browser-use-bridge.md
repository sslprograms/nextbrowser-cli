# browser-use + nextbrowser (agent reference)

## Agent must know

1. Install **both** skills: `nextbrowser agent install --force --with-browser-use`
2. **browser-use** = all UI (`state`, `click`, `input`)
3. **nextbrowser** = accounts, connect, **chain** login, disconnect, scrape
4. MLX browser **must stay open** during login — use **one** `browser-use chain`
5. Ask user: account name, new login?, credentials
6. `disconnect` only when login is finished

## Why chain?

Each separate `nextbrowser exec` or isolated `browser-use run` used to **stop** the Multilogin profile. Cookies/session only persist in MLX while that profile’s browser stays running.

## Commands

```bash
nextbrowser status                    # agent_must_know in JSON
nextbrowser account add NAME --create-mlx
nextbrowser browser-use connect --account NAME
nextbrowser browser-use chain open "URL" state "input N x" "click M"
nextbrowser browser-use disconnect --account NAME
```

## Forbidden during login

- `nextbrowser exec` per click/type
- `browser-use close`
- `multilogin stop-all`
- Placeholder USER/PASS

## Official browser-use skill

https://github.com/browser-use/browser-use/blob/main/skills/browser-use/SKILL.md
