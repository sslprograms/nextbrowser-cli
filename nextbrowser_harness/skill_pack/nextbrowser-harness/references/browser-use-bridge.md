# browser-use bridge (CDP session lifecycle)

## Where each tool sits

| Tool | Owns |
|------|------|
| **Multilogin X** | Browser profile, cookies, fingerprint, residential proxy |
| **nextbrowser** | Account registry, MLX launch + keep-alive, CDP handoff |
| **browser-use** | UI primitives (state, click, input, eval, screenshot) |

`nextbrowser` starts the MLX profile, captures the CDP URL, and saves a keep-alive marker. Every UI command runs through browser-use using that CDP URL. The MLX profile stays open until `nextbrowser ui close`.

## Connection flow

```
nextbrowser login <name> --url <url>
  ├── ensure account exists (auto-create MLX profile if missing)
  ├── MLX launcher: start_profile (or reuse if already running)
  ├── save CDP URL → ~/.nextbrowser/browser_use_session.json
  ├── mark keep-alive → ~/.nextbrowser/mlx_keep_alive.json
  ├── browser-use chain: open → state   (one shell pass)
  └── if credentials supplied: chain input → input → click → state
```

Every `nextbrowser ui <cmd>` reads the saved session and shells out to `browser-use --cdp-url <cdp> <cmd> ...`.

## Why one chain matters

Each `subprocess.run` of `browser-use` is fast (~50ms) because the browser-use daemon keeps the actual browser open. But the **Multilogin** profile is owned by the MLX launcher — if we call `stop_profile` between steps, cookies/state are lost.

`nextbrowser ui ...` never calls `stop_profile`; only `ui close` does (which also calls `browser-use close` and clears keep-alive).

## Recovering a stale session

```bash
nextbrowser browser-use session     # show saved CDP + account
nextbrowser browser-use doctor      # browser-use CLI + session diagnostics
nextbrowser multilogin doctor       # launcher reachability
```

If the saved CDP URL is dead:

```bash
nextbrowser ui close                # cleanup
nextbrowser login <name> --url <url>   # fresh session
```

## Official browser-use docs

- Skill: <https://github.com/browser-use/browser-use/blob/main/skills/browser-use/SKILL.md>
- CLI: <https://github.com/browser-use/browser-use/blob/main/browser_use/skill_cli/README.md>
