# judge

Grades each tool's search results against ground truth. No search code lives here.

- `pipeline.py` — Grades one search result: pulls out an answer, then asks the judge two questions about it.
- `extraction.py` — Asks an OpenAI model to answer the question from the search snippets alone. An agent setup's answer is graded as written, without this step, and the `model_only` baseline answers from the question alone.
- `judging.py` — Judge prompts. One checks the answer against ground truth; the other finds which snippets already hold the answer.
- `bedrock.py` — Calls the Claude judge through Amazon Bedrock and reads its JSON reply.
- `metrics.py` — Builds the board: accuracy, answer found in the top 1, 5 and 10 hits, source page in the top 5, latency, and cost per 1,000 correct answers.
- `tests/` — Tests for the board.

Every question counts toward accuracy and recall, so a failed request counts as a miss. If grading itself fails (an extract or judge error), the cell records `score_error` and no evaluation, and `python -m harness evaluate --run-dir <run>` grades it again. Latency only uses requests that succeeded, and the board shows how many those were.
