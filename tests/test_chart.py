import unittest
import xml.etree.ElementTree as ET

from chart import START, axis, embed, parse_log, render_svg, table, totals

LOG = """# Voice log
## Prompt 0
- Words: 100
- Spoken: 60 s
- Typing: 150 s
## Prompt 1
- Words: 200
- Spoken: 120 s
- Typing: 300 s
## Prompt 2
- Words: 50
- Spoken: ? s
- Typing: 75 s
"""
ROWS = parse_log(LOG)


class ChartTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(ROWS[0], (0, 100, 60.0, 150.0))
        self.assertEqual(ROWS[2], (2, 50, None, 75.0))

    def test_minor_cleanup_prompts_stay_off_the_chart(self):
        log = LOG + "## Prompt 3\n- Words: 9\n- Spoken: ? s\n- Typing: 14 s\n- Chart: no (minor cleanup)\n"
        self.assertEqual(parse_log(log), ROWS)

    def test_totals_skip_unknown_spoken(self):
        self.assertEqual(totals(ROWS), (3.0, 7.5, 4.5))

    def test_svg_is_valid_and_complete(self):
        svg = render_svg(ROWS)
        root = ET.fromstring(svg)
        self.assertEqual((root.get("width"), root.get("height")), ("900", "300"))
        self.assertIn("3.0 min spoken · 7.5 min typed", svg)
        self.assertIn("4.5 min saved</tspan> · 2.5× faster", svg)
        self.assertEqual(svg.count("<path"), 5)  # 3 typed + 2 known spoken bars
        for text in ("#0", "#2", ">?<", ">5.0<", "Typed at 40 wpm"):
            self.assertIn(text, svg)

    def test_axis(self):
        self.assertEqual([axis(m) for m in (0.5, 4.1, 20.5, 60, 137)],
                         [(1, 0.5), (6, 2), (30, 10), (60, 20), (150, 50)])

    def test_table(self):
        t = table(ROWS)
        self.assertIn("| 2 | 50 | ? | 1.2 | ? |", t)
        self.assertIn("| **Total** | **300** | **3.0** | **7.5** | **4.5** |", t)

    def test_table_untimed_prompt_is_unknown_not_negative(self):
        # Regression (PR #8): an untimed prompt once showed negative minutes saved.
        row = table([(9, 100, None, 150)]).splitlines()[2]
        self.assertEqual(row, "| 9 | 100 | ? | 2.5 | ? |")

    def test_embed_at_top_and_idempotent(self):
        once = embed("# Shipit\n", ROWS)
        self.assertTrue(once.startswith(START))
        self.assertIn("| Prompt | Words |", once)
        self.assertEqual(embed(once, ROWS), once)


if __name__ == "__main__":
    unittest.main()
