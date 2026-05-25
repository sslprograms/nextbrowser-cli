"""MLX setup wizard unit tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nextbrowser_harness.integrations.multilogin.setup_wizard import (
    SetupWizardOptions,
    run_setup_wizard,
    update_dotenv,
)


def test_update_dotenv_merges(tmp_path):
    env = tmp_path / ".env"
    env.write_text("FOO=bar\nMULTILOGIN_EMAIL=old@x.com\n", encoding="utf-8")
    update_dotenv(env, {"MULTILOGIN_EMAIL": "new@x.com", "NEXTBROWSER_BROWSER": "multilogin"})
    text = env.read_text(encoding="utf-8")
    assert "FOO=bar" in text
    assert "MULTILOGIN_EMAIL=new@x.com" in text
    assert "NEXTBROWSER_BROWSER=multilogin" in text
    assert "old@x.com" not in text


def test_wizard_writes_env_no_password(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    opts = SetupWizardOptions(
        env_file=env_path,
        profile_key="default",
        skip_signin=True,
        non_interactive=True,
        open_download=False,
    )
    client = MagicMock()
    client.token_path = tmp_path / "tokens.yaml"
    client.token_path.write_text("automation_token: fake\n", encoding="utf-8")
    client.list_folders.return_value = [{"id": "folder-1", "name": "Default"}]
    client.search_profiles.return_value = [{"id": "profile-1", "name": "Main"}]

    monkeypatch.setenv("MULTILOGIN_FOLDER_ID", "folder-1")
    monkeypatch.setenv("MULTILOGIN_PROFILE_ID", "profile-1")
    monkeypatch.setenv("NEXTBROWSER_BROWSER", "multilogin")

    with patch(
        "nextbrowser_harness.integrations.multilogin.setup_wizard.mlx_install_check",
        return_value={"installed": True, "checked_paths": []},
    ):
        with patch(
            "nextbrowser_harness.integrations.multilogin.setup_wizard.try_start_mlx_desktop",
            return_value=True,
        ):
            with patch(
                "nextbrowser_harness.integrations.multilogin.doctor.mlx_doctor_report",
                return_value={"ok": True, "next_steps": []},
            ):
                with patch(
                    "nextbrowser_harness.integrations.multilogin.setup_wizard.onboard_from_env",
                ):
                    result = run_setup_wizard(options=opts, client=client)

    assert result["folder_id"] == "folder-1"
    assert result["profile_id"] == "profile-1"
    content = env_path.read_text(encoding="utf-8")
    assert "MULTILOGIN_PASSWORD" not in content
    assert "password" not in content.lower() or "NEXTBROWSER" in content
    assert "NEXTBROWSER_BROWSER=multilogin" in content
