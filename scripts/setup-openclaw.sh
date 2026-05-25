#!/usr/bin/env bash
# Install Nextbrowser Harness + OpenClaw skill (Linux / macOS)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Nextbrowser Harness — OpenClaw setup (Linux/macOS)"
echo "Repo: $REPO_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -e .
pip install -e ".[playwright]"
playwright install chromium

python scripts/sync_skill_pack.py

if [[ "$(uname -s)" == "Linux" ]]; then
  echo "==> Installing Playwright system deps (Linux)..."
  playwright install-deps chromium || echo "Warning: install-deps failed — try: sudo playwright install-deps chromium"
fi

nextbrowser openclaw install --force
nextbrowser openclaw doctor

echo ""
echo "Next steps:"
echo "  1. Edit ~/.openclaw/openclaw.json — see docs/OPENCLAW.md"
echo "  2. nextbrowser init --env"
echo "  3. Start a new OpenClaw session"
