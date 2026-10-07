"""Items are plain dicts so they serialize straight to JSON for the board and GitHub."""
import re

SECTIONS = ("done", "blocked", "next")
LABELS = ("docs", "infra", "core")


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
