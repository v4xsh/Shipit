
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shipit import agent, claude, debug, items, review, worktree
from shipit.github import Gh
from tests.fakegh import FakeGitHub


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          encoding="utf-8").stdout.strip()


def fake_claude(edits=None, ok=True, result="Added it.", commit=True):
    """Stands in for claude.run: edits files in the worktree and commits, like the real one."""
    calls = []

    def run(prompt, cwd, on_line=print):
        calls.append((prompt, Path(cwd)))
        on_line("→ Edit app.py")
        for name, text in (edits or {"app.py": "VERSION = '1.0'\n"}).items():
            (Path(cwd) / name).write_text(text, encoding="utf-8")
        if commit:
            git(cwd, "add", "-A")
            git(cwd, "-c", "user.email=a@b", "-c", "user.name=Agent", "commit", "-qm", "agent work")
        return {"ok": ok, "result": result, "code": 0 if ok else 1}
    run.calls = calls
    return run


class Repo(unittest.TestCase):
    """A real git repo with a bare origin, so worktrees and pushes are real."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origin, self.root = base / "origin.git", base / "work"
        git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(base, "clone", "-q", str(self.origin), str(self.root))
        git(self.root, "checkout", "-q", "-b", "main")
        (self.root / "app.py").write_text("print('hi')\n", encoding="utf-8")
        (self.root / ".gitignore").write_text(".shipit/\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "-c", "user.email=a@b", "-c", "user.name=T", "commit", "-qm", "init")
        git(self.root, "push", "-q", "-u", "origin", "main")
        env = mock.patch.dict(os.environ, {"SHIPIT_TEST_CMD": "python -c pass"})
        env.start()
        self.addCleanup(env.stop)
        quiet = [mock.patch("shipit.agent.say"), mock.patch("shipit.agent.warn"),
                 mock.patch("shipit.debug.say"), mock.patch("shipit.review.say")]
        for q in quiet:
            q.start()
            self.addCleanup(q.stop)
        self.fake = FakeGitHub([{"number": 7, "title": "Add a --version flag",
                                 "body": 'Said: "version flag add karna hai"'}])
        self.gh = Gh("o/r", run=self.fake)
        self.board = mock.Mock()

    def tearDown(self):
        subprocess.run(["git", "worktree", "prune"], cwd=self.root, capture_output=True)
        self.tmp.cleanup()

    def remote_branches(self):
        return git(self.origin, "branch", "--format=%(refname:short)").split()


class ClaudeTest(unittest.TestCase):
    def test_describe(self):
        event = {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Adding the flag.\nMore"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "python -m unittest"}}]}}
        self.assertEqual(claude.describe(event), ["Adding the flag.", "→ Bash python -m unittest"])
        self.assertEqual(claude.describe({"type": "result", "num_turns": 4}), ["✓ finished after 4 turns"])

    def test_run_streams_and_reads_result(self):
        lines = [json.dumps({"type": "system"}), "",
                 json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}),
                 json.dumps({"type": "result", "is_error": False, "result": "Done.", "num_turns": 1})]
        proc = mock.Mock(stdout=iter(l + "\n" for l in lines))
        proc.wait.return_value = 0
        seen = []
        out = claude.run("do it", ".", seen.append, spawn=lambda args, cwd: proc)
        self.assertEqual(out, {"ok": True, "result": "Done.", "code": 0})
        self.assertEqual(seen, ["hi", "✓ finished after 1 turns"])
        proc.stdin.write.assert_called_once_with("do it")
        proc.stdin.close.assert_called_once()

    def test_not_installed(self):
        proc = mock.Mock(stdout=iter(["'claude' is not recognized\n"]))
        proc.wait.return_value = 1
        seen = []
        out = claude.run("x", ".", seen.append, spawn=lambda a, c: proc)
        self.assertFalse(out["ok"])
        self.assertIn("not recognized", seen[0])

    def test_command_is_headless_and_scoped(self):
        cmd = claude.command()
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertIn("stream-json", cmd)
        self.assertIn("Bash(git commit:*)", cmd)
        self.assertNotIn("Bash(git push:*)", cmd)  # pushing is Shipit's job, after the tests


class AgentTest(Repo):
    def test_issue_to_pr(self):
        run = fake_claude()
        item = items.make("i1", "next", "Add a --version flag", "version flag add karna hai")
        r = agent.work(7, item, self.root, "main", self.gh, self.board, run)
        self.assertEqual(r["pr"], "https://github.com/o/r/pull/100")
        prompt, cwd = run.calls[0]
        for bit in ("issue #7", "Add a --version flag", 'said: "version flag add karna hai"',
                    "python -c pass", '"Add a --version flag (#7)"'):
            self.assertIn(bit, prompt)
        self.assertIn("shipit-issue-7", str(cwd))
        self.assertFalse(cwd.exists())  # worktree cleaned up after the PR
        self.assertIn("shipit/issue-7", self.remote_branches())
        pr = self.fake.prs[100]
        self.assertEqual((pr["head"], pr["base"], pr["title"]),
                         ("shipit/issue-7", "main", "Add a --version flag (#7)"))
        for bit in ("Closes #7", '> Said: "version flag add karna hai"', "Added it.", "app.py"):
            self.assertIn(bit, pr["body"])
        statuses = [c.args[0]["status"] for c in self.board.agent.call_args_list]
        self.assertEqual([s for s in statuses if s != "working"],
                         ["branch created", "testing", "pushing", "PR open"])

    def test_failed_agent_keeps_branch_and_opens_nothing(self):
        r = agent.work(7, items.make("i1", "next", "x", "y"), self.root, "main", self.gh, self.board,
                       fake_claude(ok=False, result="I got stuck"))
        self.assertIsNone(r["pr"])
        self.assertEqual(self.fake.prs, {})
        self.assertTrue(worktree.exists(self.root, "shipit/issue-7"))
        self.assertEqual(self.board.agent.call_args.args[0]["status"], "failed")

    def test_no_commit_or_red_tests_means_no_pr(self):
        r = agent.work(7, items.make("i1", "next", "x", "y"), self.root, "main", self.gh, self.board,
                       fake_claude(commit=False))
        self.assertIsNone(r["pr"])
        with mock.patch.dict(os.environ, {"SHIPIT_TEST_CMD": "python -c \"raise SystemExit(1)\""}):
            r = agent.work(7, items.make("i1", "next", "x", "y"), self.root, "main", self.gh,
                           self.board, fake_claude())
        self.assertIsNone(r["pr"])
        self.assertNotIn("shipit/issue-7", self.remote_branches())

    def test_parallel_worktrees(self):
        self.fake.issues[8] = {**self.fake.issues[7], "number": 8, "title": "Add a --help example"}
        run = fake_claude()
        picks = [(7, items.make("i1", "next", "a", "a")), (8, items.make("i2", "next", "b", "b"))]
        results = agent.run_all(picks, self.root, self.gh, self.board, run)
        self.assertEqual([r["pr"] is not None for r in results], [True, True])
        self.assertEqual(len({str(cwd) for _, cwd in run.calls}), 2)

    def test_pick(self):
        found = [items.make("i1", "next", "a", "a", assignee="me"),
                 items.make("i2", "blocked", "b", "b", assignee="me"),
                 items.make("i3", "next", "c", "c", assignee="milap"),
                 items.make("i4", "next", "d", "d", assignee="me"),
                 items.make("i5", "next", "e", "e", assignee="me")]
        done = {"opened": [(found[0], 1), (found[1], 2), (found[2], 3), (found[4], 5)],
                "duplicates": [(found[3], 4)]}
        self.assertEqual([n for n, _ in agent.pick(done, found, "me", 2)], [1, 4])

    def test_dry_run_runs_no_agent(self):
        run = fake_claude()
        with mock.patch("shipit.agent.say") as say:
            agent.run_all([(7, items.make("i1", "next", "a", "a"))], self.root,
                          Gh("o/r", dry_run=True, run=self.fake), self.board, run)
        self.assertEqual(run.calls, [])
        self.assertIn("would work #7", say.call_args.args[0])


class DebugTest(Repo):
    HYPS = {"bug": "Balance shows 0 after refresh", "hypotheses": [
        {"id": "x", "title": "Cache returns a stale balance", "said": "shayad cache purana hai",
         "check": "look at cache.py"},
        {"id": "y", "title": "Timezone rounding", "said": "ya timezone ka issue", "check": "dates"}]}

    def test_extract_and_verdict(self):
        bug, hyps = debug.extract("ramble", chat=lambda m: json.dumps(self.HYPS))
        self.assertEqual((bug, [h["id"] for h in hyps]), ("Balance shows 0 after refresh", ["h1", "h2"]))
        down = mock.Mock(side_effect=debug.groq.GroqError("down"))
        with mock.patch("shipit.debug.warn"):
            bug, hyps = debug.extract("Balance zero aa raha hai\nrefresh ke baad", chat=down)
        self.assertEqual((bug, len(hyps)), ("Balance zero aa raha hai", 1))
        self.assertEqual(debug.verdict("...\nVERDICT: Ruled out\nEVIDENCE: tz is UTC (dates.py:4)"),
                         ("ruled out", "tz is UTC (dates.py:4)"))
        self.assertEqual(debug.verdict("no idea")[0], "unclear")

    def test_confirm_then_fix_it(self):
        def run(prompt, cwd, on_line=print):
            if "Hypothesis to check: Cache" in prompt:
                return {"ok": True, "result": "VERDICT: confirmed\nEVIDENCE: cache.py:12 never expires",
                        "code": 0}
            if "Hypothesis to check" in prompt:
                return {"ok": True, "result": "VERDICT: ruled out\nEVIDENCE: all UTC", "code": 0}
            return fake_claude({"cache.py": "TTL = 60\n"}, result="Added a TTL.")(prompt, cwd, on_line)

        checked, prs = debug.run("balance zero...", self.root, self.gh, self.board,
                                 read=lambda _: "fix it", chat=lambda m: json.dumps(self.HYPS),
                                 run_claude=run)
        self.assertEqual([h["verdict"] for h in checked], ["confirmed", "ruled out"])
        self.assertEqual(prs, ["https://github.com/o/r/pull/100"])
        body = self.fake.prs[100]["body"]
        for bit in ("Cache returns a stale balance", "cache.py:12 never expires", 'Said: "shayad cache purana hai"'):
            self.assertIn(bit, body)
        self.assertFalse(worktree.exists(self.root, "shipit/debug-h2"))  # ruled out: tidied away
        moves = [c.args[0][0][1] for c in self.board.apply.call_args_list]
        self.assertEqual(sorted((m["id"], m["to"]) for m in moves), [("h1", "done"), ("h2", "blocked")])

    def test_enter_fixes_nothing(self):
        def run(prompt, cwd, on_line=print):
            return {"ok": True, "result": "VERDICT: confirmed\nEVIDENCE: yes", "code": 0}
        checked, prs = debug.run("x", self.root, self.gh, self.board, read=lambda _: "",
                                 chat=lambda m: json.dumps(self.HYPS), run_claude=run)
        self.assertEqual(prs, [])
        self.assertFalse(worktree.exists(self.root, "shipit/debug-h1"))


class ReviewTest(Repo):
    def setUp(self):
        super().setUp()
        git(self.root, "checkout", "-q", "-b", "shipit/issue-7")
        (self.root / "app.py").write_text("print('v1')\n", encoding="utf-8")
        git(self.root, "-c", "user.email=a@b", "-c", "user.name=T", "commit", "-qam", "v1")
        git(self.root, "push", "-q", "-u", "origin", "shipit/issue-7")
        git(self.root, "checkout", "-q", "main")
        self.gh.create_pr("shipit/issue-7", "main", "Add a --version flag (#7)", "body")
        self.chat = lambda m: json.dumps({"summary": "Nearly there.",
                                          "points": ["Print the version from one constant", "Add a test"]})

    def test_write_up(self):
        text = review.markdown(review.write_up("x", {"title": "t"}, self.chat), "flag theek hai, test daalo")
        for bit in ("### Review", "Nearly there.", "- [ ] Add a test", '> Said: "flag theek hai, test daalo"'):
            self.assertIn(bit, text)

    def test_post_address_push_merge(self):
        before = git(self.origin, "rev-parse", "shipit/issue-7")
        answers = iter(["haan", "merge"])
        run = fake_claude({"app.py": "VERSION = '1.0'\nprint(VERSION)\n"})
        out = review.run(100, "constant use karo aur test daalo", self.root, self.gh, self.board,
                         read=lambda _: next(answers), chat=self.chat, run_claude=run)
        self.assertEqual(out, "merged")
        pr = self.fake.prs[100]
        self.assertIn("- [ ] Print the version from one constant", pr["comments"][0])
        self.assertIn("Address every point", run.calls[0][0])
        self.assertNotEqual(git(self.origin, "rev-parse", "shipit/issue-7"), before)  # pushed
        self.assertEqual(pr["state"], "MERGED")

    def test_no_means_nothing_posted(self):
        out = review.run(100, "x", self.root, self.gh, self.board, read=lambda _: "no",
                         chat=self.chat, run_claude=fake_claude())
        self.assertIsNone(out)
        self.assertEqual(self.fake.prs[100]["comments"], [])


if __name__ == "__main__":
    unittest.main()
