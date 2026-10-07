# Voice log

Typing time assumes 40 wpm. Saved = typing − spoken. `?` = not given yet.

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
- Spoken: ? s
- Typing: 609 s
- Saved: ? s

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
