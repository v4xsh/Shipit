# Voice log

Typing time assumes 40 wpm. Saved = typing − spoken. `?` = not given yet.
`Chart: no` marks a minor cleanup prompt: logged here, left off the chart.

## Prompt 0
- Time: 2026-10-07 12:10
- Words: 165
- Spoken: 73 s
- Typing: 248 s
- Saved: 175 s

```text
what's up, dude? New project called Shipit. Make a Claude.md with these rules:
1. Log every prompt in voice log.md word for word, with timestamp, word count, the seconds I took to say it (which I'll tell you later), typing time (40 minutes, 40 words a minute), and time saved. Easy: replace with redacted.
2. Never say "done" without running the test.
3. Every commit message ends with the voice prompt number.
4. Readme stays in sync and adds script standard library only. Regenerate an SVG chart of spoken versus typed minutes per word at the top of the Readme on every commit.
5. Keys live in a .gitignore.env.
6. Don't stop to ask. Think it through, make sensible calls, and tell me after.
7. Keep files small. I review by voice and `git init`, remote `github.com/v4xsh/shipit`. S is capital, and everything else is small. Commit after every step and push at the end.
Go ahead and commit this, and that's prompt 0. Go ahead.
```

## Prompt 1
- Time: 2026-10-07 12:28
- Words: 820
- Spoken: 285 s
- Typing: 1230 s
- Saved: 945 s

```text
prompt 0 took 73 seconds. Fill that in.
Now here's what we are building. Think it through properly and put all of it in the plan and README.
Shipit is a command-line tool for developers. Instead of typing a standup, you talk, and it ships. Tagline: Say it. It's tagged. It started.
How it works:
1. You run Shipit inside any Git repo.
2. It checks GH auth, finds the repo from the origin remote, fetches the collaborators with the GH API, and saves them in a gitignore team file.
3. Refreshed if older than a day, it reads the Git log since the last run, stored in a state file, and drafts my done list from the commits.
4. The tool does the boring part, and my voice does the human part.
5. I speak the rest, English or Hinglish, messy, with corrections like "assign it to me," "scratch that," or "actually make that Friday," pronouns like that, and it refers to the previous item.
6. I can speak for the whole team, like "Milap takes the balance bug," "I take the agent," "Milap blocks on Tender," or "I pass the --from-notes with the meeting transcript file." The same parser turns one meeting into issues for everyone mentioned.
7. The Groq model: OpenAI/GPT-OSS-120B env, from .env, temperature 0, JSON output. Parses everything into done, logged, and next items.
8. Each item has a title, a type label (docs, infra, or core), an assignee (managed to the collaborator login with fuzzy matching on the first name and nicknames), an optional deadline, dependencies on other items, and the exact spoken line it came from.
9. A live board, a local HTML page served by the tool on the local host, updated by the server-sent events as the parse comes back. Card slide-in, group done, group by done, block next. Each quoting the spoken line with the assignee, GitHub avatar, label, color, and deadline.
10. Corrections animate. A scratch item fades out, or a reassign item swaps. Waiter later in the agent column shows branch, test, PR status.
11. Keep it one HTML file, no framework. Dark theme looks good on screen recording.
12. Confirm card in the terminal. Nothing touches GitHub before I say yes on confirm via GH.
13. One issue per block and next item labels created if missing, with sensible colors.
14. Assignee set.
15. Deadline becomes milestone with due date created if missing. Dependency written as blocked by #n and blocked #n in the body.
16. Did up by normalized title against open issue, so repeating myself never duplicates.
17. Open issue closed with a comment for done items that match or dated summary comment on a tracking issue called Shipit log created on first one.
18. Every issue body ends up with a line set: quoting the exact words.
19. A script printed and shown on the board was spoken.
20. Seconds issued, open, closed, assign, and type.
21. Ping time saved at 40 minutes or 40 words a minute, plus the running total across runs.
22. A workload check after assignment: if someone has more open issues than the others, say so and let me move one by voice.
23. --agent n runs `claude -p` on the top and next issues in parallel, each on its own branch, with a prompt that includes the issue body.
24. Opens a pull request with GH that quotes the spoken line and streams status to the board's agent column on Windows.
25. Call `claude.cmd`, use `shell true`, encoding `UTF-8`.
26. --debug lets me ramble about a bug and turns each hypothesis into a card, and then agent runs.
27. --review lets me speak a review of a PR, post it as a comment, and rerun the agent to address it.
28. A doc folder with a static site for GitHub Pages comes at the end.
29. Fallbacks so it never dies on camera.
30. If GH fails, print the issue as Markdown and copy to clipboard.
31. If Grok returns bad JSON, retry once, then fallback to a keywords splitter on log next, then socket timeout.
32. Cord-friendly messages.
33. Constraints: Python started library only, Windows first, UTF-8 everywhere, including subprocess calls and console output.
34. Smaller files, one module per concern.
35. Test with recorder model responses so they need no key.
36. Write plan.md with 8 steps.
37. 1. repo, team, and state.
38. 2. git log done list.
39. 3. parser with Grok corrections, English, team matching.
40. 4. live board.
41. 5. confirm card and git actions.
42. 6. receipt and workload.
43. 7. agent.
44. 8. debug review and docsites.
Build steps 1, 2, and 3 now, fully with test. Run the parser for green real agent. Grok with these three messy English standups and show me after this one. Commit after each step, and that's prompt 1. Go ahead and build it.
```

