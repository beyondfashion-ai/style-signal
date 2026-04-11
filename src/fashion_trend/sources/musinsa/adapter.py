from ...schema import Product, Query
from ..base import SourceAdapter
from .parser import parse_musinsa_markdown
from .urls import CATEGORY_MAP, GENDER_MAP, SORT_MAP, build_ranking_url, build_search_url


class MusinsaAdapter(SourceAdapter):
    name = "musinsa"
    supported_genders = ("men", "women", "unisex")
    supported_sorts = ("popular", "new", "price_asc", "price_desc")
    supported_categories = CATEGORY_MAP

    def build_url(self, query: Query) -> str:
        gender_token = GENDER_MAP.get(query.gender, "A")
        sort_token = SORT_MAP.get(query.sort, "POPULAR")

        if query.keyword:
            return build_search_url(query.keyword, sort_token, gender_token)

        category_code = self.supported_categories.get(query.category or "")
        if not category_code:
            raise ValueError("Musinsa requires keyword or supported category")
        return build_ranking_url(category_code, gender_token)

    def parse(self, raw_markdown: str, query: Query) -> list[Product]:
        return parse_musinsa_markdown(raw_markdown, query, limit=query.limit)

    def describe(self) -> dict:
        data = super().describe()
        data["notes"] = "Musinsa category codes are documented assumptions for Phase 1."
        return data
