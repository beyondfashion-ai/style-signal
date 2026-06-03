import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import _path  # noqa: F401
from fashion_trend.cli import main
from fashion_trend.signals import build_signal_report


def fetch_payload(products):
    return {
        "success": True,
        "query": {
            "source": "kream",
            "category": "shoes",
            "keyword": None,
            "gender": "men",
            "sort": "popular",
            "limit": 4,
            "curation": "top100",
        },
        "products": products,
        "raw_path": "artifacts/kream-result.md",
        "error": None,
        "message": None,
        "file_size": 2048,
        "attempts": 1,
    }


PRODUCTS = [
    {
        "source": "kream",
        "source_id": "100001",
        "url": "https://kream.co.kr/products/100001",
        "brand": "NIKE",
        "name": "Air Force 1",
        "name_en": "Air Force 1 Low",
        "price_krw": 129000,
        "image_url": "https://kream-phinf.pstatic.net/item-1.jpg",
        "rank": 1,
        "category": "shoes",
        "gender": "men",
        "interest_count": 3211,
        "review_count": 42,
        "trade_count": 258,
        "raw": {},
    },
    {
        "source": "kream",
        "source_id": "100002",
        "url": "https://kream.co.kr/products/100002",
        "brand": "NIKE",
        "name": "Vomero 5",
        "price_krw": 189000,
        "image_url": "https://kream-phinf.pstatic.net/item-2.jpg",
        "rank": 2,
        "category": "shoes",
        "gender": "men",
        "interest_count": 1880,
        "review_count": 21,
        "trade_count": 140,
        "raw": {},
    },
    {
        "source": "kream",
        "source_id": "100003",
        "url": "https://kream.co.kr/products/100003",
        "brand": "ASICS",
        "name": "Gel-Kayano 14",
        "price_krw": 219000,
        "image_url": "https://kream-phinf.pstatic.net/item-3.jpg",
        "rank": 3,
        "category": "shoes",
        "gender": "men",
        "interest_count": 950,
        "review_count": 18,
        "trade_count": 88,
        "raw": {},
    },
    {
        "source": "kream",
        "source_id": "100004",
        "url": "https://kream.co.kr/products/100004",
        "brand": "NEW BALANCE",
        "name": "1906R",
        "price_krw": 159000,
        "image_url": None,
        "rank": 4,
        "category": "shoes",
        "gender": "men",
        "interest_count": 630,
        "review_count": 8,
        "trade_count": 41,
        "raw": {},
    },
]


class SignalReportTest(unittest.TestCase):
    def test_build_signal_report_scores_brands_and_price_bands(self):
        report = build_signal_report(fetch_payload(PRODUCTS), generated_at="2026-06-03T00:00:00Z")

        self.assertTrue(report["success"])
        self.assertEqual(report["kind"], "style_signal")
        self.assertEqual(report["product_count"], 4)
        self.assertEqual(report["top_brands"][0]["brand"], "NIKE")
        self.assertEqual(report["top_brands"][0]["count"], 2)
        self.assertEqual(report["top_brands"][0]["evidence_product_ids"], ["100001", "100002"])
        self.assertEqual(report["price_bands"][0]["band"], "100k-200k")
        self.assertGreater(report["scores"]["evidence_strength"], 0)
        self.assertEqual(report["source_guard"]["verdict"], "review")
        self.assertIn("products_without_image", report["source_guard"]["issues"][0]["type"])

    def test_manifest_hash_changes_when_evidence_changes(self):
        first = build_signal_report(fetch_payload(PRODUCTS), generated_at="2026-06-03T00:00:00Z")
        changed_products = [dict(product) for product in PRODUCTS]
        changed_products[0]["brand"] = "ADIDAS"
        second = build_signal_report(fetch_payload(changed_products), generated_at="2026-06-03T00:00:00Z")

        self.assertNotEqual(first["manifest"]["hash"], second["manifest"]["hash"])

    def test_signal_cli_reads_fetch_json_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "fetch.json"
            manifest_path = Path(tmpdir) / "manifest.json"
            input_path.write_text(json.dumps(fetch_payload(PRODUCTS)), encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["signal", "--input", str(input_path), "--manifest-output", str(manifest_path)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["success"])
            self.assertEqual(payload["manifest"]["path"], str(manifest_path))
            self.assertTrue(manifest_path.exists())
            self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8"))["version"], 1)

    def test_signal_cli_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "fetch.json"
            input_path.write_text("[]", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["signal", "--input", str(input_path)])

            self.assertEqual(code, 1)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["error"], "INPUT_JSON_INVALID")


if __name__ == "__main__":
    unittest.main()
