from __future__ import annotations

import os
import time
from collections import Counter
from typing import Any

import requests

from harness.http_client import now, redact_headers
from harness.models import Attempt, Case, Hit, HttpAudit, SearchResult
from harness.tool_base import ProviderAdapter, WebAdapter, hit

AGENT_URL = "https://api.firecrawl.dev/v2/agent"
AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "description": "The specific fact that answers the question, as short as possible. Empty string if not found."},
        "source_url": {"type": "string", "description": "URL of the page or data record the answer came from."},
    },
    "required": ["answer", "source_url"],
}


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


def agent_hits(status: dict[str, Any], job_id: str | None) -> list[Hit]:
    """The one hit for a finished agent job: the agent's answer, or [] when it found none.

    The agent already reads the sources and writes the answer, so the judge grades this answer
    directly instead of running the snippet extractor over it (see judge/pipeline.py).
    """
    data = status.get("data") or {}
    if isinstance(data, dict) and "answer" not in data and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict):
            data = inner
    answer = str((data or {}).get("answer") or "").strip()
    source = str((data or {}).get("source_url") or "").strip()
    if not answer:
        return []
    url = source if source.startswith("http") else f"{AGENT_URL}/{job_id}"
    return [Hit(url=url, title="Firecrawl Agent answer", snippet=answer[:2000],
                metadata={"kind": "agent_answer", "answer": answer, "message": str(status.get("message") or "").strip()})]


def trace_summary(trace: Any) -> dict[str, Any]:
    events = (trace or {}).get("events") or []
    names = Counter(e.get("toolName") or "?" for e in events if e.get("type") == "tool_call.started")
    return {"tool_calls": dict(names), "total_tool_calls": sum(names.values()), "events": len(events)}


class FirecrawlAgentAdapter(ProviderAdapter):
    """Firecrawl Agent with Alexandria data toolkits (Apollo by default).

    Not a single search call: the agent researches the question, may search the web, fetch pages and
    call the toolkit's data tools, and returns one answer. Start the job, then poll until it finishes.
    """

    surface = "agent"
    docs_url = "https://docs.firecrawl.dev/features/agent"
    required_env = ("FIRECRAWL_API_KEY",)

    def __init__(self, name: str, *, model: str, effort: str, max_credits: int, toolkits: list[str],
                 max_toolkit_calls: int, timeout_s: int = 600, poll_s: int = 5) -> None:
        super().__init__(name)
        self.model, self.effort, self.max_credits = model, effort, max_credits
        self.toolkits, self.max_toolkit_calls = list(toolkits), max_toolkit_calls
        self.timeout_s, self.poll_s = timeout_s, poll_s

    def body(self, case: Case) -> dict[str, Any]:
        return {
            "prompt": case.question, "model": self.model, "effort": self.effort, "maxCredits": self.max_credits,
            "schema": AGENT_SCHEMA,
            "exchange": {"enabled": True, "toolkits": self.toolkits, "maxCalls": self.max_toolkit_calls},
        }

    def search(self, case: Case) -> SearchResult:
        self.validate_credentials()
        headers = {"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}", "Content-Type": "application/json"}
        body = self.body(case)
        started, started_at = time.perf_counter(), now()
        attempts: list[Attempt] = []
        status: dict[str, Any] = {}
        status_code: int | None = None
        error, job_id, trace = "", None, None
        try:
            response = requests.post(AGENT_URL, headers=headers, json=body, timeout=60)
            status_code = response.status_code
            start = response.json()
            attempts.append(Attempt(number=1, status_code=status_code, ok=response.ok,
                                    latency_ms=round((time.perf_counter() - started) * 1000)))
            job_id = start.get("id") or start.get("jobId")
            if not response.ok or not job_id:
                error, status = f"HTTP {status_code} agent start: {str(start)[:300]}", start
            else:
                while time.perf_counter() - started < self.timeout_s:
                    status = requests.get(f"{AGENT_URL}/{job_id}", headers=headers, timeout=60).json()
                    if status.get("status") in {"completed", "failed", "cancelled"}:
                        break
                    time.sleep(self.poll_s)
                if status.get("status") != "completed":
                    error = (f"agent {status.get('status') or 'timed out'}: "
                             f"{status.get('stopReason') or status.get('error') or 'no result'}")
                try:
                    trace = trace_summary(requests.get(f"{AGENT_URL}/{job_id}/trace", headers=headers, timeout=60).json())
                except Exception as exc:  # noqa: BLE001
                    trace = {"error": f"{type(exc).__name__}: {exc}"}
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
        audit = HttpAudit(
            method="POST", url=AGENT_URL,
            request={"headers": redact_headers(headers), "body": body, "params": None,
                     "job_id": job_id, "trace_summary": trace, "credits_used": status.get("creditsUsed")},
            response=status, ok=not error, status_code=status_code, error=error, attempts=attempts,
            latency_ms=round((time.perf_counter() - started) * 1000), started_at=started_at, ended_at=now(),
        )
        hits = agent_hits(status, job_id) if audit.ok else []
        return SearchResult(endpoint=self.name, surface=self.surface, hits=hits, audit=audit)


def setup(name: str, *, kind: str = "search", **settings: Any) -> ProviderAdapter:
    if kind == "agent":
        return FirecrawlAgentAdapter(name, **settings)
    return WebAdapter(name, "https://docs.firecrawl.dev/api-reference/endpoint/search", ("FIRECRAWL_API_KEY",), _build, _parse)
