# Phase 1 — Multi-Source Adapter Architecture

> Handoff spec for implementation. Scope is locked: do not expand beyond what is listed here.
> Part of the [OPENSOURCE_ROADMAP](./OPENSOURCE_ROADMAP.md). Phases 2 and 3 have their own spec docs.

## Goal

Convert the current KREAM-only shell-scripted skill into a pluggable multi-source adapter architecture and land the **first three Korean-market adapters** fully working: KREAM, Musinsa, 29CM. Scaffold stubs for SSENSE, Farfetch, Grailed, StyleShare that register in the registry but raise `NotImplementedError` with a clear TODO.

The Claude Code skill must keep working with no user-visible regression.

## Free-source principles (applies to all phases)

- **No paid infra.** SQLite, FastAPI, Scrapling, Gemini free tier only.
- **No Firebase/Firestore** — SQLite file storage is the canonical store.
- **No Vercel/Cloud Run** for the API — target local or a free-tier VPS (fly.io free tier acceptable).
- **No paid LLMs** in the default code path — Gemini 2.5 Flash free tier for vision; Claude only runs inside the user's own Claude Code session, which they already pay for.
- **No new build tooling.** Stdlib + `argparse` + `unittest`. No pytest/ruff/mypy/black unless already present.

## Non-goals (phase 1)

- No Gemini vision tagging (phase 2).
- No database / REST API (phase 3).
- No dashboard, MCP server, Cloud Run, GitHub Actions publishing — those are explicitly cut from the roadmap per owner decision.
- No redesign of the HTML report (Claude still generates it).

## Target file layout

```
fashion-trend/
├── SKILL.md                    # updated Step 2/3 to use Python CLI
├── README.md                   # add “Architecture” section + adapter list
├── LICENSE                     # unchanged
├── pyproject.toml              # NEW
├── scripts/
│   ├── setup.sh                # extended — also pip install -e .
│   └── crawl.sh                # KEEP as deprecated thin wrapper (BC)
├── src/fashion_trend/
│   ├── __init__.py
│   ├── __main__.py             # entry for `python -m fashion_trend`
│   ├── cli.py                  # argparse CLI (fetch / list-sources / describe)
│   ├── schema.py               # Query, Product, FetchResult dataclasses
│   ├── registry.py             # name -> adapter class
│   ├── fetcher.py              # scrapling stealthy-fetch subprocess wrapper
│   └── sources/
│       ├── __init__.py
│       ├── base.py             # SourceAdapter ABC
│       ├── kream/              # FULL implementation
│       │   ├── __init__.py
│       │   ├── adapter.py
│       │   ├── urls.py
│       │   └── parser.py
│       ├── musinsa/             # FULL implementation
│       │   ├── __init__.py
│       │   ├── adapter.py
│       │   ├── urls.py
│       │   └── parser.py
│       ├── twentyninecm/        # FULL implementation (29CM)
│       │   ├── __init__.py
│       │   ├── adapter.py
│       │   ├── urls.py
│       │   └── parser.py
│       ├── ssense/              # STUB (raises NotImplementedError, registered)
│       │   └── adapter.py
│       ├── farfetch/            # STUB
│       │   └── adapter.py
│       ├── grailed/             # STUB
│       │   └── adapter.py
│       └── styleshare/          # STUB
│           └── adapter.py
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   └── kream_sample.md     # synthetic minimal sample (see below)
    ├── test_registry.py
    ├── test_kream_urls.py
    └── test_kream_parser.py
```

## Data schemas (`src/fashion_trend/schema.py`)

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

Gender = Literal["men", "women", "unisex"]
Sort = Literal["popular", "recommend", "new", "price_asc", "price_desc", "premium_asc"]
Curation = Literal["top100"]

@dataclass
class Query:
    source: str
    category: Optional[str] = None   # canonical bucket: "shoes" | "bags" | "tops" | ...
    keyword: Optional[str] = None    # free-text search term
    gender: Optional[Gender] = None
    sort: Sort = "popular"
    limit: int = 40
    curation: Optional[Curation] = None

@dataclass
class Product:
    source: str
    source_id: str
    url: str
    brand: str
    name: str
    name_en: Optional[str] = None
    price_krw: Optional[int] = None
    price_original_krw: Optional[int] = None
    discount_pct: Optional[int] = None
    image_url: Optional[str] = None
    rank: Optional[int] = None
    category: Optional[str] = None
    gender: Optional[Gender] = None
    interest_count: Optional[int] = None
    review_count: Optional[int] = None
    trade_count: Optional[int] = None
    raw: dict = field(default_factory=dict)

