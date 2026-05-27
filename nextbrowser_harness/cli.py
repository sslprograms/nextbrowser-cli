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
    p_init.add_argument("--mlx", action="store_true", help="After init, run Multilogin setup-wizard")

    sub.add_parser("status", help="Show current harness configuration")

    p_scrape = sub.add_parser("scrape", help="Scrape a URL with tier DB + escalation")
    p_scrape.add_argument("url", help="Target URL")
    p_scrape.add_argument("--tier", type=int, choices=[1, 2, 3], help="Force tier (skip escalation)")
    p_scrape.add_argument("--json", action="store_true", help="JSON output for agents")

    p_browse = sub.add_parser("browse", help="Open URL in browser and run actions (tier 2/3)")
    p_browse.add_argument("url", nargs="?", default="https://www.reddit.com", help="Target URL")
    p_browse.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="Force tier; omit to use tier DB recommendation for URL (exec uses tier 2+)",
    )
    p_browse.add_argument("--browser", choices=["native", "multilogin"], default=None,
                          help="Override config browser for this run")
    p_browse.add_argument("--profile", default=None, help="Named Multilogin account (tier 3)")
    p_browse.add_argument("--account", default=None, help="Same as --profile (tier 3 required)")
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
    p_exec.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="Force tier; omit to use tier DB recommendation for URL (min tier 2 for browser)",
    )
    p_exec.add_argument("--browser", choices=["native", "multilogin"], default=None)
    p_exec.add_argument("--profile", default=None, help="Named Multilogin account (tier 3)")
    p_exec.add_argument("--account", default=None, help="Same as --profile (tier 3 required)")
    p_exec.add_argument("--screenshot", default=None)
    p_exec.add_argument("--headless", action="store_true")
    p_exec.add_argument("--js", default=None)
    p_exec.add_argument("--js-file", default=None)
    p_exec.add_argument("--steps-file", default=None)
    p_exec.add_argument(
        "--recipe",
        default=None,
        help="Site recipe id, e.g. reddit.com/login (see nextbrowser recipes list)",
    )
    p_exec.add_argument(
        "--var",
        action="append",
        default=None,
        help="Recipe variable KEY=VALUE (repeatable), e.g. --var username=u --var password=p",
    )
    p_exec.add_argument("--action", action="append", default=None)
    p_exec.add_argument(
        "--element-search",
        choices=["playwright", "indexed", "browser_use"],
        default=None,
        help="Element lookup: indexed (state/click:N for agents) or playwright (CSS)",
    )
    p_exec.add_argument(
        "--keep-open",
        action="store_true",
        default=None,
        help="Leave MLX browser running (default on tier 3)",
    )
    p_exec.add_argument(
        "--close",
        action="store_true",
        help="Stop MLX profile when done (default: keep open on tier 3)",
    )

    p_recipes = sub.add_parser("recipes", help="List built-in site action recipes")
    p_recipes.add_argument("--json", action="store_true", help="JSON output")

    p_tier = sub.add_parser("tier", help="Tier database commands")
    tier_sub = p_tier.add_subparsers(dest="tier_cmd", required=True)
    p_tier_set = tier_sub.add_parser("set", help="Override tier for a domain")
    p_tier_set.add_argument("domain")
    p_tier_set.add_argument("level", type=int, choices=[1, 2, 3])
    p_tier_lookup = tier_sub.add_parser("lookup", help="Lookup recommended tier")
    p_tier_lookup.add_argument("url")

    p_acct = sub.add_parser("account", help="Account automation")
    acct_sub = p_acct.add_subparsers(dest="acct_cmd", required=True)
    p_acct_add = acct_sub.add_parser("add", help="Register named Multilogin account (tier 3)")
    p_acct_add.add_argument("account_id", help="Short name, e.g. reddit_main")
    p_acct_add.add_argument("--notes", default="")
    p_acct_add.add_argument("--display-name", default="", help="MLX profile display name")
    p_acct_add.add_argument("--site", default="", help="Site label, e.g. reddit.com")
    p_acct_add.add_argument(
        "--mlx-profile",
        default=None,
        help="Link existing Multilogin profile UUID (skip --create-mlx)",
    )
    p_acct_add.add_argument(
        "--create-mlx",
        action="store_true",
        help="Create a new Multilogin browser profile and save cookies for reuse",
    )
    p_acct_list = acct_sub.add_parser("list", help="List registered accounts")
    p_acct_list.add_argument("--json", action="store_true", help="JSON output")
    p_acct_run = acct_sub.add_parser("run", help="Run task for an account")
    p_acct_run.add_argument("account_id")
    p_acct_run.add_argument("task")
    p_acct_run.add_argument("--url", default=None)
    p_acct_run.add_argument("--js", default=None, help="Shorthand: eval:<javascript>")
    p_acct_run.add_argument("--json", action="store_true", default=True)

    p_bu = sub.add_parser(
        "browser-use",
        aliases=["bu"],
        help="Connect Multilogin CDP to browser-use CLI (use browser-use skill for UI)",
    )
    bu_sub = p_bu.add_subparsers(dest="bu_cmd", required=True)
    p_bu_connect = bu_sub.add_parser("connect", help="Start MLX profile; save CDP for browser-use")
    p_bu_connect.add_argument("--account", required=True, help="Registered account name")
    p_bu_connect.add_argument("--headless", action="store_true")
    bu_sub.add_parser("doctor", help="Check browser-use CLI + saved CDP session")
    bu_sub.add_parser("session", help="Show saved browser-use CDP session JSON")
    p_bu_run = bu_sub.add_parser("run", help="Run browser-use with --cdp-url from connect")
    p_bu_run.add_argument("bu_args", nargs=argparse.REMAINDER, help="e.g. state, click 5, open URL")
    p_bu_chain = bu_sub.add_parser(
        "chain",
        help="Run multiple browser-use steps in one shell (keeps MLX open)",
    )
    p_bu_chain.add_argument(
        "steps",
        nargs="+",
        help='Steps as quoted strings, e.g. \'open "https://site.com"\' \'state\' \'click 5\'',
    )
    p_bu_disconnect = bu_sub.add_parser(
        "disconnect",
        help="Stop MLX profile when login is done (cookies already saved in profile)",
    )
    p_bu_disconnect.add_argument("--account", required=True)
    p_bu_skill = bu_sub.add_parser(
        "install-skill",
        help="Download official browser-use SKILL.md for your agent",
    )
    p_bu_skill.add_argument(
        "--dest",
        default=None,
        help="Skill dir (default: ~/.cursor/skills/browser-use)",
    )

    p_login = sub.add_parser(
        "login",
        help="One-shot tier-3 login: ensure account, connect MLX, open URL, optional credentials",
    )
    p_login.add_argument("account_id", help="Account name (created automatically if missing)")
    p_login.add_argument("--url", required=True, help="URL to open")
    p_login.add_argument("--username", default=None)
    p_login.add_argument("--password", default=None)
    p_login.add_argument(
        "--username-index", type=int, default=None, help="Element index from state (chain login)"
    )
    p_login.add_argument("--password-index", type=int, default=None)
    p_login.add_argument("--submit-index", type=int, default=None)
    p_login.add_argument("--site", default="", help="Site label for new account")
    p_login.add_argument(
        "--no-create",
        action="store_true",
        help="Fail if account is not already registered (no auto-create)",
    )
    p_login.add_argument(
        "--close",
        action="store_true",
        help="Disconnect MLX when finished (default: keep open for follow-up `ui` commands)",
    )

    p_ui = sub.add_parser(
        "ui",
        help="Browser-use UI commands using the active CDP session (state, click N, type N text, close)",
    )
    ui_sub = p_ui.add_subparsers(dest="ui_cmd", required=True)
    p_ui_situation = ui_sub.add_parser(
        "situation",
        help="Live snapshot: URL, logged-in estimate, agent_gates, element map snippet",
    )
    p_ui_situation.add_argument(
        "--permissive",
        action="store_true",
        help="Do not fail exit code when logged out (default: strict — exit 1 if not logged in)",
    )
    ui_sub.add_parser(
        "require-login",
        help="Fail-closed gate: exit 0 only when live page proves logged in",
    )
    p_ui_verify = ui_sub.add_parser(
        "verify",
        help="Proof submitted text is visible in live state (exit 0 = safe to claim success)",
    )
    p_ui_verify.add_argument(
        "--text",
        required=True,
        help="Exact substring to find in browser-use state (min 8 chars)",
    )
    ui_sub.add_parser("state", help="List clickable elements with indices")
    p_ui_scroll = ui_sub.add_parser("scroll", help="Scroll page (browser-use scroll)")
    p_ui_scroll.add_argument(
        "direction",
        nargs="?",
        default="down",
        choices=["down", "up"],
        help="Scroll direction (default: down)",
    )
    p_ui_scroll.add_argument(
        "--pages",
        type=float,
        default=1.0,
        help="Number of pages to scroll (e.g. 0.5, 1, 2)",
    )
    p_ui_open = ui_sub.add_parser("open", help="Navigate to URL")
    p_ui_open.add_argument("url")
    p_ui_click = ui_sub.add_parser("click", help="Click by index")
    p_ui_click.add_argument("index")
    p_ui_type = ui_sub.add_parser("type", help="Type into element by index")
    p_ui_type.add_argument("index")
    p_ui_type.add_argument("text")
    p_ui_input = ui_sub.add_parser("input", help="Alias of `type`")
    p_ui_input.add_argument("index")
    p_ui_input.add_argument("text")
    p_ui_keys = ui_sub.add_parser("keys", help="Send keys (Enter, Control+a, ...)")
    p_ui_keys.add_argument("combo")
    p_ui_eval = ui_sub.add_parser("eval", help="Run JavaScript")
    p_ui_eval.add_argument("code")
    p_ui_screenshot = ui_sub.add_parser("screenshot", help="Take screenshot")
    p_ui_screenshot.add_argument("path", nargs="?", default=None)
    p_ui_chain = ui_sub.add_parser(
        "chain",
        help="Run multiple browser-use steps in one shell (keeps browser open)",
    )
    p_ui_chain.add_argument("steps", nargs="+")
    p_ui_raw = ui_sub.add_parser("run", help="Pass arbitrary args to browser-use")
    p_ui_raw.add_argument("bu_args", nargs=argparse.REMAINDER)
    ui_sub.add_parser("close", help="Disconnect browser-use and stop MLX profile (end of task)")

    p_agent_run = sub.add_parser(
        "agent-run",
        help="Run the AI browser agent over a Multilogin CDP session (browser-use + LLM)",
    )
    p_agent_run.add_argument("task", help="Task description for the AI agent")
    p_agent_run.add_argument(
        "--account", default=None, help="Multilogin account name (uses existing session if omitted)"
    )
    p_agent_run.add_argument("--url", default=None, help="URL to navigate to before starting the task")
    p_agent_run.add_argument(
        "--model", default=None,
        help="LLM model name (default: gpt-4o or NEXTBROWSER_LLM_MODEL env)",
    )
    p_agent_run.add_argument("--max-steps", type=int, default=100, help="Max agent steps (default: 100)")
    p_agent_run.add_argument("--captcha", action="store_true", help="Enable captcha solving guidance")
    p_agent_run.add_argument("--approval", action="store_true", help="Enable content approval mode")
    p_agent_run.add_argument("--headless", action="store_true", help="Run MLX browser headless")
    p_agent_run.add_argument(
        "--keep-open",
        action="store_true",
        help="Leave Multilogin profile running after task (default: stop profile when done)",
    )

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
    p_mlx_fix = mlx_sub.add_parser(
        "fix-linux-launcher",
        help="Fix /opt/mlx/usr/bin/mlx when it points at wrong agent.bin (Linux .deb)",
    )
    p_mlx_fix.add_argument("--dry-run", action="store_true", help="Show fix without writing")
    mlx_sub.add_parser("print-env", help="Print .env lines for MLX (no secrets)")
    p_mlx_setup = mlx_sub.add_parser("setup", help="How to configure MLX (platform-specific)")
    p_mlx_wizard = mlx_sub.add_parser(
        "setup-wizard",
        help="Interactive MLX setup (email in .env, password never saved)",
    )
    p_mlx_wizard.add_argument("--env-file", default=".env", help="Path to .env file")
    p_mlx_wizard.add_argument("--profile-key", default="default", help="MULTILOGIN_PROFILE_<KEY> name")
    p_mlx_wizard.add_argument("--skip-signin", action="store_true", help="Use saved token only")
    p_mlx_wizard.add_argument("--non-interactive", action="store_true", help="Auto-pick when only one choice")
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
        p_inst.add_argument(
            "--with-browser-use",
            action="store_true",
            help="Also install official browser-use skill (recommended for UI automation)",
        )
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
        if args.env:
            cfg = onboard_from_env()
        elif getattr(args, "mlx", False):
            cfg = onboard_interactive(run_mlx_wizard=True)
        else:
            cfg = onboard_interactive()
        print(f"Ready. Config: {cfg.save()}")
        return 0

    harness = Harness()

    if args.command == "status":
        print(json.dumps(harness.status(), indent=2))
        return 0

    def _recipe_vars(ns) -> dict[str, str]:
        out: dict[str, str] = {}
        for raw in getattr(ns, "var", None) or []:
            if "=" in raw:
                k, _, v = raw.partition("=")
                out[k.strip()] = v.strip()
        return out

    def _exec_kwargs(ns):
        actions = list(ns.action or [])
        recipe = getattr(ns, "recipe", None)
        if not actions and not ns.js and not ns.js_file and not ns.steps_file and not recipe:
            actions = ["goto", "wait_load", "title", "scroll", "final_url"]
        account = getattr(ns, "account", None) or ns.profile
        return dict(
            tier=ns.tier,
            profile_id=account,
            screenshot=ns.screenshot,
            headless=True if ns.headless else None,
            actions=actions or None,
            steps_file=ns.steps_file,
            js=ns.js,
            js_file=ns.js_file,
            keep_open=False if getattr(ns, "close", False) else getattr(ns, "keep_open", None),
            recipe=recipe,
            recipe_vars=_recipe_vars(ns) or None,
            element_search=getattr(ns, "element_search", None),
        )

    if args.command == "browse":
        if args.browser:
            harness.config.browser = args.browser  # type: ignore[assignment]
        kw = _exec_kwargs(args)
        if not args.action and not args.js and not args.js_file and not args.steps_file:
            kw["actions"] = ["goto", "wait_load", "title", "scroll", "reddit_feed_check", "final_url"]
        account = getattr(args, "account", None) or args.profile
        out = harness.browse(args.url, profile_id=account, **kw)
        print(json.dumps(out, indent=2))
        return 0 if out.get("success") else 1

    if args.command == "recipes":
        from nextbrowser_harness.site_recipes import list_recipes

        items = list_recipes()
        if getattr(args, "json", False):
            print(json.dumps(items, indent=2))
        else:
            for r in items:
                print(f"  {r['id']}")
        return 0

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
        from nextbrowser_harness.integrations.multilogin.recommend import multilogin_recommendation

        if args.tier_cmd == "set":
            harness.set_tier_override(args.domain, args.level)
            print(f"Override: {args.domain} -> tier {args.level}")
            return 0
        rec = harness.tiers.recommended_tier(args.url)
        mlx = multilogin_recommendation(harness.config, args.url, tier=int(rec.tier))
        payload = {"domain": rec.domain, "tier": rec.tier, "source": rec.source}
        if mlx:
            payload["multilogin_recommendation"] = mlx
        print(json.dumps(payload, indent=2))
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
            if getattr(args, "with_browser_use", False):
                from nextbrowser_harness.integrations.browser_use.bridge import install_browser_use_skill

                bu_path = install_browser_use_skill()
                print(f"\nInstalled browser-use skill: {bu_path}")
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
        if args.mlx_cmd == "fix-linux-launcher":
            from nextbrowser_harness.integrations.multilogin.platform_hints import (
                fix_linux_mlx_launcher_script,
            )

            result = fix_linux_mlx_launcher_script(apply=not args.dry_run)
            print(json.dumps(result, indent=2))
            return 0 if result.get("applied") or not result.get("wrong_path_in_script") else 1
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
                mlx_setup_wizard_command,
                mlx_start_desktop_hint,
            )
            import platform

            sysname = platform.system().lower()
            script = mlx_setup_script_path()
            print(f"Platform: {sysname}")
            print(f"Recommended: {mlx_setup_wizard_command()}")
            print(f"Guided script: {mlx_setup_script_hint()}")
            if not script.is_file():
                print(f"  (script missing at {script})")
            print(f"\n{mlx_start_desktop_hint()}")
            print("\nManual CLI flow:")
            print("  nextbrowser multilogin setup-wizard")
            print("  nextbrowser multilogin doctor")
            print("\nAgents: do NOT edit ~/.nextbrowser/multilogin_tokens.yaml manually.")
            return 0
        if args.mlx_cmd == "setup-wizard":
            from pathlib import Path

            from nextbrowser_harness.integrations.multilogin.setup_wizard import (
                SetupWizardOptions,
                run_setup_wizard,
            )

            opts = SetupWizardOptions(
                env_file=Path(args.env_file),
                profile_key=args.profile_key,
                skip_signin=args.skip_signin,
                non_interactive=args.non_interactive,
            )
            try:
                result = run_setup_wizard(options=opts)
            except Exception as e:
                print(str(e))
                return 1
            return 0 if result.get("doctor_ok") else 1
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
            try:
                p = wf.register_account(
                    args.account_id,
                    notes=args.notes,
                    display_name=args.display_name,
                    site=args.site,
                    mlx_profile_id=args.mlx_profile or "",
                    create_mlx=args.create_mlx,
                )
            except Exception as e:
                from nextbrowser_harness.accounts.registry import Tier3AccountError

                if isinstance(e, Tier3AccountError):
                    print(json.dumps({"error": str(e), "agent_prompt": e.agent_prompt, "code": e.code}, indent=2))
                    return 1
                raise
            out = p.to_dict()
            out["mlx_saved"] = True
            out["hint"] = (
                f"Profile {p.mlx_profile_id} should appear in Multilogin app "
                f"(folder {p.mlx_folder_id}). Then: nextbrowser browser-use connect --account {p.account_id}"
            )
            print(json.dumps(out, indent=2))
            return 0
        if args.acct_cmd == "list":
            accounts = wf.list_accounts()
            if args.json:
                print(json.dumps([a.to_dict() for a in accounts], indent=2))
            else:
                for p in accounts:
                    login = "logged_in" if p.logged_in else "needs_login"
                    mlx = p.mlx_profile_id
                    mlx_short = f"{mlx[:8]}..." if len(mlx) > 8 else (mlx or "-")
                    print(
                        f"{p.account_id}  mlx={mlx_short}  "
                        f"site={p.site or '-'}  {login}  last_run={p.last_run}"
                    )
            return 0
        if args.acct_cmd == "run":
            task = args.task
            if args.js:
                task = f"eval:{args.js}" if not args.js.startswith("eval:") else args.js
            out = harness.run_accounts(args.account_id, task, url=args.url)
            print(json.dumps(out, indent=2))
            return 0 if out.get("success") else 1

    if args.command == "agent-run":
        from nextbrowser_harness.agent.runner import run_agent

        res = run_agent(
            harness.config,
            args.task,
            account_id=args.account,
            model=args.model,
            url=args.url,
            enable_captcha=args.captcha,
            enable_approval=args.approval,
            max_steps=args.max_steps,
            headless=args.headless,
            keep_open=args.keep_open,
        )
        print(json.dumps(res.to_dict(), indent=2))
        return 0 if res.success else 1

    if args.command == "login":
        from nextbrowser_harness.workflows.login import login as login_workflow

        res = login_workflow(
            harness.config,
            args.account_id,
            url=args.url,
            username=args.username,
            password=args.password,
            username_index=args.username_index,
            password_index=args.password_index,
            submit_index=args.submit_index,
            site=args.site,
            create_if_missing=not args.no_create,
            keep_open=not args.close,
        )
        print(json.dumps(res.to_dict(), indent=2))
        return 0 if res.success else 1

    if args.command == "ui":
        from nextbrowser_harness.workflows import ui as ui_workflow

        cmd = args.ui_cmd
        if cmd == "scroll":
            res = ui_workflow.scroll(
                harness.config,
                args.direction,
                args.pages,
            )
            print(json.dumps(res.to_dict(), indent=2))
            return 0 if res.success else 1
        if cmd == "situation":
            out = ui_workflow.situation(
                harness.config,
                strict=not args.permissive,
            )
            print(json.dumps(out, indent=2))
            if not out.get("connected"):
                return 1
            if not out.get("browser_use_ok"):
                return 1
            if out.get("cli_should_exit_nonzero"):
                return 1
            return 0
        if cmd == "require-login":
            out = ui_workflow.require_login(harness.config)
            print(json.dumps(out, indent=2))
            if not out.get("connected"):
                return 1
            return 0 if out.get("require_login_ok") else 1
        if cmd == "verify":
            out = ui_workflow.verify_text(harness.config, args.text)
            print(json.dumps(out, indent=2))
            return 0 if out.get("verified") else 1
        if cmd == "close":
            out = ui_workflow.close(harness.config)
            print(json.dumps(out, indent=2))
            return 0 if out.get("success") else 1
        if cmd == "chain":
            res = ui_workflow.chain(harness.config, args.steps)
            print(json.dumps(res.to_dict(), indent=2))
            return 0 if res.success else 1
        if cmd == "run":
            bu_args = [a for a in (args.bu_args or []) if a != "--"]
            if not bu_args:
                print(json.dumps({"success": False, "error": "no args"}, indent=2))
                return 1
            res = ui_workflow.run(harness.config, bu_args[0], args=bu_args[1:])
            print(json.dumps(res.to_dict(), indent=2))
            return 0 if res.success else 1
        ui_args: list[str] = []
        if cmd in ("click", "input", "type"):
            ui_args.append(str(args.index))
            if cmd in ("input", "type"):
                ui_args.append(args.text)
        elif cmd == "open":
            ui_args.append(args.url)
        elif cmd == "keys":
            ui_args.append(args.combo)
        elif cmd == "eval":
            ui_args.append(args.code)
        elif cmd == "screenshot" and args.path:
            ui_args.append(args.path)
        res = ui_workflow.run(harness.config, cmd, args=ui_args)
        print(json.dumps(res.to_dict(), indent=2))
        return 0 if res.success else 1

    if args.command in ("browser-use", "bu"):
        from nextbrowser_harness.accounts.registry import Tier3AccountError
        from nextbrowser_harness.integrations.browser_use.bridge import (
            browser_use_doctor,
            connect_account,
            disconnect_account,
            install_browser_use_skill,
            load_session,
            run_browser_use,
            run_browser_use_chain,
        )

        if args.bu_cmd == "doctor":
            print(json.dumps(browser_use_doctor(), indent=2))
            return 0
        if args.bu_cmd == "session":
            sess = load_session()
            print(json.dumps(sess or {}, indent=2))
            return 0 if sess else 1
        if args.bu_cmd == "install-skill":
            from pathlib import Path

            dest = Path(args.dest).expanduser() if args.dest else None
            path = install_browser_use_skill(dest)
            print(f"Installed browser-use skill: {path}")
            print("Start a new agent session. Use browser-use skill for state/click/input.")
            return 0
        if args.bu_cmd == "connect":
            try:
                out = connect_account(
                    harness.config,
                    args.account,
                    headless=args.headless,
                )
            except (Tier3AccountError, Exception) as e:
                payload = {"success": False, "error": str(e)}
                if isinstance(e, Tier3AccountError):
                    payload["agent_prompt"] = e.agent_prompt
                    payload["code"] = e.code
                print(json.dumps(payload, indent=2))
                return 1
            print(json.dumps(out, indent=2))
            return 0
        if args.bu_cmd == "run":
            bu_args = [a for a in (args.bu_args or []) if a != "--"]
            if not bu_args:
                print("Usage: nextbrowser browser-use run state")
                return 1
            try:
                proc = run_browser_use(bu_args)
            except (Tier3AccountError, FileNotFoundError) as e:
                payload = {"success": False, "error": str(e)}
                if isinstance(e, Tier3AccountError):
                    payload["agent_prompt"] = e.agent_prompt
                print(json.dumps(payload, indent=2))
                return 1
            return proc.returncode
        if args.bu_cmd == "chain":
            try:
                proc = run_browser_use_chain(args.steps)
            except (Tier3AccountError, FileNotFoundError) as e:
                payload = {"success": False, "error": str(e)}
                if isinstance(e, Tier3AccountError):
                    payload["agent_prompt"] = e.agent_prompt
                print(json.dumps(payload, indent=2))
                return 1
            return proc.returncode
        if args.bu_cmd == "disconnect":
            out = disconnect_account(harness.config, args.account)
            print(json.dumps(out, indent=2))
            return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
