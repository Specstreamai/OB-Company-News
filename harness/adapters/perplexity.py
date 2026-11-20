from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parse(payload: Any) -> list[Hit]:
    return [item for row in (payload or {}).get("results") or [] if (item := hit(row.get("url"), row.get("title"), row.get("snippet") or row.get("content")))]


def _build(case: Case):
    return "POST", "https://api.perplexity.ai/search", {"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}", "Content-Type": "application/json"}, {"query": case.question, "max_results": 10, "search_context_size": "low"}, None, 45


def setup(name: str) -> WebAdapter:
    return WebAdapter(name, "https://docs.perplexity.ai/api-reference/search-post", ("PERPLEXITY_API_KEY",), _build, _parse)

