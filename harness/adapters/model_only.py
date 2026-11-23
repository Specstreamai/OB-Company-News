from __future__ import annotations

from harness.http_client import now
from harness.models import Case, HttpAudit, SearchResult
from harness.tool_base import ProviderAdapter


class ModelOnlyAdapter(ProviderAdapter):
    """Baseline with no search at all: nothing is called, and the judge step asks the extract model to
    answer from what it already knows (judge/extraction.py MODEL_ONLY_PROMPT). It shows how much of the
    benchmark a model answers without any tool."""

    surface = "baseline"
    docs_url = ""
    required_env = ()

    def search(self, case: Case) -> SearchResult:
        stamp = now()
        return SearchResult(
            endpoint=self.name, surface=self.surface, hits=[],
            audit=HttpAudit(method="NONE", url="", request={"case_id": case.id}, response=None, ok=True,
                            latency_ms=None, started_at=stamp, ended_at=stamp),
        )


def setup(name: str) -> ModelOnlyAdapter:
    return ModelOnlyAdapter(name)
