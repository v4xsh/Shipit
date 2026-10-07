import datetime
import json
import os
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest import mock

from shipit import cards, fallback, groq, items, match, parser, prompt

FIX = Path(parser.__file__).parent / "fixtures"
DATA = json.loads((FIX / "standups.json").read_text(encoding="utf-8"))
TEAM, TODAY = DATA["team"], datetime.date.fromisoformat(DATA["today"])


def reply(n):
    return json.loads((FIX / f"reply{n}.json").read_text(encoding="utf-8"))["reply"]


def parse(n, drafts=()):
    """Parse fixture standup n with its recorded model reply."""
    return parser.parse(DATA["standups"][n - 1], TEAM, drafts, TODAY, chat=lambda m: reply(n))


def by_id(result):
    return {i["id"]: i for i in result["items"]}


class MatchTest(unittest.TestCase):
    def test_names(self):
        cases = {"Milap": "milap-dev", "milap shah": "milap-dev", "Milu": "milap-dev",
                 "@milap-dev": "milap-dev", "Milapp": "milap-dev", "Vansh": "v4xsh",
                 "me": "v4xsh", "Main": "v4xsh", "Rahul": None, "": None}
        for said, login in cases.items():
            self.assertEqual(match.resolve(said, TEAM), login, said)


class RecordedStandupTest(unittest.TestCase):
    def test_every_item_quotes_the_transcript(self):
        for n in (1, 2, 3):
            for i in parse(n)["items"]:
                self.assertIn(i["said"], DATA["standups"][n - 1], (n, i["id"]))
                self.assertIn(i["section"], items.SECTIONS)
                self.assertIn(i["label"], items.LABELS)

    def test_english_corrections_and_team(self):
        r = parse(1)
        self.assertEqual(r["source"], "groq")
        got = by_id(r)
        self.assertEqual([got[k]["section"] for k in ("i1", "i3", "i5")], ["done", "next", "blocked"])
        self.assertEqual(got["i3"]["assignee"], "milap-dev")
        self.assertEqual(got["i3"]["changes"][0]["from"], "v4xsh")  # "me" resolved
        self.assertEqual(got["i4"]["deadline"], "2026-10-09")       # "make that Friday"
        self.assertEqual(got["i5"]["title"], "Get Render API keys")
        self.assertEqual(got["i3"]["depends_on"], [])

    def test_hinglish_scratch_and_dependency(self):
        got = by_id(parse(2))
        self.assertEqual(got["i1"]["assignee"], "v4xsh")  # "maine"
        self.assertTrue(got["i3"]["scratched"])
        self.assertEqual(got["i4"]["depends_on"], ["i2"])
        self.assertEqual(got["i4"]["deadline"], "2026-10-13")
        self.assertEqual(len(items.live(parse(2)["items"])), 3)

    def test_meeting_notes_and_dedupe_against_commits(self):
        draft = items.make("c1", "done", "Fix: flaky parser test!", "commit abc1234")
        r = parse(3, drafts=[draft])
        titles = [i["title"] for i in r["items"]]
        self.assertEqual(titles.count("Fix flaky parser test"), 0)
        self.assertEqual(r["items"][0]["id"], "c1")
        got = by_id(r)
        self.assertEqual(got["i3"]["assignee"], "milap-dev")  # nickname Milu
        self.assertEqual(got["i3"]["changes"][0]["from"], "Rahul")  # unknown name kept
        self.assertEqual((got["i3"]["section"], got["i3"]["depends_on"]), ("blocked", ["i2"]))
        self.assertEqual(got["i2"]["section"], "next")
        self.assertEqual(got["i5"]["assignee"], "v4xsh")


