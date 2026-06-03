# style-signal Data Schema and Ethics

Phase 3 persists every fetch as a snapshot in a local SQLite file. This document is the canonical reference for the schema, the ethical stance, and the dataset license.

## Why SQLite

- **Free.** Zero infra cost, zero external service.
- **Portable.** The `.sqlite` file is a single artifact — commit it to a release, attach it to a GitHub Issue, copy it onto any machine.
- **Offline-first.** No network dependency for queries, no cloud lock-in.
- **Small enough.** A daily snapshot of 40 products × 365 days × 7 sources = ~100k rows, well under SQLite's comfort zone.

Firebase, Postgres, and Supabase were all rejected for these reasons (see [OPENSOURCE_ROADMAP.md](./OPENSOURCE_ROADMAP.md) free-source stance).

## Default location

```
./data/style_signal.sqlite
```

Override with `--db PATH` on the CLI or `STYLE_SIGNAL_DB` env var. Parent directory is created on first write.

## Tables

### `snapshots`

One row per `(source, feed, fetch_date)` triple. Re-running a fetch on the same UTC day replaces the existing row.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `source` | TEXT NOT NULL | Registered adapter name (`kream`, `musinsa`, ...) |
| `query_json` | TEXT NOT NULL | JSON of the canonical feed signature — `{source, category, keyword, gender, sort, curation}`. Excludes `limit` so 40-item and 100-item fetches of the same feed collapse. |
| `fetched_at` | TEXT NOT NULL | ISO-8601 UTC timestamp of the fetch |
| `fetch_date` | TEXT NOT NULL | `YYYY-MM-DD` UTC, used for daily uniqueness |
| `product_count` | INTEGER NOT NULL | Number of products in this snapshot |
| `raw_path` | TEXT NULL | Optional pointer to the `artifacts/*.md` raw crawl output |

Unique constraint: `(source, query_json, fetch_date)`. `ON CONFLICT REPLACE` to support daily upserts.

### `products`

| Column | Type | Notes |
|---|---|---|
| `snapshot_id` | INTEGER NOT NULL | FK → `snapshots(id)` ON DELETE CASCADE |
| `rank` | INTEGER NULL | 1-based rank in the listing (null if the source does not rank) |
| `source_id` | TEXT NOT NULL | Product ID on the source site |
| `brand` | TEXT NOT NULL | Brand name, normalized where possible |
| `name` | TEXT NOT NULL | Product name (usually Korean) |
| `name_en` | TEXT NULL | English product name if available |
| `price_krw` | INTEGER NULL | Current trading / listing price in KRW |
| `price_original_krw` | INTEGER NULL | Original / list price in KRW (pre-discount) |
| `discount_pct` | INTEGER NULL | Integer percentage, 0–99 |
| `image_url` | TEXT NULL | HTTPS URL on the source's CDN |
| `url` | TEXT NULL | Canonical product page URL |
| `category` | TEXT NULL | Canonical category (`shoes`, `bags`, ...) |
| `gender` | TEXT NULL | `men` / `women` / `unisex` |
| `interest_count` | INTEGER NULL | Source-reported interest / wishlist count |
| `review_count` | INTEGER NULL | Source-reported review count |
| `trade_count` | INTEGER NULL | Source-reported trade / order count |
| `tags_json` | TEXT NULL | Serialized `ProductTags` from Phase 2 Gemini tagging, or NULL |

Primary key: `(snapshot_id, source_id)`. Indexes on `brand`, `(snapshot_id, brand)`, and `(source, fetch_date)` to keep trend queries cheap.

### `schema_version`

Single-row sentinel for future migration support. Phase 3 bootstraps with version `1`.

```sql
CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES (1);
```

## Data ethics — what we store and what we don't

### What we store

- Product metadata: brand, name, price, discount, category, gender, stats.
- **Image URLs**, not image bytes. If the source CDN takes a URL down, it's gone from our dataset.
- Product page URLs.
- AI-generated tags (Phase 2) — derived work, our own output, no upstream copyright.

### What we explicitly do NOT store

- **Image bytes.** Never download, never cache. The URL-only stance is the single most important rule.
- **User-generated content.** No reviews, no comments, no user profiles. Even if a scraper incidentally pulls them in, the parser must drop them.
- **Pricing telemetry** beyond what the product listing publicly shows. No per-user prices, no logged-in-only data.
- **Personal data** of any kind.
- **Full page HTML archives** — only the parsed product fields land in the DB. Raw markdown in `artifacts/` is gitignored.

### Why

The upstream project's disclaimer (see [README.md](../README.md)) establishes that this tool is for personal learning and research. Commercial redistribution of product images, brand marks, or other copyrighted material is out of scope. Storing URLs instead of bytes keeps us downstream of the source's own takedown controls — if they delete a product, we lose access automatically, which is the correct ethical default.

## Dataset license

The SQLite database file, when shared as a release asset or published anywhere, is licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. See [`DATA_LICENSE`](../DATA_LICENSE) at the repo root.

- ✅ Academic research
- ✅ Personal learning and portfolio projects
- ✅ Non-commercial visualization and exploration
- ❌ Commercial products or services
- ❌ Reselling the dataset
- ❌ Training commercial ML models (dual-license the tags-only derivative if you need this — ask the owner)

The **code** remains under MIT (see [`LICENSE`](../LICENSE)). Only the data artifact is CC BY-NC.

## Retention

There is no automatic retention policy. The DB grows append-only (modulo same-day upserts). If you want to prune:

```sql
DELETE FROM snapshots WHERE fetch_date < date('now', '-90 days');
```

`products` rows cascade via the FK.

## Consuming the data

- **SQL directly:** `sqlite3 data/style_signal.sqlite` and query the tables above.
- **Python:** `from style_signal.storage.queries import rising_brands, new_brands, brand_history`.
- **REST API:** see [API.md](./API.md).
- **Pandas:** `pandas.read_sql("SELECT * FROM products WHERE snapshot_id = ?", conn, params=[42])`.

## Non-goals

- No columnar/analytic store (DuckDB, ClickHouse). SQLite is enough.
- No cross-source brand identity resolution. "NEW BALANCE" and "new balance" are compared case-insensitively in queries but stored as-seen.
- No time-zone awareness beyond UTC. All `fetch_date` / `fetched_at` values are UTC.
- No schema migrations in Phase 3 — plain `CREATE TABLE IF NOT EXISTS`. If the schema changes, bump `schema_version` manually.
