import re

from ...schema import Product, Query
from .urls import build_product_url


PRODUCT_RE = re.compile(r"/(?:app/goods|products)/(\d+)")
IMAGE_RE = re.compile(r"https?://[^\s)\"']*image\.msscdn\.net/[^\s)\"']+")
PRICE_RE = re.compile(r"([\d,]+)\s*원")
LINK_TEXT_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def _to_int(value: str) -> int:
    return int(value.replace(",", ""))


def _clean_line(line: str) -> str:
    match = LINK_TEXT_RE.search(line)
    if match:
        return match.group(1).strip()
    return line.strip().strip("-").strip()


def _is_product_text(line: str) -> bool:
    if not line or line.startswith("!["):
        return False
    if PRODUCT_RE.search(line) or IMAGE_RE.search(line) or PRICE_RE.search(line):
        return False
    if re.fullmatch(r"\d+", line.strip()):
        return False
    return True


def _rank_from_window(lines: list[str]) -> int | None:
    for line in reversed(lines):
        match = re.match(r"^#?\s*(\d+)\s*$", line.strip())
        if match:
            return int(match.group(1))
    return None


def parse_musinsa_markdown(raw_markdown: str, query: Query, limit: int | None = None) -> list[Product]:
    lines = [line.strip() for line in raw_markdown.splitlines() if line.strip()]
    products: list[Product] = []
    seen: set[str] = set()
    max_products = limit or query.limit

    for index, line in enumerate(lines):
        match = PRODUCT_RE.search(line)
        if not match:
            continue

        product_id = match.group(1)
        if product_id in seen:
            continue
        seen.add(product_id)

        before = lines[max(0, index - 6):index]
        after = lines[index + 1:index + 8]
        window = before + [line] + after
        text_after = [_clean_line(item) for item in after if _is_product_text(item)]
        brand = _clean_line(line)
        if not brand or brand == line:
            brand = text_after[0] if text_after else ""
            text_after = text_after[1:]
        name = text_after[0] if text_after else ""

        price_match = next((PRICE_RE.search(item) for item in after if PRICE_RE.search(item)), None)
        image_lines = list(reversed(before)) + after
        image_match = next((IMAGE_RE.search(item) for item in image_lines if IMAGE_RE.search(item)), None)

        if not brand or not name:
            continue

        products.append(
            Product(
                source="musinsa",
                source_id=product_id,
                url=build_product_url(product_id),
                brand=brand,
                name=name,
                price_krw=_to_int(price_match.group(1)) if price_match else None,
                image_url=image_match.group(0) if image_match else None,
                rank=_rank_from_window(before),
                category=query.category,
                gender=query.gender,
                raw={"lines": window},
            )
        )

        if len(products) >= max_products:
            break

    return products
