"""Take the docs screenshots with headless Edge (or Chrome). Stdlib only.

Run: python docs/shots.py   -> docs/img/*.png
Boards come from the --replay fixtures, frozen at their final frame; the terminal is a real
confirm card; GitHub pages are the live issue and PR, in dark mode.
"""
import datetime
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
IMG = DOCS / "img"
sys.path.insert(0, str(ROOT))
from shipit import __version__, cards, confirm, items, parser, receipt, replay, ship  # noqa: E402
from shipit.hub import Hub  # noqa: E402

BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe", "google-chrome", "chromium"]
FREEZE = "*,*::before{animation:none!important;transition:none!important}.transcript .w{opacity:1!important}"
REPO = "https://github.com/v4xsh/Shipit"


def browser():
    found = next((b for b in BROWSERS if Path(b).exists() or shutil.which(b)), None)
    if not found:
        sys.exit("Needs Edge or Chrome for headless screenshots.")
    return found


def shoot(url, out, size=(1440, 900), dark=True, budget=8000):
    with tempfile.TemporaryDirectory() as profile:
        args = [browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                f"--window-size={size[0]},{size[1]}", f"--virtual-time-budget={budget}",
                f"--screenshot={out}", url]
        if dark:
            args.insert(1, "--blink-settings=preferredColorScheme=0")
        subprocess.run(args, capture_output=True, timeout=120)
    print(f"  {out.relative_to(ROOT)}" if out.exists() else f"  ! failed: {out.name}")


class Recorder:
    """A board that records events instead of serving them."""

    def __init__(self):
        self.hub = Hub()

    def __getattr__(self, name):
        from shipit.live import Board
        return getattr(Board, name).__get__(self)


def board_page(events, tmp, name, extra_css=""):
    page = (ROOT / "shipit" / "board.html").read_text(encoding="utf-8").replace("{{version}}", __version__)
    shim = ("<script>const EVENTS=" + json.dumps(events, ensure_ascii=False) + ";window.EventSource=class{"
            "constructor(){this.l={};setTimeout(()=>EVENTS.forEach(([k,d])=>this.l[k]&&this.l[k]({data:"
            "JSON.stringify(d)})),30)}addEventListener(k,f){this.l[k]=f}};</script>")
    page = page.replace("<script>", shim + "<script>", 1).replace("</style>", FREEZE + extra_css + "</style>", 1)
    path = Path(tmp) / f"{name}.html"
    path.write_text(page, encoding="utf-8")
    return path.as_uri()


def standup(n, upto="receipt", toast=False):
    """Board events for fixture standup n, stopping after `upto`."""
    data, replies = replay.load()
    team, today = data["team"], datetime.date.fromisoformat(data["today"])
    text = data["standups"][n - 1]
    b = Recorder()
    b.run("v4xsh/Shipit", team)
    drafts = [items.make("c1", "done", "Redo the chart as a dark card", "commit dc11d73", label="chore",
                         assignee=team["me"]),
              items.make("c2", "done", "Add the live board", "commit b2c1a9b", label="feature",
                         assignee=team["me"])]
    b.status("listening")
    b.items(drafts)
    b.transcript(text)
    if upto == "listening":
        return b.hub.events, None
    result = parser.parse(text, team, drafts, today, chat=lambda m: replies[n - 1])
    b.status("parsing")
    b.items(result["items"])
    b.status("ready")
    if upto == "receipt":
        b.receipt({**receipt.stats(text, result["items"]), "opened": 4, "closed": 1, "assigned": 4,
                   "runs": 6, "total_saved_s": 2210})
        toast and b.toast("Heads-up: @v4xsh has 4 open issues, clearly more than the rest (@v4xsh 4, @milap-dev 1).")
    return b.hub.events, result


def terminal(tmp):
    """The real confirm card for standup 1, in a Windows Terminal-ish frame."""
    _, result = standup(1, upto="board")
    plan = ship.plan(result["items"], [{"number": 3, "title": "Fix balance bug"}])
    text = (f"PS C:\\code\\payments> shipit\nShipit · v4xsh/Shipit · 2 on the team\n2 done from your commits.\n"
            f"Dictate your standup with Wispr Flow. Empty line to finish:\n> …\n\n{cards.board(result['items'])}\n\n"
            f"{confirm.card(plan)}\n> yes")
    page = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#0a0c10;padding:28px;font:14px/1.5 "Cascadia Code","Cascadia Mono",Consolas,monospace}}
.win{{background:#0c0c0c;border:1px solid #2b2b2b;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.6);overflow:hidden}}
.bar{{height:34px;background:#1f1f1f;display:flex;align-items:center;gap:8px;padding:0 14px;color:#bbb;font:12px "Segoe UI",sans-serif}}
.bar i{{width:11px;height:11px;border-radius:50%;background:#3a3a3a;display:inline-block}}
pre{{margin:0;padding:16px 20px;color:#cccccc;white-space:pre-wrap}} b{{color:#5cc8ff;font-weight:400}}
</style><div class="win"><div class="bar"><i></i><i></i><i></i>&nbsp; Windows PowerShell</div><pre>{html.escape(text)
        .replace("┌─ Ship it?", "<b>┌─ Ship it?</b>").replace("[y]es · [e]dit · [n]o", "<b>[y]es · [e]dit · [n]o</b>")}</pre></div>"""
    path = Path(tmp) / "terminal.html"
    path.write_text(page, encoding="utf-8")
    return path.as_uri()


def main():
    IMG.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hero, _ = standup(3)
        shoot(board_page(hero, tmp, "hero"), IMG / "board.png", (1440, 900))
        speak, _ = standup(1, upto="listening")
        shoot(board_page(speak, tmp, "speak"), IMG / "step-speak.png", (1280, 640))
        full, _ = standup(1, upto="board")
        shoot(board_page(full, tmp, "board"), IMG / "step-board.png", (1280, 760))
        shoot(terminal(tmp), IMG / "step-confirm.png", (1000, 870), dark=False)
        receipt_events, _ = standup(2, toast=True)
        shoot(board_page(receipt_events, tmp, "receipt"), IMG / "step-receipt.png", (1280, 720))
    shoot(f"{REPO}/issues/3", IMG / "step-issue.png", (1280, 900), budget=15000)
    shoot(f"{REPO}/pull/7", IMG / "step-pr.png", (1280, 900), budget=15000)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
