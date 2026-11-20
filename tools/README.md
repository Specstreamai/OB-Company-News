# tools

One `<tool>.yaml` file per tool. Keeping each tool in its own file makes it easy to compare setups and open pull requests without merge conflicts.

Each file lists the tool's setups. For each setup:

- `class` — `main` setups run by default. Any other class runs only when named with `--endpoints`.
- `settings` — Options passed to the tool's code in `harness/adapters/<tool>.py`.
- `pricing` — The public list price per request in US dollars. Put the source and the date you checked it in a comment.

Prices without a dated comment are list prices as of 2026-10-20.

To add a tool: add `tools/<tool>.yaml`, add its code in `harness/adapters/<tool>.py`, add its name to `TOOLS` in `harness/registry.py`, add its API key to `.env.example`, run the tests, and open a pull request.