@dataclass
class FetchResult:
    success: bool
    query: Query
    products: list[Product]
    raw_path: Optional[str] = None
    error: Optional[str] = None      # BLOCKED | EMPTY_RESULT | NO_OUTPUT | NETWORK | PARSE_FAILED | MISSING_ARGS
    message: Optional[str] = None
    file_size: Optional[int] = None
    attempts: int = 1
```

`FetchResult.to_json()` must return a dict that JSON-serializes cleanly (include nested `query` and `products`).

## Adapter base (`src/fashion_trend/sources/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional
from ..schema import Query, Product

class SourceAdapter(ABC):
    name: str
    supported_genders: tuple[str, ...] = ("men", "women", "unisex")
    supported_sorts: tuple[str, ...] = ("popular",)
    supported_categories: dict[str, str] = {}  # canonical -> source-native token
    supported_curations: tuple[str, ...] = ()

    @abstractmethod
    def build_url(self, query: Query) -> str: ...

    @abstractmethod
    def parse(self, raw_markdown: str, query: Query) -> list[Product]: ...

    def detect_block(self, raw_markdown: str, file_size: int) -> Optional[str]:
        """Return error code if blocked/empty, else None. Default impl mirrors crawl.sh."""
        if file_size < 1000:
            lowered = raw_markdown.lower()
            if any(sig in lowered for sig in ("akamai", "blocked", "access denied", "bot detect")):
                return "BLOCKED"
            return "EMPTY_RESULT"
        return None
```

## Fetcher (`src/fashion_trend/fetcher.py`)

Thin wrapper around `scrapling extract stealthy-fetch`. Replaces the logic currently in `scripts/crawl.sh`.

Contract:

```python
def stealthy_fetch(
    url: str,
    output_path: str,
    timeout_ms: int = 40000,
    wait_ms: int = 5000,
    real_chrome: bool = False,
    scrapling_bin: Optional[str] = None,  # auto-discover if None (reuse setup.sh logic)
) -> tuple[bool, int, str]:
    """Return (success, file_size, raw_text_or_empty)."""
```

- Auto-discover `scrapling` binary: try `shutil.which("scrapling")`, then `~/Library/Python/3.{11,12,13}/bin/scrapling`, then `~/.local/bin/scrapling`. If not found, raise `FetcherNotInstalled`.
- On subprocess error, still check if output file exists (scrapling sometimes exits non-zero but writes partial output).

## Registry (`src/fashion_trend/registry.py`)

```python
from .sources.base import SourceAdapter
from .sources.kream.adapter import KreamAdapter

_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "kream":        KreamAdapter,
    "musinsa":      MusinsaAdapter,
    "29cm":         TwentyNineCMAdapter,
    "ssense":       SsenseAdapter,       # stub
    "farfetch":     FarfetchAdapter,     # stub
    "grailed":      GrailedAdapter,      # stub
    "styleshare":   StyleshareAdapter,   # stub
}

def get_adapter(name: str) -> SourceAdapter:
    if name not in _ADAPTERS:
        raise ValueError(f"Unknown source: {name}. Available: {list(_ADAPTERS)}")
    return _ADAPTERS[name]()

def list_sources() -> list[str]:
    return sorted(_ADAPTERS.keys())
```

## CLI (`src/fashion_trend/cli.py`)

Commands:

```
python -m fashion_trend list-sources
python -m fashion_trend describe --source kream
python -m fashion_trend fetch \
    --source kream \
    [--keyword "러닝화" | --category shoes | --curation top100] \
    [--gender men|women|unisex] \
    [--sort popular|recommend|new|price_asc|price_desc|premium_asc] \
    [--limit 40] \
    [--raw-output PATH] \
    [--timeout-ms 40000] \
    [--retry-on-block]
```

- `fetch` prints a JSON-encoded `FetchResult` to stdout.
- On success: exit 0.
- On failure: exit 1, still prints the JSON error payload to stdout.
- `--retry-on-block`: on `BLOCKED`, sleep 30s and retry once (preserving current SKILL.md behavior). `attempts` in the result reflects this.
- `--raw-output` path defaults to `artifacts/{source}-result.md` relative to CWD; create parent dirs.

## KREAM adapter specifics

### `sources/kream/urls.py`

```python
KREAM_BASE = "https://kream.co.kr"

