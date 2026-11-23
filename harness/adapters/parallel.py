from __future__ import annotations

import os
import threading
from typing import Any

from pydantic import BaseModel

from harness.models import Case, Hit
from harness.openai_client import parse_openai
from harness.tool_base import WebAdapter, hit

# Parallel's Search API takes an objective plus 2-3 short keyword search_queries; sending the raw question
# as the only query is the pattern its docs warn against, and an objective alone is rejected (HTTP 422).
# Its docs say a pipeline with no model in the loop should add one model call to write them, so each
# question gets one query plan from the extractor model, shared by every Parallel mode in the run.
QUERY_PROMPT = (
    "You write search requests for the Parallel Search API. Given one question, "
    "return an objective and 2-3 search_queries. The objective is a self-contained "
    "natural-language description of what is needed, with enough context to "
    "understand the intent; it may restate the question. Each search query is a "
    "concise keyword query of 3-6 words (company name plus the key terms). Do not "
    "answer the question and do not add facts that are not in it."
)


class QueryPlan(BaseModel):
    objective: str
    search_queries: list[str]


_CACHE: dict[str, tuple[dict[str, Any], dict[str, int]]] = {}
_LOCK = threading.Lock()
_INFLIGHT: dict[str, threading.Lock] = {}


def plan_queries(question: str) -> tuple[dict[str, Any], dict[str, int]]:
    """One model call per question; every Parallel mode waits for and reuses the same plan."""
    with _LOCK:
        gate = _INFLIGHT.setdefault(question, threading.Lock())
    with gate:
        with _LOCK:
            cached = _CACHE.get(question)
        if cached is not None:
            return cached
        parsed, tokens = parse_openai(QUERY_PROMPT, {"question": question}, QueryPlan)
        queries = [q.strip()[:500] for q in parsed.search_queries if isinstance(q, str) and q.strip()][:3]
        plan = {"objective": (parsed.objective or "").strip() or question,
                "search_queries": queries or [question[:500]],
                "model": os.getenv("EXTRACT_MODEL", "gpt-5.6-terra"), "tokens": tokens}
        with _LOCK:
            _CACHE[question] = (plan, tokens)
        return plan, tokens


def _parse(payload: Any) -> list[Hit]:
    output: list[Hit] = []
    for row in (payload or {}).get("results") or []:
        item = hit(row.get("url"), row.get("title"), "\n".join(row.get("excerpts") or []))
        if item:
            output.append(item)
    return output


def setup(name: str, *, mode: str) -> WebAdapter:
    def build(case: Case):
        plan, _ = plan_queries(case.question)
        return (
            "POST", "https://api.parallel.ai/v1/search",
            {"x-api-key": os.environ["PARALLEL_API_KEY"], "Content-Type": "application/json"},
            {"objective": plan["objective"], "search_queries": plan["search_queries"], "mode": mode,
             "advanced_settings": {"max_results": 10}},
            None, 90 if mode in {"basic", "advanced"} else 60,
        )
    return WebAdapter(name, "https://docs.parallel.ai/api-reference/search", ("PARALLEL_API_KEY",), build, _parse)
