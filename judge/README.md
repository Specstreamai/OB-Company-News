# judge

Grades each tool's search results against ground truth. No search code lives here.

- `pipeline.py` — Grades one search result: pulls out an answer, then asks the judge two questions about it.
- `extraction.py` — Asks an OpenAI model to answer the question from the search snippets alone. An agent setup's answer is graded as written, without this step, and the `model_only` baseline answers from the question alone.
- `judging.py` — Judge prompts. One checks the answer against ground truth; the other finds which snippets already hold the answer.
- `bedrock.py` — Calls the Claude judge through Amazon Bedrock and reads its JSON reply.
- `metrics.py` — Builds the board: accuracy, answer found in the top 1, 5 and 10 hits, source page in the top 5, latency, cost per query, and cost per 1,000 correct answers.
- `tests/` — Tests for the board.

Every question counts toward accuracy and recall, so a failed request counts as a miss. Latency covers every request that was sent, failed ones included. If grading itself fails (an extract or judge error), the cell records `score_error` and no evaluation, and `python -m harness evaluate --run-dir <run>` grades it again.

Cost follows what each tool charges. A request is billed at its list price when it succeeded or failed with anything other than an auth or payment error (401, 402, 403); a request that was never sent costs nothing. A credit-billed setup (`credit_usd` in its yaml) is charged for the credits it reports using. The extract model's tokens are added at its list price (`EXTRACT_USD_PER_M` in `metrics.py`), including Parallel's query plan. The board shows `usd_search`, `usd_extract`, `usd_per_query`, and cost per 1,000 correct answers for search alone and in total.

The ground-truth page counts as found in the top 5 when a hit has the same URL, or the same host with the gold page's file name in its path.