SORT_MAP = {
    ("popular", "men"):     "male_popularity",
    ("popular", "women"):   "female_popularity",
    ("recommend", None):    "recommend",
    ("premium_asc", None):  "pricepremium[asc]",
}

TOP100 = {
    "men":   f"{KREAM_BASE}/exhibitions/15243",
    "women": f"{KREAM_BASE}/exhibitions/15242",
}

def build_search_url(keyword: str, sort_token: str) -> str: ...
def build_curation_url(curation: str, gender: str) -> str: ...
def build_product_url(product_id: str) -> str: ...
```

### `sources/kream/parser.py`

Input: markdown from scrapling (KREAM search results or exhibition page).
Output: `list[Product]`.

Extraction rules:
- Product URL: regex `/products/(\d+)` → `source_id`
- Image URL: match `kream-phinf\.pstatic\.net/[^\s)]+`
- Brand + name: adjacent lines around the product link; heuristic — first line is brand (uppercase or short), next is Korean name, optional English follows
- Price: `[\d,]+원` → int
- Discount: `\d+%` near price
- Rank: leading `#?\d+` if present (TOP100 pages)
- Stats (관심/리뷰/거래): `관심\s*([\d,]+)`, `리뷰\s*([\d,]+)`, `거래\s*([\d,]+)`

Return empty list on parse failure — caller decides whether this is `EMPTY_RESULT` or `PARSE_FAILED`.

### `sources/kream/adapter.py`

```python
class KreamAdapter(SourceAdapter):
    name = "kream"
    supported_genders = ("men", "women", "unisex")
    supported_sorts = ("popular", "recommend", "premium_asc")
    supported_curations = ("top100",)
    supported_categories = {
        # canonical -> KREAM native keyword
        "shoes":    "신발",
        "sneakers": "스니커즈",
        "bags":     "가방",
        "tops":     "상의",
        "outer":    "아우터",
        "accessories": "액세서리",
    }

    def build_url(self, query: Query) -> str:
        if query.curation == "top100":
            return build_curation_url("top100", query.gender or "men")
        keyword = query.keyword or self.supported_categories.get(query.category or "", "")
        if not keyword:
            raise ValueError("KREAM search requires keyword or category")
        sort_token = SORT_MAP.get((query.sort, query.gender)) or SORT_MAP.get((query.sort, None)) or "male_popularity"
        return build_search_url(keyword, sort_token)

    def parse(self, raw_markdown: str, query: Query) -> list[Product]:
        return parse_kream_markdown(raw_markdown, query, limit=query.limit)
```

## Additional adapters (Musinsa, 29CM)

Implement these to real parity with KREAM. They must pass the same acceptance checks (URL builder + parser + fixture test).

### Musinsa

- Base: `https://www.musinsa.com`
- Search: `https://www.musinsa.com/search/musinsa/goods?q={keyword}&sortCode={sort}`
- Sort tokens: `POPULAR` (popular), `NEW` (new), `LOW_PRICE` (price_asc), `HIGH_PRICE` (price_desc)
- Gender: query param `gf=A|M|F` (all/men/women) — map to supported_genders
- Ranking page: `https://www.musinsa.com/ranking/best?period=NOW&mainCategory=&subCategory=&gf={M|F}`
- Canonical category → Musinsa mainCategory code map (at minimum: shoes=`103`, bags=`004`, tops=`001`, outer=`002`, accessories=`018`). Codex may verify codes against a live page; if uncertain, document the assumption and surface in `describe`.
- Parser: extract product id from `/app/goods/{id}` or `/products/{id}`, image CDN `image.msscdn.net`, brand (Korean), name, price `[\d,]+원`, rank from list index.

### 29CM

- Base: `https://www.29cm.co.kr`
- Category URL pattern: `https://www.29cm.co.kr/category/{code}` with sort query `?sort=recent|popular|priceAsc|priceDesc`
- Gender handled via category code (29CM categorizes by department)
- Keyword search: `https://search.29cm.co.kr/search?keyword={keyword}&sort={sort}`
- Parser: product URL pattern `/product/{id}`, image CDN `img.29cm.co.kr`, brand, name, price, sale price

### Stubs (SSENSE / Farfetch / Grailed / StyleShare)

