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
- label: bug (something broken or flaky to fix), feature (new capability users see),
  infra (CI, deploy, build, tooling, config, hosting), chore (upkeep: docs, release notes,
  cleanup, dependency bumps, renames), core (everything else: refactors, internal work,
  third-party integrations).
- assignee: the person's name exactly as spoken, or "me" for the speaker (I, I'm, my,
  main, maine, mujhe, mera, "assign it to me", or the speaker's own name). Work the
  speaker did or will do with nobody else named is "me". null only for work left open
  ("someone needs to...") that nobody takes. The team list helps you spell names.
- deadline: resolve relative dates ("Friday", "kal", "next week") against today.
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


def messages(transcript, team, drafts, today=None):
    today = today or datetime.date.today()
    people = [{"login": m["login"], "name": m.get("name"), "aliases": m.get("aliases", [])}
              for m in team["members"]]
    context = {"today": f"{today.isoformat()} ({today.strftime('%A')})",
               "speaker": team["me"], "team": people,
               "already_done_from_git": [d["title"] for d in drafts]}
    user = (f"Context:\n{json.dumps(context, ensure_ascii=False)}\n\n"
            f"Transcript:\n{transcript}")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
