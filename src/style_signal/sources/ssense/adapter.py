from ...schema import Product, Query
from ..base import SourceAdapter


TODO = "TODO: phase-2 contribution welcome — see docs/ADAPTERS.md"


class SsenseAdapter(SourceAdapter):
    name = "ssense"
    status = "stub"
    supported_categories = {}

    def build_url(self, query: Query) -> str:
        raise NotImplementedError(TODO)

    def parse(self, raw_markdown: str, query: Query) -> list[Product]:
        raise NotImplementedError(TODO)