Each stub adapter must:
1. Inherit from `SourceAdapter`
2. Set `name` and minimal `supported_categories` (can be empty dict)
3. `build_url` and `parse` raise `NotImplementedError("TODO: phase-2 contribution welcome — see docs/ADAPTERS.md")`
4. Be registered in `_ADAPTERS` so `list-sources` shows them
5. `describe` clearly marks them as `status: "stub"`

Add a top-level `status` field to the `describe` output: `"ready"` for kream/musinsa/29cm, `"stub"` for the rest.

## `pyproject.toml`

```toml
[project]
name = "fashion-trend"
version = "0.2.0"
description = "Pluggable fashion trend crawler + report skill"
requires-python = ">=3.11"
dependencies = [
    "scrapling[all]>=0.3",
]

[project.scripts]
fashion-trend = "fashion_trend.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fashion_trend"]
```

## `scripts/setup.sh` changes

After scrapling install, run `pip3 install -e "${SKILL_DIR}"` so `python -m fashion_trend` works from anywhere. Keep `check` / `install` / `path` action contract.

## `scripts/crawl.sh` changes

Keep file + signature for backward compat. Add a deprecation comment at the top pointing at the Python CLI. Do NOT delete — SKILL.md phase-1 still may call it for raw fetches.

## `SKILL.md` changes

Only Steps 2 and 3 change meaningfully.

**Step 2 (new):**

```bash
python -m fashion_trend fetch \
    --source kream \
    --curation top100 \         # OR --keyword "..."
    --gender men \
    --sort popular \
    --limit 40 \
    --raw-output "${SKILL_DIR}/../../artifacts/kream-result.md" \
    --retry-on-block \
    > "${SKILL_DIR}/../../artifacts/kream-result.json"
```

The JSON already contains parsed `products`. Step 3 becomes: Read the JSON, skip manual markdown parsing.

**Step 3 (new):** Read `kream-result.json` directly. Only fall back to the raw markdown if `products` is empty.

Steps 0, 1, 4, 5 unchanged in logic — only reference the new CLI where relevant.

## Tests

Minimum viable fixture — hand-write a synthetic `tests/fixtures/kream_sample.md` containing 3 products with realistic markdown patterns. Do not scrape a live page.

Tests:
1. `test_registry.py` — `list_sources() == ["kream"]`; `get_adapter("kream")` returns `KreamAdapter`; unknown source raises `ValueError`.
2. `test_kream_urls.py` — parametrize: (sort, gender) pairs → correct `SORT_MAP` token; curation `top100` + men/women → correct exhibition URL.
3. `test_kream_parser.py` — parse fixture, assert ≥3 products, assert required fields populated (brand, name, url, source_id, price_krw, image_url).

Run with `python -m unittest discover tests` (no pytest dependency).

## Acceptance criteria

1. `python -m fashion_trend list-sources` → `kream`
2. `python -m fashion_trend describe --source kream` → JSON with `supported_categories`, `supported_genders`, `supported_sorts`, `supported_curations`
3. `python -m fashion_trend fetch --source kream --curation top100 --gender men --limit 10` → exits 0 with JSON `{success: true, products: [...]}` when network works; exits 1 with `{success: false, error: "BLOCKED"|"EMPTY_RESULT"}` when blocked. (Manual verification only — no network test in CI.)
4. `python -m unittest discover tests` → all green.
5. `bash scripts/crawl.sh /path/to/scrapling URL out.md 40000` still works unchanged (BC).
6. `SKILL.md` Step 2/3 updated to new CLI; other steps untouched.
7. `README.md` gains an “Architecture” section explaining the adapter pattern and how to add a new source in ≤ 10 lines of prose.
8. No new runtime dependencies beyond `scrapling[all]`.

## Commit policy

One commit per logical chunk, conventional commit style:

- `feat(core): add fashion_trend package skeleton and schemas`
- `feat(core): add SourceAdapter base + registry`
- `feat(kream): port KREAM logic into adapter`
- `feat(cli): add fetch/list-sources/describe commands`
- `test: add KREAM parser and URL tests`
- `docs(skill): switch SKILL.md Step 2/3 to Python CLI`
- `docs(readme): add architecture section`
- `chore(setup): pip install -e . in setup.sh`

Include the trailer block from the user’s commit protocol on each commit (Constraint / Rejected / Confidence / Scope-risk / Directive where relevant).

## Out of scope — reject if requested

- Adding any source other than KREAM.
- Changing the HTML report template.
- Introducing pytest, ruff, mypy, or other new dev tools.
- Adding async / concurrency.
- Touching LICENSE or disclaimer.
