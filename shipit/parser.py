"""Transcript -> items via Groq, validated; retry once, then the keyword splitter."""
import datetime
import json

from . import fallback, groq, items, match, prompt


class BadOutput(ValueError):
    pass


def parse(transcript, team, drafts=(), today=None, chat=groq.chat):
    """Return {"items": [...], "source": "groq"|"fallback", "notes": [...]}."""
    msgs = prompt.messages(transcript, team, drafts, today)
    error = None
    for _ in range(2):
        notes = []
        try:
            found = clean(json.loads(chat(msgs)), team, notes)
            return {"items": dedupe(found, drafts), "source": "groq", "notes": notes}
        except groq.GroqError as e:
            error = str(e)
            if not e.bad_json:
                break
        except (ValueError, TypeError, AttributeError) as e:
            error = f"Groq sent messy JSON ({e.__class__.__name__})"
    found = fallback.split(transcript, team)
    note = f"{error}. Used the simple splitter, so check the cards."
    return {"items": dedupe(found, drafts), "source": "fallback", "notes": [note]}


def clean(data, team, notes):
    raw = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise BadOutput("no items list")
    out, seen = [], set()
    for n, r in enumerate(raw, 1):
        if not isinstance(r, dict) or not str(r.get("title", "")).strip():
            raise BadOutput("item without a title")
        section = r.get("section")
        if section not in items.SECTIONS:
            raise BadOutput(f"bad section {section!r}")
        id = str(r.get("id") or f"i{n}")
        id = id if id not in seen else f"i{n}"
        seen.add(id)
        who = r.get("assignee")
        login = match.resolve(who, team) if who else None
        if who and not login:
            notes.append(f"Couldn't match '{who}' to a collaborator; left unassigned.")
        out.append(items.make(
            id, section, title(r["title"]), str(r.get("said") or r["title"]),
            label=r.get("label") if r.get("label") in items.LABELS else "core",
            assignee=login, deadline=iso_date(r.get("deadline")),
            depends_on=[str(d) for d in r.get("depends_on") or []],
            scratched=bool(r.get("scratched")), changes=changes(r.get("changes"), team)))
    ids = {i["id"] for i in out}
    for i in out:
        i["depends_on"] = [d for d in i["depends_on"] if d in ids and d != i["id"]]
    return out


def iso_date(value):
    try:
        return datetime.date.fromisoformat(str(value)).isoformat() if value else None
    except ValueError:
        return None


def changes(raw, team):
    out = []
    for c in raw if isinstance(raw, list) else []:
        if isinstance(c, dict) and c.get("field"):
            c = {k: c.get(k) for k in ("field", "from", "to", "said")}
            if c["field"] == "assignee":
                c["from"] = match.resolve(c["from"], team) or c["from"]
                c["to"] = match.resolve(c["to"], team) or c["to"]
            out.append(c)
    return out


def dedupe(found, drafts):
    """Drafted commits come first; spoken items repeating them are dropped."""
    done = {items.norm_title(d["title"]) for d in drafts}
    return list(drafts) + [i for i in found if items.norm_title(i["title"]) not in done]


def title(value):
    t = str(value).strip().rstrip(".")
    return t[:1].upper() + t[1:]