## Prompt 2
- Time: 2026-10-07 15:48
- Words: 406
- Spoken: 154 s
- Typing: 609 s
- Saved: 455 s

```text
Prompt 1 took 285 seconds. Fill it in.
- Grok key is in .env now.
- A few misers: labels are bug, feature, infra, and core, not docs.
- The CHO R1.
- The tagline is: say it's tracked. It started in the fixture.
- Tender is render, and input comes from Wispr Flow, dictating into the terminal, not Win+H. Say that everywhere.
- The rhythmic chart looks terrible. Redo it properly: wide SVG, 900 by 300, that works on GitHub dark and light themes. A dark card background with light text, two bars per prompt, spoken and typed, with the numbers printed above each bar in minutes. Prompt numbers under them, a legend, a headline at the top with the totals, like 12 minutes spoken, 41 minutes typed, 29 minutes saved, 3.4 times faster, and the time saved number in bright accent color. Rounded bars, subtle grid lines, clean sans-serif font.
- It must regenerate from the voice-log.md on every commit like before.
- Add a small table under it in the README: one row per prompt with words, tokens typed and saved.
- Run test/record.py against real Grok.
- Show me all three boards.
- Fix the prompt until the real replies are right.
- Run the test.
- The live board needs to look like a real product, not a demo page: one HTML file served on localhost, no frameworks, open in the browser.
- When shipit starts, dark theme, good typography, generous spacing, subtle shadows, smooth animations.
- Header with the repo name, team of stars, and a live status pill: listening, parsing, ready.
- Four columns: done, blocked, next, and agent.
- Server sends event push items as the party returns, and the card slides in one by one with a slight delay.
- Each card shows the title, a colorful label chip, the Chinese GitHub avatar, the deadline dependencies arrows or chip, and the spoken line in quotes in a muted italic under it.
- A scratched card strikes, throws, and fades.
- A reassigned card swipes to the after with the flip.
- A changed deadline pulses.
- Footer bar for the speed ship that counts up when the run ends.
- Add a --replay flag that plays the three fixtures through the board for demos without running it for real.
- Screenshot: nothing, just make sure it works.
That was prompt 2, so go ahead and build it.
```

## Prompt 3
- Time: 2026-10-07 16:16
- Words: 266
- Spoken: 103 s
- Typing: 399 s
- Saved: 296 s

```text
Prompt 2 took 154 seconds.
The CHO R1 was CHORE, the fifth label. Tagline: it started with the apostrophe S. Milap is now a collaborator. Refresh the team.
Now steps 5 and 6 together:
1. After the board shows the parts, confirm card in the terminal: yes, edit or no. Nothing touches GitHub before yes.
2. On yes, using GH, one issue per blogged item. Labels created if missing, and good colors. Assignee set. Deadlines become milestones with due date. Created if missing. Dependencies written as blog by #n and blocks #n in the body, and cross-linked after creation.
3. Video by normalized title against open issue.
4. Done items close the matching open issue with a comment.
5. Updated summary comment on a tracking issue called shipit.
6. Log created on first run, and every issue body ends with "said: the exact spoken word in quotes". Save state only after a successful run.
7. The speed received in the terminal and on the board: words, seconds, issues, open, closed, assigned, type, timing, time saved at 40 words a minute, and run in total.
8. The workload check: count open issues per person if someone has clearly more, say so.
9. Move the docs 1 to Milap, and it reassigns.
10. A --dry-run flag that prints the `gh` command instead of running them.
11. Test with `gh` mocked, then run it for real on this repo with one messy Hinglish standup that assigns something to Milap, and show me the issue it made.
12. Commit.
That was our prompt number 3. Go ahead and build it.
```

## Prompt 4
- Time: 2026-10-07 23:13
- Words: 288
- Spoken: 98 s
- Typing: 432 s
- Saved: 334 s

