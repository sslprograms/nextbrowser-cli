#!/usr/bin/env bash
# Multilogin X (MLX) setup for Nextbrowser Harness — Linux / macOS
# Delegates to Python setup-wizard (single source of truth).
#
# Usage:
#   ./scripts/setup-multilogin.sh
#   ./scripts/setup-multilogin.sh --env-file .env --profile-key reddit_default
#   ./scripts/setup-multilogin.sh --skip-signin
#
set -euo pipefail

ENV_FILE=".env"
PROFILE_KEY="reddit_default"
SKIP_SIGNIN=0
NONINTERACTIVE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --profile-key) PROFILE_KEY="$2"; shift 2 ;;
    --skip-signin) SKIP_SIGNIN=1; shift ;;
    --non-interactive) NONINTERACTIVE=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--env-file .env] [--profile-key default] [--skip-signin] [--non-interactive]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Nextbrowser Harness — Multilogin X setup ($(uname -s))"
echo "Repo: $REPO_ROOT"

command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }
[[ -d .venv ]] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e .
pip install -q -e ".[playwright]"
if [[ "$(uname -s)" == "Linux" ]]; then
  playwright install-deps chromium 2>/dev/null || true
fi

WIZARD=(multilogin setup-wizard --env-file "$ENV_FILE" --profile-key "$PROFILE_KEY")
[[ "$SKIP_SIGNIN" -eq 1 ]] && WIZARD+=(--skip-signin)
[[ "$NONINTERACTIVE" -eq 1 ]] && WIZARD+=(--non-interactive)

python -m nextbrowser_harness.cli "${WIZARD[@]}"
