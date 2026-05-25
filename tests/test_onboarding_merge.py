"""Config merge — init --env must not wipe MLX UUIDs."""

from pathlib import Path

import yaml

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.onboarding import onboard_from_env


def test_onboard_from_env_preserves_mlx_uuids(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    real_folder = "35a23b4c-be1b-4d01-b0ef-390ab28048be"
    real_profile = "5ada779c-c9cd-4c0d-848d-2277a8dfbbf0"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "browser": "multilogin",
                "multilogin": {
                    "folder_id": real_folder,
                    "default_profile_id": real_profile,
                    "profiles": {"default": real_profile},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NEXTBROWSER_CONFIG", str(cfg_path))
    monkeypatch.setenv("MULTILOGIN_FOLDER_ID", "folder-1")
    monkeypatch.setenv("MULTILOGIN_PROFILE_ID", "profile-1")
    monkeypatch.setenv("NEXTBROWSER_BROWSER", "multilogin")

    onboard_from_env()

    saved = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert saved["multilogin"]["folder_id"] == real_folder
    assert saved["multilogin"]["default_profile_id"] == real_profile


def test_onboard_from_env_applies_real_env_ids(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump({"browser": "native"}), encoding="utf-8")
    monkeypatch.setenv("NEXTBROWSER_CONFIG", str(cfg_path))
    real_folder = "35a23b4c-be1b-4d01-b0ef-390ab28048be"
    real_profile = "5ada779c-c9cd-4c0d-848d-2277a8dfbbf0"
    monkeypatch.setenv("MULTILOGIN_FOLDER_ID", real_folder)
    monkeypatch.setenv("MULTILOGIN_PROFILE_ID", real_profile)
    monkeypatch.setenv("NEXTBROWSER_BROWSER", "multilogin")

    onboard_from_env()

    saved = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert saved["multilogin"]["folder_id"] == real_folder
    assert saved["multilogin"]["default_profile_id"] == real_profile
