"""Backward-compatible wrapper — use agent_setup for all agent hosts."""

from nextbrowser_harness.agent_setup import (  # noqa: F401
    config_snippets,
    install_for_host,
    install_skill_to_dir,
    print_post_install,
)

# OpenClaw-only alias
openclaw_config_snippet = lambda: config_snippets()["openclaw"]  # noqa: E731


def install_skill(*, target: str = "managed", workspace=None, force: bool = False):
    return install_for_host("openclaw", target=target, workspace=workspace, force=force)
