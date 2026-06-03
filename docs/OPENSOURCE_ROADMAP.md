# style-signal Open-Source Roadmap

> This independent project turns a KREAM-first Claude Code skill into a pluggable, open, free-to-run fashion trend signal toolkit.

## Scope (locked)

Only three items from the original brainstorm ship. Everything else is explicitly out.

| # | Phase | Doc | Status |
|---|---|---|---|
| 1 | Multi-source adapter architecture | [PHASE1_REFACTOR_PLAN.md](./PHASE1_REFACTOR_PLAN.md) | spec ready |
| 2 | Gemini vision auto-tagging | [PHASE2_VISION_TAGGING.md](./PHASE2_VISION_TAGGING.md) | spec ready |
| 3 | SQLite time-series DB + FastAPI REST | [PHASE3_TIMESERIES_API.md](./PHASE3_TIMESERIES_API.md) | spec ready |

## Explicitly cut

- Next.js / Vercel dashboard
- MCP server mode
- Scheduled Cloud Run + SNS auto-posting
- GitHub Actions daily report publishing

## Free-source stance (non-negotiable)

- **Storage:** SQLite (stdlib). No Firestore/Postgres/Supabase.
- **API:** FastAPI + Uvicorn, runs anywhere. No Vercel/Cloud Run/Lambda.
- **Vision tagging:** Gemini 2.5 Flash free tier only. No paid LLM APIs in the default code path.
- **Scraping:** Scrapling (already used). No paid scraping services.
- **CI/dev tools:** stdlib `unittest` + `argparse`. No pytest/ruff/mypy unless already in-tree.
- **Optional deps are actually optional:** `pip install -e .` must succeed on a plain Python 3.11 install with zero new required packages beyond `scrapling[all]`.

## Global principles

1. **Backward compat first.** The original Claude Code skill (`SKILL.md`) must keep working on every phase. No user-visible regression.
2. **Silent fallbacks.** Tagging and DB are both optional; missing API key / missing optional deps degrade gracefully, never hard-fail the core fetch.
3. **Deterministic JSON contracts.** Every CLI command prints a stable JSON shape to stdout; exit code signals success/failure.
4. **Offline tests.** No network calls in the test suite. Fixtures are synthetic or recorded.
5. **Data ethics.** Store image URLs only, never bytes. Dataset ships under CC BY-NC 4.0; code stays MIT.

## Execution order for the implementing agent (codex)

1. Land phase 1 end-to-end (scaffold + KREAM + Musinsa + 29CM + stubs + tests + SKILL.md update + README architecture section). Commit in logical chunks per phase 1 spec. Do not proceed until `python -m unittest discover tests` is green.
2. Land phase 2 (tagging module, optional dep, CLI flag, SKILL.md step 4.5, tests). Phase 1 tests must still pass.
3. Land phase 3 (storage, queries, FastAPI app, CLI commands, tests, DATA_LICENSE, docs/DATA.md). Phases 1 and 2 tests must still pass.

Between phases, run:

```bash
python -m fashion_trend list-sources
python -m fashion_trend describe --source kream
python -m unittest discover tests
```

If any of these fail, stop and report rather than patching forward.

## Commit policy

Conventional commits with trailer block per the repo's CLAUDE.md:

```
feat(core): add adapter registry

Constraint: stdlib-only registry, no plugin discovery magic
Rejected: entry_points-based discovery | adds setuptools complexity for no near-term gain
Confidence: high
Scope-risk: narrow
```

One commit per logical chunk — do not lump the whole phase into a single commit.

## Done definition (per phase)

- All acceptance criteria in the phase doc pass.
- `python -m unittest discover tests` green.
- Previous phases still green.
- `SKILL.md` still runnable end-to-end via the Claude Code skill flow.
- No new required runtime deps beyond what the phase doc authorizes.
