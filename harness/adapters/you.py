from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _text(row: dict[str, Any]) -> str:
    contents = row.get("contents") if isinstance(row.get("contents"), dict) else {}
    highlights = contents.get("highlights")
    if not isinstance(highlights, list):
        highlights = row.get("highlights")
    parts: list[str] = []
    for part in highlights if isinstance(highlights, list) else []:
        if isinstance(part, str) and part.strip():
            parts.append(part.strip())
        elif isinstance(part, dict):
            text = str(part.get("text") or part.get("snippet") or part.get("content") or "").strip()
            if text:
                parts.append(text)
    if parts:
        return "\n".join(parts)
    chunks = row.get("snippets") or []
    if isinstance(chunks, list) and chunks:
        return "\n".join(str(part) for part in chunks if part)
    return str(row.get("description") or row.get("snippet") or "")


def _parse(payload: Any) -> list[Hit]:
    results = (payload or {}).get("results") if isinstance(payload, dict) else payload
    rows = list((results or {}).get("web") or []) + list((results or {}).get("news") or []) if isinstance(results, dict) else results or []
    return [item for row in rows if isinstance(row, dict) if (item := hit(row.get("url"), row.get("title"), _text(row)))]


def setup(name: str, *, core: bool) -> WebAdapter:
    def build(case: Case):
        body: dict[str, Any] = {
            "query": case.question, "count": 10,
            "extraction": {"extraction_mode": "highlights"},
        }
        if core:
            body["knowledge"] = "core"
        return "POST", "https://ydc-index.io/v1/search", {"X-API-Key": os.environ["YDC_API_KEY"], "Content-Type": "application/json"}, body, None, 45
    return WebAdapter(name, "https://documentation.you.com/api-reference/search", ("YDC_API_KEY",), build, _parse)

