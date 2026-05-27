# Host agent drives MLX via raw CDP

Any AgentSkills host. **No indexed shortcuts** — only `cdp send`.

## Connect

```bash
nextbrowser connect --account <name>
nextbrowser cdp session
```

## Loop

```bash
nextbrowser cdp send <Domain.method> --params '<json>'
```

See `cdp-agent.md` for navigate, DOM, Input, Runtime, screenshot.

## End

```bash
nextbrowser disconnect --account <name>
```
