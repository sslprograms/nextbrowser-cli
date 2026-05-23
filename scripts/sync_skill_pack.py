"""Copy skills/nextbrowser-harness → nextbrowser_harness/skill_pack for pip wheels."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def sync_skill_pack() -> Path:
    root = Path(__file__).resolve().parent.parent
    src = root / "skills" / "nextbrowser-harness"
    dest = root / "nextbrowser_harness" / "skill_pack" / "nextbrowser-harness"
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(f"Missing source skill: {src / 'SKILL.md'}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


if __name__ == "__main__":
    path = sync_skill_pack()
    print(f"Synced skill pack to {path}")
    sys.exit(0)
