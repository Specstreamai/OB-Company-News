from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any
from urllib.parse import urlparse

# Extract model list price, USD per million tokens. Its calls (the extractor, and Parallel's query plan)
# are part of each setup's cost; the judge's calls are not.
EXTRACT_USD_PER_M = {"input": 0.40, "output": 1.60}
# An auth or payment error is not billed by the tool; any other answered request is.
UNBILLED_STATUS = {401, 402, 403}


def _pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def _tokens(text: str) -> int:
    return max(1, round(len(" ".join((text or "").split())) / 4)) if text.strip() else 0


def _host(url: str) -> str:
    return urlparse(url or "").netloc.lower().removeprefix("www.")


def _url_key(url: str) -> str:
    parsed = urlparse((url or "").strip())
    return f"{parsed.netloc.lower().removeprefix('www.')}{parsed.path.rstrip('/')}"


def source_rank(hits: list[dict[str, Any]], gold_url: str) -> int | None:
    """Rank of the ground-truth page: the same URL, or the same host with the gold page's file name in the path."""
    if not gold_url:
        return None
    gold, gold_host = _url_key(gold_url), _host(gold_url)
    gold_tail = Path(urlparse(gold_url).path).name.lower()
    for rank, row in enumerate(hits, 1):
        url = row.get("url") or ""
        if _url_key(url) == gold or (gold_host == _host(url) and gold_tail and gold_tail in urlparse(url).path.lower()):
            return rank
    return None


def search_usd(cell: dict[str, Any], pricing: dict[str, Any]) -> float:
    """What the tool charged for this cell: per credit used, or the list price when the request was billed.
    A call that was never made (no status code) costs nothing."""
    if "credit_usd" in pricing:
        return max(0, int(cell.get("credits_used") or 0)) * float(pricing["credit_usd"])
    status = cell.get("status_code")
    billed = bool(cell.get("ok")) or (status is not None and status not in UNBILLED_STATUS)
    return float(pricing.get("list_usd") or 0) if billed else 0.0


def extract_usd(cell: dict[str, Any]) -> float:
    tokens = [((cell.get("evaluation") or {}).get("tokens") or {}).get("extract") or {}, cell.get("tool_llm_tokens") or {}]
    return sum(int(t.get("input_tokens") or 0) * EXTRACT_USD_PER_M["input"]
               + int(t.get("output_tokens") or 0) * EXTRACT_USD_PER_M["output"] for t in tokens) / 1_000_000


def aggregate(cells: list[dict[str, Any]], pricing: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        grouped[cell["endpoint"]].append(cell)
    rows: list[dict[str, Any]] = []
    for endpoint, items in grouped.items():
        correct = sum(bool((item.get("evaluation") or {}).get("accuracy", {}).get("correct")) for item in items)
        succeeded = [item for item in items if item.get("ok") and item.get("latency_ms") is not None]
        # Latency covers every request that was sent, failed ones included; a cell with no request has none.
        latencies = [float(item["latency_ms"]) for item in items if item.get("latency_ms") is not None]
        recall = [(item.get("evaluation") or {}).get("answer_recall") or {} for item in items]
        source5 = sum(1 for item in items
                      if (rank := source_rank(item.get("hits") or [], item.get("ground_truth_url") or "")) and rank <= 5)
        snippet_tokens = [sum(_tokens(f"{hit.get('title', '')} {hit.get('snippet', '')}") for hit in item.get("hits") or [])
                          for item in items]
        spec = pricing.get(endpoint, {})
        usd_search = sum(search_usd(item, spec) for item in items)
        usd_extract = sum(extract_usd(item) for item in items)
        usd = usd_search + usd_extract
        rows.append({
            "endpoint": endpoint,
            "surface": items[0].get("surface"),
            "total_cases": len(items),
            "successful_requests": len(succeeded),
            "correct": correct,
            "accuracy_pct": _pct(correct, len(items)),
            "answer_recall_1_pct": _pct(sum(bool(r.get("ar1")) for r in recall), len(items)),
            "answer_recall_5_pct": _pct(sum(bool(r.get("ar5")) for r in recall), len(items)),
            "answer_recall_10_pct": _pct(sum(bool(r.get("ar10")) for r in recall), len(items)),
            "source_recall_5_pct": _pct(source5, len(items)),
            "mean_snippet_tokens": round(mean(snippet_tokens), 1) if snippet_tokens else 0,
            "mean_latency_ms": round(mean(latencies), 1) if latencies else None,
            "median_latency_ms": round(median(latencies), 1) if latencies else None,
            "usd_search": round(usd_search, 4),
            "usd_extract": round(usd_extract, 4),
            "usd": round(usd, 4),
            "usd_per_query": round(usd / len(items), 5) if items else None,
            "search_cost_per_1000_correct_usd": round(usd_search * 1000 / correct, 2) if correct else None,
            "cost_per_1000_correct_usd": round(usd * 1000 / correct, 2) if correct else None,
        })
    return sorted(rows, key=lambda row: (row["surface"], row["cost_per_1000_correct_usd"] is None,
                                         row["cost_per_1000_correct_usd"] or 0, row["endpoint"]))
