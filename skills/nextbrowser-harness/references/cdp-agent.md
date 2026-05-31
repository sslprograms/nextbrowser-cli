# Raw CDP control (no shortcuts)

The host agent issues **Chrome DevTools Protocol** methods directly. Do not use `ui click N` / `ui type N` for account automation — those are legacy indexed helpers.

## Connect

```bash
nextbrowser connect --account <name>
nextbrowser cdp session
```

`session` returns `cdp_url`, `page_url`, and open tabs.

## Survey full page (required before actions)

```bash
nextbrowser cdp survey --account <name>
```

Scrolls the page in viewport steps. For each step JSON includes:

- `visible_text` — text in that slice
- `interactive` — buttons/links/inputs visible in that slice (with approximate position)
- `logged_in_hint` / `logged_in_reason` — heuristic for that slice
- `scroll_y`, `at_page_bottom`

Read **every** object in `segments[]` before `cdp send` click/type on that page.

### Snapshots (required for understanding)

Each segment includes `screenshot_path` → PNG under `snapshot_dir`. **Open these files with your vision model** before acting. Text-only `visible_text` is not enough.

```bash
nextbrowser cdp snapshot --account <name>
nextbrowser cdp snapshot --account <name> C:\path\to\after-click.png
```

Uses CDP `Page.captureScreenshot`. After clicks/submits, snapshot again to verify.

Survey options: `--step-ratio 0.85`, `--max-segments 50`, `--wait-ms 350`, `--no-reset-top`, `--embed-base64` (inline PNG if you cannot read files)

## Send CDP

```bash
nextbrowser cdp send <Domain.method> --params '<json object>'
```

Params must be a JSON object (use single quotes outside on shell).

### Navigate

```bash
nextbrowser cdp send Page.navigate --params '{"url":"https://example.com"}'
```

### Read the DOM

```bash
nextbrowser cdp send DOM.getDocument --params '{"depth":-1,"pierce":true}'
```

Use `DOM.querySelector`, `DOM.getAttributes`, `DOM.getBoxModel` with `nodeId` from prior results.

### Run JavaScript

```bash
nextbrowser cdp send Runtime.evaluate --params '{"expression":"document.body.innerText.slice(0,5000)","returnByValue":true}'
```

### Click (coordinates from getBoxModel)

```bash
nextbrowser cdp send Input.dispatchMouseEvent --params '{"type":"mousePressed","x":400,"y":300,"button":"left","clickCount":1}'
nextbrowser cdp send Input.dispatchMouseEvent --params '{"type":"mouseReleased","x":400,"y":300,"button":"left","clickCount":1}'
```

### Type text

```bash
nextbrowser cdp send Input.insertText --params '{"text":"hello"}'
```

Or key events via `Input.dispatchKeyEvent`.

### Screenshot

```bash
nextbrowser cdp send Page.captureScreenshot --params '{"format":"png"}'
```

(Base64 in result — decode if you need a file.)

## One-shot login

For account login you usually don't need to hand-build the field clicks — use the
deterministic helper, which detects the form, types with trusted CDP `Input.insertText`,
submits, and verifies:

```bash
nextbrowser account set-credentials <name> --username "U" --password "P"
nextbrowser login <name> --url "https://site.com/login"
```

It returns `logged_in` (true/false/uncertain), `filled`, `submitted`, `obstacle`
(captcha/2FA/email-verify if detected), and `screenshots` (before/after PNGs to open with
vision). Drop to manual `cdp send` only for unusual flows.

## Proof before claims

After login or submit, **send CDP** to read the live page (Runtime.evaluate or DOM) and confirm the expected string is present. Do not claim success from memory.

## Examples list

```bash
nextbrowser cdp catalog
```

## End

```bash
nextbrowser disconnect --account <name>
```
