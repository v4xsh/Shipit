"""The live board as seen from the CLI: publish run events, open the browser."""
import webbrowser

from . import server
from .hub import Hub


class Board:
    def __init__(self, port=7878, open_browser=True):
        self.hub = Hub()
        self.server = server.start(self.hub, port)
        self.url = server.url(self.server)
        if open_browser:
            webbrowser.open(self.url)

    def run(self, repo, team, replay=False):
        self.hub.reset()
        self.hub.publish("meta", {"repo": repo, "replay": replay, "me": team["me"],
                                  "team": team["members"]})

    def status(self, state):
        self.hub.publish("status", state)

    def transcript(self, text):
        self.hub.publish("transcript", text)

    def items(self, items):
        for i in items:
            self.hub.publish("item", i)

    def receipt(self, stats):
        self.hub.publish("receipt", stats)

    def close(self):
        self.server.shutdown()


class NoBoard:
    """Stands in when --no-board is passed, so callers never check."""
    url = None

    def __getattr__(self, name):
        return lambda *a, **k: None
