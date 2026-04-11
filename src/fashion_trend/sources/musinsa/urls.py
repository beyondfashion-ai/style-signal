from urllib.parse import urlencode


MUSINSA_BASE = "https://www.musinsa.com"

SORT_MAP = {
    "popular": "POPULAR",
    "new": "NEW",
    "price_asc": "LOW_PRICE",
    "price_desc": "HIGH_PRICE",
}

GENDER_MAP = {
    None: "A",
    "unisex": "A",
    "men": "M",
    "women": "F",
}

CATEGORY_MAP = {
    "shoes": "103",
    "bags": "004",
    "tops": "001",
    "outer": "002",
    "accessories": "018",
}


def build_search_url(keyword: str, sort_token: str, gender_token: str) -> str:
    query = urlencode({"q": keyword, "sortCode": sort_token, "gf": gender_token})
    return f"{MUSINSA_BASE}/search/musinsa/goods?{query}"


def build_ranking_url(category_code: str, gender_token: str) -> str:
    query = urlencode(
        {
            "period": "NOW",
            "mainCategory": category_code,
            "subCategory": "",
            "gf": gender_token,
        }
    )
    return f"{MUSINSA_BASE}/ranking/best?{query}"


def build_product_url(product_id: str) -> str:
    return f"{MUSINSA_BASE}/app/goods/{product_id}"
