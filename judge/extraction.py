from __future__ import annotations

from harness.models import Case, ExtractVerdict, Hit
from harness.openai_client import parse_openai

EXTRACT_PROMPT = (
    "Answer only from the provided search snippets. No extra research. "
    "If the snippets do not contain the fact, answer empty. Do not use outside knowledge."
)


def extract(case: Case, hits: list[Hit]) -> tuple[ExtractVerdict, dict[str, int]]:
    if not hits:
        return ExtractVerdict(), {"input_tokens": 0, "output_tokens": 0}
    packed = [{"url": row.url, "title": row.title, "snippet": row.snippet} for row in hits[:10]]
    return parse_openai(EXTRACT_PROMPT, {"question": case.question, "results": packed}, ExtractVerdict)
