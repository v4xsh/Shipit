"""Build docs/built-by-voice.html from voice-log.md, and copy the chart. Stdlib only.

Run: python docs/build.py   (the pre-commit hook runs it, so the page never drifts)
"""
import html
import re
import shutil
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
sys.path.insert(0, str(ROOT))
from chart import parse_log, totals  # noqa: E402

NAV = """<nav class="wrap"><a class="brand" href="index.html"><span class="logo"><svg width="16" height="16"
 viewBox="0 0 24 24" fill="none" stroke="#0a0c10" stroke-width="2.8" stroke-linecap="round"
 stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg></span>Shipit</a><div class="links">
<a href="index.html#how">How it works</a><a href="commands.html">Commands</a>
<a href="built-by-voice.html"{current}>Built by voice</a>
<a href="https://github.com/v4xsh/Shipit">GitHub ↗</a></div></nav>"""


def page(title, body, current=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><meta name="description" content="Shipit: say your standup, it ships to GitHub.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="style.css"></head>
<body>{NAV.format(current=' aria-current="page"' if current else "")}
<main class="wrap">{body}</main>
<footer class="wrap">Shipit · Python stdlib · <a href="https://github.com/v4xsh/Shipit">github.com/v4xsh/Shipit</a></footer>
</body></html>
"""


def prompts(text):
    """[(number, time, words, spoken, typing, saved, said)] straight from the log."""
    out = []
    for block in re.split(r"^## Prompt ", text, flags=re.M)[1:]:
        field = lambda name: re.search(rf"^- {name}: (.+)$", block, re.M).group(1).strip()
        said = re.search(r"```text\n(.*?)\n```", block, re.S).group(1)
        out.append((int(block.split()[0]), field("Time"), field("Words"), field("Spoken"),
                    field("Typing"), field("Saved"), said))
    return out


def table(rows):
    fmt = lambda sec: "?" if sec is None else f"{sec / 60:.1f}"
    body = "".join(f"<tr><td>#{n}</td><td>{w}</td><td>{fmt(s)}</td><td>{fmt(t)}</td>"
                   f"<td>{fmt(None if s is None else t - s)}</td></tr>" for n, w, s, t in rows)
    spoken, typed, saved = totals(rows)
    words = sum(w for _, w, s, _ in rows if s is not None)
    return ("<table><thead><tr><th>Prompt</th><th>Words</th><th>Spoken (min)</th><th>Typed (min)</th>"
            f"<th>Saved (min)</th></tr></thead><tbody>{body}<tr class=\"total\"><td>Total</td>"
            f"<td>{words}</td><td>{spoken:.1f}</td><td>{typed:.1f}</td><td>{saved:.1f}</td></tr>"
            "</tbody></table>")


def voice_page(text):
    rows = parse_log(text)
    spoken, typed, saved = totals(rows)
    log = "".join(
        f'<article class="prompt" id="prompt-{n}"><div class="meta"><b>Prompt {n}</b><span>{html.escape(t)}</span>'
        f'<span><b>{w}</b> words</span><span><b>{html.escape(s)}</b> spoken</span>'
        f'<span><b>{html.escape(ty)}</b> to type</span><span class="saved"><b>{html.escape(sv)}</b> saved</span></div>'
        f"<pre>{html.escape(said)}</pre></article>"
        for n, t, w, s, ty, sv, said in prompts(text))
    body = f"""
<h1>Built by <span class="grad">voice</span></h1>
<p class="lead">Every prompt that built Shipit was dictated with Wispr Flow into Claude Code. Mouse and Enter were
used only for approvals. {spoken:.1f} minutes of talking replaced {typed:.1f} minutes of typing at 40 wpm:
<b style="color:var(--done)">{saved:.1f} minutes saved</b>.</p>
<section><img class="shot" src="chart.svg" alt="Spoken vs typed minutes per prompt"></section>
<section><h2>Per prompt</h2>{table(rows)}</section>
<section><h2>The full voice log</h2><p class="muted">Word for word, as transcribed, slips and all.
Typing time assumes 40 wpm; saved = typing − spoken; <code>?</code> means not timed yet.</p>{log}</section>"""
    return page("Built by voice · Shipit", body, current="voice")


def main():
    text = (ROOT / "voice-log.md").read_text(encoding="utf-8")
    (DOCS / "built-by-voice.html").write_text(voice_page(text), encoding="utf-8", newline="\n")
    shutil.copyfile(ROOT / "chart.svg", DOCS / "chart.svg")


if __name__ == "__main__":
    main()
