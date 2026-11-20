from __future__ import annotations

import os

from harness.http_client import request_json
from harness.models import Case, Hit, SearchResult
from harness.tool_base import ProviderAdapter, dedupe, hit


class SeltzNewsAdapter(ProviderAdapter):
    surface = "news-index"
    docs_url = "https://docs.seltz.ai/api-reference/search"
    required_env = ("SELTZ_API_KEY",)

    def search(self, case: Case) -> SearchResult:
        self.validate_credentials()
        audit = request_json(
            "POST", "https://api.seltz.ai/v1/search",
            headers={"x-api-key": os.environ["SELTZ_API_KEY"], "Content-Type": "application/json"},
            body={"query": case.question, "max_results": 10, "scope": "news"}, timeout=45,
        )
        rows: list[Hit] = []
        if audit.ok:
            for record in (audit.response or {}).get("documents") or []:
                item = hit(record.get("url"), record.get("title"), record.get("content") or record.get("snippet"))
                if item:
                    rows.append(item)
        return SearchResult(endpoint=self.name, surface=self.surface, hits=dedupe(rows), audit=audit)


def setup(name: str) -> SeltzNewsAdapter:
    return SeltzNewsAdapter(name)

