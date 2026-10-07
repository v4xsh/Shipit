"""Regenerate chart.svg from voice-log.md and embed it at the top of README.md.

Stdlib only. Run: python chart.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
START, END = "<!-- chart -->", "<!-- /chart -->"


def parse_log(text):
    """Return [(prompt_no, spoken_seconds_or_None, typing_seconds)]."""
    rows = []
    for block in re.split(r"^## Prompt ", text, flags=re.M)[1:]:
        num = int(block.split()[0])
        spoken = re.search(r"^- Spoken: (\S+)", block, re.M).group(1)
        typing = re.search(r"^- Typing: (\d+)", block, re.M).group(1)
        rows.append((num, None if spoken == "?" else float(spoken), float(typing)))
    return rows


def render_svg(rows):
    w, h, pad, bw = max(240, 60 + 50 * len(rows)), 200, 30, 18
    top = max([t for _, s, t in rows] + [s or 0 for _, s, _ in rows] + [60]) / 60
    y = lambda sec: h - pad - (h - 2 * pad) * (sec / 60) / top
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           'font-family="sans-serif" font-size="11">',
           f'<rect width="{w}" height="{h}" fill="#fff"/>',
           f'<text x="{pad}" y="16">Minutes per prompt: spoken (blue) vs typed (grey)</text>',
           f'<line x1="{pad}" y1="{h - pad}" x2="{w - 10}" y2="{h - pad}" stroke="#999"/>']
    for i, (num, spoken, typing) in enumerate(rows):
        x = pad + 10 + 50 * i
        for dx, sec, color in ((0, spoken, "#3b82f6"), (bw, typing, "#9ca3af")):
            if sec is not None:
                out.append(f'<rect x="{x + dx}" y="{y(sec):.1f}" width="{bw - 2}" '
                           f'height="{h - pad - y(sec):.1f}" fill="{color}"/>')
        out.append(f'<text x="{x + bw - 4}" y="{h - pad + 14}">{num}</text>')
    return "\n".join(out + ["</svg>"]) + "\n"


def embed(readme, rows):
    saved = sum(t - s for _, s, t in rows if s is not None) / 60
    block = f"{START}\n![chart](chart.svg)\n\nTime saved so far: {saved:.1f} min\n{END}"
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
