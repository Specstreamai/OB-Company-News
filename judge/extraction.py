from __future__ import annotations

from pydantic import BaseModel

from harness.models import Case, ExtractVerdict, Hit
from harness.openai_client import parse_openai

EXTRACT_PROMPT = (
    "Answer only from the provided search snippets. No extra research. "
    "If the snippets do not contain the fact, answer empty. Do not use outside knowledge."
)

MODEL_ONLY_PROMPT = (
    "You have no search results, no browsing and no tools. Answer the question from what you already know. "
    "Reply with the shortest answer that fully answers it: the name, amount, date, place or product asked "
    "for, with no explanation and no hedging. If you are not sure, still give your single most likely "
    "specific answer. Leave the answer empty only if you cannot name anything specific."
)

class ModelOnlyAnswer(BaseModel):
    answer: str = ""


NO_TOKENS = {"input_tokens": 0, "output_tokens": 0}


def extract(case: Case, hits: list[Hit]) -> tuple[ExtractVerdict, dict[str, int]]:
    if not hits:
        return ExtractVerdict(), dict(NO_TOKENS)
    packed = [{"url": row.url, "title": row.title, "snippet": row.snippet} for row in hits[:10]]
    return parse_openai(EXTRACT_PROMPT, {"question": case.question, "results": packed}, ExtractVerdict)


def model_only_answer(case: Case) -> tuple[ExtractVerdict, dict[str, int]]:
    """The baseline: the question alone, no results, no tools."""
    verdict, tokens = parse_openai(MODEL_ONLY_PROMPT, {"question": case.question}, ModelOnlyAnswer)
    return ExtractVerdict(answer=verdict.answer.strip()), tokens


def agent_answer(hits: list[Hit]) -> ExtractVerdict:
    """An agent setup already wrote its answer; it is graded as written, not extracted again
    (a second extraction over a bare answer phrase dropped correct answers at random)."""
    if not hits:
        return ExtractVerdict()
    first = hits[0]
    return ExtractVerdict(answer=str(first.metadata.get("answer") or first.snippet).strip(), cited_url=first.url)
