#!/usr/bin/env bash
# Multilogin X (MLX) setup for Nextbrowser Harness — Linux / macOS
# Interactive: sign in, automation token, pick folder/profile, write .env
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
      echo "Usage: $0 [--env-file .env] [--profile-key reddit_default] [--skip-signin]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
ENV_PATH="$REPO_ROOT/$ENV_FILE"

step() { echo ""; echo "==> $*"; }

import_dotenv() {
  [[ -f "$ENV_PATH" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$ENV_PATH"
  set +a
}

write_dotenv() {
  local folder_id="$1" profile_id="$2" profile_key="$3"
  FOLDER_ID="$folder_id" PROFILE_ID="$profile_id" PROFILE_KEY="$profile_key" \
  MULTILOGIN_EMAIL="${MULTILOGIN_EMAIL:-}" \
  "$PY" - "$ENV_PATH" <<'PY'
import os, sys
from pathlib import Path

path = Path(sys.argv[1])
folder = os.environ["FOLDER_ID"]
profile = os.environ["PROFILE_ID"]
key = os.environ["PROFILE_KEY"].upper().replace("-", "_")
profile_key = f"MULTILOGIN_PROFILE_{key}"
updates = {
    "NEXTBROWSER_BROWSER": "multilogin",
    "NEXTBROWSER_AUTOMATION": "playwright",
    "MULTILOGIN_FOLDER_ID": folder,
    "MULTILOGIN_PROFILE_ID": profile,
    profile_key: profile,
}
email = os.environ.get("MULTILOGIN_EMAIL", "").strip()
if email:
    updates["MULTILOGIN_EMAIL"] = email

lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
out, seen = [], set()
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        k = line.split("=", 1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY
}

select_json_item() {
  local json="$1"
  local prompt="${2:-Select}"
  local count
  count="$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)")"
  if [[ "$count" -eq 0 ]]; then
    echo "No items from API." >&2
    exit 1
  fi
  echo "$json" | python3 -c "
import json, sys
items = json.load(sys.stdin)
for i, it in enumerate(items):
    uid = it.get('id') or it.get('uuid') or ''
    name = it.get('name') or it.get('profile_name') or '(no name)'
    print(f'  [{i}] {name}  ({uid})')
"
  if [[ "$NONINTERACTIVE" -eq 1 && "$count" -eq 1 ]]; then
    idx=0
  else
    read -r -p "$prompt [0-$((count - 1))]: " idx
  fi
  echo "$json" | python3 -c "
import json, sys
items = json.load(sys.stdin)
idx = int(sys.argv[1])
it = items[idx]
print(it.get('id') or it.get('uuid') or '')
" "$idx"
}

echo "Nextbrowser Harness — Multilogin X setup ($(uname -s))"
echo "Repo: $REPO_ROOT"

step "Python environment"
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }
[[ -d .venv ]] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
PY=".venv/bin/python"
pip install -q -e .
pip install -q -e ".[playwright]"
if [[ "$(uname -s)" == "Linux" ]]; then
  playwright install-deps chromium 2>/dev/null || true
fi

step "Multilogin X desktop app"
"$PY" -c "
from nextbrowser_harness.integrations.multilogin.platform_hints import try_start_mlx_desktop, mlx_start_desktop_hint
if try_start_mlx_desktop():
    print('Started or found MLX desktop app.')
else:
    print(mlx_start_desktop_hint())
"

step "Load existing .env"
import_dotenv

CLI=("$PY" -m nextbrowser_harness.cli)
has_token=0
[[ -n "${MULTILOGIN_AUTOMATION_TOKEN:-}" || -n "${MULTILOGIN_TOKEN:-}" ]] && has_token=1

if [[ "$SKIP_SIGNIN" -eq 0 && "$has_token" -eq 0 ]]; then
  step "MLX sign-in"
  [[ -n "${MULTILOGIN_EMAIL:-}" ]] || read -r -p "Multilogin X email: " MULTILOGIN_EMAIL
  [[ -n "${MULTILOGIN_PASSWORD:-}" ]] || read -r -s -p "Multilogin X password: " MULTILOGIN_PASSWORD
  echo ""
  export MULTILOGIN_EMAIL MULTILOGIN_PASSWORD
  "${CLI[@]}" multilogin signin
  "${CLI[@]}" multilogin automation-token
elif [[ "$SKIP_SIGNIN" -eq 1 ]]; then
  echo "Skipping sign-in (--skip-signin)."
else
  echo "Automation token already in environment."
fi

step "Choose workspace folder"
FOLDER_ID="${MULTILOGIN_FOLDER_ID:-}"
if [[ -z "$FOLDER_ID" ]]; then
  folders_json="$("${CLI[@]}" multilogin folders)"
  FOLDER_ID="$(select_json_item "$folders_json" "Folder")"
fi

step "Choose browser profile"
PROFILE_ID="${MULTILOGIN_PROFILE_ID:-}"
if [[ -z "$PROFILE_ID" ]]; then
  export MULTILOGIN_FOLDER_ID="$FOLDER_ID"
  profiles_json="$("${CLI[@]}" multilogin profiles --folder-id "$FOLDER_ID")"
  PROFILE_ID="$(select_json_item "$profiles_json" "Profile")"
fi

step "Write $ENV_FILE"
write_dotenv "$FOLDER_ID" "$PROFILE_ID" "$PROFILE_KEY"
import_dotenv

"${CLI[@]}" init --env

step "Doctor"
if "${CLI[@]}" multilogin doctor; then
  doctor_ok=1
else
  doctor_ok=0
fi

echo ""
echo "Done. Saved to: $ENV_PATH"
echo "  NEXTBROWSER_BROWSER=multilogin"
echo "  MULTILOGIN_FOLDER_ID=$FOLDER_ID"
echo "  MULTILOGIN_PROFILE_ID=$PROFILE_ID"
profile_env_key="MULTILOGIN_PROFILE_$(echo "$PROFILE_KEY" | tr '[:lower:]' '[:upper:]' | tr -c 'A-Z0-9' '_')"
echo "  $profile_env_key=$PROFILE_ID"
echo ""
echo "Test: nextbrowser exec \"https://www.reddit.com\" --browser multilogin --profile $PROFILE_KEY --tier 3"
[[ "$doctor_ok" -eq 1 ]] || exit 1
