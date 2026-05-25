# Using Nextbrowser Harness with OpenClaw (Linux, macOS, Windows)

> **Other agents (Claude Code, Cursor, Codex, …):** see **[AGENT_HOSTS.md](AGENT_HOSTS.md)** — use `nextbrowser agent install --host all`.

OpenClaw loads **skills** from `SKILL.md` folders ([skills guide](https://openclawx.cloud/en/tools/skills)). The CLI lives at **[github.com/sslprograms/nextbrowser-cli](https://github.com/sslprograms/nextbrowser-cli)**; this repo ships `skills/nextbrowser-harness/` for **darwin**, **linux**, and **win32**.

The agent runs shell commands — use the **`nextbrowser`** CLI (or `python3 -m nextbrowser_harness.cli` on all platforms).

---

## 1. Install the harness (same machine as OpenClaw gateway)

### Linux / macOS

```bash
git clone https://github.com/sslprograms/nextbrowser-cli.git
cd nextbrowser-cli
# or: cd /path/to/your/local/clone
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ".[playwright]"
playwright install chromium
# Linux only — browser system dependencies:
playwright install-deps chromium
```

### Windows (PowerShell)

```powershell
cd C:\path\to\nextbrowser-cli
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e ".[playwright]"
playwright install chromium
```

Verify:

```bash
nextbrowser openclaw doctor
# or: python -m nextbrowser_harness.cli openclaw doctor
```

---

## 2. Install the OpenClaw skill (cross-platform)

**Recommended** — works on Linux, macOS, and Windows:

```bash
nextbrowser agent install --host openclaw
# or: nextbrowser openclaw install   (alias)
# Per-agent workspace:
nextbrowser agent install --host openclaw --target workspace --workspace ~/my-openclaw-workspace
# Every supported host at once:
nextbrowser agent install --host all
```

This copies the skill to:

| Target | Path |
|--------|------|
| `managed` (default) | `~/.openclaw/skills/nextbrowser-harness` |
| `workspace` | `<workspace>/skills/nextbrowser-harness` |

**Manual copy (alternative)**

```bash
# Shared (all agents)
mkdir -p ~/.openclaw/skills
cp -R /path/to/nextbrowser-cli/skills/nextbrowser-harness ~/.openclaw/skills/

# Or workspace-local
mkdir -p ./skills
cp -R /path/to/nextbrowser-cli/skills/nextbrowser-harness ./skills/
```

Start a **new OpenClaw session** after installing (skills snapshot per session).

---

## 3. Configure `~/.openclaw/openclaw.json`

Merge under `skills.entries` ([skills config](https://documentation.openclaw.ai/tools/skills-config)):

```json5
{
  skills: {
    entries: {
      "nextbrowser-harness": {
        enabled: true,
        env: {
          NEXTBROWSER_USE_CASE: "scrape",
          NEXTBROWSER_BROWSER: "native",
          NEXTBROWSER_PROXY: "nodemaven",
          NODEMAVEN_PROXY_HOST: "gate.nodemaven.com:8080",
          NODEMAVEN_PROXY_USER: "your-user",
          NODEMAVEN_PROXY_PASSWORD: "your-pass",
        },
      },
    },
  },
}
```

Optional: load skill from repo without copying:

```json5
{
  skills: {
    load: {
      extraDirs: ["/absolute/path/to/nextbrowser-cli/skills"],
    },
  },
}
```

Use forward slashes in JSON paths on all OSes.

---

## 4. Bootstrap

```bash
export NEXTBROWSER_USE_CASE=scrape
nextbrowser init --env
nextbrowser status
```

Multilogin (all platforms — MLX desktop app must be running):

```bash
nextbrowser multilogin signin
nextbrowser multilogin automation-token
export NEXTBROWSER_BROWSER=multilogin
export MULTILOGIN_FOLDER_ID=...
export MULTILOGIN_PROFILE_ID=...
nextbrowser init --env
```

---

## 5. What OpenClaw runs

The skill teaches the agent to execute shell commands. **Primary automation** (inject JS, click, fill):

```bash
nextbrowser exec "https://www.reddit.com" --js "document.title" --json
nextbrowser exec "https://www.reddit.com" --js-file examples/scripts/count-posts.js --tier 3
nextbrowser exec "https://www.reddit.com" --steps-file examples/steps-reddit.json --browser multilogin
nextbrowser exec "https://shop.com" --action "click:button.buy" --action "eval:document.title"
```

Also:

```bash
nextbrowser scrape "https://example.com/pricing" --json
nextbrowser tier lookup "https://reddit.com"
nextbrowser account add social_01
nextbrowser account run social_01 "eval:document.title" --url "https://..." --json
nextbrowser multilogin profiles
```

**Teaching guide:** [AGENT_QUICKSTART.md](AGENT_QUICKSTART.md)

If `nextbrowser` is not on PATH, the agent should use:

```bash
python3 -m nextbrowser_harness.cli scrape "https://example.com" --json
```

`nextbrowser status` includes `platform.cli` with the correct prefix.

---

## 6. Sandboxed agents (Docker)

If OpenClaw runs tools in a **sandbox container**, install Python, this package, Playwright, and Chromium **inside the image**. Example `setupCommand`:

```bash
pip install -e /opt/nextbrowser-cli && playwright install chromium && playwright install-deps chromium
```

See [OpenClaw sandboxing](https://openclawx.cloud/en/gateway/sandboxing).

---

## 7. Remote gateway + local Mac (Multilogin)

If the **gateway is on Linux** but **Multilogin runs on a Mac node**, OpenClaw can route `system.run` to the Mac node when binaries exist there ([remote macOS nodes](https://openclawx.cloud/en/tools/skills)). Install the harness on the Mac and set `NEXTBROWSER_BROWSER=multilogin` only on that node.

---

## ClawHub

When published: `clawhub install nextbrowser-harness` from [ClawHub](https://clawhub.com/).
