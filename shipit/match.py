"""Map a spoken name ("Milap", "Milu", "me", "main") to a collaborator login."""
import difflib
import re

ME = {"me", "i", "myself", "self", "mujhe", "main", "mai", "mein", "mera", "mere", "apun"}


def keys(member):
    """Every lowercase way to say this person: login, its parts, name, first name, aliases."""
    login = member["login"].lower()
    name = (member.get("name") or "").lower()
    out = {login, name, *re.split(r"[-_.\d]+", login), *name.split()[:1]}
    out.update(a.lower() for a in member.get("aliases", []))
    return {k for k in out if len(k) > 1}


def resolve(spoken, team):
    """Return a login or None when nobody is a confident match."""
    said = (spoken or "").strip().lower().lstrip("@")
    if not said:
        return None
    if said in ME:
        return team["me"]
    table = {k: m["login"] for m in team["members"] for k in keys(m)}
    if said in table:
        return table[said]
    first = said.split()[0]
    if first in table:
        return table[first]
    close = difflib.get_close_matches(said, table, n=1, cutoff=0.75)
    return table[close[0]] if close else None
