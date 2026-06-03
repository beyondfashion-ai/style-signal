from urllib.parse import urlencode


KREAM_BASE = "https://kream.co.kr"

SORT_MAP = {
    ("popular", "men"): "male_popularity",
    ("popular", "women"): "female_popularity",
    ("recommend", None): "recommend",
    ("premium_asc", None): "pricepremium[asc]",
}

TOP100 = {
    "men": f"{KREAM_BASE}/exhibitions/15243",
    "women": f"{KREAM_BASE}/exhibitions/15242",
}


def build_search_url(keyword: str, sort_token: str) -> str:
    query = urlencode({"keyword": keyword, "tab": "products", "sort": sort_token})
    return f"{KREAM_BASE}/search?{query}"


def build_curation_url(curation: str, gender: str) -> str:
    if curation != "top100":
        raise ValueError(f"Unsupported KREAM curation: {curation}")
    if gender not in TOP100:
        raise ValueError("KREAM top100 requires gender men or women")
    return TOP100[gender]


def build_product_url(product_id: str) -> str:
    return f"{KREAM_BASE}/products/{product_id}"
