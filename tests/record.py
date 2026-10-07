"""Run the fixture standups through real Groq and save the replies as fixtures.

Usage: python tests/record.py [N ...]   (needs GROQ_API_KEY in .env; default: all)
"""
import datetime
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shipit import cards, console, env, groq, parser, prompt  # noqa: E402

FIX = ROOT / "shipit" / "fixtures"
PAUSE = 30  # free-tier Groq limits tokens per minute


def record(n, text, team, today):
    reply = groq.chat(prompt.messages(text, team, [], today), timeout=60)
    result = parser.parse(text, team, today=today, chat=lambda m: reply)
    print(f"\n=== Standup {n} ({result['source']}) ===\n{text}\n\n{cards.board(result['items'])}")
    for note in result["notes"]:
        print(f"  ~ {note}")
    model = os.environ.get("GROQ_MODEL", groq.MODEL)
    record = {"recorded": f"groq {model} {datetime.date.today()}", "reply": reply}
    (FIX / f"reply{n}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False),
                                        encoding="utf-8", newline="\n")


def main(which):
    console.setup()
    env.load(ROOT)
    data = json.loads((FIX / "standups.json").read_text(encoding="utf-8"))
    today = datetime.date.fromisoformat(data["today"])
    which = which or range(1, len(data["standups"]) + 1)
    for k, n in enumerate(which):
        if k:
            time.sleep(PAUSE)
        record(n, data["standups"][n - 1], data["team"], today)


if __name__ == "__main__":
    try:
        main([int(a) for a in sys.argv[1:]])
    except groq.GroqError as e:
        sys.exit(f"  ~ {e}.")
