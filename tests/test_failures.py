"""Never dies on camera: each failure is one friendly line, with a fallback where it matters."""
import json
import os
import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest import mock

from shipit import agent, claude, cli, debug, env, flow, groq, items, live, net, parser, review, ship, team
from shipit.github import Gh

TEAM = {"me": "v4xsh", "members": [{"login": "v4xsh", "name": "Vansh", "aliases": []},
                                   {"login": "milap1afk", "name": "milap1afk", "aliases": []}]}
FOUND = [items.make("i1", "next", "Fix CI", "Aaj CI fix karna hai", assignee="v4xsh")]


class GitHubFailingTest(unittest.TestCase):
    def test_reasons_are_plain(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertIn("isn't installed", net.gh_problem("gh: not found"))
        with mock.patch("shutil.which", return_value="gh"):
            self.assertIn("gh auth login", net.gh_problem("To get started with GitHub CLI, run: gh auth login"))
            self.assertIn("offline", net.gh_problem("error connecting to api.github.com"))
            self.assertIsNone(net.gh_problem("HTTP 422: Validation Failed"))

    def test_markdown_and_clipboard(self):
        gh = Gh("o/r", run=lambda *a, **k: (1, "", "error connecting to api.github.com"))
        p = ship.plan(FOUND, [])
        with mock.patch("shipit.flow.clipboard.copy", return_value=True) as copy, \
                mock.patch("shipit.flow.say") as say, mock.patch("shipit.flow.warn") as warn, \
                mock.patch("shutil.which", return_value="gh"):
            self.assertIsNone(flow.deliver(p, gh, mock.Mock(), "2026-10-08"))
        self.assertEqual(warn.call_count, 1)  # one line
        self.assertIn("Can't reach GitHub (offline?)", warn.call_args[0][0])
        self.assertIn("also on your clipboard", warn.call_args[0][0])
        self.assertIn('Said: "Aaj CI fix karna hai"', copy.call_args[0][0])
        self.assertIn("## Fix CI", say.call_args[0][0])

    def test_dry_run_survives_failed_reads(self):
        gh = Gh("o/r", dry_run=True, run=lambda *a, **k: (1, "", "error connecting"), echo=mock.Mock())
        done = ship.execute(ship.plan(FOUND, []), gh, "2026-10-08")
        self.assertEqual(done["opened"][0][1], "new1")


class GroqFailingTest(unittest.TestCase):
    def chat(self, error):
        def transport(*a):
            raise error
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "k"}):
            with self.assertRaises(groq.GroqError) as e:
                groq.chat([], transport)
        return str(e.exception)

    def test_messages(self):
        self.assertIn("check GROQ_API_KEY", self.chat(urllib.error.HTTPError("u", 401, "x", {}, BytesIO(b""))))
        self.assertIn("offline?", self.chat(urllib.error.URLError("no route")))
        self.assertIn("in time", self.chat(TimeoutError()))

    def test_parse_falls_back_with_one_note(self):
        r = parser.parse("Aaj CI fix karna hai.", TEAM,
                         chat=mock.Mock(side_effect=groq.GroqError("Couldn't reach Groq (offline?)")))
        self.assertEqual((r["source"], len(r["notes"])), ("fallback", 1))
        self.assertTrue(r["items"])


class ClaudeMissingTest(unittest.TestCase):
    def setUp(self):
        p = mock.patch("shipit.net.claude_missing", return_value=True)
        p.start()
        self.addCleanup(p.stop)

    def test_agent_skips_before_creating_anything(self):
        gh = mock.Mock(dry=False)
        with mock.patch("shipit.agent.warn") as warn, mock.patch("shipit.agent.worktree") as wt:
            self.assertEqual(agent.run_all([(7, FOUND[0])], ".", gh, mock.Mock(), claude.run), [])
        self.assertIn("Claude Code isn't installed", warn.call_args[0][0])
        wt.add.assert_not_called()
        gh.issue.assert_not_called()

    def test_debug_leaves_hypotheses_unchecked(self):
        hyps = json.dumps({"bug": "b", "hypotheses": [{"title": "cache", "said": "cache"}]})
        with mock.patch("shipit.debug.warn") as warn, mock.patch("shipit.debug.say"), \
                mock.patch("shipit.debug.worktree") as wt:
            checked, prs = debug.run("x", ".", mock.Mock(), mock.Mock(), chat=lambda m: hyps)
        self.assertEqual(([h["verdict"] for h in checked], prs), (["unchecked"], []))
        self.assertIn("isn't installed", warn.call_args[0][0])
        wt.add.assert_not_called()

    def test_review_posts_then_says_so(self):
        gh = mock.Mock(dry=False)
        gh.pr.return_value = {"title": "t", "url": "u", "headRefName": "h", "baseRefName": "main"}
        chat = lambda m: json.dumps({"summary": "", "points": ["Add a test"]})
        with mock.patch("shipit.review.warn") as warn, mock.patch("shipit.review.say"):
            out = review.run(7, "test daalo", ".", gh, mock.Mock(), read=lambda _: "y", chat=chat)
        self.assertEqual(out, "posted")
        gh.pr_comment.assert_called_once()
        self.assertIn("isn't installed", warn.call_args[0][0])

    def test_review_comment_failure_goes_to_clipboard(self):
        gh = mock.Mock(dry=False)
        gh.pr.return_value = {"title": "t", "url": "u", "headRefName": "h", "baseRefName": "main"}
        gh.pr_comment.side_effect = review.GhError("Can't reach GitHub (offline?)")
        with mock.patch("shipit.review.clipboard.copy", return_value=True) as copy, \
                mock.patch("shipit.review.warn") as warn, mock.patch("shipit.review.say"):
            self.assertIsNone(review.run(7, "x", ".", gh, mock.Mock(), read=lambda _: "y",
                                         chat=lambda m: "{}"))
        self.assertIn("### Review", copy.call_args[0][0])
        self.assertIn("on your clipboard", warn.call_args[0][0])


