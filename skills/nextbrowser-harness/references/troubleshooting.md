# Troubleshooting (CDP only)

## Agent used `ui` or `login` wrong

**Wrong:**

```bash
nextbrowser ui --account X close
nextbrowser login X --url ...
```

**Right:**

```bash
nextbrowser disconnect --account X
nextbrowser connect --account X
nextbrowser cdp navigate --account X "https://..."
```

## Browser did not move

1. `nextbrowser multilogin doctor`
2. `nextbrowser connect --account <name>` — must succeed with `cdp_url`
3. `nextbrowser cdp send --account <name> Page.navigate --params '{"url":"..."}'`
4. `nextbrowser cdp survey --account <name>` — confirm page content in `segments`

## Profile not running

Every command needs `--account`. Run `connect` before `cdp send` / `survey`.
