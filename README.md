<!-- chart -->
![Spoken vs typed minutes per prompt](chart.svg)

| Prompt | Words | Spoken (min) | Typed (min) | Saved (min) |
|---:|---:|---:|---:|---:|
| 0 | 165 | 1.2 | 4.1 | 2.9 |
| 1 | 820 | 4.8 | 20.5 | 15.8 |
| 2 | 406 | 2.6 | 10.2 | 7.6 |
| 3 | 266 | ? | 6.7 | ? |
| **Total** | **1391** | **8.5** | **34.8** | **26.2** |
<!-- /chart -->

# Shipit

**Say it. It's tracked. It's started.**

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
   title, label (bug/feature/infra/core/chore), assignee login, deadline, dependencies and the exact words said.
6. A live board opens in your browser (localhost, one HTML file, no framework): Done, Blocked,
   Next and Agent columns; cards slide in as the parse returns, quoting what you said.
   Corrections play out on screen: scratched cards strike, shake and fade, reassigned avatars
   flip, changed deadlines pulse. A receipt counts up the minutes saved.
7. *(coming)* A confirm card, then GitHub issues, labels, milestones, closes, workload check,
   and `--agent N` to hand the next issues to Claude Code. See [plan.md](plan.md).

## Setup

```sh
cp .env.example .env                 # add GROQ_API_KEY; .env is gitignored
gh auth login
python -m shipit                     # dictate with Wispr Flow, empty line to finish
python -m shipit --text "I fixed login. Milap takes the balance bug by Friday."
python -m shipit --from-notes meeting.txt   # one meeting, issues for everyone mentioned
python -m shipit --replay            # demo: three recorded standups on the board, no keys
python -m shipit --no-board          # terminal only
```

## Development

Python stdlib only. Voice log in [voice-log.md](voice-log.md); the chart above compares
minutes spoken vs. minutes it would take to type (40 wpm).

```sh
git config core.hooksPath hooks   # pre-commit regenerates the chart
python -m unittest                # tests use recorded model responses, no key needed
python tests/record.py             # re-record them from real Groq (needs .env key)
```
