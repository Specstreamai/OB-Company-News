from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parse(payload: Any) -> list[Hit]:
    data = (payload or {}).get("data") if isinstance(payload, dict) else payload
    rows = data.get("web") or data.get("results") or [] if isinstance(data, dict) else data or []
    return [item for row in rows if (item := hit(row.get("url") or row.get("link"), row.get("title"), row.get("description") or row.get("snippet")))]


def _build(case: Case):
    return (
        "POST", "https://api.firecrawl.dev/v2/search",
        {"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}", "Content-Type": "application/json"},
        {"query": case.question, "limit": 10}, None, 60,
    )


def setup(name: str) -> WebAdapter:
    return WebAdapter(name, "https://docs.firecrawl.dev/api-reference/endpoint/search", ("FIRECRAWL_API_KEY",), _build, _parse)

