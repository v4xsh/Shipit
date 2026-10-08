<!-- chart -->
![Spoken vs typed minutes per prompt](chart.svg)

| Prompt | Words | Spoken (min) | Typed (min) | Saved (min) |
|---:|---:|---:|---:|---:|
| 0 | 165 | 1.2 | 4.1 | 2.9 |
| 1 | 820 | 4.8 | 20.5 | 15.8 |
| 2 | 406 | 2.6 | 10.2 | 7.6 |
| 3 | 266 | 1.7 | 6.7 | 4.9 |
| 4 | 288 | 1.6 | 7.2 | 5.6 |
| 5 | 325 | ? | 8.1 | -6.0 |
| **Total** | **1945** | **11.9** | **48.6** | **36.8** |
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
7. A confirm card in the terminal: **yes**, **edit** (say the fix, the board animates it) or
   **no**. Nothing touches GitHub before yes.
8. On yes, via `gh`: one issue per blocked/next item with label, assignee and a `Due <date>`
   milestone (all created if missing), `Blocked by #n` / `Blocks #n` cross-links, no duplicates
   of open issues, done items close their issue, and a dated summary goes on the "Shipit log"
   issue. Every issue body ends with `Said: "<your exact words>"`.
9. A receipt (terminal and board): words, seconds, opened, closed, assigned, time saved vs
   typing at 40 wpm, and the running total. Then a workload check: if someone carries clearly
   more, it says so and you can move one by voice ("docs wala Milap ko de do").
10. `--agent N`: Claude Code (`claude -p`) works your top N next issues in parallel, each in its
    own git worktree on `shipit/issue-<n>`. Its steps stream to the terminal (`[#7] …`) and the
    board's Agent column. Shipit runs the tests itself, then pushes and opens a PR that closes
    the issue and quotes what you said. A failed agent keeps its branch for you to look at.
11. `--debug`: ramble about a bug. Each hypothesis becomes a card and gets its own agent, which
    reports confirmed or ruled out with evidence. Say "fix it" to get a PR for the confirmed one.
12. `--review PR`: speak a review. It's written up and posted on the PR, an agent addresses it
    on the PR branch and pushes, and saying "merge" merges it.

## Setup

```sh
cp .env.example .env                 # add GROQ_API_KEY; .env is gitignored
gh auth login
python -m shipit                     # dictate with Wispr Flow, empty line to finish
python -m shipit --text "I fixed login. Milap takes the balance bug by Friday."
python -m shipit --from-notes meeting.txt   # one meeting, issues for everyone mentioned
python -m shipit --replay            # demo: three recorded standups on the board, no keys
python -m shipit --agent 1           # ...then Claude Code takes your top next issue to a PR
python -m shipit --debug             # ramble about a bug; agents check each hypothesis
python -m shipit --review 12         # speak a review of PR #12
python -m shipit --dry-run           # print the gh commands instead of running them
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
