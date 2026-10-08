"""Items are plain dicts so they serialize straight to JSON for the board and GitHub."""
import re

SECTIONS = ("done", "blocked", "next")
LABELS = ("bug", "feature", "infra", "core", "chore")


def make(id, section, title, said, label="core", assignee=None, deadline=None,
         depends_on=(), scratched=False, changes=()):
    return {"id": id, "section": section, "title": title, "label": label,
            "assignee": assignee, "deadline": deadline, "depends_on": list(depends_on),
            "said": said, "scratched": scratched, "changes": list(changes)}


def norm_title(title):
    """Lowercase, no punctuation, single spaces: used to dedupe."""
    return " ".join(re.sub(r"[^\w\s]", " ", title.lower()).split())


def live(items):
    return [i for i in items if not i["scratched"]]


def is_commit(item):
    """Drafted from a commit rather than spoken."""
    return bool(re.fullmatch(r"commit [0-9a-f]{7,}", item["said"]))


FIELDS = ("title", "assignee", "deadline", "section", "label")


def diff(old, new):
    """Board events that turn `old` into `new`: changes, scratches and new cards."""
    before = {i["id"]: i for i in old}
    events = []
    for i in new:
        was = before.get(i["id"])
        if was is None:
            events.append(("item", i))
            continue
        said = i["changes"][-1]["said"] if len(i["changes"]) > len(was["changes"]) else None
        for f in FIELDS:
            if i[f] != was[f]:
                events.append(("change", {"id": i["id"], "field": f, "from": was[f], "to": i[f],
                                          "said": said}))
        if i["scratched"] and not was["scratched"]:
            events.append(("scratch", {"id": i["id"]}))
    gone = {i["id"] for i in new}
    events += [("scratch", {"id": i["id"]}) for i in old if i["id"] not in gone and not i["scratched"]]
    return events
