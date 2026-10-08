"""Keep the README's numbers true: prompts, commits and tests. Stdlib only.

Run: python stats.py [--pending]   (the pre-commit hook passes --pending: the commit being made counts)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
START, END = "<!-- stats -->", "<!-- /stats -->"


def counts(pending=False):
    log = (ROOT / "voice-log.md").read_text(encoding="utf-8")
    prompts = len(re.findall(r"^## Prompt \d+", log, re.M))
    out = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    commits = int(out.stdout.strip() or 0) + (1 if pending else 0)
    tests = sum(len(re.findall(r"^\s+def test_", p.read_text(encoding="utf-8"), re.M))
                for p in (ROOT / "tests").glob("test_*.py"))
    return prompts, commits, tests


def line(prompts, commits, tests):
    return (f"**{prompts} voice prompts → {commits} commits → {tests} tests.** "
            f"[Read the voice log](voice-log.md), word for word.")


def embed(readme, text):
    block = f"{START}\n{text}\n{END}"
    return re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, readme, flags=re.S)


def main():
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(embed(text, line(*counts("--pending" in sys.argv))), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
