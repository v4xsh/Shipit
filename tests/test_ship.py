import unittest
from unittest import mock

from shipit import confirm, flow, items, ship
from shipit.github import Gh, GhError
from tests.fakegh import FakeGitHub

TODAY = "2026-10-07"
TEAM = {"me": "v4xsh", "members": [{"login": "v4xsh", "name": "Vansh Dobhal", "aliases": []},
                                   {"login": "milap1afk", "name": "milap1afk", "aliases": []}]}


def it(id, section, title, said="", **kw):
    return items.make(id, section, title, said or f"I said {title}", **kw)


STANDUP = [
    items.make("c1", "done", "Add chart", "commit abc1234", assignee="v4xsh"),
    it("i1", "done", "Fix balance bug", label="bug", assignee="v4xsh"),
    it("i2", "next", "Fix CI pipeline", label="infra", assignee="v4xsh", deadline="2026-10-09"),
    it("i3", "blocked", "Review payment webhook", assignee="milap1afk", deadline="2026-10-09",
       depends_on=["i2"], said="Milap ko bolo payment webhook dekh le"),
    it("i4", "next", "Write CLI docs", label="chore", depends_on=["i5"]),
    it("i5", "next", "Set up docs site", label="infra"),
    it("i6", "next", "Fix CI pipeline!", label="infra"),       # said twice in one run
    it("i7", "next", "Set up Docker", label="infra", scratched=True),
]
OPEN = [{"number": 1, "title": "Fix the balance bug"}, {"number": 2, "title": "Set up docs site"},
        {"number": 3, "title": "Shipit log"}]


def shipped(fake=None, dry=False):
    fake = fake or FakeGitHub(OPEN)
    gh = Gh("o/r", dry_run=dry, run=fake, echo=mock.Mock())
    p = ship.plan(STANDUP, gh.open_issues())
    return fake, gh, p, ship.execute(p, gh, TODAY)


class PlanTest(unittest.TestCase):
    def test_sorts_items(self):
        p = ship.plan(STANDUP, FakeGitHub(OPEN).list(["--state", "open"]))
        self.assertEqual([i["id"] for i in p["create"]], ["i2", "i3", "i4"])
        self.assertEqual([(i["id"], n) for i, n in p["duplicate"]], [("i5", 2)])
        self.assertEqual([(i["id"], n) for i, n in p["close"]], [("i1", 1)])  # normalized match
        self.assertEqual([i["id"] for i in p["log"]], ["c1"])

    def test_confirm_card(self):
        text = confirm.card(ship.plan(STANDUP, FakeGitHub(OPEN).list(["--state", "open"])))
        for bit in ("+ open   Fix CI pipeline → @v4xsh [infra, due 2026-10-09]", "= skip   #2",
                    "✓ close  #1 Fix balance bug", "1 done item(s)", "[y]es · [e]dit · [n]o"):
            self.assertIn(bit, text)

    def test_ask(self):
        answers = iter(["huh?", "Haan.", ])
        self.assertEqual(confirm.ask(lambda _: next(answers)), "yes")
        self.assertEqual(confirm.ask(lambda _: "e"), "edit")
        self.assertEqual(confirm.ask(lambda _: "nahi"), "no")


class MatchTest(unittest.TestCase):
    def test_reworded_titles_match(self):
        issues = [{"number": n, "title": t} for n, t in
                  [(1, "Work on confirm card"), (2, "Write README docs"), (3, "Review Render deploy"),
                   (4, "Set up GitHub Pages")]]
        for said, n in [("Implement confirm card", 1), ("Write README documentation", 2),
                        ("Check Render deploy", 3), ("Setup GitHub Pages", 4)]:
            self.assertEqual(ship.find(said, issues)["number"], n, said)
        for said in ("Fix confirm card crash", "Write API docs", "Render deploy rollback"):
            self.assertIsNone(ship.find(said, issues), said)


