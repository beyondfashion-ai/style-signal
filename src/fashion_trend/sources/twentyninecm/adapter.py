from ...schema import Product, Query
from ..base import SourceAdapter
from .parser import parse_twentyninecm_markdown
from .urls import CATEGORY_MAP, SORT_MAP, build_category_url, build_search_url


class TwentyNineCMAdapter(SourceAdapter):
    name = "29cm"
    supported_genders = ("men", "women", "unisex")
    supported_sorts = ("popular", "recommend", "new", "price_asc", "price_desc")
    supported_categories = CATEGORY_MAP

    def build_url(self, query: Query) -> str:
        sort_token = SORT_MAP.get(query.sort, "popular")
        if query.keyword:
            return build_search_url(query.keyword, sort_token)

        category_code = self.supported_categories.get(query.category or "")
        if not category_code:
            raise ValueError("29CM requires keyword or supported category")
        return build_category_url(category_code, sort_token)

    def parse(self, raw_markdown: str, query: Query) -> list[Product]:
        return parse_twentyninecm_markdown(raw_markdown, query, limit=query.limit)
