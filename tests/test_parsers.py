from pathlib import Path
import unittest

import _path  # noqa: F401
from fashion_trend.schema import Query
from fashion_trend.sources.kream.parser import parse_kream_markdown
from fashion_trend.sources.musinsa.parser import parse_musinsa_markdown
from fashion_trend.sources.twentyninecm.parser import parse_twentyninecm_markdown


FIXTURES = Path(__file__).parent / "fixtures"


class ParserTest(unittest.TestCase):
    def test_kream_parser_extracts_products(self):
        products = parse_kream_markdown(
            (FIXTURES / "kream_sample.md").read_text(encoding="utf-8"),
            Query(source="kream", curation="top100", gender="men", limit=3),
        )

        self.assertGreaterEqual(len(products), 3)
        first = products[0]
        self.assertEqual(first.source, "kream")
        self.assertEqual(first.source_id, "100001")
        self.assertEqual(first.brand, "NIKE")
        self.assertEqual(first.rank, 1)
        self.assertEqual(first.price_krw, 129000)
        self.assertEqual(first.discount_pct, 12)
        self.assertIn("kream-phinf.pstatic.net", first.image_url)
        self.assertEqual(first.interest_count, 3211)
        self.assertEqual(first.review_count, 42)
        self.assertEqual(first.trade_count, 258)

    def test_musinsa_parser_extracts_products(self):
        products = parse_musinsa_markdown(
            (FIXTURES / "musinsa_sample.md").read_text(encoding="utf-8"),
            Query(source="musinsa", category="tops", gender="unisex", limit=3),
        )

        self.assertGreaterEqual(len(products), 3)
        first = products[0]
        self.assertEqual(first.source, "musinsa")
        self.assertEqual(first.source_id, "200001")
        self.assertEqual(first.brand, "무신사 스탠다드")
        self.assertEqual(first.rank, 1)
        self.assertEqual(first.price_krw, 89900)
        self.assertIn("image.msscdn.net", first.image_url)

    def test_29cm_parser_extracts_products(self):
        products = parse_twentyninecm_markdown(
            (FIXTURES / "twentyninecm_sample.md").read_text(encoding="utf-8"),
            Query(source="29cm", category="outer", limit=3),
        )

        self.assertGreaterEqual(len(products), 3)
        first = products[0]
        self.assertEqual(first.source, "29cm")
        self.assertEqual(first.source_id, "300001")
        self.assertEqual(first.brand, "RECTO")
        self.assertEqual(first.rank, 1)
        self.assertEqual(first.price_original_krw, 398000)
        self.assertEqual(first.price_krw, 278600)
        self.assertEqual(first.discount_pct, 30)
        self.assertIn("img.29cm.co.kr", first.image_url)


if __name__ == "__main__":
    unittest.main()
