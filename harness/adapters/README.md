# adapters

One file per tool. Each file builds the tool's request and turns its response into search hits. Setups and prices live in `tools/<tool>.yaml`.

Web search tools take the question as written:

- `brave.py` — Brave web search and Brave LLM context.
- `context.py` — Context Developer search, with highlights (`context`) or without (`context_nohl`).
- `exa.py` — Exa search with highlights.
- `firecrawl.py` — Firecrawl search, and the Firecrawl Agent with an Alexandria data toolkit (`firecrawl_agent_apollo`): starts a job, polls it, and returns its answer as one hit.
- `keenable.py` — Keenable search.
- `linkup.py` — Linkup search results.
- `nimble.py` — Nimble search.
- `parallel.py` — Parallel search. The extract model writes one objective and 2-3 keyword queries per question, shared by every Parallel mode.
- `perplexity.py` — Perplexity search.
- `serp.py` — Google results through a RapidAPI search service.
- `tavily.py` — Tavily search.
- `tinyfish.py` — TinyFish search.
- `you.py` — You.com search with highlights.

News index:

- `seltz.py` — Seltz search: news scope (`seltz_news`), web scope (`seltz_web`), and web scope with passages instead of full content (`seltz_web_snippets`).

The baseline needs no tool:

- `model_only.py` — Makes no call; the judge step asks the extract model to answer from its own knowledge.

Each file ends with `setup(name, ...)`. Its arguments are the `settings` from the tool's yaml file.
