from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml

from nextbrowser_harness.config import TierLevel

TierLevel = Literal[1, 2, 3]
BUNDLED_DB = Path(__file__).with_name("database.json")


@dataclass
class TierResult:
    domain: str
    tier: TierLevel
    source: str  # database | cache | override | default


class TierResolver:
    """Curated tier database + local cache + user overrides."""

    def __init__(self, cache_path: Path, overrides: dict[str, int] | None = None):
        self.cache_path = Path(cache_path)
        self.overrides = self._load_overrides_from_cache()
        if overrides:
            self.overrides.update({k.lower(): int(v) for k, v in overrides.items()})
        self._db = self._load_database()
        self._cache = self._load_cache()

    def _load_database(self) -> dict:
        with open(BUNDLED_DB, encoding="utf-8") as f:
            return json.load(f)

    def _load_cache(self) -> dict[str, int]:
        if not self.cache_path.exists():
            return {}
        data = yaml.safe_load(self.cache_path.read_text(encoding="utf-8")) or {}
        return {str(k).lower(): int(v) for k, v in (data.get("domains") or {}).items()}

    def _load_overrides_from_cache(self) -> dict[str, int]:
        if not self.cache_path.exists():
            return {}
        data = yaml.safe_load(self.cache_path.read_text(encoding="utf-8")) or {}
        return {str(k).lower(): int(v) for k, v in (data.get("overrides") or {}).items()}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"domains": self._cache, "overrides": self.overrides}
        self.cache_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")

    @staticmethod
    def domain_from_url(url: str) -> str:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return (parsed.hostname or url).lower()

    def _pattern_tier(self, domain: str) -> int | None:
        for entry in self._db.get("patterns", []):
            pattern = entry.get("match", "")
            if fnmatch.fnmatch(domain, pattern) or fnmatch.fnmatch(f"*.{domain}", pattern):
                return int(entry["tier"])
        return None

    def recommended_tier(self, url: str) -> TierResult:
        domain = self.domain_from_url(url)
        if domain in self.overrides:
            t = self.overrides[domain]
            return TierResult(domain, t, "override")  # type: ignore[arg-type]
        if domain in self._cache:
            return TierResult(domain, self._cache[domain], "cache")  # type: ignore[arg-type]
        domains = self._db.get("domains", {})
        if domain in domains:
            return TierResult(domain, int(domains[domain]), "database")  # type: ignore[arg-type]
        pat = self._pattern_tier(domain)
        if pat:
            return TierResult(domain, pat, "database")  # type: ignore[arg-type]
        return TierResult(domain, 1, "default")  # type: ignore[arg-type]

    def remember_success(self, domain: str, tier: TierLevel) -> None:
        self._cache[domain.lower()] = int(tier)
        self._save_cache()

    def escalation_order(self, start: TierLevel) -> list[TierLevel]:
        order: list[TierLevel] = [1, 2, 3]
        idx = order.index(start)
        return order[idx:]
