import datetime
import json
import unittest
from pathlib import Path

from shipit import parser, ship

ROOT = Path(__file__).resolve().parent.parent
NOTES = (ROOT / "examples" / "meeting.md").read_text(encoding="utf-8")
RECORDED = json.loads((ROOT / "shipit" / "fixtures" / "meeting_reply.json").read_text(encoding="utf-8"))


def parsed():
    today = datetime.date.fromisoformat(RECORDED["today"])
    return parser.parse(NOTES, RECORDED["team"], today=today, chat=lambda m: RECORDED["reply"])["items"]


class MeetingTest(unittest.TestCase):
    """examples/meeting.md: a two-person standup that gives both people issues (--from-notes)."""

    def test_issues_for_both_people(self):
        p = ship.plan(parsed(), [])
        owners = {i["assignee"] for i in p["create"]}
        self.assertEqual(owners, {"v4xsh", "milap1afk"})

    def test_first_person_means_the_line_speaker(self):
        by_said = {i["said"]: i for i in parsed()}
        webhook = next(i for s, i in by_said.items() if "Aaj main webhook" in s)
        self.assertEqual(webhook["assignee"], "milap1afk")  # Milap's "main", not the person running it
        mobile = next(i for s, i in by_said.items() if "board on mobile" in s)
        self.assertEqual((mobile["assignee"], mobile["deadline"]), ("v4xsh", "2026-10-09"))

    def test_correction_dependency_and_quotes(self):
        found = parsed()
        notes = " ".join(NOTES.split())
        for i in found:
            self.assertIn(" ".join(i["said"].split()), notes)  # every card quotes the notes
        release = next(i for i in found if "release notes" in i["title"].lower())
        self.assertEqual(release["deadline"], "2026-10-13")  # "actually make that Tuesday"
        mobile = next(i for i in found if "mobile" in i["title"].lower())
        self.assertEqual(release["depends_on"], [mobile["id"]])
        self.assertTrue(any(i["section"] == "blocked" for i in found))


if __name__ == "__main__":
    unittest.main()
