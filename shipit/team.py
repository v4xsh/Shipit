"""Collaborators cached in .shipit/team.json, refreshed when older than a day."""
import json
import time
from pathlib import Path

from . import gh, proc
from .console import warn

MAX_AGE = 24 * 3600


def path(root):
    return Path(root) / ".shipit" / "team.json"


def load(root, slug, now=None):
    now = now or time.time()
    p = path(root)
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    if old and old.get("repo") == slug and now - old.get("fetched_at", 0) < MAX_AGE:
        return old
    team = fetch(root, slug, now)
    keep_aliases(team, old)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(team, indent=2, ensure_ascii=False), encoding="utf-8")
    return team


def fetch(root, slug, now):
    ok = gh.authed()
    login = ok and gh.me()
    people = gh.collaborators(slug) if login else None
    if not login:
        warn("GitHub CLI isn't logged in (gh auth login). Using just you for now.")
        login = proc.run(["git", "config", "user.name"], cwd=root)[1].strip() or "me"
    elif people is None:
        warn("Couldn't read collaborators. Using just you for now.")
    people = people or [{"login": login, "avatar_url": ""}]
    members = []
    for p in people:
        name = gh.user(p["login"]).get("name") if ok else None
        members.append({"login": p["login"], "name": name or p["login"],
                        "avatar": p.get("avatar_url", ""), "aliases": []})
    return {"repo": slug, "me": login, "fetched_at": now, "members": members}


def keep_aliases(team, old):
    """Nicknames are typed by hand into team.json; never lose them on refresh."""
    saved = {m["login"]: m.get("aliases", []) for m in (old or {}).get("members", [])}
    for m in team["members"]:
        m["aliases"] = saved.get(m["login"], [])
