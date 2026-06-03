from ...schema import Product, Query
from ..base import SourceAdapter
from .parser import parse_kream_markdown
from .urls import SORT_MAP, build_curation_url, build_search_url


class KreamAdapter(SourceAdapter):
    name = "kream"
    supported_genders = ("men", "women", "unisex")
    supported_sorts = ("popular", "recommend", "premium_asc")
    supported_curations = ("top100",)
    supported_categories = {
        "shoes": "신발",
        "sneakers": "스니커즈",
        "bags": "가방",
        "tops": "상의",
        "outer": "아우터",
        "accessories": "액세서리",
    }

    def build_url(self, query: Query) -> str:
        if query.curation == "top100":
            return build_curation_url("top100", query.gender or "men")

        keyword = query.keyword or self.supported_categories.get(query.category or "", "")
        if not keyword:
            raise ValueError("KREAM search requires keyword or category")

        sort_token = (
            SORT_MAP.get((query.sort, query.gender))
            or SORT_MAP.get((query.sort, None))
            or "male_popularity"
        )
        return build_search_url(keyword, sort_token)

    def parse(self, raw_markdown: str, query: Query) -> list[Product]:
        return parse_kream_markdown(raw_markdown, query, limit=query.limit)
