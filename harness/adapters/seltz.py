from __future__ import annotations

import os
from typing import Any

from harness.http_client import request_json
from harness.models import Case, Hit, SearchResult
from harness.tool_base import ProviderAdapter, dedupe, hit


def _text(record: dict[str, Any]) -> str:
    text = record.get("content") or record.get("snippet")
    if not text and isinstance(record.get("snippets"), list):
        # fields.snippets=true: the highest-scoring passages, in document order, each {"text": ...}.
        text = "\n".join(
            (part.get("text") if isinstance(part, dict) else part) or ""
            for part in record["snippets"] if isinstance(part, (dict, str))
        ).strip()
    return text or ""


def _parse(payload: Any) -> list[Hit]:
    return [item for record in (payload or {}).get("documents") or [] if isinstance(record, dict)
            if (item := hit(record.get("url"), record.get("title"), _text(record)))]


class SeltzAdapter(ProviderAdapter):
    docs_url = "https://docs.seltz.ai/api-reference/search"
    required_env = ("SELTZ_API_KEY",)

    def __init__(self, name: str, *, scope: str = "news", snippets: bool = False) -> None:
        super().__init__(name)
        self.scope, self.snippets = scope, snippets
        self.surface = "news-index" if scope == "news" else "web-search"

    def body(self, case: Case) -> dict[str, Any]:
        body: dict[str, Any] = {"query": case.question, "max_results": 10, "scope": self.scope}
        if self.snippets:
            body["fields"] = {"snippets": True}
        return body

    def search(self, case: Case) -> SearchResult:
        self.validate_credentials()
        audit = request_json(
            "POST", "https://api.seltz.ai/v1/search",
            headers={"x-api-key": os.environ["SELTZ_API_KEY"], "Content-Type": "application/json"},
            body=self.body(case), timeout=45,
        )
        rows = dedupe(_parse(audit.response)) if audit.ok else []
        return SearchResult(endpoint=self.name, surface=self.surface, hits=rows, audit=audit)


def setup(name: str, **settings: Any) -> SeltzAdapter:
    return SeltzAdapter(name, **settings)
