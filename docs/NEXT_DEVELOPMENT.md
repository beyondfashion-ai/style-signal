# style-signal Next Development Backlog

This backlog is based on the current local repo state after `beyondfashion-ai/style-signal`
was recreated as an independent public repository.

## Current Baseline

- Public repo: `https://github.com/beyondfashion-ai/style-signal`
- Local development worktree: `/home/beyondfashion/style-signal-dev`
- Branch: `codex/style-signal-dev`
- Core implementation: adapter-based Python CLI with `list-sources`, `describe`, `fetch`, and `signal`.
- Ready adapters: `kream`, `musinsa`, `29cm`.
- Stub adapters: `ssense`, `farfetch`, `grailed`, `styleshare`.
- KALEI-inspired public layer: deterministic brand frequency, price-band balance, source guard, evidence manifest hash.
- Verification baseline: `python3 -m unittest discover tests` passes 15 tests.

## Priority 0 - OSS Credibility Cleanup

Goal: make the repository look clean and self-contained before larger feature work.

Evidence:
- `README.md` has been rewritten for the independent `beyondfashion-ai/style-signal` repository and now separates implemented features from planned features.
- `LICENSE` now contains only MIT text.
- `NOTICE` carries scraping/source-use responsibility notes.
- `DATA_LICENSE` exists for CC BY-NC 4.0 data artifacts.
- `docs/OPENSOURCE_ROADMAP.md` now uses independent-project language.

Work:
- Keep README clone URLs pointed at `https://github.com/beyondfashion-ai/style-signal.git`.
- Keep `LICENSE`, `NOTICE`, and `DATA_LICENSE` split by responsibility.
- Keep roadmap wording aligned with the independent-project status.
- Add a short "Project Status" section that honestly separates implemented features from planned features.

Acceptance:
- GitHub license detection should show MIT, not Other.
- README no longer references the old fork as the primary install source.
- `python3 -m unittest discover tests` remains green.

## Priority 1 - Align Product Promise With CLI Reality

Goal: remove the gap between README/SKILL promises and actual package behavior.

Evidence:
- README now positions HTML report generation as the Claude/Codex skill layer, not the core CLI.
- `src/style_signal/cli.py` currently implements only `list-sources`, `describe`, and `fetch`.
- `SKILL.md` can generate an HTML report through the host agent, but the Python package itself does not expose `report`.

Work:
- Either add a `report` command that renders a static HTML report from fetch JSON, or revise README wording so HTML is clearly a Claude/Codex skill layer rather than a package feature.
- Prefer adding `report` because it makes the OSS tool usable outside Claude/Codex.
- Keep it dependency-free with a small standard-library HTML renderer.

Acceptance:
- `python3 -m style_signal report --input artifacts/example.json --output trend-report/example.html` works with a fixture.
- Offline test verifies the report includes product names, images, ranks, prices, and source links.
- README examples match real commands.

## Priority 2 - Implement Phase 2 Tagging Contract

Goal: add optional style tagging without changing the core install footprint.

Evidence:
- `docs/PHASE2_VISION_TAGGING.md` specifies `ProductTags`, `Product.tags`, `--tag`, `--tag-limit`, and a standalone `tag` command.
- `src/style_signal/schema.py` has `Product`, but no `ProductTags` or `tags` field.
- `pyproject.toml` has no optional dependency group yet.

Work:
- Add `ProductTags` and optional `tags` to `Product`.
- Add `src/style_signal/tagging/` with base tagger, prompt template, JSON parser, and Gemini implementation.
- Add optional dependency group: `tagging = ["google-genai>=0.3"]`.
- Add `tag` command and `fetch --tag --tag-limit`.
- Missing `GEMINI_API_KEY` should warn to stderr and leave `tags=None`; it must not fail fetch.

