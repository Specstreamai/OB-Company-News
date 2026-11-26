# judge

Grades each tool's search results against ground truth. No search code lives here.

- `pipeline.py` — Grades one search result: pulls out an answer, then asks the judge two questions about it.
- `extraction.py` — Asks an OpenAI model to answer the question from the search snippets alone. Agent setups skip this step; `model_only` answers from the question alone.
- `judging.py` — Judge prompts. One checks the answer against ground truth; the other finds which snippets already hold the answer.
- `bedrock.py` — Calls the Claude judge through Amazon Bedrock and reads its JSON reply.
- `metrics.py` — Builds the board: accuracy, answer found in the top 1, 5 and 10 hits, source page in the top 5, latency, cost per query, and cost per 1,000 correct answers.
- `tests/` — Tests for the board.

Every question counts toward accuracy and recall, so a failed request counts as a miss. Latency covers every request that was sent, failed ones included. A failed extract or judge call is saved as `score_error`; `python -m harness evaluate --run-dir <run>` grades it again.

A request is billed at list price unless it was never sent or failed with 401, 402 or 403. Credit-billed setups (`credit_usd`) are charged for the credits they report. Extract-model tokens are added at `EXTRACT_USD_PER_M`, Parallel's query plan included. The board shows `usd_search`, `usd_extract`, `usd_per_query`, and cost per 1,000 correct answers for search alone and in total.

Source recall@5 matches the gold URL exactly, or the same host with the gold page's file name in its path.
