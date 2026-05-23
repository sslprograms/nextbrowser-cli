from __future__ import annotations

import argparse
import json
import sys

from nextbrowser_harness import __version__
from nextbrowser_harness.config import HarnessConfig, resolve_config_path
from nextbrowser_harness.harness import Harness
from nextbrowser_harness.onboarding import onboard_from_env, onboard_interactive
from nextbrowser_harness.agent_hosts import list_hosts
from nextbrowser_harness.agent_setup import (
    doctor_report,
    install_all_hosts,
    install_for_host,
    print_post_install,
)
from nextbrowser_harness.openclaw_setup import install_skill  # backward compat
from nextbrowser_harness.platform_paths import (
    cli_command_string,
    platform_status,
    playwright_install_hints,
    venv_activate_hint,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nextbrowser",
        description="Nextbrowser Harness — multimodular browser automation for AI agents",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Run onboarding (interactive or --env)")
    p_init.add_argument("--env", action="store_true", help="Non-interactive onboarding from env vars")
    p_init.add_argument("--yes", action="store_true", help="Skip if config already exists")

    sub.add_parser("status", help="Show current harness configuration")

    p_scrape = sub.add_parser("scrape", help="Scrape a URL with tier DB + escalation")
    p_scrape.add_argument("url", help="Target URL")
    p_scrape.add_argument("--tier", type=int, choices=[1, 2, 3], help="Force tier (skip escalation)")
    p_scrape.add_argument("--json", action="store_true", help="JSON output for agents")

    p_browse = sub.add_parser("browse", help="Open URL in browser and run actions (tier 2/3)")
    p_browse.add_argument("url", nargs="?", default="https://www.reddit.com", help="Target URL")
    p_browse.add_argument("--tier", type=int, choices=[1, 2, 3], default=3)
    p_browse.add_argument("--browser", choices=["native", "multilogin"], default=None,
                          help="Override config browser for this run")
    p_browse.add_argument("--profile", default="reddit_default", help="Profile / MLX account key")
    p_browse.add_argument("--screenshot", default=None, help="Save PNG screenshot path")
    p_browse.add_argument("--headless", action="store_true", help="Headless (native only; MLX usually headful)")
    p_browse.add_argument("--json", action="store_true", default=True)
    p_browse.add_argument("--js", default=None, help="Run JS in page after goto (Playwright evaluate)")
    p_browse.add_argument("--js-file", default=None, help="Path to .js file to evaluate in page")
    p_browse.add_argument("--steps-file", default=None, help="JSON steps file (see examples/steps-reddit.json)")
    p_browse.add_argument(
        "--action", action="append", default=None,
        help="Repeatable action: eval:..., click:sel, fill:sel|val, jsfile:path, scroll, ...",
    )

    p_exec = sub.add_parser("exec", help="Browser automation with JS inject and step files (for agents)")
    p_exec.add_argument("url", help="Start URL")
    p_exec.add_argument("--tier", type=int, choices=[1, 2, 3], default=3)
    p_exec.add_argument("--browser", choices=["native", "multilogin"], default=None)
    p_exec.add_argument("--profile", default="default", help="Profile / MLX account key")
    p_exec.add_argument("--screenshot", default=None)
    p_exec.add_argument("--headless", action="store_true")
    p_exec.add_argument("--js", default=None)
    p_exec.add_argument("--js-file", default=None)
    p_exec.add_argument("--steps-file", default=None)
    p_exec.add_argument("--action", action="append", default=None)
    p_exec.add_argument("--keep-open", action="store_true", help="Leave browser running (MLX)")

    p_tier = sub.add_parser("tier", help="Tier database commands")
    tier_sub = p_tier.add_subparsers(dest="tier_cmd", required=True)
    p_tier_set = tier_sub.add_parser("set", help="Override tier for a domain")
    p_tier_set.add_argument("domain")
    p_tier_set.add_argument("level", type=int, choices=[1, 2, 3])
    p_tier_lookup = tier_sub.add_parser("lookup", help="Lookup recommended tier")
    p_tier_lookup.add_argument("url")

    p_acct = sub.add_parser("account", help="Account automation")
    acct_sub = p_acct.add_subparsers(dest="acct_cmd", required=True)
    p_acct_add = acct_sub.add_parser("add", help="Register account profile")
    p_acct_add.add_argument("account_id")
    p_acct_add.add_argument("--notes", default="")
    acct_sub.add_parser("list", help="List registered accounts")
    p_acct_run = acct_sub.add_parser("run", help="Run task for an account")
    p_acct_run.add_argument("account_id")
    p_acct_run.add_argument("task")
    p_acct_run.add_argument("--url", default=None)
    p_acct_run.add_argument("--js", default=None, help="Shorthand: eval:<javascript>")
    p_acct_run.add_argument("--json", action="store_true", default=True)

    p_mlx = sub.add_parser("multilogin", help="Multilogin X API (see Postman docs)")
    mlx_sub = p_mlx.add_subparsers(dest="mlx_cmd", required=True)
    p_mlx_signin = mlx_sub.add_parser("signin", help="Sign in and save tokens")
    p_mlx_signin.add_argument("--email", default=None)
    p_mlx_signin.add_argument("--password", default=None)
    mlx_sub.add_parser("automation-token", help="Fetch long-lived workspace automation token")
    mlx_sub.add_parser("folders", help="List workspace folders")
    p_mlx_profiles = mlx_sub.add_parser("profiles", help="Search profiles in folder")
    p_mlx_profiles.add_argument("--folder-id", default=None)
    p_mlx_profiles.add_argument("--search", default="", help="search_text (empty = all)")
    mlx_sub.add_parser("stop-all", help="Stop all running MLX profiles (launcher)")
    mlx_sub.add_parser("doctor", help="Check MLX launcher, token, folder/profile env")
    mlx_sub.add_parser("print-env", help="Print .env lines for MLX (no secrets)")
    p_mlx_setup = mlx_sub.add_parser("setup", help="How to configure MLX (platform-specific)")
    p_mlx_start = mlx_sub.add_parser("start", help="Start profile (launcher must be running)")
    p_mlx_start.add_argument("profile_id", help="Multilogin profile UUID")
    p_mlx_start.add_argument("--folder-id", default=None)
    p_mlx_start.add_argument("--headless", action="store_true")
    p_mlx_stop = mlx_sub.add_parser("stop", help="Stop profile")
    p_mlx_stop.add_argument("profile_id")

    def _agent_parser(name: str, help_text: str):
        p = sub.add_parser(name, help=help_text)
        subp = p.add_subparsers(dest="agent_cmd", required=True)
        p_inst = subp.add_parser("install", help="Install SKILL.md for an agent host")
        p_inst.add_argument(
            "--host",
            default="openclaw",
            help="Host id: openclaw, claude, cursor, codex, gemini, windsurf, project, all (default: openclaw)",
        )
        p_inst.add_argument("--list-hosts", action="store_true", help="List supported agent hosts and exit")
        p_inst.add_argument(
            "--target",
            choices=["managed", "workspace"],
            default="managed",
            help="managed=~/.{host}/skills; workspace=project skills dir",
        )
        p_inst.add_argument("--workspace", type=str, default=None)
        p_inst.add_argument("--force", action="store_true")
        subp.add_parser("doctor", help="Check CLI, bundled skill, and install paths for all hosts")
        subp.add_parser("list-hosts", help="List agent hosts (OpenClaw, Claude Code, Cursor, …)")
        return p

    _agent_parser("agent", "Install skill for AI agent hosts (OpenClaw, Claude, Cursor, …)")
    _agent_parser("openclaw", "Alias for: nextbrowser agent (OpenClaw)")

    args = parser.parse_args(argv)

    if args.command == "init":
        if args.yes and resolve_config_path().exists():
            print(f"Config exists: {resolve_config_path()}")
            return 0
        cfg = onboard_from_env() if args.env else onboard_interactive()
        print(f"Ready. Config: {cfg.save()}")
        return 0

    harness = Harness()

    if args.command == "status":
        print(json.dumps(harness.status(), indent=2))
        return 0

    def _exec_kwargs(ns):
        actions = list(ns.action or [])
        if not actions and not ns.js and not ns.js_file and not ns.steps_file:
            actions = ["goto", "wait_load", "title", "scroll", "final_url"]
        return dict(
            tier=ns.tier,
            profile_id=ns.profile,
            screenshot=ns.screenshot,
            headless=True if ns.headless else None,
            actions=actions or None,
            steps_file=ns.steps_file,
            js=ns.js,
            js_file=ns.js_file,
            keep_open=getattr(ns, "keep_open", False),
        )

    if args.command == "browse":
        if args.browser:
            harness.config.browser = args.browser  # type: ignore[assignment]
        kw = _exec_kwargs(args)
        if not args.action and not args.js and not args.js_file and not args.steps_file:
            kw["actions"] = ["goto", "wait_load", "title", "scroll", "reddit_feed_check", "final_url"]
        out = harness.browse(args.url, profile_id=args.profile, **kw)
        print(json.dumps(out, indent=2))
        return 0 if out.get("success") else 1

    if args.command == "exec":
        if args.browser:
            harness.config.browser = args.browser  # type: ignore[assignment]
        out = harness.exec(args.url, **_exec_kwargs(args))
        print(json.dumps(out, indent=2))
        return 0 if out.get("success") else 1

    if args.command == "scrape":
        out = harness.scrape(args.url, tier=args.tier)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"tier={out['tier']} success={out['success']} status={out.get('status_code')}")
            if out.get("escalated_from"):
                print(f"escalated from tier {out['escalated_from']}")
            if out.get("error"):
                print(f"error: {out['error']}")
            else:
                print(out.get("preview", "")[:800])
        return 0 if out["success"] else 1

    if args.command == "tier":
        if args.tier_cmd == "set":
            harness.set_tier_override(args.domain, args.level)
            print(f"Override: {args.domain} -> tier {args.level}")
            return 0
        rec = harness.tiers.recommended_tier(args.url)
        print(json.dumps({"domain": rec.domain, "tier": rec.tier, "source": rec.source}, indent=2))
        return 0

    if args.command in ("agent", "openclaw"):
        from pathlib import Path

        cmd = args.agent_cmd
        if cmd == "list-hosts" or getattr(args, "list_hosts", False):
            for h in list_hosts():
                print(f"{h.id:12} {h.name:16} {h.managed_skill_parent}")
            return 0
        if cmd == "doctor":
            report = doctor_report()
            print(json.dumps(report, indent=2))
            print("\nSuggested agent command prefix:", cli_command_string())
            print("Venv activate:", venv_activate_hint())
            print("Playwright:", " && ".join(playwright_install_hints()))
            return 0 if report.get("skill_present") else 1
        if cmd == "install":
            ws = Path(args.workspace).expanduser() if args.workspace else None
            host = args.host
            try:
                if host == "all":
                    paths = install_all_hosts(target=args.target, workspace=ws, force=args.force)
                else:
                    paths = [(host, install_for_host(host, target=args.target, workspace=ws, force=args.force))]
            except (FileExistsError, KeyError) as e:
                print(str(e))
                return 1
            print(print_post_install(paths))
            return 0

    if args.command == "multilogin":
        import os

        from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient

        client = MultiloginXClient()
        if args.mlx_cmd == "signin":
            email = (args.email or os.getenv("MULTILOGIN_EMAIL") or "").strip()
            password = (args.password or os.getenv("MULTILOGIN_PASSWORD") or "").strip()
            if not email or not password:
                print("Provide --email/--password or MULTILOGIN_EMAIL/MULTILOGIN_PASSWORD")
                return 1
            try:
                token = client.signin(email, password)
            except Exception as e:
                from nextbrowser_harness.integrations.multilogin.client import MultiloginXError

                if isinstance(e, MultiloginXError) and "incorrect" in str(e).lower():
                    print(str(e))
                    print("\nThis is Multilogin rejecting login — not a harness bug.")
                    print("  - Use your Multilogin X (MLX) app login at https://app.multilogin.com")
                    print("  - Not legacy Multilogin 6 credentials")
                    print("  - Or skip signin: copy automation token in MLX -> set MULTILOGIN_AUTOMATION_TOKEN")
                    return 1
                raise
            print(f"Signed in. Token saved to {client.token_path}")
            print("Run: nextbrowser multilogin automation-token  (recommended for automation)")
            return 0
        if args.mlx_cmd == "automation-token":
            token = client.fetch_automation_token()
            print(f"Automation token saved ({len(token)} chars)")
            return 0
        if args.mlx_cmd == "doctor":
            from nextbrowser_harness.integrations.multilogin.doctor import mlx_doctor_report

            report = mlx_doctor_report(client)
            print(json.dumps(report, indent=2))
            if report.get("next_steps"):
                print("\nNext steps:")
                for i, step in enumerate(report["next_steps"], 1):
                    print(f"  {i}. {step}")
            return 0 if report.get("ok") else 1
        if args.mlx_cmd == "print-env":
            from nextbrowser_harness.integrations.multilogin.doctor import mlx_print_env_snippet

            print(mlx_print_env_snippet())
            return 0
        if args.mlx_cmd == "setup":
            from nextbrowser_harness.integrations.multilogin.platform_hints import (
                mlx_setup_script_hint,
                mlx_setup_script_path,
                mlx_start_desktop_hint,
            )
            import platform

            sysname = platform.system().lower()
            script = mlx_setup_script_path()
            print(f"Platform: {sysname}")
            print(f"Guided setup: {mlx_setup_script_hint()}")
            if not script.is_file():
                print(f"  (script missing at {script})")
            print(f"\n{mlx_start_desktop_hint()}")
            if sysname != "windows":
                print("\nManual CLI flow:")
                print("  nextbrowser multilogin signin")
                print("  nextbrowser multilogin automation-token")
                print("  nextbrowser multilogin folders")
                print("  nextbrowser multilogin profiles --folder-id <folder-uuid>")
                print("  nextbrowser multilogin print-env   # add to .env")
                print("  nextbrowser init --env")
                print("  nextbrowser multilogin doctor")
            print("\nAgents: do NOT edit ~/.nextbrowser/multilogin_tokens.yaml manually.")
            return 0
        if args.mlx_cmd == "folders":
            folders = client.list_folders()
            print(json.dumps(folders, indent=2))
            return 0
        if args.mlx_cmd == "profiles":
            folder = args.folder_id or os.getenv("MULTILOGIN_FOLDER_ID")
            profiles = client.search_profiles(folder_id=folder, search_text=args.search)
            print(json.dumps(profiles, indent=2))
            return 0
        if args.mlx_cmd == "stop-all":
            print(json.dumps(client.stop_all_profiles(), indent=2))
            return 0
        if args.mlx_cmd == "start":
            folder = args.folder_id or os.getenv("MULTILOGIN_FOLDER_ID")
            if not folder:
                print("Set --folder-id or MULTILOGIN_FOLDER_ID")
                return 1
            started = client.start_profile(
                folder, args.profile_id, headless=args.headless
            )
            print(json.dumps({"cdp_url": started.cdp_url, "port": started.port, "raw": started.raw}, indent=2))
            return 0
        if args.mlx_cmd == "stop":
            print(json.dumps(client.stop_profile(args.profile_id), indent=2))
            return 0

    if args.command == "account":
        wf = __import__(
            "nextbrowser_harness.workflows.accounts", fromlist=["AccountAutomationWorkflow"]
        ).AccountAutomationWorkflow(harness.config)
        if args.acct_cmd == "add":
            p = wf.register_account(args.account_id, notes=args.notes)
            print(json.dumps(p.__dict__, indent=2))
            return 0
        if args.acct_cmd == "list":
            for p in wf.list_accounts():
                print(f"{p.account_id}  profile={p.browser_profile}  last_run={p.last_run}")
            return 0
        if args.acct_cmd == "run":
            task = args.task
            if args.js:
                task = f"eval:{args.js}" if not args.js.startswith("eval:") else args.js
            out = harness.run_accounts(args.account_id, task, url=args.url)
            print(json.dumps(out, indent=2))
            return 0 if out.get("success") else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