class ExecuteTest(unittest.TestCase):
    def test_issues_labels_milestones(self):
        fake, _, _, done = shipped()
        self.assertEqual(fake.labels, {"bug", "infra", "core", "chore"})
        self.assertEqual(fake.milestones, {"Due 2026-10-09"})
        ci = fake.issues[4]
        self.assertEqual((ci["title"], ci["assignees"], ci["labels"], ci["milestone"]),
                         ("Fix CI pipeline", ["v4xsh"], ["infra"], "Due 2026-10-09"))
        self.assertEqual([n for _, n in done["opened"]], [4, 5, 6])
        self.assertEqual(done["assigned"], 2)
        for n in (4, 5, 6):
            self.assertTrue(fake.issues[n]["body"].rstrip().splitlines()[-1].startswith('Said: "'))
        self.assertTrue(fake.issues[5]["body"].endswith('Said: "Milap ko bolo payment webhook dekh le"\n'))

    def test_cross_links(self):
        fake, *_ = shipped()
        self.assertIn("Blocked by #4", fake.issues[5]["body"])  # webhook after CI
        self.assertIn("Blocks #5", fake.issues[4]["body"])
        self.assertIn("Blocked by #2", fake.issues[6]["body"])  # docs after existing #2
        self.assertTrue(fake.issues[2]["body"].startswith("Blocks #6\n"))

    def test_close_and_log(self):
        fake, _, _, done = shipped()
        self.assertEqual(fake.issues[1]["state"], "closed")
        self.assertIn("Done, per the 2026-10-07 standup", fake.issues[1]["comments"][0])
        self.assertEqual(done["log_issue"], 3)
        log = fake.issues[3]["comments"][0]
        for bit in ("### Standup Wed 07 Oct 2026", "- Add chart @v4xsh · commit abc1234",
                    "#1 Fix balance bug (closed)", "#5 Review payment webhook @milap1afk, due 2026-10-09",
                    "#2 Set up docs site"):
            self.assertIn(bit, log)

    def test_log_issue_created_once(self):
        fake = FakeGitHub([])
        gh = Gh("o/r", run=fake)
        p = ship.plan(STANDUP[:1], [])
        first = ship.execute(p, gh, TODAY)["log_issue"]
        second = ship.execute(p, gh, TODAY)["log_issue"]
        self.assertEqual(first, second)
        self.assertEqual(len(fake.issues[first]["comments"]), 2)

    def test_dry_run_prints_and_writes_nothing(self):
        fake = FakeGitHub(OPEN)
        _, gh, _, done = shipped(fake, dry=True)
        printed = [c.args[0] for c in gh.echo.call_args_list]
        self.assertTrue(any(line.startswith("  $ gh issue create -R o/r --title \"Fix CI pipeline\"")
                            for line in printed))
        self.assertTrue(any("gh issue close 1" in line for line in printed))
        self.assertEqual(set(fake.issues), {1, 2, 3})
        self.assertEqual(fake.issues[1]["state"], "open")
        self.assertEqual(done["opened"][0][1], "new1")


class FailureTest(unittest.TestCase):
    def test_github_down_gives_markdown(self):
        fake = FakeGitHub(OPEN, fail_on="create")
        gh = Gh("o/r", run=fake)
        p = ship.plan(STANDUP, gh.open_issues())
        board = mock.Mock()
        with mock.patch("shipit.flow.clipboard.copy", return_value=True) as copy, \
                mock.patch("shipit.flow.say"), mock.patch("shipit.flow.warn") as warn:
            self.assertIsNone(flow.deliver(p, gh, board, TODAY))
        md = copy.call_args[0][0]
        self.assertIn("## Fix CI pipeline", md)
        self.assertIn('Said: "Milap ko bolo payment webhook dekh le"', md)
        self.assertIn("Bad gateway", warn.call_args[0][0])

    def test_gh_error_message(self):
        gh = Gh("o/r", run=lambda *a, **k: (1, "", "gh: not logged in\n"))
        with self.assertRaisesRegex(GhError, "gh auth login"):
            gh.open_issues()


class AgreeTest(unittest.TestCase):
    def test_edit_then_yes(self):
        found = [it("i1", "next", "Write CLI docs", label="chore", assignee="v4xsh")]
        moved = [{**found[0], "assignee": "milap1afk",
                  "changes": [{"field": "assignee", "from": "v4xsh", "to": "milap1afk",
                               "said": "docs wala Milap ko de do"}]}]
        answers = iter(["e", "docs wala Milap ko de do", "y"])
        board, gh = mock.Mock(), Gh("o/r", run=FakeGitHub([]))
        with mock.patch("shipit.flow.parser.amend", return_value=(moved, [])), \
                mock.patch("shipit.flow.say"):
            final, p = flow.agree(found, gh, TEAM, board, read=lambda _: next(answers))
        self.assertEqual(final[0]["assignee"], "milap1afk")
        self.assertEqual(p["create"][0]["assignee"], "milap1afk")
        board.apply.assert_called_once_with([("change", {"id": "i1", "field": "assignee",
                                                         "from": "v4xsh", "to": "milap1afk",
                                                         "said": "docs wala Milap ko de do"})])

    def test_no_touches_nothing(self):
        fake = FakeGitHub([])
        with mock.patch("shipit.flow.say"):
            result = flow.agree(STANDUP, Gh("o/r", run=fake), TEAM, mock.Mock(), read=lambda _: "no")
        self.assertEqual(result, (None, None))
        self.assertEqual([c[:2] for c in fake.calls], [["issue", "list"]])  # one read, no writes


if __name__ == "__main__":
    unittest.main()
