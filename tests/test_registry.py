import unittest

import _path  # noqa: F401
from style_signal.registry import get_adapter, list_sources
from style_signal.sources.kream.adapter import KreamAdapter


class RegistryTest(unittest.TestCase):
    def test_lists_ready_and_stub_sources(self):
        self.assertEqual(
            list_sources(),
            ["29cm", "farfetch", "grailed", "kream", "musinsa", "ssense", "styleshare"],
        )

    def test_get_adapter(self):
        self.assertIsInstance(get_adapter("kream"), KreamAdapter)

    def test_unknown_source_raises_value_error(self):
        with self.assertRaises(ValueError) as context:
            get_adapter("unknown")

        self.assertIn("Unknown source: unknown", str(context.exception))
        self.assertIn("kream", str(context.exception))

    def test_stub_raises_clear_todo(self):
        adapter = get_adapter("ssense")

        with self.assertRaises(NotImplementedError) as context:
            adapter.build_url(None)

        self.assertIn("phase-2 contribution welcome", str(context.exception))


if __name__ == "__main__":
    unittest.main()
