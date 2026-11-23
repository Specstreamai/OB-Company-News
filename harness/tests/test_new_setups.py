from unittest.mock import patch

from harness.models import Case, Hit, HttpAudit, SearchResult
from harness.registry import all_adapters
from judge import pipeline

CASE = Case(id="q", question="Who did Acme hire as CFO?", expected_answer="Jane Doe")


def test_firecrawl_agent_request_pins_apollo_toolkit():
    body = all_adapters()["firecrawl_agent_apollo"].body(CASE)
    assert body["prompt"] == CASE.question
    assert (body["model"], body["effort"], body["maxCredits"]) == ("spark-2", "medium", 800)
    assert body["exchange"] == {"enabled": True, "toolkits": ["apollo"], "maxCalls": 16}
    assert body["schema"]["required"] == ["answer", "source_url"]


def test_firecrawl_agent_answer_becomes_one_hit():
    from harness.adapters.firecrawl import agent_hits
    hits = agent_hits({"status": "completed", "data": {"answer": "Jane Doe", "source_url": "https://acme.com/news"}}, "j1")
    assert [(h.url, h.snippet, h.metadata["answer"]) for h in hits] == [("https://acme.com/news", "Jane Doe", "Jane Doe")]
    assert agent_hits({"data": {"answer": "", "source_url": ""}}, "j1") == []
    assert agent_hits({"data": {"answer": "x", "source_url": ""}}, "j1")[0].url.endswith("/v2/agent/j1")


def _audit(ok=True):
    return HttpAudit(method="POST", url="", request={}, ok=ok, latency_ms=1, started_at="", ended_at="")


def test_agent_answer_skips_the_extractor_and_model_only_answers_alone():
    agent = SearchResult(endpoint="firecrawl_agent_apollo", surface="agent", audit=_audit(),
                         hits=[Hit(url="https://acme.com", snippet="Jane Doe", metadata={"answer": "Jane Doe"})])
    with patch.object(pipeline, "extract", side_effect=AssertionError("extractor must not run")), \
         patch.object(pipeline, "model_only_answer", side_effect=AssertionError), \
         patch.object(pipeline, "judge_accuracy", side_effect=lambda case, ex: (_accuracy(ex), {})), \
         patch.object(pipeline, "judge_recall", side_effect=lambda case, hits: (_recall(), {})):
        out = pipeline.evaluate_search_result(CASE, agent)
    assert out["extract"]["answer"] == "Jane Doe" and out["accuracy"]["correct"]

    from harness.models import ExtractVerdict
    baseline = SearchResult(endpoint="model_only", surface="baseline", audit=_audit(), hits=[])
    with patch.object(pipeline, "extract", side_effect=AssertionError("extractor must not run")), \
         patch.object(pipeline, "model_only_answer", return_value=(ExtractVerdict(answer="Jane Doe"), {})), \
         patch.object(pipeline, "judge_accuracy", side_effect=lambda case, ex: (_accuracy(ex), {})), \
         patch.object(pipeline, "judge_recall", side_effect=lambda case, hits: (_recall(), {})):
        assert pipeline.evaluate_search_result(CASE, baseline)["accuracy"]["correct"]


def _accuracy(extracted):
    from harness.models import AccuracyVerdict
    return AccuracyVerdict(correct=extracted.answer == "Jane Doe")


def _recall():
    from harness.models import RecallVerdict
    return RecallVerdict()


def test_seltz_web_setups():
    adapters = all_adapters()
    assert adapters["seltz_news"].surface == "news-index"
    assert adapters["seltz_web"].body(CASE) == {"query": CASE.question, "max_results": 10, "scope": "web"}
    assert adapters["seltz_web"].surface == "web-search"
    assert adapters["seltz_web_snippets"].body(CASE)["fields"] == {"snippets": True}
    from harness.adapters.seltz import _parse
    hits = _parse({"documents": [{"url": "https://a.com", "snippets": [{"text": "one"}, {"text": "two"}]}]})
    assert hits[0].snippet == "one\ntwo"


def test_context_without_highlights_uses_description():
    adapter = all_adapters()["context_nohl"]
    with patch.dict("os.environ", {"CONTEXT_API_KEY": "k"}):
        assert adapter.build(CASE)[3]["highlightsOptions"] == {"enabled": False}
    row = {"url": "https://a.com", "description": "desc", "highlights": {"code": "SUCCESS", "highlights": ["hl"]}}
    assert adapter.parse({"results": [row]})[0].snippet == "desc"
    assert all_adapters()["context"].parse({"results": [row]})[0].snippet == "hl"


def test_keenable_request_and_parse():
    adapter = all_adapters()["keenable_realtime"]
    with patch.dict("os.environ", {"KEENABLE_API_KEY": "k"}):
        method, url, _, body, _, timeout = adapter.build(CASE)
    assert (method, url, timeout) == ("POST", "https://api.keenable.ai/v1/search", 45)
    assert body == {"query": CASE.question, "mode": "realtime", "max_results": 10}
    hits = adapter.parse({"results": [{"url": "https://a.com", "description": "short", "snippet": "long"}]})
    assert hits[0].snippet == "long"


def test_parallel_sends_one_shared_model_written_plan():
    from harness.adapters import parallel
    from harness.adapters.parallel import QueryPlan
    parallel._CACHE.clear()
    plan = QueryPlan(objective="Find Acme's new CFO", search_queries=["Acme CFO hire", " ", "Acme new CFO"])
    with patch.object(parallel, "parse_openai", return_value=(plan, {})) as model, \
         patch.dict("os.environ", {"PARALLEL_API_KEY": "k"}):
        fast = all_adapters()["parallel_fast"].build(CASE)[3]
        advanced = all_adapters()["parallel_advanced"].build(CASE)[3]
    assert model.call_count == 1
    assert fast["objective"] == "Find Acme's new CFO"
    assert fast["search_queries"] == advanced["search_queries"] == ["Acme CFO hire", "Acme new CFO"]


def test_failed_grade_is_recorded_not_raised():
    from harness import orchestration
    result = SearchResult(endpoint="exa_fast", surface="web-search", audit=_audit(), hits=[])
    with patch.object(orchestration, "evaluate_search_result", side_effect=RuntimeError("judge down")):
        evaluation, error = orchestration._grade(CASE, result)
    assert evaluation is None and "judge down" in error
