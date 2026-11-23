from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parse(payload: Any) -> list[Hit]:
    # Keenable returns a short `description` and a longer `snippet`; the snippet is the excerpt.
    return [item for row in (payload or {}).get("results") or [] if isinstance(row, dict)
            if (item := hit(row.get("url"), row.get("title"), row.get("snippet") or row.get("description")))]


def setup(name: str, *, mode: str) -> WebAdapter:
    def build(case: Case):
        return (
            "POST", "https://api.keenable.ai/v1/search",
            {"X-API-Key": os.environ["KEENABLE_API_KEY"], "Content-Type": "application/json"},
            {"query": case.question, "mode": mode, "max_results": 10},
            None, 90 if mode == "pro" else 45,
        )
    return WebAdapter(name, "https://docs.keenable.ai", ("KEENABLE_API_KEY",), build, _parse)
