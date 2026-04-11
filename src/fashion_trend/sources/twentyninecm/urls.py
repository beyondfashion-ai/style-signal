from urllib.parse import urlencode


TWENTYNINECM_BASE = "https://www.29cm.co.kr"
TWENTYNINECM_SEARCH_BASE = "https://search.29cm.co.kr"

SORT_MAP = {
    "popular": "popular",
    "recommend": "popular",
    "new": "recent",
    "price_asc": "priceAsc",
    "price_desc": "priceDesc",
}

CATEGORY_MAP = {
    "shoes": "272100100",
    "bags": "268100100",
    "tops": "255100100",
    "outer": "255100200",
    "accessories": "269100100",
}


def build_search_url(keyword: str, sort_token: str) -> str:
    query = urlencode({"keyword": keyword, "sort": sort_token})
    return f"{TWENTYNINECM_SEARCH_BASE}/search?{query}"


def build_category_url(category_code: str, sort_token: str) -> str:
    query = urlencode({"sort": sort_token})
    return f"{TWENTYNINECM_BASE}/category/{category_code}?{query}"


def build_product_url(product_id: str) -> str:
    return f"{TWENTYNINECM_BASE}/product/{product_id}"
