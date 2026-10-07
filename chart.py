"""Regenerate chart.svg from voice-log.md and embed it, plus a table, at the top of README.md.

Stdlib only. Run: python chart.py
"""
import math
import re
from pathlib import Path

ROOT = Path(__file__).parent
START, END = "<!-- chart -->", "<!-- /chart -->"
W, H = 900, 300
LEFT, RIGHT, TOP, BOTTOM = 56, 24, 92, 252
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
BG, CARD_LINE, GRID = "#0d1117", "#30363d", "#21262d"
TEXT, MUTED = "#e6edf3", "#8b949e"
SPOKEN, TYPED, ACCENT = "#58a6ff", "#6e7681", "#3fb950"


def parse_log(text):
    """Return [(prompt_no, words, spoken_seconds_or_None, typing_seconds)]."""
    rows = []
    for block in re.split(r"^## Prompt ", text, flags=re.M)[1:]:
        field = lambda name: re.search(rf"^- {name}: (\S+)", block, re.M).group(1)
        spoken = field("Spoken")
        rows.append((int(block.split()[0]), int(field("Words")),
                     None if spoken == "?" else float(spoken), float(field("Typing"))))
    return rows


def totals(rows):
    """Minutes spoken, typed and saved, over prompts whose spoken time is known."""
    known = [(s, t) for _, _, s, t in rows if s is not None]
    spoken = sum(s for s, _ in known) / 60
    typed = sum(t for _, t in known) / 60
    return spoken, typed, typed - spoken


def axis(minutes):
    """A round tick step (1, 2 or 5 x 10^n) giving about 4 gridlines, and the axis top."""
    raw = max(minutes, 1) / 4
    power = 10 ** math.floor(math.log10(raw))
    step = next(k * power for k in (1, 2, 5, 10) if k * power >= raw)
    return step * math.ceil(max(minutes, 1) / step), step


def bar(x, y, w, h, color):
    """A bar with rounded top corners."""
    r = min(5, w / 2, h)
    return (f'<path d="M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
            f'H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z" '
            f'fill="{color}"/>')


def headline(rows):
    spoken, typed, saved = totals(rows)
    faster = f"{typed / spoken:.1f}× faster" if spoken else "speak a prompt to start"
    return (f'<text x="28" y="44" font-size="20" font-weight="600" fill="{TEXT}">'
            f'{spoken:.1f} min spoken · {typed:.1f} min typed · '
            f'<tspan fill="{ACCENT}">{saved:.1f} min saved</tspan> · {faster}</text>')


def legend():
    out = []
    for i, (name, color) in enumerate((("Spoken", SPOKEN), ("Typed at 40 wpm", TYPED))):
        x = 28 + i * 96
        out += [f'<rect x="{x}" y="60" width="10" height="10" rx="2" fill="{color}"/>',
                f'<text x="{x + 16}" y="69" font-size="12" fill="{MUTED}">{name}</text>']
    return out


def render_svg(rows):
    top, step = axis(max([t / 60 for *_, t in rows] + [(s or 0) / 60 for _, _, s, _ in rows]))
    y = lambda minutes: BOTTOM - (BOTTOM - TOP) * minutes / top
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
           f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" '
           f'stroke="{CARD_LINE}"/>', headline(rows), *legend()]
    for k in range(round(top / step) + 1):
        minutes = step * k
        out += [f'<line x1="{LEFT}" y1="{y(minutes):.1f}" x2="{W - RIGHT}" y2="{y(minutes):.1f}" '
                f'stroke="{GRID}"/>',
                f'<text x="{LEFT - 8}" y="{y(minutes) + 4:.1f}" font-size="11" fill="{MUTED}" '
                f'text-anchor="end">{minutes:g}</text>']
    group = (W - LEFT - RIGHT) / max(len(rows), 1)
    bw = min(34, group * 0.32)
    for i, (num, _, spoken, typed) in enumerate(rows):
        mid = LEFT + group * (i + 0.5)
        for x, sec, color in ((mid - bw - 3, spoken, SPOKEN), (mid + 3, typed, TYPED)):
            label = "?" if sec is None else f"{sec / 60:.1f}"
            if sec:
                out.append(bar(x, y(sec / 60), bw, BOTTOM - y(sec / 60), color))
            if bw >= 14:
                out.append(f'<text x="{x + bw / 2:.1f}" y="{y((sec or 0) / 60) - 6:.1f}" '
                           f'font-size="11" fill="{TEXT}" text-anchor="middle">{label}</text>')
        out.append(f'<text x="{mid:.1f}" y="{BOTTOM + 20}" font-size="12" fill="{MUTED}" '
                   f'text-anchor="middle">#{num}</text>')
    out.append(f'<text x="{W - RIGHT}" y="{H - 14}" font-size="11" fill="{MUTED}" '
               f'text-anchor="end">minutes per voice prompt</text>')
    return "\n".join(out + ["</svg>"]) + "\n"


def table(rows):
    fmt = lambda sec: "?" if sec is None else f"{sec / 60:.1f}"
    lines = ["| Prompt | Words | Spoken (min) | Typed (min) | Saved (min) |",
             "|---:|---:|---:|---:|---:|"]
    for num, words, spoken, typed in rows:
        saved = None if spoken is None else typed - spoken
        lines.append(f"| {num} | {words} | {fmt(spoken)} | {fmt(typed)} | {fmt(saved)} |")
    spoken, typed, saved = totals(rows)
    words = sum(w for _, w, s, _ in rows if s is not None)
    lines.append(f"| **Total** | **{words}** | **{spoken:.1f}** | **{typed:.1f}** | **{saved:.1f}** |")
    return "\n".join(lines)


def embed(readme, rows):
    block = f"{START}\n![Spoken vs typed minutes per prompt](chart.svg)\n\n{table(rows)}\n{END}"
    if START in readme:
        return re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block,
                      readme, flags=re.S)
    return block + "\n\n" + readme


def main():
    rows = parse_log((ROOT / "voice-log.md").read_text(encoding="utf-8"))
    (ROOT / "chart.svg").write_text(render_svg(rows), encoding="utf-8", newline="\n")
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    readme.write_text(embed(text, rows), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
