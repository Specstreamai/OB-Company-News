from harness.registry import DEFAULT_ENDPOINTS, all_adapters, pricing


def test_default_roster_is_twenty_eight_unique_endpoints():
    adapters = all_adapters()
    assert len(DEFAULT_ENDPOINTS) == 28
    assert len(set(DEFAULT_ENDPOINTS)) == 28
    assert set(DEFAULT_ENDPOINTS) <= set(adapters)
    assert {adapters[name].surface for name in DEFAULT_ENDPOINTS} == {"web-search", "news-index"}


def test_agent_and_baseline_run_only_when_named():
    adapters = all_adapters()
    assert adapters["firecrawl_agent_apollo"].surface == "agent"
    assert adapters["model_only"].surface == "baseline"
    assert "firecrawl_agent_apollo" not in DEFAULT_ENDPOINTS
    assert "model_only" not in DEFAULT_ENDPOINTS
    assert pricing()["firecrawl_agent_apollo"] == {"credit_usd": 0.0025, "basis": "credits"}
