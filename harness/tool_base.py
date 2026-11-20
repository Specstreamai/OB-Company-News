from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Literal
from urllib.parse import urlparse

from .http_client import now, request_json
from .models import Case, Hit, HttpAudit, SearchResult

RequestBuilder = Callable[[Case], tuple[str, str, dict[str, str], dict[str, Any] | None, dict[str, Any] | None, int]]
Parser = Callable[[Any], list[Hit]]


def require_env(*names: str) -> tuple[str, ...]:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"missing credentials: {', '.join(missing)}")
    return tuple(os.environ[name] for name in names)


def hit(url: Any, title: Any = "", snippet: Any = "", **metadata: Any) -> Hit | None:
    clean_url = str(url or "").strip()
    if not clean_url:
        return None
    return Hit(
        url=clean_url,
        title=str(title or "").strip(),
        snippet=str(snippet or "").strip(),
        metadata=metadata,
    )


def dedupe(rows: list[Hit], limit: int = 10) -> list[Hit]:
    seen: set[str] = set()
    output: list[Hit] = []
    for row in rows:
        parsed = urlparse(row.url)
        key = f"{parsed.netloc.lower().removeprefix('www.')}{parsed.path.rstrip('/')}"
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(row)
        if len(output) == limit:
            break
    return output


def skipped(endpoint: str, case: Case, reason: str) -> SearchResult:
    stamp = now()
    return SearchResult(
        endpoint=endpoint,
        surface="news-index",
        hits=[],
        audit=HttpAudit(
            method="SKIP", url="", request={"case_id": case.id}, response={"skip_reason": reason},
            ok=True, error="", attempts=[], latency_ms=None, started_at=stamp, ended_at=stamp,
        ),
    )


class ProviderAdapter(ABC):
    name: str
    surface: Literal["web-search", "news-index"]
    docs_url: str
    required_env: tuple[str, ...]

    def __init__(self, name: str) -> None:
        self.name = name

    def validate_credentials(self) -> None:
        require_env(*self.required_env)

    @abstractmethod
    def search(self, case: Case) -> SearchResult:
        raise NotImplementedError


@dataclass
class WebAdapter(ProviderAdapter):
    name: str
    docs_url: str
    required_env: tuple[str, ...]
    build: RequestBuilder
    parse: Parser
    surface: str = "web-search"

    def search(self, case: Case) -> SearchResult:
        self.validate_credentials()
        method, url, headers, body, params, timeout = self.build(case)
        audit = request_json(method, url, headers=headers, body=body, params=params, timeout=timeout)
        hits = dedupe(self.parse(audit.response), 10) if audit.ok else []
        return SearchResult(endpoint=self.name, surface="web-search", hits=hits, audit=audit)
