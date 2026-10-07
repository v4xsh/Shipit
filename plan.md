# Shipit plan

Talk your standup; Shipit turns it into GitHub issues, a live board and agent runs.
Python stdlib only, Windows first, UTF-8 everywhere (console, files, subprocess).
One module per concern in `shipit/`. Tests use recorded model responses (no key needed).

## Data model

An **item** has: `id`, `section` (`done` | `blocked` | `next`), `title`,
`label` (`bug` | `feature` | `infra` | `core` | `chore`), `assignee` (collaborator login), `deadline`
(ISO date or null), `depends_on` (item ids), `said` (exact spoken words),
`scratched` (bool) and `changes` (corrections applied: field, from, to, said).
Scratched items and `changes` stay in the result so the board can animate them.

## 1. Repo, team and state ✅
- Find the repo root; read `owner/name` from the `origin` remote (https or ssh).
- `gh auth status`, then `gh api user` for "me" and `gh api repos/:o/:r/collaborators`
  plus `users/:login` for real names. Cache it in `.shipit/team.json` (gitignored), refreshed
  when older than a day. Users add `aliases` (nicknames) by hand in that file.
- `.shipit/state.json` keeps the last run's commit and time, plus running totals.
- If `gh` fails, continue with a team of just "me" and say so.

## 2. Git log → done list ✅
- `git log <last-run-commit>..HEAD` by my email (first run: last 24 hours), no merges.
- Each commit becomes a drafted `done` item: prefix like `feat:` stripped, label guessed
  from the commit prefix and files touched (bug/feature/infra/core/chore), `said` = `commit <sha>`.

## 3. Parser ✅
- Input: Wispr Flow dictating into the terminal, `--text`, or `--from-notes FILE`.
- Groq `openai/gpt-oss-120b` (override with `GROQ_MODEL`), key `GROQ_API_KEY` from `.env`,
  temperature 0, JSON output. Prompt gets today's date, the team, and the drafted done list.
- Handles English and Hinglish, corrections ("scratch that", "assign it to me",
  "actually make that Friday"), pronouns that point to the previous item, and whole-team
  speech ("Milap takes the balance bug", "Milap blocks on Render").
- Names map to logins: exact login/name/alias, then fuzzy (difflib) on first names.
- Bad JSON → retry once → keyword splitter fallback. Network timeout → keyword splitter.

## 4. Live board ✅
- Tool serves one HTML file (no framework, dark theme) on localhost; server-sent events
  push items as the parse returns. Columns Done / Blocked / Next; cards slide in, quote the
  spoken line, show assignee + GitHub avatar, label colour, deadline.
- Corrections animate: scratched cards fade out, reassigned cards swap avatar.
- An Agent column (filled in step 7) shows branch, tests, PR status.
- Footer receipt counts up items, words and minutes saved.
- `--replay` plays the three recorded standups through the board for demos.

## 5. Confirm card and GitHub actions
- Terminal confirm card; nothing touches GitHub before "yes". All calls go via `gh`.
- One issue per blocked/next item; labels created if missing with sensible colours;
  assignee set; deadline → milestone with due date (created if missing);
  dependencies written as `Blocked by #n` / `Blocks #n` in the body.
- Dedupe by normalized title against open issues, so repeating yourself never duplicates.
- Done items: close the matching open issue with a comment, otherwise add a dated summary
  comment on a tracking issue "Shipit log" (created the first time).
- Every issue body ends with `Said: "<exact words>"`.
- If `gh` fails: print the issues as Markdown and copy them to the clipboard (`clip`).
- State saved only after a successful run.

## 6. Receipt and workload
- Receipt in the terminal and on the board: issues opened, closed, assigned, words spoken,
  time saved vs typing at 40 wpm, plus the running total across runs.
- Workload check: if someone has clearly more open issues than the rest, say so and let me
  move one by voice.

## 7. Agent
- `--agent N` runs `claude -p` on the top N next issues in parallel, each on its own branch,
  prompt includes the issue body. Opens a PR via `gh` quoting the spoken line, streams
  status to the board's Agent column.
- Windows: call `claude.cmd` with `shell=True`, `encoding="utf-8"`.

## 8. Debug, review, docs site
- `--debug`: ramble about a bug; each hypothesis becomes a card, then agent runs.
- `--review PR`: speak a review, post it as a PR comment, rerun the agent to address it.
- `docs/` static site for GitHub Pages.

## Never die on camera
Every external call (gh, Groq, git, claude) has a fallback and a short, friendly,
camera-safe message instead of a traceback.
