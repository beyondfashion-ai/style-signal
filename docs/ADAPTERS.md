# Contributing a New Source Adapter

Short guide for adding a new fashion site as a `fashion-trend` data source. Each adapter is ~150 lines of Python.

## Prerequisites

- You have a real page URL on the target site that returns product listings.
- The site is scrapable via `scrapling stealthy-fetch` (or you have a plan to extend `fetcher.py`).
- You understand the [canonical schema](../src/fashion_trend/schema.py) — `Query`, `Product`, `FetchResult`.

## Checklist

1. **Copy the stub layout**
   ```
   src/fashion_trend/sources/<name>/
   ├── __init__.py
   ├── adapter.py     # <Name>Adapter
   ├── urls.py        # URL builders + sort mapping
   └── parser.py      # markdown -> list[Product]
   ```
   Use one of the stub sources (`ssense/`, `farfetch/`, etc.) as a starting point if only `adapter.py` exists, or mirror `kream/` for a full-featured example.

2. **Implement `build_url(query: Query) -> str`**
   - Map `Query.sort` + `Query.gender` to the site's native sort token.
   - Map canonical categories (`"shoes"`, `"bags"`, `"tops"`, ...) to site-specific category codes via `supported_categories`.
   - If the site has a curation/ranking page (e.g. KREAM's TOP100 exhibitions), handle `Query.curation` here.
   - Percent-encode keywords with `urllib.parse.quote`.

3. **Implement `parse(raw_markdown: str, query: Query) -> list[Product]`**
   - Input is the markdown that `scrapling extract stealthy-fetch` produced.
   - Use plain `re` — no BeautifulSoup, no lxml. Keep it stdlib.
   - Required `Product` fields: `source`, `source_id`, `url`, `brand`, `name`, `image_url`.
   - Optional but encouraged: `price_krw`, `rank`, `interest_count`, `review_count`, `trade_count`.
   - On parse ambiguity, prefer returning fewer high-quality products over many noisy ones.

4. **Keep `detect_block` simple**
   - Default implementation in `SourceAdapter.detect_block` handles most cases (file size < 1000 + akamai/blocked/access-denied signatures).
   - Override only if the site has unique block signals (e.g. a specific redirect page or JSON error body).

5. **Write a synthetic fixture**
   - Hand-craft `tests/fixtures/<name>_sample.md` with 3+ realistic product blocks.
   - Do NOT commit scraped live data — licensing + drift risk.
   - Cover the full happy path: rank, brand, name, price, image URL, product URL.

6. **Add tests**
   - `tests/test_urls.py` — add a new test method parametrizing your sort/gender/category combos.
   - `tests/test_parsers.py` — load the fixture, assert ≥3 products and required fields populated.
   - Aim for 2–3 new tests per adapter.

7. **Register in `src/fashion_trend/registry.py`**
   ```python
   from .sources.<name>.adapter import <Name>Adapter
   _ADAPTERS["<name>"] = <Name>Adapter
   ```
   Name must be lowercase, no spaces. Prefer the brand's canonical domain stem (`kream`, `musinsa`, not `kream-korea`).

8. **Update the README status table**
   Move your adapter from "stub" to "ready" in the architecture section.

9. **Run the checks**
   ```bash
   python -m unittest discover tests
   python -m fashion_trend list-sources
   python -m fashion_trend describe --source <name>
   python -m fashion_trend fetch --source <name> --keyword "러닝화" --limit 5
   ```
   The last command needs a real network connection and `scrapling` installed. If it returns `BLOCKED`, try `--retry-on-block` and confirm the retry logic in your adapter.

## Parser patterns that work

Extracting from scrapling's markdown output, the following regex patterns cover most Korean fashion sites:

| Field | Pattern |
|---|---|
| Product ID | `/products?/(\d+)` or site-specific `/goods/(\d+)` |
| Image CDN | site-specific host regex, e.g. `[a-z0-9.-]+\.(pstatic\|msscdn\|29cm)\.[^\s)]+` |
| Price (KRW) | `([\d,]+)\s*원` → `int(match.group(1).replace(",", ""))` |
| Discount % | `(\d+)\s*%` near the price |
| Rank | Leading `#?(\d+)\s` on an exhibition/ranking page |
| Stats | `관심\s*([\d,]+)`, `리뷰\s*([\d,]+)`, `거래\s*([\d,]+)` |

## Things to avoid

- **Do not download images.** Keep URLs only — the project commits to URL-only storage for licensing reasons.
- **Do not add new runtime dependencies.** Core install must stay `scrapling[all]`-only.
- **Do not bypass `detect_block` to "always succeed".** A failing fetch is valuable signal; masking it hides site-side problems.
- **Do not scrape user-generated content** (reviews, comments, profile pages). Product listings only.
- **Do not commit scraped live data** as test fixtures. Synthesize minimal examples instead.

## Submitting

Open a PR against `main` with:
- The adapter code
- The fixture
- Tests
- README status table update
- One commit per logical chunk, conventional commit style, trailer block from [CLAUDE.md](../CLAUDE.md) commit protocol when applicable.
