from judge.metrics import aggregate, source_rank

PRICE = {"exa_instant": {"list_usd": 0.007}, "agent": {"credit_usd": 0.0025}}


def _cell(**kw):
    base = {"endpoint": "exa_instant", "surface": "web-search", "ok": True, "status_code": 200, "latency_ms": 100,
            "ground_truth_url": "", "hits": [], "evaluation": None}
    return {**base, **kw}


def test_accuracy_keeps_failures_in_denominator_and_latency_keeps_failed_requests():
    cells = [
        _cell(ground_truth_url="https://example.com/a", hits=[{"url": "https://example.com/a", "title": "", "snippet": "answer"}],
              evaluation={"accuracy": {"correct": True}, "answer_recall": {"ar1": True, "ar5": True, "ar10": True}}),
        _cell(ok=False, status_code=500, latency_ms=900),
    ]
    row = aggregate(cells, PRICE)[0]
    assert row["accuracy_pct"] == 50.0
    assert row["mean_latency_ms"] == 500.0
    assert row["successful_requests"] == 1
    assert row["source_recall_5_pct"] == 50.0


def test_only_billed_requests_cost_money():
    cells = [
        _cell(evaluation={"accuracy": {"correct": True}}),
        _cell(ok=False, status_code=500),                 # answered with an error: billed
        _cell(ok=False, status_code=401),                 # auth error: not billed
        _cell(ok=False, status_code=None, latency_ms=None),  # never sent: not billed
    ]
    row = aggregate(cells, PRICE)[0]
    assert row["usd_search"] == 0.014
    assert row["search_cost_per_1000_correct_usd"] == 14.0


def test_credit_billed_setup_and_extract_tokens():
    cells = [_cell(endpoint="agent", surface="agent", credits_used=10,
                   evaluation={"accuracy": {"correct": True}, "tokens": {"extract": {"input_tokens": 1_000_000}}},
                   tool_llm_tokens={"output_tokens": 1_000_000})]
    row = aggregate(cells, PRICE)[0]
    assert row["usd_search"] == 0.025
    assert row["usd_extract"] == 2.0


def test_source_match_accepts_same_host_and_file_name():
    gold = "https://www.acme.com/news/2026/cfo-hire.html"
    assert source_rank([{"url": "https://x.com"}, {"url": "https://acme.com/news/2026/cfo-hire.html/"}], gold) == 2
    assert source_rank([{"url": "https://acme.com/amp/cfo-hire.html?x=1"}], gold) == 1
    assert source_rank([{"url": "https://other.com/cfo-hire.html"}], gold) is None
