"""Confirmed items -> GitHub: issues, labels, milestones, closes, cross-links, a log comment."""
import datetime
import difflib
import re

from . import items as it

LOG_TITLE = "Shipit log"
LABELS = {  # GitHub label colours, picked to match the board
    "bug": ("d73a4a", "Something is broken"),
    "feature": ("a371f7", "New capability"),
    "infra": ("fbca04", "CI, deploy, build, tooling"),
    "core": ("1f6feb", "Core work"),
    "chore": ("8b949e", "Upkeep: docs, cleanup, bumps"),
}


VERBS = re.compile(r"^(work on|implement|build|write|check|review|set up|fix|add|create|update|"
                   r"finish|do|handle|get|look into|make) ")
SAME = {"setup": "set up", "documentation": "docs", "doc": "docs", "readme": "readme"}


def key(title):
    """The work, not the wording: "Implement confirm card" and "Work on confirm card" agree."""
    words = " ".join(SAME.get(w, w) for w in it.norm_title(title).split()
                     if w not in ("the", "a", "an"))
    return VERBS.sub("", words + " ").strip() or words


def find(title, issues, cutoff=0.88):
    """An open issue for the same work: same key, or a very close one."""
    table = {key(i["title"]): i for i in issues if i["title"] != LOG_TITLE}
    k = key(title)
    if k in table:
        return table[k]
    close = difflib.get_close_matches(k, table, n=1, cutoff=cutoff)
    return table[close[0]] if close else None


def plan(items, open_issues):
    """Decide what to do. Pure: no GitHub calls, so the confirm card can show it."""
    p = {"create": [], "duplicate": [], "close": [], "log": []}
    seen = set()
    for i in it.live(items):
        match = find(i["title"], open_issues)
        if i["section"] == "done":
            p["close"].append((i, match["number"])) if match else p["log"].append(i)
        elif match:
            p["duplicate"].append((i, match["number"]))
        elif key(i["title"]) not in seen:
            p["create"].append(i)
        seen.add(key(i["title"]))
    return p


def milestone(iso):
    return f"Due {iso}" if iso else None


def body(item, today, blocked_by=(), blocks=()):
    parts = []
    links = [f"Blocked by #{n}" for n in blocked_by] + [f"Blocks #{n}" for n in blocks]
    if links:
        parts.append("\n".join(links))
    meta = [f"Label: `{item['label']}`"] + ([f"Due {item['deadline']}"] if item["deadline"] else [])
    parts.append(" · ".join(meta + [f"From the {today} standup, via Shipit"]))
    parts.append(f'Said: "{item["said"]}"')
    return "\n\n".join(parts) + "\n"


def execute(p, gh, today, on_issue=lambda item, number: None):
    """Do it. Returns what happened, for the receipt."""
    done = {"opened": [], "closed": [], "duplicates": p["duplicate"], "logged": p["log"],
            "assigned": 0, "log_issue": None}
    have = gh.labels() if p["create"] else set()
    for name in sorted({i["label"] for i in p["create"]} - have):
        gh.create_label(name, *LABELS.get(name, ("ededed", "")))
    have = gh.milestones() if any(i["deadline"] for i in p["create"]) else set()
    for iso in sorted({i["deadline"] for i in p["create"] if i["deadline"]}):
        if milestone(iso) not in have:
            gh.create_milestone(milestone(iso), iso)
    numbers = {i["id"]: n for i, n in p["duplicate"]}
    for i in p["create"]:
        n = gh.create_issue(i["title"], body(i, today), [i["label"]], i["assignee"],
                            milestone(i["deadline"]))
        numbers[i["id"]] = n
        done["opened"].append((i, n))
        done["assigned"] += bool(i["assignee"])
        on_issue(i, n)
    for i, n in p["duplicate"]:
        on_issue(i, n)
    link(p, numbers, gh, today)
    for i, n in p["close"]:
        gh.close(n, f'Done, per the {today} standup.\n\nSaid: "{i["said"]}"')
        done["closed"].append((i, n))
        on_issue(i, n)
    done["log_issue"] = log(gh, done, today)
    return done


def link(p, numbers, gh, today):
    """Write Blocked by / Blocks on both ends once every issue has a number."""
    blocked_by, blocks = {}, {}
    for i in p["create"] + [i for i, _ in p["duplicate"]]:
        for dep in i["depends_on"]:
            if dep in numbers:
                blocked_by.setdefault(i["id"], []).append(numbers[dep])
                blocks.setdefault(numbers[dep], []).append(numbers[i["id"]])
    created = {numbers[i["id"]]: i for i in p["create"]}
    for i in p["create"]:
        n = numbers[i["id"]]
        if i["id"] in blocked_by or n in blocks:
            gh.edit_body(n, body(i, today, blocked_by.get(i["id"], ()), blocks.get(n, ())))
    for n, ns in blocks.items():
        if n not in created:  # an issue that was already open: add the lines on top
            old = gh.body(n)
            new = [f"Blocks #{x}\n" for x in ns if f"Blocks #{x}\n" not in old]
            if new:
                gh.edit_body(n, "".join(new) + "\n" + old)


def summary(done, today):
    day = datetime.date.fromisoformat(today).strftime("%a %d %b %Y")
    who = lambda i: f" @{i['assignee']}" if i["assignee"] else ""
    lines = [f"### Standup {day}"]
    sections = [
        ("Done", [f"- {i['title']}{who(i)} · {i['said']}" for i in done["logged"]]
         + [f"- #{n} {i['title']} (closed)" for i, n in done["closed"]]),
        ("Opened", [f"- #{n} {i['title']}{who(i)}" + (f", due {i['deadline']}" if i["deadline"] else "")
                    for i, n in done["opened"]]),
        ("Said again, already open", [f"- #{n} {i['title']}" for i, n in done["duplicates"]]),
    ]
    for name, rows in sections:
        if rows:
            lines += ["", f"**{name}**", *rows]
    return "\n".join(lines) + "\n"


def log(gh, done, today):
    n = gh.find_issue(LOG_TITLE)
    if n is None:
        n = gh.create_issue(LOG_TITLE, "Standup summaries from Shipit, one comment per run.\n")
    gh.comment(n, summary(done, today))
    return n


def markdown(p, today):
    """Fallback when GitHub is down: the issues as Markdown to paste by hand."""
    out = [f"# Shipit · {today}"]
    for i in p["create"]:
        out += ["", f"## {i['title']}", f"Assignee: @{i['assignee'] or '?'}", "", body(i, today)]
    for i, n in p["close"]:
        out += ["", f"Close #{n}: {i['title']}"]
    return "\n".join(out) + "\n"
