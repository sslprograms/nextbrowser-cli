from __future__ import annotations

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.automation.base import AutomationResult
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.layers.proxy import CustomProxyLayer, NodeMavenProxyLayer


class PlaywrightAutomationLayer:
    """Bring-your-own style automation using Playwright directly."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.browser_layer = browser_layer_for(config)

    @classmethod
    def from_config(cls, config: HarnessConfig) -> PlaywrightAutomationLayer:
        return cls(config)

    def _proxy(self):
        if self.config.proxy == "nodemaven":
            return NodeMavenProxyLayer.from_config(self.config)
        if self.config.custom_proxies:
            return CustomProxyLayer.from_config(self.config)
        return None

    def run_task(self, task: str, *, url: str | None = None, profile_id: str = "default") -> AutomationResult:
        from nextbrowser_harness.browser_actions import ActionSpec, run_actions

        session = self.browser_layer.ensure_profile(profile_id)
        proxy_layer = self._proxy()
        proxy_ep = proxy_layer.get_endpoint(profile_id) if proxy_layer else None
        ctx = self.browser_layer.launch_context(
            session, proxy=proxy_ep, headless=self.config.headless
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            t = (task or "").strip()
            if t.startswith(("eval:", "js:")):
                specs = [ActionSpec.parse(f"eval:{t.split(':', 1)[1]}")]
                if url:
                    specs.insert(0, ActionSpec.parse(f"goto:{url}"))
                results = run_actions(page, specs, default_url=url or "about:blank")
                eval_out = next((r.detail for r in results if r.name == "eval" and r.ok), "")
                return AutomationResult(
                    success=all(r.ok for r in results),
                    output=f"task={task!r}\nurl={page.url}\nscript_result={eval_out}",
                    error=None if all(r.ok for r in results) else "; ".join(
                        f"{r.name}:{r.detail}" for r in results if not r.ok
                    ),
                )
            if t.startswith("jsfile:"):
                specs = [ActionSpec.parse(t)]
                if url:
                    specs.insert(0, ActionSpec.parse(f"goto:{url}"))
                results = run_actions(page, specs, default_url=url or "about:blank")
                out = next((r.detail for r in results if r.name == "jsfile" and r.ok), "")
                return AutomationResult(
                    success=all(r.ok for r in results),
                    output=f"task={task!r}\nurl={page.url}\nscript_result={out}",
                    error=None if all(r.ok for r in results) else "; ".join(
                        f"{r.name}:{r.detail}" for r in results if not r.ok
                    ),
                )
            if url:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            title = page.title()
            text = page.inner_text("body")[:2000] if page.url else ""
            return AutomationResult(
                success=True,
                output=f"task={task!r}\nurl={page.url}\ntitle={title}\npreview={text[:500]}...",
            )
        except Exception as e:
            return AutomationResult(success=False, output="", error=str(e))
        finally:
            if hasattr(ctx, "_harness_mlx"):
                ctx._harness_mlx.close()
            elif hasattr(ctx, "_harness_uc"):
                ctx._harness_uc.close()
            else:
                ctx.close()
                if hasattr(ctx, "_harness_playwright"):
                    ctx._harness_playwright.stop()
