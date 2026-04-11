from dataclasses import asdict, dataclass, field
from typing import Literal, Optional


Gender = Literal["men", "women", "unisex"]
Sort = Literal["popular", "recommend", "new", "price_asc", "price_desc", "premium_asc"]
Curation = Literal["top100"]


@dataclass
class Query:
    source: str
    category: Optional[str] = None
    keyword: Optional[str] = None
    gender: Optional[Gender] = None
    sort: Sort = "popular"
    limit: int = 40
    curation: Optional[Curation] = None

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class Product:
    source: str
    source_id: str
    url: str
    brand: str
    name: str
    name_en: Optional[str] = None
    price_krw: Optional[int] = None
    price_original_krw: Optional[int] = None
    discount_pct: Optional[int] = None
    image_url: Optional[str] = None
    rank: Optional[int] = None
    category: Optional[str] = None
    gender: Optional[Gender] = None
    interest_count: Optional[int] = None
    review_count: Optional[int] = None
    trade_count: Optional[int] = None
    raw: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class FetchResult:
    success: bool
    query: Query
    products: list[Product]
    raw_path: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    file_size: Optional[int] = None
    attempts: int = 1

    def to_json(self) -> dict:
        data = asdict(self)
        data["query"] = self.query.to_json()
        data["products"] = [product.to_json() for product in self.products]
        return data
