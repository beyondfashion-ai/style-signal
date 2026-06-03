from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from statistics import mean
from typing import Any


SIGNAL_KIND = "style_signal"
SIGNAL_VERSION = 1
MANIFEST_VERSION = 1

PRICE_BANDS = (
    (None, 50_000, "under-50k"),
    (50_000, 100_000, "50k-100k"),
    (100_000, 200_000, "100k-200k"),
    (200_000, 500_000, "200k-500k"),
    (500_000, None, "500k+"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split())


def _number(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _price_band(price_krw: Any) -> str | None:
    price = _number(price_krw)
    if not price:
        return None

    for low, high, label in PRICE_BANDS:
        if low is None and price < high:
            return label
        if high is None and price >= low:
            return label
        if low is not None and high is not None and low <= price < high:
            return label
    return None


def _product_id(product: dict[str, Any], index: int) -> str:
    return _clean_text(product.get("source_id")) or f"row-{index + 1}"


def _rank(product: dict[str, Any], fallback: int) -> int:
    return _number(product.get("rank")) or fallback


def _share(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def _source_from_payload(payload: dict[str, Any], products: list[dict[str, Any]]) -> str:
    query = payload.get("query") or {}
    return _clean_text(query.get("source")) or _clean_text(products[0].get("source") if products else "") or "unknown"


def _score_evidence_strength(products: list[dict[str, Any]]) -> int:
    volume = len(products)
    for product in products:
        volume += _number(product.get("interest_count"))
        volume += _number(product.get("review_count"))
        volume += _number(product.get("trade_count"))
    if volume <= 0:
        return 0
    return min(100, round(math.log10(volume + 1) * 25))


def _build_source_guard(payload: dict[str, Any], products: list[dict[str, Any]]) -> dict[str, Any]:
    if not payload.get("success", False):
        return {
            "verdict": "reject",
            "issues": [
                {
                    "type": "input_fetch_failed",
                    "count": 1,
                    "severity": "block",
                    "detail": payload.get("error") or payload.get("message") or "fetch payload was not successful",
                }
            ],
        }

    required_fields = ("source_id", "url", "brand", "name")
    issues = []
    for field in required_fields:
        missing = sum(1 for product in products if not _clean_text(product.get(field)))
        if missing:
            issues.append(
                {
                    "type": f"products_without_{field}",
                    "count": missing,
                    "severity": "block",
                    "detail": f"{missing} product(s) are missing {field}",
                }
            )

    missing_images = sum(1 for product in products if not _clean_text(product.get("image_url")))
    if missing_images:
        issues.append(
            {
                "type": "products_without_image",
                "count": missing_images,
                "severity": "review",
                "detail": f"{missing_images} product(s) have no image URL",
            }
        )

    if not products:
        issues.append(
            {
                "type": "empty_product_set",
                "count": 1,
                "severity": "block",
                "detail": "no products available for signal analysis",
            }
        )

    if any(issue["severity"] == "block" for issue in issues):
        verdict = "reject"
    elif issues:
        verdict = "review"
    else:
        verdict = "accept"

    return {"verdict": verdict, "issues": issues}


def _build_top_brands(products: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, product in enumerate(products):
        brand = _clean_text(product.get("brand"))
        if brand:
            grouped[brand].append((index, product))

    total = len(products)
    brands = []
    for brand, items in grouped.items():
        ranks = [_rank(product, index + 1) for index, product in items]
        ordered = sorted(items, key=lambda item: _rank(item[1], item[0] + 1))
        brands.append(
            {
                "brand": brand,
                "count": len(items),
                "share": _share(len(items), total),
                "avg_rank": round(mean(ranks), 2),
                "evidence_product_ids": [_product_id(product, index) for index, product in ordered[:5]],
            }
        )

    return sorted(brands, key=lambda item: (-item["count"], item["avg_rank"], item["brand"]))[:limit]


def _build_price_bands(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    band_order = {label: index for index, (_, _, label) in enumerate(PRICE_BANDS)}

    for index, product in enumerate(products):
        band = _price_band(product.get("price_krw"))
        if band:
            grouped[band].append((index, product))

    total = sum(len(items) for items in grouped.values())
    bands = []
    for band, items in grouped.items():
        ordered = sorted(items, key=lambda item: _rank(item[1], item[0] + 1))
        bands.append(
            {
                "band": band,
                "count": len(items),
                "share": _share(len(items), total),
                "evidence_product_ids": [_product_id(product, index) for index, product in ordered[:5]],
            }
        )

    return sorted(bands, key=lambda item: (-item["count"], band_order[item["band"]]))


def _build_evidence_refs(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = []
    for index, product in enumerate(products):
        source = _clean_text(product.get("source")) or "unknown"
        source_id = _product_id(product, index)
        refs.append(
            {
                "id": f"product:{source}:{source_id}",
                "source": source,
                "source_id": source_id,
                "brand": _clean_text(product.get("brand")) or None,
                "name": _clean_text(product.get("name")) or None,
                "url": _clean_text(product.get("url")) or None,
                "rank": _number(product.get("rank")) or None,
                "price_krw": _number(product.get("price_krw")) or None,
            }
        )
    return refs


def _build_claims(top_brands: list[dict[str, Any]], price_bands: list[dict[str, Any]], guard: dict[str, Any]) -> list[dict[str, Any]]:
    claims = []
    for brand in top_brands:
        claims.append(
            {
                "id": f"brand:{brand['brand'].lower()}",
                "type": "brand_frequency",
                "text": f"{brand['brand']} appears in {brand['count']} product(s)",
                "support": "supported",
                "gate_severity": "none",
                "evidence_product_ids": brand["evidence_product_ids"],
            }
        )

    for band in price_bands:
        claims.append(
            {
                "id": f"price_band:{band['band']}",
                "type": "price_band",
                "text": f"{band['band']} contains {band['count']} priced product(s)",
                "support": "supported",
                "gate_severity": "none",
                "evidence_product_ids": band["evidence_product_ids"],
            }
        )

    for issue in guard["issues"]:
        claims.append(
            {
                "id": f"guard:{issue['type']}",
                "type": "source_guard",
                "text": issue["detail"],
                "support": "review_required" if issue["severity"] == "review" else "unsupported",
                "gate_severity": "advisory" if issue["severity"] == "review" else "block",
                "evidence_product_ids": [],
            }
        )

    return claims[:24]


def _build_scores(products: list[dict[str, Any]], guard: dict[str, Any], top_brands: list[dict[str, Any]], price_bands: list[dict[str, Any]]) -> dict[str, int]:
    product_count = len(products)
    required_complete = sum(
        1
        for product in products
        if all(_clean_text(product.get(field)) for field in ("source_id", "url", "brand", "name"))
    )
    source_quality = round((required_complete / product_count) * 100) if product_count else 0
    if guard["verdict"] == "review":
        source_quality = min(source_quality, 85)
    elif guard["verdict"] == "reject":
        source_quality = min(source_quality, 30)

    brand_concentration = round((top_brands[0]["count"] / product_count) * 100) if product_count and top_brands else 0
    price_coverage = round((sum(band["count"] for band in price_bands) / product_count) * 100) if product_count else 0
    evidence_strength = _score_evidence_strength(products)
    overall = round(source_quality * 0.35 + evidence_strength * 0.35 + price_coverage * 0.15 + brand_concentration * 0.15)

    return {
        "source_quality": source_quality,
        "evidence_strength": evidence_strength,
        "price_coverage": price_coverage,
        "brand_concentration": brand_concentration,
        "overall": overall,
    }


def _build_summary(source: str, top_brands: list[dict[str, Any]], price_bands: list[dict[str, Any]], product_count: int) -> str:
    if not product_count:
        return f"{source}: no products available for signal analysis."

    brand_text = ", ".join(f"{item['brand']}({item['count']})" for item in top_brands[:3]) or "no brand signal"
    band_text = ", ".join(f"{item['band']}({item['count']})" for item in price_bands[:2]) or "no price signal"
    return f"{source}: {product_count} products analyzed. Top brand signals: {brand_text}. Price balance: {band_text}."


def build_signal_report(
    fetch_payload: dict[str, Any],
    *,
    generated_at: str | None = None,
    top_limit: int = 10,
) -> dict[str, Any]:
    products = [product for product in fetch_payload.get("products") or [] if isinstance(product, dict)]
    source = _source_from_payload(fetch_payload, products)
    generated_at = generated_at or _now_iso()
    top_brands = _build_top_brands(products, top_limit)
    price_bands = _build_price_bands(products)
    source_guard = _build_source_guard(fetch_payload, products)
    evidence_refs = _build_evidence_refs(products)
    claims = _build_claims(top_brands, price_bands, source_guard)
    scores = _build_scores(products, source_guard, top_brands, price_bands)
    summary = _build_summary(source, top_brands, price_bands, len(products))

    manifest_body = {
        "version": MANIFEST_VERSION,
        "kind": SIGNAL_KIND,
        "source": source,
        "query": fetch_payload.get("query") or {},
        "product_count": len(products),
        "top_brands": top_brands,
        "price_bands": price_bands,
        "source_guard": source_guard,
        "claims": claims,
        "evidence_refs": evidence_refs,
    }
    manifest = {**manifest_body, "hash": _sha256(manifest_body)}

    return {
        "success": source_guard["verdict"] != "reject",
        "kind": SIGNAL_KIND,
        "version": SIGNAL_VERSION,
        "generated_at": generated_at,
        "source": source,
        "query": fetch_payload.get("query") or {},
        "product_count": len(products),
        "summary": summary,
        "scores": scores,
        "top_brands": top_brands,
        "price_bands": price_bands,
        "source_guard": source_guard,
        "evidence": evidence_refs[:top_limit],
        "manifest": manifest,
    }
