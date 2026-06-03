# style-signal Signal Layer

The `signal` command turns a saved `fetch` JSON payload into a deterministic trend-signal report. It is the public, dependency-free version of ideas proven inside KALEI: brand frequency, evidence strength, source-quality gating, and manifest hashing.

It does not copy KALEI private data, Firebase integrations, content-generation paths, or internal scoring state.

## Command

```bash
style-signal fetch --source kream --curation top100 --gender men --limit 40 > artifacts/kream-result.json

style-signal signal \
  --input artifacts/kream-result.json \
  --manifest-output artifacts/kream-result.manifest.json
```

## Output Shape

The command writes JSON to stdout:

```json
{
  "success": true,
  "kind": "style_signal",
  "version": 1,
  "source": "kream",
  "product_count": 40,
  "summary": "kream: 40 products analyzed...",
  "scores": {
    "source_quality": 85,
    "evidence_strength": 94,
    "price_coverage": 100,
    "brand_concentration": 20,
    "overall": 82
  },
  "top_brands": [],
  "price_bands": [],
  "source_guard": {"verdict": "accept", "issues": []},
  "evidence": [],
  "manifest": {"version": 1, "hash": "..."}
}
```

## Rebalanced Scores

- `source_quality`: required product fields present; review/block issues reduce the score.
- `evidence_strength`: logarithmic score from product count plus public engagement fields.
- `price_coverage`: share of products with a usable KRW price.
- `brand_concentration`: top brand share, useful for detecting one-brand dominance.
- `overall`: weighted blend of source quality, evidence strength, price coverage, and brand concentration.

## Evidence Manifest

The manifest contains source refs, supported claims, guard issues, and a stable SHA-256 hash. If the products, brand counts, price bands, guard verdict, or evidence refs change, the hash changes.

This makes generated reports easier to audit: prose can cite a manifest rather than inventing unsupported claims.

## Source Guard

The guard rejects failed/empty fetch payloads and review-flags incomplete but usable product sets, such as rows missing image URLs. Image URLs are treated as references only; image bytes are never stored.
