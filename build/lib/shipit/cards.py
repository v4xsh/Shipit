"""Plain-text cards for the terminal."""
import datetime

MARK = {"done": "✓", "blocked": "■", "next": "→"}


def due(iso):
    return datetime.date.fromisoformat(iso).strftime("due %a %d %b") if iso else ""


def card(i):
    if i["scratched"]:
        return f"  ✗ {i['title']}  (scratched)"
    bits = [f"[{i['label']}]", f"@{i['assignee']}" if i["assignee"] else "@?", due(i["deadline"]),
            f"after {', '.join(i['depends_on'])}" if i["depends_on"] else ""]
    lines = [f"  {MARK[i['section']]} {i['id']}  {i['title']}  {' '.join(b for b in bits if b)}",
             f"      “{i['said']}”"]
    lines += [f"      ↺ {c['field']}: {c['from']} → {c['to']}  (“{c['said']}”)" for c in i["changes"]]
    return "\n".join(lines)


def board(items):
    out = []
    for section in ("done", "blocked", "next"):
        group = [i for i in items if i["section"] == section]
        if group:
            out += [section.upper()] + [card(i) for i in group] + [""]
    return "\n".join(out).rstrip()
