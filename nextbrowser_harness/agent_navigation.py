"""Backward-compat shim — agent_rules.py is the source of truth."""

from __future__ import annotations

from nextbrowser_harness.agent_rules import (
    MUST_KNOW as AGENT_MUST_KNOW,
    POLICY as AGENT_NAVIGATION_POLICY,
    automation_guide as agent_automation_guide,
    command_recipes as agent_command_recipes,
)

__all__ = [
    "AGENT_MUST_KNOW",
    "AGENT_NAVIGATION_POLICY",
    "agent_automation_guide",
    "agent_command_recipes",
]
