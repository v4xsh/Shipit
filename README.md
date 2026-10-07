<!-- chart -->
![Spoken vs typed minutes per prompt](chart.svg)

| Prompt | Words | Spoken (min) | Typed (min) | Saved (min) |
|---:|---:|---:|---:|---:|
| 0 | 165 | 1.2 | 4.1 | 2.9 |
| 1 | 820 | 4.8 | 20.5 | 15.8 |
| 2 | 406 | ? | 10.2 | ? |
| **Total** | **985** | **6.0** | **24.6** | **18.7** |
<!-- /chart -->

# Shipit

**Say it. It's tracked. It started.**

Shipit is a command-line tool for developers. Instead of typing a standup, you talk, and it ships.

## How it works

1. Run `python -m shipit` inside any Git repo.
2. It checks `gh` auth, finds the repo from `origin`, and caches your collaborators in
   `.shipit/team.json` (gitignored, refreshed daily; add nicknames under `aliases`).
3. It reads `git log` since the last run and drafts your **done** list from your commits.
4. You speak the rest, English or Hinglish, messy is fine: "Milap takes the balance bug",
   "assign it to me", "scratch that", "actually make that Friday". Speak for the whole team,
   or pass a meeting transcript with `--from-notes notes.txt`.
5. Groq (`openai/gpt-oss-120b`) turns it into **done / blocked / next** items, each with a
   title, label (bug/feature/infra/core), assignee login, deadline, dependencies and the exact words said.
6. *(coming)* A live dark-theme board on localhost, a confirm card, then GitHub issues,
   labels, milestones, closes, a receipt with time saved, and `--agent N` to hand the next
   issues to Claude Code. See [plan.md](plan.md).

## Setup

```sh
cp .env.example .env                 # add GROQ_API_KEY; .env is gitignored
gh auth login
python -m shipit                     # dictate with Wispr Flow, empty line to finish
python -m shipit --text "I fixed login. Milap takes the balance bug by Friday."
```

## Development

Python stdlib only. Voice log in [voice-log.md](voice-log.md); the chart above compares
minutes spoken vs. minutes it would take to type (40 wpm).

```sh
git config core.hooksPath hooks   # pre-commit regenerates the chart
python -m unittest                # tests use recorded model responses, no key needed
python tests/record.py             # re-record them from real Groq (needs .env key)
```
