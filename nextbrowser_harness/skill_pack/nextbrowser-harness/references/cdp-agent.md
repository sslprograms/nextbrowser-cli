# Raw CDP control (no shortcuts)

The host agent issues **Chrome DevTools Protocol** methods directly. Do not use `ui click N` / `ui type N` for account automation — those are legacy indexed helpers.

## Connect

```bash
nextbrowser connect --account <name>
nextbrowser cdp session
```

`session` returns `cdp_url`, `page_url`, and open tabs.

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