```text
prompt 3 took 103 seconds.
Now, step 7: the agent + debug and review.
- After confirming, take the top N next issues assigned to me.
- For each one, create a branch named `shipit/issue/-number`.
- Run `claude-p` with the prompt that includes the issue title, body, the spoken line, and says to implement it.
- Run the test and commit.
- On Windows, call `claude.cmd` with `shell true`, `UTF-8`, and stream its output to the terminal with the issue number as a prefix and to the board's agent column as status: `branch created`, `working trees`, `PRs open`.
- Run them in parallel with threads in separate Git worktrees so they don't fight.
- When one finishes, push the branch and open a pull request with GH that references the issue, codes the spoken line, and summarizes the change.
- If the agent fails, say so and leave the branch.
- `--debug`: I ramble about a bug.
- Grok extracts each hypothesis as a card on the board in the hypothesis column. One agent per hypothesis in its own worktree checks it and reports `confirmed` or `ruled out` with evidence, and I can say `fix it` to open a PR for the confirmed one.
- `--review` with the PR number as `ica review`. Grok turns it into a clear review, comments on the PR, assigns the agent on that branch to address them, and pushes, saying `merge`. It merges the PR.
- Test everything with Claude and GH mocked, then do one real run.
- `shipit -agent 1` on this repo. Let the agent take a small real issue and show me that PR it's open.
- Commit.
That was our prompt 4. Go ahead and build it.
```

## Prompt 5
- Time: 2026-10-08 13:17
- Words: 325
- Spoken: 109 s
- Typing: 488 s
- Saved: 379 s

```text
Prompt 4 took 98 seconds. Agent used the current prompt number in their commits. Fix the leading spaces on line 1 of CLAUDE.md if it's not done. That was a deletion slip.
Now run the two modes for real:
1. `--review 7`. The review looks good. Also print the version in the board header, then merge it. Take it through comments, agent fix, test, and merge, and show me.
2. `--debug`. Plant a small real bug in the chart script, like save minute going negative when spoken time is missing. Then feed this ramble: chart shows negative save time. Maybe the parser reads the question mark as zero, or maybe the subtraction is backward, or the hook runs before the log is written. Let the hypothesis race and fix it with the PR.
Then step it: the docs side.
A docs folder with:
- a static site for GitHub Pages
- a landing page with tagline
- a 60-second install
- How It Works section with one screenshot per step
- a command page for every flag
- a Built by Voice page with the chart, the per-prompt table, and the full voice log rendered
- a link to the repo
Same dark style as the board. Take the screenshot yourself with headless Edge from the replay board, a terminal confirm card, and the GitHub issue and the PR pages via GH, and save them in docs/image-enabled pages on the repo with `gh` API from the docs folder on `main`.
Then the README:
- tagline
- a hero screenshot of the board at the top under the chart
- Try It 2 Minutes
- the commands
- How This Was Built
- line that mouse and enter were used only for approvals
- Prompt and Commits
- Test Count
- a link to the voice log
- Run Thus
End side: run everything, commit, push, and that was prompt 5. Go ahead and build it.
```

## Prompt 6
- Time: 2026-10-08 18:03
- Words: 256
- Spoken: 100 s
- Typing: 384 s
- Saved: 284 s

```text
Prompt 5 took 109 seconds. This is the final pass.
1. Review the whole repo like a judge who has never seen it and has 5 minutes. Read the README, sideboard, and every command. Fix anything confusing, slow, or that could crash on camera. Make sure GH failing, Grok failing, Claude missing, and no internet each get one friendly line in the Markdown and clipboard fallback.
2. Meeting input: add a doc section and a README section called "From a Meeting" that explains --from-notes. Say Wispr Flow's Notetaker is the natural source. The MCP server is Mac only today, so on Windows, you export the notes and pass the file. It includes sample meeting.md in examples with a two-person standup between me and Milab that produces issues for both of us. It asks for it.
3. Add a section to the README called "Notes for the Wispr team" with 5 real friction points from dictating into Claude code during this build, taken from the mishears in the voice-log, like Grok heard as Grok, didup as didup, core as ch1, and one or two things that could have helped, like a dictionary for repo words or a command to send the prompt.
4. In how this was built, state the account was created through the HSGOR fielding. The Wispr Flow history matches the voice-log.
5. Update counts everywhere and make sure the chart and site regenerate. No keys anywhere in the history. .env.example is blank. Run all tests, commit, push, and that was prompt 6. Go ahead.
```

## Prompt 7
- Time: 2026-10-10 19:20
- Words: 59
- Spoken: ? s
- Typing: 88 s
- Saved: ? s
- Chart: no (minor cleanup)

```text
Prompt 6 took 100 seconds. Fill it in. If the HCL Gua referral line isn't in how this was built yet, add it. Log this message as part of prompt 7 entry in the voice log, not as a new prompt, so the chart doesn't get an extra bar for this one. Update the counts, commit, push. Go ahead.
```

## Prompt 8
- Time: 2026-10-10 19:34
- Words: 94
- Spoken: ? s
- Typing: 141 s
- Saved: ? s
- Chart: no (minor cleanup)

```text
fix the README. It's not HCLGUVA referral or anything like that, and it's actually HH Goa, which is Hacker House Goa referral, so fix that part. It's Hacker House Goa.

Again, log this as prompt 7, the previous one, and this as prompt 8. No need to update 8 and 7 on the bar because the bar will have till 6 because those were the major ones. These are just minor cleanups.

Finally, push and check if there is nothing like this. Everything, everywhere, should show HH Goa, not anything else like you did.
```
