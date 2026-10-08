"""--replay: play the three recorded standups through the board, no keys or network needed."""
import datetime
import json
import time
from pathlib import Path

from . import cards, parser, receipt
from .console import say

FIX = Path(__file__).with_name("fixtures")


def load():
    data = json.loads((FIX / "standups.json").read_text(encoding="utf-8"))
    replies = [json.loads((FIX / f"reply{n}.json").read_text(encoding="utf-8"))["reply"]
               for n in range(1, len(data["standups"]) + 1)]
    return data, replies


def show_time(text, items):
    """Roughly how long the board needs to animate this run, in seconds."""
    changes = sum(len(i["changes"]) for i in items)
    scratched = sum(1 for i in items if i["scratched"])
    return 1.2 + len(text.split()) * 0.035 + len(items) * 0.3 + changes * 1.6 + scratched * 2.2 + 2


def run(board, sleep=time.sleep, hold=3):
    data, replies = load()
    team, today = data["team"], datetime.date.fromisoformat(data["today"])
    for n, (text, reply) in enumerate(zip(data["standups"], replies), 1):
        board.run(team["repo"], team, replay=True)
        board.status("listening")
        sleep(1.2)
        board.transcript(text)
        sleep(len(text.split()) * 0.035 + 0.6)
        board.status("parsing")
        sleep(0.9)
        result = parser.parse(text, team, today=today, chat=lambda m, r=reply: r)
        board.items(result["items"])
        board.status("ready")
        board.receipt(receipt.stats(text, result["items"]))
        say(f"\nStandup {n}/{len(replies)}\n{cards.board(result['items'])}")
        sleep(show_time(text, result["items"]) + hold)
