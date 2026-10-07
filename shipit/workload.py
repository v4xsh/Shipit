"""Who has too much open? And "move the docs one to Milap" by voice."""
import json
import re

from . import groq, match, ship

MOVE = """You get a team's open GitHub issues and one spoken sentence (English or Hinglish)
asking to move an issue to someone. Reply with JSON only: {"number": <issue number or null>,
"to": "<name exactly as spoken, or me>"}. Pick the issue the sentence describes."""


def counts(open_issues, team):
    out = {m["login"]: 0 for m in team["members"]}
    for i in open_issues:
        if i["title"] == ship.LOG_TITLE:
            continue
        for a in i.get("assignees", []):
            out[a["login"]] = out.get(a["login"], 0) + 1
    return out


def heavy(counts):
    """(login, n) when one person clearly carries more than everyone else."""
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    if len(ranked) < 2:
        return None
    (top, n), second = ranked[0], ranked[1][1]
    return (top, n) if n - second >= 2 and n >= 1.5 * max(second, 1) else None


def message(counts):
    spread = ", ".join(f"@{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    load = heavy(counts)
    if not load:
        return f"Workload looks even: {spread}."
    return f"Heads-up: @{load[0]} has {load[1]} open issues, clearly more than the rest ({spread})."


def move(sentence, open_issues, team, chat=groq.chat):
    """Return (issue, login) for "move the docs one to Milap", or None."""
    issues = [i for i in open_issues if i["title"] != ship.LOG_TITLE]
    listing = [{"number": i["number"], "title": i["title"],
                "assignees": [a["login"] for a in i.get("assignees", [])]} for i in issues]
    try:
        reply = json.loads(chat([{"role": "system", "content": MOVE},
                                 {"role": "user", "content": json.dumps(
                                     {"issues": listing, "said": sentence}, ensure_ascii=False)}]))
        number, to = reply.get("number"), reply.get("to")
    except (groq.GroqError, ValueError, AttributeError):
        number, to = guess(sentence, issues)
    issue = next((i for i in issues if i["number"] == number), None)
    login = match.resolve(to, team)
    return (issue, login) if issue and login else None


def guess(sentence, issues):
    """Keyword fallback: the issue sharing most words, and the name after "to" or before "ko"."""
    m = re.search(r"\bto\s+@?([\w-]+)|([\w-]+)\s+ko\b", sentence, re.I)
    to = m and (m.group(1) or m.group(2))
    words = set(re.findall(r"\w+", sentence.lower()))
    scored = [(len(words & set(re.findall(r"\w+", i["title"].lower()))), i["number"]) for i in issues]
    best = max(scored, default=(0, None))
    return (best[1] if best[0] else None), to
