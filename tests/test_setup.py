import json
import os
import tempfile
import unittest
from unittest import mock

from shipit import env, gh, repo, state, team


class RepoTest(unittest.TestCase):
    def test_parse_remote(self):
        for url in ("https://github.com/v4xsh/Shipit.git", "git@github.com:v4xsh/Shipit.git",
                    "https://github.com/v4xsh/Shipit", "ssh://git@github.com/v4xsh/Shipit.git\n"):
            self.assertEqual(repo.parse_remote(url), "v4xsh/Shipit")
        self.assertIsNone(repo.parse_remote("https://gitlab.com/a/b.git"))


class EnvTest(unittest.TestCase):
    def test_load_keeps_existing(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".env"), "w", encoding="utf-8") as f:
                f.write("# c\nSHIPIT_T1='abc'\nSHIPIT_T2=x\n")
            with mock.patch.dict(os.environ, {"SHIPIT_T2": "keep"}):
                env.load(d)
                self.assertEqual(os.environ["SHIPIT_T1"], "abc")
                self.assertEqual(os.environ["SHIPIT_T2"], "keep")


def fake_api(path):
    return {
        "user": {"login": "v4xsh"},
        "repos/v4xsh/Shipit/collaborators?per_page=100": [
            {"login": "v4xsh", "avatar_url": "a1"}, {"login": "milap-dev", "avatar_url": "a2"}],
        "users/v4xsh": {"name": "Vansh Dobhal"},
        "users/milap-dev": {"name": "Milap Shah"},
    }.get(path)


class TeamTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = self.dir.name
        patches = [mock.patch.object(gh, "api", side_effect=fake_api),
                   mock.patch.object(gh, "authed", return_value=True)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.dir.cleanup()

    def test_fetch_and_cache(self):
        t = team.load(self.root, "v4xsh/Shipit", now=1000)
        self.assertEqual(t["me"], "v4xsh")
        self.assertEqual([m["name"] for m in t["members"]], ["Vansh Dobhal", "Milap Shah"])
        gh.api.side_effect = AssertionError("should use cache")
        self.assertEqual(team.load(self.root, "v4xsh/Shipit", now=1000 + 3600), t)

    def test_refresh_keeps_aliases(self):
        t = team.load(self.root, "v4xsh/Shipit", now=1000)
        t["members"][1]["aliases"] = ["Milu"]
        team.path(self.root).write_text(json.dumps(t), encoding="utf-8")
        fresh = team.load(self.root, "v4xsh/Shipit", now=1000 + team.MAX_AGE + 1)
        self.assertEqual(fresh["fetched_at"], 1000 + team.MAX_AGE + 1)
        self.assertEqual(fresh["members"][1]["aliases"], ["Milu"])

    def test_gh_down_falls_back_to_me(self):
        gh.authed.return_value = False
        with mock.patch("shipit.team.warn"):
            t = team.load(self.root, "v4xsh/Shipit", now=1000)
        self.assertEqual(len(t["members"]), 1)
        self.assertEqual(t["members"][0]["login"], t["me"])


class StateTest(unittest.TestCase):
    def test_roundtrip_with_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(state.load(d)["last_commit"])
            state.save(d, {"last_commit": "abc", "runs": 2})
            s = state.load(d)
            self.assertEqual((s["last_commit"], s["runs"], s["words"]), ("abc", 2, 0))


if __name__ == "__main__":
    unittest.main()
