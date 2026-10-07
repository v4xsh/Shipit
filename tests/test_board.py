import json
import threading
import unittest
import urllib.request
from unittest import mock

from shipit import cli, live, receipt, replay, server
from shipit.hub import Hub


class HubTest(unittest.TestCase):
    def test_wait_returns_new_events(self):
        hub = Hub()
        hub.publish("status", "listening")
        events, seen, gen = hub.wait(0, hub.generation, timeout=0)
        self.assertEqual((events, seen), ([("status", "listening")], 1))
        self.assertEqual(hub.wait(seen, gen, timeout=0)[0], [])

    def test_reset_restarts_clients(self):
        hub = Hub()
        hub.publish("item", {"id": "a"})
        _, seen, gen = hub.wait(0, hub.generation, timeout=0)
        hub.reset()
        hub.publish("meta", {})
        events, _, new_gen = hub.wait(seen, gen, timeout=0)
        self.assertEqual([k for k, _ in events], ["reset", "meta"])
        self.assertNotEqual(new_gen, gen)

    def test_wait_wakes_on_publish(self):
        hub = Hub()
        threading.Timer(0.05, hub.publish, ("status", "ready")).start()
        events, _, _ = hub.wait(0, hub.generation, timeout=2)
        self.assertEqual(events, [("status", "ready")])


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.hub = Hub()
        self.server = server.start(self.hub, port=0)
        self.url = server.url(self.server)
        self.addCleanup(self.server.shutdown)

    def test_page(self):
        with urllib.request.urlopen(self.url, timeout=5) as r:
            html = r.read().decode("utf-8")
        self.assertIn("<title>Shipit board</title>", html)
        for col in ("done", "blocked", "next", "agent"):
            self.assertIn(f'data-col="{col}"', html)

    def test_missing_page_is_404(self):
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.url + "nope", timeout=5)

    def test_event_stream_utf8(self):
        self.hub.publish("item", {"id": "i1", "said": "Milap ko bolo — kal tak"})
        with urllib.request.urlopen(self.url + "events", timeout=5) as r:
            self.assertIn("text/event-stream", r.headers["Content-Type"])
            self.assertEqual(r.readline().decode(), "event: item\n")
            data = json.loads(r.readline().decode("utf-8")[len("data: "):])
        self.assertEqual(data["said"], "Milap ko bolo — kal tak")


class ReceiptTest(unittest.TestCase):
    def test_stats(self):
        items = [{"scratched": False, "assignee": "a"}, {"scratched": True, "assignee": "b"},
                 {"scratched": False, "assignee": None}]
        s = receipt.stats(" ".join(["word"] * 150), items)
        self.assertEqual((s["words"], s["items"], s["assigned"]), (150, 2, 1))
        self.assertEqual((s["typed_s"], s["spoken_s"], s["saved_s"]), (225, 60, 165))


class FakeBoard:
    url = None

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda *a, **k: self.calls.append((name, a[0] if a else None))


class ReplayTest(unittest.TestCase):
    def test_plays_all_three_standups_in_order(self):
        board = FakeBoard()
        with mock.patch.object(replay, "say"):
            replay.run(board, sleep=lambda s: None)
        kinds = [k for k, _ in board.calls]
        self.assertEqual(kinds.count("run"), 3)
        self.assertEqual(kinds.count("receipt"), 3)
        first = kinds[:kinds.index("receipt") + 1]
        self.assertEqual(first, ["run", "status", "transcript", "status", "items", "status", "receipt"])
        statuses = [v for k, v in board.calls if k == "status"][:3]
        self.assertEqual(statuses, ["listening", "parsing", "ready"])
        scratched = [i for k, v in board.calls if k == "items" for i in v if i["scratched"]]
        self.assertEqual([i["title"] for i in scratched], ["Setup Docker"])


class CliTest(unittest.TestCase):
    def test_flags(self):
        o = cli.args(["--replay", "--no-board", "--port", "9000"])
        self.assertEqual((o.replay, o.no_board, o.port), (True, True, 9000))
        self.assertIsInstance(cli.open_board(o), live.NoBoard)


if __name__ == "__main__":
    unittest.main()
