import unittest

import _path  # noqa: F401
from style_signal.schema import Query
from style_signal.sources.kream.adapter import KreamAdapter
from style_signal.sources.musinsa.adapter import MusinsaAdapter
from style_signal.sources.twentyninecm.adapter import TwentyNineCMAdapter


class UrlBuilderTest(unittest.TestCase):
    def test_kream_search_sort_tokens(self):
        cases = [
            ("popular", "men", "sort=male_popularity"),
            ("popular", "women", "sort=female_popularity"),
            ("recommend", None, "sort=recommend"),
            ("premium_asc", None, "sort=pricepremium%5Basc%5D"),
        ]

        for sort, gender, expected in cases:
            with self.subTest(sort=sort, gender=gender):
                url = KreamAdapter().build_url(
                    Query(source="kream", keyword="러닝화", sort=sort, gender=gender)
                )
                self.assertIn("keyword=%EB%9F%AC%EB%8B%9D%ED%99%94", url)
                self.assertIn(expected, url)

    def test_kream_top100_urls(self):
        self.assertEqual(
            KreamAdapter().build_url(Query(source="kream", curation="top100", gender="men")),
            "https://kream.co.kr/exhibitions/15243",
        )
        self.assertEqual(
            KreamAdapter().build_url(Query(source="kream", curation="top100", gender="women")),
            "https://kream.co.kr/exhibitions/15242",
        )

    def test_musinsa_search_and_ranking_urls(self):
        search_url = MusinsaAdapter().build_url(
            Query(source="musinsa", keyword="셔츠", sort="new", gender="women")
        )
        self.assertIn("https://www.musinsa.com/search/musinsa/goods", search_url)
        self.assertIn("q=%EC%85%94%EC%B8%A0", search_url)
        self.assertIn("sortCode=NEW", search_url)
        self.assertIn("gf=F", search_url)

        ranking_url = MusinsaAdapter().build_url(
            Query(source="musinsa", category="shoes", gender="men")
        )
        self.assertIn("https://www.musinsa.com/ranking/best", ranking_url)
        self.assertIn("mainCategory=103", ranking_url)
        self.assertIn("gf=M", ranking_url)

    def test_29cm_search_and_category_urls(self):
        search_url = TwentyNineCMAdapter().build_url(
            Query(source="29cm", keyword="코트", sort="price_asc")
        )
        self.assertIn("https://search.29cm.co.kr/search", search_url)
        self.assertIn("keyword=%EC%BD%94%ED%8A%B8", search_url)
        self.assertIn("sort=priceAsc", search_url)

        category_url = TwentyNineCMAdapter().build_url(
            Query(source="29cm", category="bags", sort="popular")
        )
        self.assertEqual(category_url, "https://www.29cm.co.kr/category/268100100?sort=popular")


if __name__ == "__main__":
    unittest.main()
