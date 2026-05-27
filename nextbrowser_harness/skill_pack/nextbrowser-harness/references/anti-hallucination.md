# Anti-hallucination (raw CDP)

Prove outcomes from **CDP command output**, not memory.

## Before claiming login

```bash
nextbrowser cdp send Runtime.evaluate --params '{"expression":"document.body.innerText.includes(\"Log out\") || document.querySelector(\"[href*=logout]\") !== null","returnByValue":true}'
```

Read `result` in JSON. If false, you are not logged in.

## Before claiming a post/submit

```bash
nextbrowser cdp send Runtime.evaluate --params '{"expression":"document.body.innerText.includes(\"exact text you submitted\")","returnByValue":true}'
```

## Every action

1. `cdp session` — know URL and targets  
2. `cdp send` — navigate, read DOM, click, type  
3. `cdp send` — verify with Runtime.evaluate or DOM  

Do not use legacy `ui click N` for account automation.
