from __future__ import annotations

from harness.models import AccuracyVerdict, Case, ExtractVerdict, Hit, RecallVerdict

from .bedrock import call_json

# Both prompts are the ones the published board was graded with, word for word.
ACCURACY_PROMPT = """Score the extracted answer against gold. correct=true only if every gold cell is present in the answer. Synonyms and equivalent numeric forms are allowed. Do not use outside knowledge or the search snippets.

### RESPONSE FORMAT (CRITICAL)

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:

{
  "correct": true,
  "cells_hit": 0,
  "note": "short reason"
}

correct must be a boolean. cells_hit is how many gold cells are present in the answer. note is a short string.
"""

RECALL_PROMPT = """Decide which search snippets already contain the gold fact.

A snippet is answer-bearing only if a reader could recover every gold cell from
that snippet alone, without outside knowledge. Synonyms and equivalent numeric
forms are allowed (eleven million = $11 million = $11M). Digit coincidence is
not enough: do not treat "2.0" as matching "2026", or "$20M" as matching
"$11 million". Stale directory pages that name a different person, company, or
round are not answer-bearing.

Ranks are 1-indexed in the order the snippets are listed.

### RESPONSE FORMAT (CRITICAL)

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:

{
  "bearing_ranks": [1, 4],
  "note": "short reason"
}

bearing_ranks is the list of ranks whose snippet contains every gold cell.
Use [] if none do. note is at most 12 words.
"""


def judge_accuracy(case: Case, extracted: ExtractVerdict) -> tuple[AccuracyVerdict, dict[str, int]]:
    if not extracted.answer.strip():
        return AccuracyVerdict(correct=False, cells_hit=0, note="empty answer"), {"input_tokens": 0, "output_tokens": 0}
    parsed, tokens = call_json(
        ACCURACY_PROMPT,
        {"question": case.question, "expected_answer": case.expected_answer,
         "cells": [cell.model_dump() for cell in case.cells], "answer": extracted.answer},
        max_tokens=1024,
    )
    return AccuracyVerdict.model_validate(parsed), tokens


def judge_recall(case: Case, hits: list[Hit]) -> tuple[RecallVerdict, dict[str, int]]:
    if not hits:
        return RecallVerdict(bearing_ranks=[], note="no snippets"), {"input_tokens": 0, "output_tokens": 0}
    snippets = [
        {"rank": index, "title": row.title[:300], "url": row.url, "snippet": row.snippet}
        for index, row in enumerate(hits[:10], 1)
    ]
    parsed, tokens = call_json(
        RECALL_PROMPT,
        {"question": case.question, "expected_answer": case.expected_answer,
         "cells": [cell.model_dump() for cell in case.cells], "snippets": snippets},
        max_tokens=2048,
    )
    verdict = RecallVerdict.model_validate(parsed)
    verdict.bearing_ranks = [rank for rank in verdict.bearing_ranks if rank <= len(snippets)]
    return verdict, tokens

