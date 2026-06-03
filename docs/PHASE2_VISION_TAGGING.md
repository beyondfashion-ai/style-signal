# Phase 2 — Gemini Vision Auto-Tagging Layer

> Handoff spec. Read [PHASE1_REFACTOR_PLAN.md](./PHASE1_REFACTOR_PLAN.md) first — this builds on the adapter + schema scaffolding.

## Goal

After a fetch, optionally tag each product's image with style / color / silhouette / aesthetic labels using **Gemini 2.5 Flash (free tier)**. Tags get stored on `Product.tags` and feed into the Claude-generated HTML report as higher-quality editorial evidence.

## Free-source constraints

- **Gemini 2.5 Flash only** via `google-genai` SDK — free tier gives 10 RPM / 250 req/day as of 2026-04, which covers a full daily style-signal run (typically <= 40 images).
- **No paid APIs.** No OpenAI, no Claude vision, no Replicate.
- **No image storage.** Send the CDN URL directly to Gemini — do not download, do not cache to disk in phase 2 (phase 3 DB covers persistence).
- **Fallback is a silent no-op** — if `GEMINI_API_KEY` missing or quota exceeded, `tags` stays empty and the fetch still succeeds. Never block the core fetch flow on tagging.

## Data changes

Extend `Product` in `src/style_signal/schema.py`:

```python
@dataclass
class ProductTags:
    styles: list[str] = field(default_factory=list)        # e.g. ["minimal", "techwear", "gorpcore"]
    colors: list[str] = field(default_factory=list)        # e.g. ["off-white", "navy"]
    silhouette: Optional[str] = None                        # e.g. "oversized", "slim", "cropped"
    materials: list[str] = field(default_factory=list)     # e.g. ["leather", "nylon"]
    aesthetic: Optional[str] = None                         # e.g. "quiet luxury", "y2k"
    confidence: float = 0.0                                 # 0..1
    model: str = "gemini-2.5-flash"
    tagged_at: Optional[str] = None                         # ISO8601

@dataclass
class Product:
    # ... existing fields ...
    tags: Optional[ProductTags] = None
```

Keep backward compat: `tags=None` when tagging is disabled. JSON output must skip `None` values cleanly.

## Module layout (additions only)

```
src/style_signal/
├── tagging/
│   ├── __init__.py
│   ├── base.py            # Tagger ABC
│   ├── gemini.py          # GeminiVisionTagger
│   └── prompts.py         # prompt template (editable, versioned)
```

## Tagger ABC (`tagging/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Iterable
from ..schema import Product, ProductTags

class Tagger(ABC):
    name: str

    @abstractmethod
    def tag(self, product: Product) -> ProductTags | None: ...

    def tag_batch(self, products: Iterable[Product]) -> list[Product]:
        """Default: sequential with error isolation. Override for batching."""
        out = []
        for p in products:
            try:
                p.tags = self.tag(p)
            except Exception as e:
                p.tags = None  # silent fallback
            out.append(p)
        return out
```

## Gemini implementation (`tagging/gemini.py`)

- Use `google-genai` (the newer SDK, not `google-generativeai`). Add to `pyproject.toml` as an **optional** dependency group: `[project.optional-dependencies] tagging = ["google-genai>=0.3"]`. Core install must not pull it.
- Lazy import — if the package isn't installed, `GeminiVisionTagger.__init__` raises a clear `ImportError` saying `pip install "style-signal[tagging]"`.
- API key: env var `GEMINI_API_KEY`. If missing, raise `TaggerNotConfigured`.
- Rate limit: built-in simple token bucket at 8 req/min (leave 20% headroom under free tier).
- Retry: on 429 or 5xx, exponential backoff 2s/4s/8s, max 3 attempts, then return `None`.
- Input: pass `product.image_url` (HTTPS) directly as a `Part.from_uri` (Gemini supports URL inputs for public CDNs; for KREAM `kream-phinf.pstatic.net` confirm it works — if not, fall back to downloading to bytes via stdlib `urllib` with 5s timeout, then `Part.from_bytes`).
- Output parsing: request JSON mode via `response_schema`. If the SDK version does not support `response_schema`, ask for a JSON block and parse with `json.loads` on the first code fence.

### Prompt template (`tagging/prompts.py`)

Fixed, versioned, single-prompt. No chain-of-thought. Concise.

```
You are a fashion product taxonomist. Given a product image and metadata, return strict JSON with these keys:
- styles: 1–3 short style descriptors (lowercase, en, hyphenated), e.g. ["minimal", "techwear"]
- colors: dominant 1–3 colors in plain English, e.g. ["off-white", "navy"]
- silhouette: one of ["oversized","relaxed","regular","slim","cropped","longline"] or null
- materials: visible materials, 1–3 items
- aesthetic: one short phrase or null
- confidence: float 0..1

Return ONLY the JSON object, no prose.
```

Include product metadata (brand, name, category) in the user-part as context alongside the image.

## CLI changes

Extend `fetch` with two flags:

```
--tag                    # enable tagging
--tag-limit N            # tag only top N products (default 20)
```

And a new standalone command:

```
python -m style_signal tag \
    --input artifacts/kream-result.json \
    --output artifacts/kream-result.tagged.json \
    --limit 20
```

Purpose: re-tag an existing fetch result without re-crawling. Idempotent — skips products that already have non-null `tags`.

## SKILL.md touch-up

Add a new optional sub-step between current Step 4 and Step 5:

> **Step 4.5 — 스타일 태깅 (선택, GEMINI_API_KEY 있을 때만)**
>
> ```bash
> python -m style_signal tag --input kream-result.json --output kream-result.tagged.json --limit 20
> ```
>
> `tags` 필드가 채워져 있으면 Step 5 인사이트 프롬프트에 "스타일/색/실루엣 태그를 근거로 본 트렌드 요약" 지시를 추가한다.

Keep this step silent-skippable — if `GEMINI_API_KEY` env var is unset, the fetch CLI should log one warning line and proceed.

## Tests

- `tests/test_gemini_prompt.py` — assert the prompt template string contains all required keys and the required JSON structure hint (no network call).
- `tests/test_tagger_fallback.py` — instantiate a mock `Tagger` that raises; call `tag_batch` over 3 products; assert all 3 come back with `tags=None` and no exception propagates.
- `tests/test_tagger_contract.py` — stub a fake Gemini response string with valid JSON; pass it through the parsing helper; assert `ProductTags` fields populate correctly.

No live network tests. Keep CI offline.

## Acceptance criteria

1. `pip install -e ".[tagging]"` installs `google-genai`; plain `pip install -e .` does not.
2. `python -m style_signal fetch --source kream --curation top100 --gender men --tag --tag-limit 5` returns JSON where first 5 products have `tags` populated (given a valid `GEMINI_API_KEY`); remaining products have `tags: null`.
3. With `GEMINI_API_KEY` unset, the same command still succeeds — all products have `tags: null`, one stderr warning is printed, exit 0.
4. `python -m style_signal tag --input X --output Y` works standalone and is idempotent on re-run.
5. Tests pass offline via `python -m unittest discover tests`.
6. No new required dependency in the core install.

## Out of scope

- Local vision models (CLIP, etc.) — phase 4+.
- Training/finetuning.
- Ingesting tags into a database — phase 3 owns that.
- UI for reviewing tags.
