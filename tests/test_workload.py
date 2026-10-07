import json
import tempfile
import unittest
from unittest import mock

from shipit import flow, items, parser, receipt, state, workload
from shipit.github import Gh
from tests.fakegh import FakeGitHub

TEAM = {"me": "v4xsh", "members": [{"login": "v4xsh", "name": "Vansh Dobhal", "aliases": []},
                                   {"login": "milap1afk", "name": "milap1afk", "aliases": []}]}
ISSUES = [{"number": n, "title": t, "assignees": [{"login": "v4xsh"}]}
          for n, t in [(1, "Write CLI docs"), (2, "Fix CI pipeline"), (3, "Set up Docker"),
                       (4, "Shipit log")]]


class WorkloadTest(unittest.TestCase):
    def test_counts_skip_log_issue(self):
        self.assertEqual(workload.counts(ISSUES, TEAM), {"v4xsh": 3, "milap1afk": 0})

    def test_heavy(self):
        self.assertEqual(workload.heavy({"a": 3, "b": 0}), ("a", 3))
        self.assertEqual(workload.heavy({"a": 5, "b": 4}), None)   # gap too small
        self.assertEqual(workload.heavy({"a": 7, "b": 5}), None)   # under 1.5x
        self.assertEqual(workload.heavy({"a": 9, "b": 4}), ("a", 9))
        self.assertEqual(workload.heavy({"a": 1, "b": 0}), None)
        self.assertIn("Heads-up: @v4xsh has 3", workload.message({"v4xsh": 3, "milap1afk": 0}))
        self.assertIn("even", workload.message({"v4xsh": 1, "milap1afk": 1}))

    def test_move_with_model(self):
        chat = mock.Mock(return_value=json.dumps({"number": 1, "to": "Milap"}))
        issue, to = workload.move("move the docs one to Milap", ISSUES, TEAM, chat=chat)
        self.assertEqual((issue["number"], to), (1, "milap1afk"))
        sent = json.loads(chat.call_args[0][0][1]["content"])
        self.assertNotIn("Shipit log", [i["title"] for i in sent["issues"]])

    def test_move_falls_back_to_keywords(self):
        chat = mock.Mock(side_effect=workload.groq.GroqError("down"))
        for said in ("move the docs one to Milap", "docker wala milap ko de do"):
            issue, to = workload.move(said, ISSUES, TEAM, chat=chat)
            self.assertEqual(to, "milap1afk")
        self.assertEqual(issue["number"], 3)

    def test_balance_moves_by_voice(self):
        fake = FakeGitHub([{**i, "assignees": ["v4xsh"]} for i in ISSUES])
        board = mock.Mock()
        chat = mock.Mock(return_value=json.dumps({"number": 1, "to": "Milap"}))
        with mock.patch("shipit.flow.say"):
            moved = flow.balance(Gh("o/r", run=fake), TEAM, board, ids={1: "i9"},
                                 read=lambda _: "move the docs one to Milap", chat=chat)
        self.assertEqual(moved, (1, "milap1afk"))
        self.assertEqual(fake.issues[1]["assignees"], ["milap1afk"])
        kind, data = board.apply.call_args[0][0][0]
        self.assertEqual((kind, data["id"], data["to"]), ("change", "i9", "milap1afk"))


class DiffAndAmendTest(unittest.TestCase):
    OLD = [items.make("i1", "next", "Write docs", "a", assignee="v4xsh"),
           items.make("i2", "next", "Docker", "b"), items.make("i3", "next", "Old", "c")]

    def test_diff(self):
        new = [dict(self.OLD[0], assignee="milap1afk", deadline="2026-10-09",
                    changes=[{"field": "assignee", "from": "v4xsh", "to": "milap1afk", "said": "Milap ko"}]),
               dict(self.OLD[1], scratched=True), items.make("i4", "next", "New thing", "d")]
        events = items.diff(self.OLD, new)
        self.assertEqual(events[0], ("change", {"id": "i1", "field": "assignee", "from": "v4xsh",
                                                "to": "milap1afk", "said": "Milap ko"}))
        self.assertEqual(events[1][1]["field"], "deadline")
        self.assertIn(("scratch", {"id": "i2"}), events)
        self.assertEqual([k for k, _ in events].count("item"), 1)
        self.assertIn(("scratch", {"id": "i3"}), events)  # dropped by the edit

    def test_amend_keeps_commits_and_survives_failure(self):
        commit = items.make("c1", "done", "Chart", "commit abc1234")
        reply = {"items": [{"id": "i1", "section": "next", "title": "Write docs", "label": "chore",
                            "assignee": "Milap", "said": "a",
                            "changes": [{"field": "assignee", "from": "v4xsh", "to": "Milap",
                                         "said": "docs Milap ko"}]}]}
        out, notes = parser.amend([commit] + self.OLD[:1], "docs Milap ko", TEAM,
                                  chat=lambda m: json.dumps(reply))
        self.assertEqual([i["id"] for i in out], ["c1", "i1"])
        self.assertEqual(out[1]["assignee"], "milap1afk")
        self.assertEqual(out[1]["changes"][0]["to"], "milap1afk")
        down = mock.Mock(side_effect=parser.groq.GroqError("Couldn't reach Groq"))
        same, notes = parser.amend(self.OLD, "x", TEAM, chat=down)
        self.assertIs(same, self.OLD)
        self.assertIn("nothing changed", notes[0])


class ReceiptStateTest(unittest.TestCase):
    def test_receipt_and_running_total(self):
        done = {"opened": [(None, 4), (None, 5)], "closed": [(None, 1)], "assigned": 2}
        r = receipt.stats(" ".join(["w"] * 40), [], done, {"runs": 2, "seconds_saved": 100})
        self.assertEqual((r["opened"], r["closed"], r["assigned"]), (2, 1, 2))
        self.assertEqual((r["typed_s"], r["spoken_s"], r["saved_s"]), (60, 16, 44))
        self.assertEqual((r["runs"], r["total_saved_s"]), (3, 144))
        self.assertIn("2 opened · 1 closed · 2 assigned", receipt.text(r))

    def test_state_record(self):
        with tempfile.TemporaryDirectory() as d:
            before = state.load(d)
            state.record(d, before, "abc", {"words": 40, "saved_s": 44}, "now")
            s = state.load(d)
            self.assertEqual((s["last_commit"], s["runs"], s["words"], s["seconds_saved"]),
                             ("abc", 1, 40, 44))


if __name__ == "__main__":
    unittest.main()