Acceptance:
- Plain `pip install -e .` does not install `google-genai`.
- `python3 -m unittest discover tests` runs without network and passes.
- Offline tests cover prompt keys, JSON parsing, and fallback isolation.

## Priority 3 - Implement SQLite Snapshot Store And Trend Queries

Goal: turn one-off fetches into an actual open trend dataset.

Evidence:
- `docs/PHASE3_TIMESERIES_API.md` defines SQLite tables, `store`, `query`, and `serve`.
- `docs/DATA.md` defines the data contract, but no storage module exists.
- KALEI has proven internal patterns for brand frequency, hot brands, and style signal summaries in `src/fashionTrend.js`; the first deterministic single-snapshot signal layer now exists in `src/style_signal/signals.py`.

Work:
- Add `src/style_signal/storage/` with schema bootstrap, snapshot upsert, and read queries.
- Add `store` command for fetch JSON.
- Add `query rising-brands`, `query new-brands`, `query brand-history`, and `query snapshots`.
- Make `query_json` exclude `limit`, matching the Phase 3 spec.
- Keep core storage stdlib-only with `sqlite3`.

Acceptance:
- In-memory SQLite tests cover roundtrip, same-day upsert, rising brands, new brands, and brand history.
- `fetch --store` creates or updates a snapshot.
- Empty DB queries return empty lists, not errors.

## Priority 4 - Add Evidence Manifest And Source/Visual Truth Guards

Goal: make generated reports auditable and harder to overclaim.

Evidence:
- KALEI has deterministic source suitability filtering, source truth checks, visual truth checks, and evidence manifests.
- `style-signal signal` now emits source refs, supported brand/price claims, source guard issues, and a stable manifest hash.

Work:
- Extend the current `src/style_signal/signals.py` layer into report generation once `report` exists.
- Add visual/tag evidence after Phase 2 tagging creates `ProductTags`.
- Bind report body text to the existing manifest hash when `report --manifest-output` lands.

Acceptance:
- Offline tests prove manifest hash changes when source evidence changes.
- Unsupported price/rank/brand claims are detectable from fixture text after `report` exists.
- Report command can emit `--manifest-output`.

## Priority 5 - Adapter Expansion And Hardening

Goal: turn the project from a Korean-market proof into a contribution-friendly trend toolkit.

Evidence:
- Registry exposes 7 sources, but 4 are stubs.
- `docs/ADAPTERS.md` already defines the adapter contribution checklist.

Work:
- Implement one global adapter first, preferably `ssense`, because it has clear product listing/search pages and fashion relevance.
- Add a smoke-test script that can run live fetches manually but is not part of offline CI.
- Add stricter parser contracts around required fields and duplicate product IDs.

Acceptance:
- At least one former stub becomes `ready`.
- Parser/URL tests use synthetic fixtures only.
- Live smoke command is documented as manual and optional.

## Priority 6 - API Surface After Storage Is Stable

Goal: add FastAPI only after the SQLite query layer has a stable contract.

Evidence:
- Phase 3 specifies REST API endpoints, but storage/query code is the prerequisite.
- Open-source users can benefit from CLI queries before a server exists.

Work:
- Add optional dependency group: `api = ["fastapi>=0.110", "uvicorn[standard]>=0.29"]`.
- Add `serve` command with a clear install hint when API extras are missing.
- Implement `/health`, `/sources`, `/snapshots`, `/trends/rising-brands`, `/trends/new-brands`, and `/brands/{brand}/history`.

Acceptance:
- Core install works without FastAPI.
- `TestClient` smoke tests run offline.
- `curl localhost:8787/health` returns a plain JSON health object when `[api]` extras are installed.

## Recommended First Sprint

1. OSS credibility cleanup.
2. Add a dependency-free `report` command using `signal` output and manifest refs.
3. Implement SQLite `store` plus `query rising-brands`.

This gives the project a stronger public story quickly: real install docs, real standalone reports,
auditable trend signals, and real historical trend analysis without paid services.
