# style-signal REST API

Phase 3 adds an optional FastAPI server exposing the SQLite snapshot database as a public read-only REST API. This document is the implementation contract — Phase 3 code must match these shapes exactly.

## Install and run

```bash
pip install -e ".[api]"
python -m style_signal serve --host 0.0.0.0 --port 8787
```

`--db PATH` overrides the default `./data/style_signal.sqlite`. `STYLE_SIGNAL_DB` env var has the same effect.

CORS is permissive (`allow_origins=["*"]`) — this is an open dataset, no auth, read-only.

## Shared response conventions

- All successful responses are JSON.
- Errors return `{"error": "<code>", "message": "<human>"}` with HTTP 4xx/5xx.
- Timestamps are ISO-8601 UTC strings (`"2026-04-11T09:00:00Z"`).
- `date` fields are `YYYY-MM-DD` (UTC day).
- Missing / null values are serialized as `null`, never omitted.

## Endpoints

### `GET /health`

```json
{"ok": true, "version": "0.2.0", "db": "/path/to/style_signal.sqlite"}
```

Always 200 if the process is up and the DB file is reachable.

### `GET /sources`

```json
{
  "sources": [
    {"name": "kream",   "status": "ready"},
    {"name": "musinsa", "status": "ready"},
    {"name": "29cm",    "status": "ready"},
    {"name": "ssense",  "status": "stub"}
  ]
}
```

Reflects the registry, not the DB.

### `GET /snapshots`

Query params:
- `source` (required, string)
- `from` (optional, `YYYY-MM-DD`)
- `to` (optional, `YYYY-MM-DD`)
- `gender` (optional)
- `curation` (optional)
- `limit` (optional, default 50, max 500)

```json
{
  "snapshots": [
    {
      "id": 42,
      "source": "kream",
      "query": {"source": "kream", "curation": "top100", "gender": "men", "sort": "popular"},
      "fetched_at": "2026-04-11T09:00:00Z",
      "fetch_date": "2026-04-11",
      "product_count": 40
    }
  ],
  "count": 1
}
```

### `GET /snapshots/{snapshot_id}`

```json
{
  "id": 42,
  "source": "kream",
  "query": {...},
  "fetched_at": "2026-04-11T09:00:00Z",
  "fetch_date": "2026-04-11",
  "product_count": 40,
  "raw_path": "artifacts/kream-result.md"
}
```

404 if missing.

### `GET /snapshots/{snapshot_id}/products`

```json
{
  "snapshot_id": 42,
  "products": [
    {
      "rank": 1,
      "source_id": "12345",
      "brand": "NEW BALANCE",
      "name": "뉴발란스 1906A 프로테이너",
      "name_en": "New Balance 1906A Protrainer",
      "price_krw": 159000,
      "price_original_krw": 189000,
      "discount_pct": 16,
      "image_url": "https://kream-phinf.pstatic.net/...",
      "url": "https://kream.co.kr/products/12345",
      "interest_count": 3311,
      "review_count": 204,
      "trade_count": 253,
      "tags": {
        "styles": ["retro", "running"],
        "colors": ["grey", "navy"],
        "silhouette": "regular",
        "materials": ["mesh", "suede"],
        "aesthetic": "gorpcore",
        "confidence": 0.82,
        "model": "gemini-2.5-flash",
        "tagged_at": "2026-04-11T09:05:00Z"
      }
    }
  ]
}
```

`tags` is `null` when Phase 2 tagging was not run on that product.

### `GET /trends/rising-brands`

Query params:
- `source` (required)
- `window` (optional int days, default 7)
- `limit` (optional int, default 10)
- `gender` (optional)
- `curation` (optional)

Semantics: for each brand present in any snapshot within `[today - window, today]`, compute its average rank today vs `window` days ago. Return the `limit` brands with the largest rank improvement (lower rank = better).

```json
{
  "window_days": 7,
  "source": "kream",
  "as_of": "2026-04-11",
  "rising": [
    {
      "brand": "ASICS",
      "rank_now": 4.2,
      "rank_before": 12.8,
      "delta": 8.6,
      "appearances_now": 6,
      "appearances_before": 3
    }
  ]
}
```

Empty `rising: []` if the DB has no data in the window — 200, not 404.

### `GET /trends/new-brands`

Query params:
- `source` (required)
- `window` (optional int days, default 7)

Semantics: brands appearing in the most recent snapshot but absent in any snapshot older than the most recent and within the prior `window` days.

```json
{
  "window_days": 7,
  "source": "kream",
  "as_of": "2026-04-11",
  "new_brands": [
    {"brand": "SALOMON", "first_seen": "2026-04-11", "rank_now": 7.0, "appearances_now": 2}
  ]
}
```

### `GET /brands/{brand}/history`

Path param: `brand` (case-insensitive, URL-encoded). Query params:
- `source` (required)
- `days` (optional int, default 30)

```json
{
  "source": "kream",
  "brand": "new balance",
  "days": 30,
  "series": [
    {"date": "2026-04-11", "min_rank": 2, "avg_rank": 5.4, "appearances": 8},
    {"date": "2026-04-10", "min_rank": 1, "avg_rank": 4.9, "appearances": 9}
  ]
}
```

Days with no data are omitted (not zero-filled).

## Error codes

| HTTP | error | when |
|---|---|---|
| 400 | `INVALID_PARAM` | malformed date, unknown source, negative window |
| 404 | `NOT_FOUND` | snapshot id does not exist |
| 500 | `DB_ERROR` | SQLite integrity/IO problem |
| 503 | `DB_UNAVAILABLE` | DB file missing at startup |

## Curl examples

```bash
curl -s localhost:8787/health | jq
curl -s "localhost:8787/sources" | jq
curl -s "localhost:8787/snapshots?source=kream&from=2026-04-01&to=2026-04-11" | jq
curl -s "localhost:8787/trends/rising-brands?source=kream&window=7&limit=5" | jq
curl -s "localhost:8787/trends/new-brands?source=kream&window=7" | jq
curl -s "localhost:8787/brands/new%20balance/history?source=kream&days=14" | jq
```

## Non-goals

- No POST / PUT / DELETE — writes happen via the CLI only.
- No WebSocket / SSE / streaming.
- No pagination cursors (snapshots are small enough for `limit`).
- No aggregate endpoints beyond the 3 trend queries above.
- No per-user auth or rate limiting (phase 4+ if ever).
