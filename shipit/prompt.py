"""The instructions that turn a messy spoken standup into structured items."""
import datetime
import json

SYSTEM = """You turn a spoken standup (English, Hindi or Hinglish, messy, transcribed by
speech-to-text) into work items. Reply with JSON only:
{"items": [{"id": "i1", "section": "done|blocked|next", "title": "...",
  "label": "bug|feature|infra|core|chore", "assignee": "...", "deadline": "YYYY-MM-DD" or null,
  "depends_on": ["i2"], "said": "...", "scratched": false,
  "changes": [{"field": "...", "from": "...", "to": "...", "said": "..."}]}]}

Rules:
- One item per piece of work: "fixed A and did B" is two items. Title: short,
  imperative, English, starts with a capital letter, no names or dates.
- section: done = finished; blocked = can't move until something else happens;
  next = will do.
- "X blocks on Y" / "X is waiting on Y" / "X atka hai Y pe": add a separate blocked item for
  what X waits on (e.g. "Get Render API keys"), assigned to X. Don't change X's other
  items or their depends_on.
- "A can't start till B is done" / "A ke liye pehle B": A is blocked and A.depends_on
  has B's id. B keeps its own section (usually next). Never mark B blocked for this.
- label: bug (something broken or flaky to fix, so "fixed X" is a bug), feature (new capability users see),
  infra (CI, deploy, build, tooling, config, hosting), chore (upkeep: docs, release notes,
  cleanup, dependency bumps, renames), core (everything else: refactors, internal work,
  third-party integrations).
- assignee: the person's name exactly as spoken, or "me" for the speaker (I, I'm, my,
  main, maine, mujhe, mera, "assign it to me", or the speaker's own name). Work the
  speaker did or will do with nobody else named is "me". null only for work left open
  ("someone needs to...") that nobody takes. The team list helps you spell names.
- deadline: look relative dates ("Friday", "kal", "tomorrow", "next week") up in the
  "dates" table in the context; never compute weekdays yourself. Hindi "kal" with a
  future verb means tomorrow.
- depends_on: ids of other items in this list that must finish first.
- said: the exact words from the transcript this item came from, copied verbatim
  (the original mention; correction words go in changes, not here).
- Corrections apply to the item they point at, usually the previous one ("it", "that",
  "usko"). "scratch that" / "cancel that" / "rehne do": keep the item with
  "scratched": true. "actually make that Friday", "assign it to me", "no wait, Milap",
  "X will... no wait, Y": update the item and record EVERY change in "changes" (field is
  title, assignee, deadline, section or label; from/to are old/new values, a name the
  speaker abandoned is the "from"; said is the correction words, verbatim).
- Ignore filler (uh, okay so, basically, matlab). Don't invent work that wasn't said.
- Items already drafted from git commits are listed; don't repeat them."""


def dates(today):
    """Weekday names -> the next such date, so the model never does calendar math."""
    day = lambda n: (today + datetime.timedelta(days=n)).isoformat()
    table = {"today": day(0), "tomorrow (kal)": day(1), "day after tomorrow (parso)": day(2)}
    for n in range(1, 8):
        d = today + datetime.timedelta(days=n)
        table[d.strftime("%A")] = d.isoformat()
    table["next week"] = day(7)
    return table


def context(team, today=None):
    today = today or datetime.date.today()
    return {"today": f"{today.isoformat()} ({today.strftime('%A')})", "dates": dates(today),
            "speaker": team["me"],
            "team": [{"login": m["login"], "name": m.get("name"), "aliases": m.get("aliases", [])}
                     for m in team["members"]]}


def messages(transcript, team, drafts, today=None):
    ctx = {**context(team, today), "already_done_from_git": [d["title"] for d in drafts]}
    user = f"Context:\n{json.dumps(ctx, ensure_ascii=False)}\n\nTranscript:\n{transcript}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


AMEND = SYSTEM + """

You are amending an existing list: you get the current items as JSON and one new spoken
edit. Return the full updated list with the same ids. Change only what the edit asks. For
every field you change, append to that item's "changes" (said = the edit words, verbatim).
New work gets a new id. Work the edit removes stays in the list with "scratched": true."""


def amend_messages(current, edit, team, today=None):
    ctx = {**context(team, today), "items": current}
    user = f"Context:\n{json.dumps(ctx, ensure_ascii=False)}\n\nEdit:\n{edit}"
    return [{"role": "system", "content": AMEND}, {"role": "user", "content": user}]
