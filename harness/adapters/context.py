from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parser(use_highlights: bool):
    def parse(payload: Any) -> list[Hit]:
        output: list[Hit] = []
        for row in (payload or {}).get("results") or []:
            snippet = ""
            if use_highlights:
                highlights = row.get("highlights") or {}
                parts = highlights.get("highlights") or []
                if highlights.get("code") == "SUCCESS":
                    snippet = "\n".join(part for part in parts if isinstance(part, str))
            item = hit(row.get("url"), row.get("title"), snippet.strip() or row.get("description") or "")
            if item:
                output.append(item)
        return output
    return parse


def setup(name: str, *, highlights: bool = True) -> WebAdapter:
    def build(case: Case):
        return (
            "POST", "https://api.context.dev/v1/web/search",
            {"Authorization": f"Bearer {os.environ['CONTEXT_API_KEY']}", "Content-Type": "application/json"},
            {"query": case.question, "numResults": 10, "highlightsOptions": {"enabled": highlights}},
            None, 90,
        )
    return WebAdapter(
        name, "https://docs.context.dev/api-reference/web-scraping/search",
        ("CONTEXT_API_KEY",), build, _parser(highlights),
    )
