from __future__ import annotations

import os
from typing import Any

from harness.models import Case, Hit
from harness.tool_base import WebAdapter, hit


def _parse(payload: Any) -> list[Hit]:
    output: list[Hit] = []
    for row in (payload or {}).get("results") or []:
        highlights = row.get("highlights") or []
        item = hit(row.get("url"), row.get("title"), " ".join(highlights) or row.get("text"))
        if item:
            output.append(item)
    return output


def setup(name: str, *, search_type: str) -> WebAdapter:
    def build(case: Case):
        return (
            "POST", "https://api.exa.ai/search",
            {"x-api-key": os.environ["EXA_API_KEY"], "Content-Type": "application/json"},
            {"query": case.question, "type": search_type, "numResults": 10, "contents": {"highlights": True}},
            None, 45,
        )
    return WebAdapter(name, "https://docs.exa.ai/reference/search", ("EXA_API_KEY",), build, _parse)

