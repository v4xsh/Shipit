"""The instructions that turn a messy spoken standup into structured items."""
import datetime
import json

SYSTEM = """You turn a spoken standup (English, Hindi or Hinglish, messy, transcribed by
speech-to-text) into work items. Reply with JSON only:
{"items": [{"id": "i1", "section": "done|blocked|next", "title": "...",
  "label": "docs|infra|core", "assignee": "...", "deadline": "YYYY-MM-DD" or null,
  "depends_on": ["i2"], "said": "...", "scratched": false,
  "changes": [{"field": "...", "from": "...", "to": "...", "said": "..."}]}]}

Rules:
- One item per piece of work. Title: short, imperative, English, no names or dates.
- section: done = finished; blocked = can't move until something else happens;
  next = will do. "X blocks on Y" / "X is waiting on Y" means X's item is blocked.
- label: docs (README, guides, notes), infra (CI, deploy, build, tooling, config), else core.
- assignee: the person's name exactly as spoken, "me" for the speaker (I, main, mujhe,
  "assign it to me"), or null if nobody is named. The team list helps you spell names.
- deadline: resolve relative dates ("Friday", "kal", "next week") against today.
- depends_on: ids of other items in this list that must finish first.
- said: the exact words from the transcript this item came from, copied verbatim.
- Corrections apply to the item they point at, usually the previous one ("it", "that",
  "usko"). "scratch that" / "cancel that" / "rehne do": keep the item with
  "scratched": true. "actually make that Friday", "assign it to me", "no wait, Milap":
  update the item and record each change in "changes" (field is title, assignee,
  deadline, section or label; from/to are the old/new values; said is the correction words).
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
