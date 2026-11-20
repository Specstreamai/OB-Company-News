# AGENTS.md — OB-Company-News

Quick navigation guide for coding agents working in `OB-Company-News`.

## Structure (Zero Overlap)

| Folder | Owns | Files |
|---|---|---|
| **`data/`** | Question file format (the question set stays private) | `data/README.md` |
| **`harness/`** | Execution only: CLI runner, orchestration, tool registry, tool adapters, HTTP client, run checks | `harness/cli.py`, `harness/orchestration.py`, `harness/registry.py`, `harness/tool_base.py`, `harness/adapters/<tool>.py`, `harness/http_client.py`, `harness/openai_client.py`, `harness/models.py`, `harness/artifacts.py`, `harness/verification.py` |
| **`tools/`** | Tool setups & pricing (one file per tool for clean PRs) | `tools/<tool>.yaml` |
| **`judge/`** | Grading only: answer extraction, judge prompts, Bedrock judge client, board math | `judge/pipeline.py`, `judge/extraction.py`, `judge/judging.py`, `judge/bedrock.py`, `judge/metrics.py` |

Tests sit next to the code they test in `harness/tests/` and `judge/tests/`. Benchmark order & win condition live at the root in `benchmark.yaml`.

## Commands

```sh
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/python -m harness list-providers
```

## Guidelines

- **Keep folders strictly separated:** Question format in `data/`; execution and tool code in `harness/`; per-tool setups and prices in `tools/<tool>.yaml`; grading in `judge/`.
- **Adding or tuning a tool:** Edit `tools/<tool>.yaml` (and `harness/adapters/<tool>.py` plus the `TOOLS` line in `harness/registry.py` for a new tool), then run `pytest`.
- **No secrets or raw run logs in git:** Keep API keys in `.env` and run outputs in `runs/` (both gitignored).
- **Consistent terminology:** Use `tool`, `setup`, `question`, `ground truth`, `judge`, `board`.