class RobustnessTest(unittest.TestCase):
    def test_bad_json_retries_once(self):
        answers = iter(["not json", reply(1)])
        chat = mock.Mock(side_effect=lambda m: next(answers))
        r = parser.parse(DATA["standups"][0], TEAM, today=TODAY, chat=chat)
        self.assertEqual((r["source"], chat.call_count), ("groq", 2))

    def test_bad_twice_falls_back(self):
        chat = mock.Mock(return_value='{"items": [{"title": "x", "section": "later"}]}')
        r = parser.parse(DATA["standups"][1], TEAM, today=TODAY, chat=chat)
        self.assertEqual((r["source"], chat.call_count), ("fallback", 2))
        self.assertTrue(r["items"])

    def test_network_error_falls_back_without_retry(self):
        chat = mock.Mock(side_effect=groq.GroqError("Couldn't reach Groq (timeout)"))
        r = parser.parse(DATA["standups"][0], TEAM, today=TODAY, chat=chat)
        self.assertEqual((r["source"], chat.call_count), ("fallback", 1))
        self.assertIn("Couldn't reach Groq", r["notes"][0])

    def test_cleaning(self):
        notes = []
        out = parser.clean({"items": [
            {"id": "a", "section": "next", "title": "X", "label": "weird", "assignee": "Zed",
             "deadline": "Friday", "depends_on": ["a", "zz", "b"]},
            {"id": "a", "section": "done", "title": "Y"}]}, TEAM, notes)
        self.assertEqual(out[0]["label"], "core")
        self.assertIsNone(out[0]["deadline"])
        self.assertIsNone(out[0]["assignee"])
        self.assertEqual(out[1]["id"], "i2")  # duplicate id renamed
        self.assertEqual(out[0]["depends_on"], [])
        self.assertIn("Zed", notes[0])


class FallbackTest(unittest.TestCase):
    def test_hinglish_keywords(self):
        got = fallback.split(DATA["standups"][1], TEAM)
        self.assertEqual(got[0]["section"], "done")
        self.assertEqual(got[0]["label"], "core")
        self.assertEqual([i["title"] for i in got if i["scratched"]],
                         ["Uske baad Docker setup karunga"])  # "..., nahi scratch that"
        self.assertEqual(got[4]["assignee"], "milap-dev")

    def test_english(self):
        got = fallback.split(DATA["standups"][0], TEAM)
        self.assertEqual(got[0]["assignee"], "v4xsh")
        self.assertEqual(got[4]["section"], "blocked")

    def test_short_scratched_item(self):
        got = fallback.split("Aaj CI fix karna hai. Docker setup, scratch that.", TEAM)
        self.assertEqual([i["scratched"] for i in got], [False, True])

    def test_scratch_alone_hits_previous_and_own_name_is_me(self):
        got = fallback.split("Vansh writes the CLI docs. Okay, scratch that.", TEAM)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["scratched"])
        self.assertEqual(got[0]["assignee"], "v4xsh")


class GroqTest(unittest.TestCase):
    def test_request_shape(self):
        sent = {}

        def transport(url, headers, body, timeout):
            sent.update(body, auth=headers["Authorization"])
            return {"choices": [{"message": {"content": "{}"}}]}

        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "k"}, clear=False):
            os.environ.pop("GROQ_MODEL", None)
            self.assertEqual(groq.chat([{"role": "user", "content": "hi"}], transport), "{}")
        self.assertEqual((sent["temperature"], sent["model"]), (0, "openai/gpt-oss-120b"))
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertEqual(sent["auth"], "Bearer k")

    def test_errors(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(groq.GroqError):
                groq.chat([])

        def bad(*a):
            raise urllib.error.HTTPError("u", 400, "x", {}, BytesIO(b'{"code":"json_validate_failed"}'))

        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "k"}):
            with self.assertRaises(groq.GroqError) as e:
                groq.chat([], bad)
        self.assertTrue(e.exception.bad_json)


class PromptAndCardsTest(unittest.TestCase):
    def test_prompt_has_context(self):
        user = prompt.messages("hi", TEAM, [items.make("c1", "done", "Ship it", "x")], TODAY)[1]
        for bit in ("2026-10-07 (Wednesday)", "milap-dev", "Milu", "Ship it", "hi"):
            self.assertIn(bit, user["content"])

    def test_board_text(self):
        text = cards.board(parse(2)["items"])
        self.assertIn("DONE", text)
        self.assertIn("(scratched)", text)
        self.assertIn("due Tue 13 Oct", text)
        self.assertIn("deadline: 2026-10-12 → 2026-10-13", text)


if __name__ == "__main__":
    unittest.main()
