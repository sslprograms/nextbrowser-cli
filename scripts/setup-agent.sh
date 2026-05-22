#!/usr/bin/env bash
# Install Nextbrowser Harness + skill for OpenClaw, Claude Code, Cursor, etc. (Linux / macOS)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Nextbrowser Harness — agent hosts setup"
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }

[[ -d .venv ]] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -e .
pip install -e ".[playwright]"
playwright install chromium
if [[ "$(uname -s)" == "Linux" ]]; then
  playwright install-deps chromium || true
fi

nextbrowser agent install --host all --force
nextbrowser agent doctor

echo ""
echo "See docs/AGENT_HOSTS.md — configure env for your agent host, then:"
echo "  nextbrowser init --env"
