import io
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import stats
from shipit import cli

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
sys.path.insert(0, str(DOCS))
import build  # noqa: E402

def flags():
    """Every long flag, read from `shipit --help`."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            cli.args(["--help"])
        except SystemExit:
            pass
    return sorted(set(re.findall(r"--[a-z][a-z-]+", buf.getvalue())) - {"--help"})


class DocsTest(unittest.TestCase):
    def test_every_flag_documented(self):
        found = flags()
        self.assertGreaterEqual(len(found), 10)
        commands = (DOCS / "commands.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for flag in found:
            self.assertIn(f"<code>{flag}", commands, flag)
            self.assertIn(f"`{flag}", readme, flag)

    def test_images_and_pages_exist(self):
        for page in ("index.html", "commands.html", "built-by-voice.html"):
            text = (DOCS / page).read_text(encoding="utf-8")
            for src in re.findall(r'(?:src|href)="([^"#:]+\.(?:png|svg|css|html))"', text):
                self.assertTrue((DOCS / src).exists(), f"{page} -> {src}")
        self.assertTrue((DOCS / ".nojekyll").exists())

    def test_voice_page_renders_every_prompt(self):
        text = (ROOT / "voice-log.md").read_text(encoding="utf-8")
        page = build.voice_page(text)
        count = len(re.findall(r"^## Prompt \d+", text, re.M))
        self.assertEqual(page.count('class="prompt"'), count)
        self.assertIn("Mouse and Enter were\nused only for approvals", page)
        self.assertIn('src="chart.svg"', page)
        self.assertNotIn("<script", page)

    def test_voice_page_escapes(self):
        log = ("## Prompt 0\n- Time: t\n- Words: 2\n- Spoken: 1 s\n- Typing: 3 s\n- Saved: 2 s\n\n"
               "```text\n<b>hi</b> & bye\n```\n")
        page = build.voice_page(log)
        self.assertIn("&lt;b&gt;hi&lt;/b&gt; &amp; bye", page)


class SectionsTest(unittest.TestCase):
    README = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_from_a_meeting(self):
        commands = (DOCS / "commands.html").read_text(encoding="utf-8")
        for text in (self.README, commands):
            for bit in ("--from-notes", "examples/meeting.md", "Notetaker", "Mac only", "Windows"):
                self.assertIn(bit, text)
        self.assertIn("## From a meeting", self.README)
        self.assertIn('id="meeting"', commands)
        self.assertTrue((ROOT / "examples" / "meeting.md").exists())

    def test_notes_for_wispr_quote_the_real_log(self):
        notes = self.README.split("## Notes for the Wispr team")[1].split("\n## ")[0]
        self.assertEqual(len(re.findall(r"^\d\. \*\*", notes, re.M)), 5)
        log = (ROOT / "voice-log.md").read_text(encoding="utf-8")
        for heard in ("Grok returns bad JSON", "Did up", "CHO R1", "Tender", "Milab", "claude-p",
                      "working trees", "codes the spoken line", "37. 1. repo, team, and state"):
            self.assertIn(heard, notes)
            self.assertIn(heard, log)  # every mishear quoted is really in the log
        self.assertEqual(log.count("Grok"), 10)  # "ten times"

    def test_failures_and_fallbacks_documented(self):
        for bit in ("never a traceback", "clipboard", "keyword splitter", "Claude Code is missing",
                    "offline", "crash.log", "python -m shipit"):
            self.assertIn(bit, self.README)


class StatsTest(unittest.TestCase):
    def test_counts_and_embed(self):
        prompts, commits, tests = stats.counts()
        self.assertEqual(stats.counts(pending=True)[1], commits + 1)
        self.assertGreater(tests, 80)
        self.assertGreaterEqual(prompts, 6)
        readme = "a\n<!-- stats -->\nold\n<!-- /stats -->\nb"
        self.assertEqual(stats.embed(readme, "new"), "a\n<!-- stats -->\nnew\n<!-- /stats -->\nb")

    def test_no_keys_in_the_repo(self):
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertRegex(example, r"(?m)^GROQ_API_KEY=\s*$")
        self.assertIn(".env", (ROOT / ".gitignore").read_text(encoding="utf-8").split())

    def test_entry_point(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('shipit = "shipit.cli:entry"', pyproject)
        self.assertTrue(callable(cli.entry))


if __name__ == "__main__":
    unittest.main()
