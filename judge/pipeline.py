from __future__ import annotations

import os
from typing import Any

from harness.models import Case, SearchResult

from .bedrock import model_id
from .extraction import agent_answer, extract, model_only_answer
from .judging import judge_accuracy, judge_recall


def _answer(case: Case, result: SearchResult):
    if result.surface == "baseline":
        return model_only_answer(case)
    hits = result.hits if result.audit.ok else []
    if result.surface == "agent":
        return agent_answer(hits), {"input_tokens": 0, "output_tokens": 0}
    return extract(case, hits)


def evaluate_search_result(case: Case, result: SearchResult) -> dict[str, Any]:
    extracted, extract_tokens = _answer(case, result)
    accuracy, accuracy_tokens = judge_accuracy(case, extracted)
    recall, recall_tokens = judge_recall(case, result.hits if result.audit.ok else [])
    ranks = recall.bearing_ranks
    return {
        "extract": extracted.model_dump(),
        "accuracy": accuracy.model_dump(),
        "answer_recall": {
            **recall.model_dump(),
            "ar1": any(rank <= 1 for rank in ranks),
            "ar5": any(rank <= 5 for rank in ranks),
            "ar10": any(rank <= 10 for rank in ranks),
        },
        "models": {
            "extractor": "none (agent answer graded as written)" if result.surface == "agent"
            else os.getenv("EXTRACT_MODEL", "gpt-5.6-terra"),
            "extractor_reasoning": os.getenv("EXTRACT_REASONING_EFFORT", "medium"),
            "judge": "claude-opus-5",
            "judge_model_id": model_id(),
            "judge_transport": "bedrock-converse",
        },
        "tokens": {"extract": extract_tokens, "accuracy": accuracy_tokens, "answer_recall": recall_tokens},
    }
