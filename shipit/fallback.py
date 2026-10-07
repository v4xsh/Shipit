"""Keyword splitter used when the model is unavailable. Crude, but never fails."""
import re

from . import items, match

DONE = re.compile(r"\b(done|finished|fixed|shipped|merged|completed|kar diya|ho gaya|ho gayi"
                  r"|kar li|kar liya)\b", re.I)
BLOCKED = re.compile(r"\b(blocked|blocks on|stuck|waiting on|waiting for|atka|atki)\b", re.I)
SCRATCH = re.compile(r"\b(?:scratch that|cancel that|never mind|rehne do)\b", re.I)
DOCS = re.compile(r"\b(docs?|readme|guide|notes)\b", re.I)
INFRA = re.compile(r"\b(ci|deploy|docker|pipeline|build|config|infra)\b", re.I)
ME = re.compile(r"\b(i|i'm|i'll|me|my|main|maine|mujhe|mera)\b", re.I)
FILLER = re.compile(r"([\s,.-]*\b(no|nahi|actually|wait|uh|um|okay|ok|so)\b)+[\s,.-]*$", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def section(text):
    return "done" if DONE.search(text) else "blocked" if BLOCKED.search(text) else "next"


def label(text):
    return "docs" if DOCS.search(text) else "infra" if INFRA.search(text) else "core"


def assignee(text, team):
    """A named teammate wins; otherwise first person means me."""
    named = [match.resolve(w, team) for w in re.findall(r"[A-Za-z][\w-]+", text) if w[0].isupper()]
    others = [n for n in named if n and n != team["me"]]
    if others:
        return others[0]
    return team["me"] if team["me"] in named or ME.search(text) else None


def add(out, text, team, scratched=False, min_words=3):
    """Append an item if the text is more than filler. Returns True if added."""
    text = FILLER.sub("", text).strip(" ,.-")
    if len(text.split()) < min_words:
        return False
    out.append(items.make(f"k{len(out) + 1}", section(text), text.rstrip(".!?")[:80], text,
                          label=label(text), assignee=assignee(text, team), scratched=scratched))
    return True


def split(transcript, team):
    out = []
    for line in filter(None, (s.strip() for s in SENTENCE.split(transcript))):
        parts = SCRATCH.split(line, maxsplit=1)
        if len(parts) == 1:
            add(out, line, team)
            continue
        before, after = parts
        if not add(out, before, team, scratched=True, min_words=2) and out:
            out[-1]["scratched"] = True  # "scratch that" on its own: the previous item
        add(out, after, team)
    return out
