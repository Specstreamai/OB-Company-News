from harness.registry import DEFAULT_ENDPOINTS, all_adapters, list_prices


def test_default_roster_is_thirty_one_unique_endpoints():
    adapters = all_adapters()
    assert len(DEFAULT_ENDPOINTS) == 31
    assert len(set(DEFAULT_ENDPOINTS)) == 31
    assert set(DEFAULT_ENDPOINTS) <= set(adapters)
    assert {adapters[name].surface for name in DEFAULT_ENDPOINTS} == {"web-search", "news-index"}


def test_agent_and_baseline_run_only_when_named():
    adapters = all_adapters()
    assert adapters["firecrawl_agent_apollo"].surface == "agent"
    assert adapters["model_only"].surface == "baseline"
    assert "firecrawl_agent_apollo" not in DEFAULT_ENDPOINTS
    assert "model_only" not in DEFAULT_ENDPOINTS
    assert list_prices()["firecrawl_agent_apollo"] == 0.0222
