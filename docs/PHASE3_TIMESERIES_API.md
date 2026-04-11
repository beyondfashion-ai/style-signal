# Phase 3 — Time-Series Trend DB + REST API

> Handoff spec. Builds on phases 1 and 2. Read [PHASE1_REFACTOR_PLAN.md](./PHASE1_REFACTOR_PLAN.md) and [PHASE2_VISION_TAGGING.md](./PHASE2_VISION_TAGGING.md) first.

## Goal

Persist every fetch as a daily snapshot in **SQLite** so we can answer queries like:
- "Which brands rose fastest week-over-week on KREAM men's TOP100?"
- "Was brand X in the TOP40 7 days ago? 30 days ago?"
- "What new brands appeared this week vs last week?"

Expose the data over a tiny **FastAPI** REST service so the project becomes an open dataset + API. SQLite is committed to the repo or shipped as a release asset; the API runs on any free-tier box (fly.io free tier, a user's own laptop, or locally).

## Free-source constraints

- **SQLite only** for storage. No Postgres, no Firestore, no cloud DB.
- **FastAPI + Uvicorn** for the API. No Vercel, no serverless framework.
- **Optional dep** — core `pip install -e .` must not pull FastAPI. Install via `pip install -e ".[api]"`.
- **No auth layer** in phase 3. The API is public read-only. Write operations happen only via the CLI running locally.
- **No migrations framework** — plain `CREATE TABLE IF NOT EXISTS` at startup. If schema changes later, bump a `schema_version` row.

## Module layout (additions only)

```
src/fashion_trend/
├── storage/
│   ├── __init__.py
│   ├── db.py              # connection, schema bootstrap
│   ├── snapshots.py       # write a FetchResult as a snapshot
│   └── queries.py         # read-side query helpers
└── api/
    ├── __init__.py
    ├── app.py             # FastAPI application factory
    └── routes.py          # endpoints
```

Default DB path: `./data/fashion_trend.sqlite` (create parent dir on demand). Override via `FASHION_TREND_DB` env var or `--db` CLI flag.

## Schema

```sql
CREATE TABLE IF NOT EXISTS snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    query_json      TEXT NOT NULL,         -- JSON-serialized Query
    fetched_at      TEXT NOT NULL,         -- ISO8601 UTC
    fetch_date      TEXT NOT NULL,         -- YYYY-MM-DD UTC (for daily uniqueness)
    product_count   INTEGER NOT NULL,
    raw_path        TEXT,
    UNIQUE(source, query_json, fetch_date) ON CONFLICT REPLACE
);

CREATE TABLE IF NOT EXISTS products (
    snapshot_id     INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    rank            INTEGER,
    source_id       TEXT NOT NULL,
    brand           TEXT NOT NULL,
    name            TEXT NOT NULL,
    name_en         TEXT,
    price_krw       INTEGER,
    price_original_krw INTEGER,
    discount_pct    INTEGER,
    image_url       TEXT,
    url             TEXT,
    category        TEXT,
    gender          TEXT,
    interest_count  INTEGER,
    review_count    INTEGER,
    trade_count     INTEGER,
    tags_json       TEXT,                  -- serialized ProductTags or NULL
    PRIMARY KEY (snapshot_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_source_brand ON products(snapshot_id, brand);
CREATE INDEX IF NOT EXISTS idx_snapshots_source_date ON snapshots(source, fetch_date);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
```

`query_json` identity: include only the fields that define a logical "feed" — `source`, `category`, `keyword`, `gender`, `sort`, `curation`. Exclude `limit` so a 40-item and 100-item fetch of the same feed collapse to one snapshot per day.

## CLI changes

Add two commands:

```
python -m fashion_trend store --input artifacts/kream-result.tagged.json
python -m fashion_trend query --help
```

`store`:
- Reads a JSON file produced by `fetch` (optionally post-`tag`) and writes it to the DB as a snapshot.
- Upserts on `(source, query_json, fetch_date)` — re-running the same feed on the same day overwrites.
- Prints `{"snapshot_id": N, "product_count": M}`.

`query`:
- `python -m fashion_trend query rising-brands --source kream --window 7 --curation top100 --gender men --limit 10`
  → Brands that gained the most rank/appearances in the last 7 days.
- `python -m fashion_trend query new-brands --source kream --window 7`
  → Brands present today but absent in the prior window.
- `python -m fashion_trend query brand-history --source kream --brand "new balance" --days 30`
  → Time series of that brand's min/avg rank and appearance count by day.
- `python -m fashion_trend query snapshots --source kream --date 2026-04-10`
  → List snapshots for a date.

Each query prints JSON. Document the exact shapes in `docs/API.md` (codex writes).

Also add `--store` flag to `fetch`:

```
python -m fashion_trend fetch --source kream --curation top100 --gender men --store
```

This fetches, optionally tags, and writes to the DB in one shot.

## REST API (`src/fashion_trend/api/`)

FastAPI app. Endpoints (all GET, all return JSON):

```
GET /health
GET /sources
GET /snapshots?source=kream&from=2026-04-01&to=2026-04-11
GET /snapshots/{snapshot_id}
GET /snapshots/{snapshot_id}/products
GET /trends/rising-brands?source=kream&window=7&limit=10&gender=men&curation=top100
GET /trends/new-brands?source=kream&window=7
GET /brands/{brand}/history?source=kream&days=30
```

Every response is a plain JSON object; no HTML, no auth headers required. Enable permissive CORS (`allow_origins=["*"]`) so the public dataset is usable from anywhere.

Run command:

```
python -m fashion_trend serve --host 0.0.0.0 --port 8787
```

This delegates to `uvicorn.run(app, ...)`. Only works when the `[api]` extra is installed, otherwise prints a clear install hint and exits 1.

## `pyproject.toml` updates

```toml
[project.optional-dependencies]
tagging = ["google-genai>=0.3"]
api = ["fastapi>=0.110", "uvicorn[standard]>=0.29"]
all = ["google-genai>=0.3", "fastapi>=0.110", "uvicorn[standard]>=0.29"]
```

Core install remains zero-new-deps beyond scrapling.

## Tests

- `test_storage_roundtrip.py` — build a synthetic `FetchResult` with 3 products; write to an in-memory SQLite (`:memory:`); read back via `queries.fetch_snapshot`; assert round-trip equality on all non-null fields.
- `test_snapshot_upsert.py` — write the same feed twice on the same `fetch_date`; assert only one snapshot row exists.
- `test_rising_brands.py` — seed 3 daily snapshots with varying brand ranks; call `rising_brands(window=3)`; assert the brand with the biggest rank improvement is first.
- `test_new_brands.py` — seed brands A/B/C on day 1 and A/B/D on day 2; assert `new_brands(window=1)` returns `["D"]`.
- `test_api_smoke.py` — use `fastapi.testclient.TestClient`; assert `/health` returns 200, `/sources` returns a list, `/trends/rising-brands` returns a list (empty is OK on empty DB).

All tests offline, SQLite `:memory:`, no uvicorn boot.

## Data ethics (carry-over)

The README disclaimer still stands. For the SQLite artifact that gets committed or released:

- **Do NOT store raw image bytes.** Store image URLs only.
- **Do NOT store user-generated content** (reviews, comments) even if scraped incidentally.
- Document the data schema openly in `docs/DATA.md` (codex writes a short file).
- License the data as CC BY-NC 4.0 in `DATA_LICENSE` — non-commercial research use only. Code license remains MIT.

## Acceptance criteria

1. `python -m fashion_trend fetch --source kream --curation top100 --gender men --store` succeeds and creates/updates a row in `snapshots` and N rows in `products`.
2. `python -m fashion_trend query rising-brands --source kream --window 7` returns a JSON list (empty on an empty DB, not an error).
3. `python -m fashion_trend serve --port 8787` boots FastAPI; `curl localhost:8787/health` returns `{"ok": true}`.
4. Re-running the same `fetch --store` on the same UTC day overwrites the same snapshot (verified by row count staying constant).
5. All storage + API tests pass offline via `python -m unittest discover tests`.
6. Plain `pip install -e .` still works without FastAPI or google-genai installed.
7. `DATA_LICENSE` (CC BY-NC 4.0) file exists; `docs/DATA.md` documents the schema.

## Out of scope

- Authentication / API keys.
- Rate limiting on the REST API.
- Websocket / streaming.
- Migration tooling (alembic etc.).
- Hosted deployment — README mentions that `serve` runs anywhere, but provides no Dockerfile or cloud config. Ops concerns stay with the user.
