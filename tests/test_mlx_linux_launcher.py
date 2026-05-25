"""Linux MLX .deb launcher script path fix."""

from pathlib import Path

def test_fix_linux_mlx_launcher_script(tmp_path, monkeypatch):
    script = tmp_path / "mlx"
    script.write_text("#!/bin/sh\nexec /opt/mlx/agent.bin\n", encoding="utf-8")
    agent = tmp_path / "opt" / "mlx" / "agent.bin"
    agent.parent.mkdir(parents=True)
    agent.write_bytes(b"fake")

    import nextbrowser_harness.integrations.multilogin.platform_hints as ph

    monkeypatch.setattr(ph, "is_linux", lambda: True)
    monkeypatch.setattr(ph, "LINUX_MLX_LAUNCHER_SCRIPT", script)
    monkeypatch.setattr(ph, "LINUX_MLX_AGENT_BIN", agent)

    diag = ph.diagnose_linux_mlx_launcher()
    assert diag["wrong_path_in_script"] is True
    assert diag["fixable"] is True

    result = ph.fix_linux_mlx_launcher_script(apply=True)
    assert result["applied"] is True
    assert str(agent) in script.read_text(encoding="utf-8")
