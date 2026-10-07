import os
import subprocess
import tempfile
import unittest

from shipit import gitlog


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def commit(root, path, msg, email="me@x.dev"):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    git(root, "add", "-A")
    git(root, "-c", f"user.email={email}", "-c", "user.name=T", "commit", "-qm", msg)


class GitlogTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = self.dir.name
        git(self.root, "init", "-q")

    def tearDown(self):
        self.dir.cleanup()

    def test_labels(self):
        self.assertEqual(gitlog.guess_label("fix: x", ["a.py"]), "bug")
        self.assertEqual(gitlog.guess_label("Fixed login", ["a.py"]), "bug")
        self.assertEqual(gitlog.guess_label("feat: x", ["a.py"]), "feature")
        self.assertEqual(gitlog.guess_label("tidy", ["README.md"]), "chore")
        self.assertEqual(gitlog.guess_label("chore: bump", ["a.py"]), "chore")
        self.assertEqual(gitlog.guess_label("ci: x", []), "infra")
        self.assertEqual(gitlog.guess_label("bump", [".github/workflows/t.yml"]), "infra")
        self.assertEqual(gitlog.guess_label("bump", ["requirements.txt"]), "infra")
        self.assertEqual(gitlog.guess_label("refactor(api): x", ["api.py", "README.md"]), "core")

    def test_clean(self):
        self.assertEqual(gitlog.clean("feat(board)!: add cards"), "Add cards")
        self.assertEqual(gitlog.clean("Fix: balance bug"), "Balance bug")

    def test_drafts_since_last_run_by_author(self):
        commit(self.root, "a.py", "feat: first")
        last = gitlog.head(self.root)
        commit(self.root, "docs/guide.md", "Write guide")
        commit(self.root, "b.py", "fix: someone else's", email="other@x.dev")
        commit(self.root, "c.py", "fix: balance rounding")
        d = gitlog.drafts(self.root, "v4xsh", since_commit=last, author="me@x.dev")
        self.assertEqual([i["title"] for i in d], ["Write guide", "Balance rounding"])
        self.assertEqual([i["label"] for i in d], ["chore", "bug"])
        self.assertTrue(all(i["section"] == "done" and i["assignee"] == "v4xsh" for i in d))
        self.assertTrue(d[0]["said"].startswith("commit "))

    def test_first_run_uses_last_day_and_unknown_sha_is_ignored(self):
        commit(self.root, "a.py", "feat: first")
        d = gitlog.drafts(self.root, "me", since_commit="deadbeef")
        self.assertEqual([i["title"] for i in d], ["First"])

    def test_empty_repo(self):
        self.assertEqual(gitlog.drafts(self.root, "me"), [])


if __name__ == "__main__":
    unittest.main()
