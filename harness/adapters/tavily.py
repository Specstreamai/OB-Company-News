from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parse(payload: Any) -> list[Hit]:
    return [item for row in (payload or {}).get("results") or [] if (item := hit(row.get("url"), row.get("title"), row.get("content")))]


def setup(name: str, *, depth: str) -> WebAdapter:
    def build(case: Case):
        return "POST", "https://api.tavily.com/search", {"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}", "Content-Type": "application/json"}, {"query": case.question, "search_depth": depth, "max_results": 10}, None, 45
    return WebAdapter(name, "https://docs.tavily.com/documentation/api-reference/endpoint/search", ("TAVILY_API_KEY",), build, _parse)