class OfflineTest(unittest.TestCase):
    def test_parse_offline_is_instant_and_quiet(self):
        board, opts = mock.Mock(), cli.args(["--text", "Aaj CI fix karna hai.", "--no-board"])
        with mock.patch("shipit.cli.gitlog.drafts", return_value=[]), mock.patch("shipit.cli.say"), \
                mock.patch("shipit.cli.warn") as warn:
            _, found = cli.hear(opts, ".", TEAM, {"last_commit": None}, board, offline=True)
        warn.assert_not_called()  # the offline line was said once, at start
        self.assertTrue(found)

    def test_deliver_offline_hands_over(self):
        with mock.patch("shipit.flow.clipboard.copy", return_value=True), mock.patch("shipit.flow.say"), \
                mock.patch("shipit.flow.warn") as warn:
            self.assertIsNone(flow.deliver(ship.plan(FOUND, []), mock.Mock(), mock.Mock(), "d", offline=True))
        self.assertIn("offline", warn.call_args[0][0])

    def test_team_offline_uses_cache_or_you(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("shipit.team.gh") as gh:
            t = team.load(d, "o/r", offline=True)
            self.assertEqual(len(t["members"]), 1)
            self.assertFalse(team.path(d).exists())  # a stand-in team is never cached
            gh.authed.assert_not_called()


class CrashPathTest(unittest.TestCase):
    def test_env_written_by_powershell(self):
        with tempfile.TemporaryDirectory() as d:
            for name, data in (("SHIPIT_U16", "SHIPIT_U16=a\r\n".encode("utf-16")),
                               ("SHIPIT_BOM", "﻿SHIPIT_BOM=b\n".encode("utf-8"))):
                Path(d, ".env").write_bytes(data)
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(name, None)
                    env.load(d)
                    self.assertIn(name, os.environ)

    def test_hand_edited_team_json(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("shipit.team.warn") as warn, \
                mock.patch("shipit.team.gh") as gh:
            team.path(d).parent.mkdir()
            team.path(d).write_text("{ aliases: [Milu] ", encoding="utf-8")
            gh.authed.return_value = False
            gh.why.return_value = "gh isn't logged in. Run: gh auth login"
            t = team.load(d, "o/r")
        self.assertIn("isn't valid JSON", warn.call_args_list[0][0][0])
        self.assertEqual(t["repo"], "o/r")

    def test_agent_thread_never_raises(self):
        gh = mock.Mock()
        gh.issue.side_effect = flow.GhError("Can't reach GitHub (offline?)")
        with mock.patch("shipit.agent.say"), mock.patch("shipit.agent.warn"):
            r = agent.work(7, FOUND[0], ".", "main", gh, mock.Mock(), run_claude=mock.Mock())
            self.assertIsNone(r["pr"])
            self.assertEqual(agent.parallel([lambda: 1 / 0, lambda: "ok"]), [None, "ok"])

    def test_board_without_a_port(self):
        with mock.patch("shipit.cli.live.Board", side_effect=OSError("no free port")), \
                mock.patch("shipit.cli.warn") as warn:
            board = cli.open_board(cli.args([]))
        self.assertIsInstance(board, live.NoBoard)
        self.assertIn("stays in the terminal", warn.call_args[0][0])

    def test_anything_else_is_one_line_and_a_log(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("shipit.cli.open_board",
                                                            side_effect=RuntimeError("boom")), \
                mock.patch("shipit.cli.warn") as warn:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                self.assertEqual(cli.main(["--no-board"]), 1)
                self.assertIn("RuntimeError: boom", Path(".shipit/crash.log").read_text(encoding="utf-8"))
            finally:
                os.chdir(cwd)
        self.assertIn("Something unexpected broke (RuntimeError: boom)", warn.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
