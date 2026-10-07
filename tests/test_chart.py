import unittest

from chart import START, embed, parse_log, render_svg

LOG = """# Voice log
## Prompt 0
- Spoken: ? s
- Typing: 248 s
## Prompt 1
- Spoken: 60 s
- Typing: 120 s
"""


class ChartTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_log(LOG), [(0, None, 248.0), (1, 60.0, 120.0)])

    def test_svg_has_bars(self):
        svg = render_svg(parse_log(LOG))
        self.assertTrue(svg.startswith("<svg"))
        self.assertEqual(svg.count("<rect"), 4)  # background + 3 bars

    def test_embed_at_top_and_idempotent(self):
        rows = parse_log(LOG)
        once = embed("# Shipit\n", rows)
        self.assertTrue(once.startswith(START))
        self.assertIn("Time saved so far: 1.0 min", once)
        self.assertEqual(embed(once, rows), once)


if __name__ == "__main__":
    unittest.main()
