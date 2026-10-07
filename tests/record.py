"""Run the three fixture standups through real Groq and save the replies as fixtures.

Usage: python tests/record.py   (needs GROQ_API_KEY in .env)
"""
import datetime
import os
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shipit import cards, console, env, groq, parser, prompt  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def main():
    console.setup()
    env.load(ROOT)
    data = json.loads((FIX / "standups.json").read_text(encoding="utf-8"))
    today = datetime.date.fromisoformat(data["today"])
    for n, text in enumerate(data["standups"], 1):
        reply = groq.chat(prompt.messages(text, data["team"], [], today), timeout=60)
        result = parser.parse(text, data["team"], today=today, chat=lambda m: reply)
        print(f"\n=== Standup {n} ({result['source']}) ===\n{text}\n\n{cards.board(result['items'])}")
        for note in result["notes"]:
            print(f"  ~ {note}")
        record = {"recorded": f"groq {os.environ.get('GROQ_MODEL', groq.MODEL)} {datetime.date.today()}", "reply": reply}
        (FIX / f"reply{n}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False),
                                            encoding="utf-8", newline="\n")


if __name__ == "__main__":
    try:
        main()
    except groq.GroqError as e:
        sys.exit(f"  ~ {e}. Add one and run again.")
