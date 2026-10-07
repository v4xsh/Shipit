# Shipit — rules for Claude

1. **Voice log.** Every prompt goes into `voice-log.md` word for word, with timestamp,
   word count, seconds spoken (user says it later; `?` until then), typing time at
   40 wpm, and time saved. Any key/secret is replaced with `[REDACTED]`.
2. **Verify.** Never say "done" without running the tests (`python -m unittest`).
3. **Commits** end with the voice prompt number, e.g. `Voice prompt: 0`.
4. **README in sync.** `chart.py` (stdlib only) regenerates `chart.svg` (spoken vs typed
   minutes, per prompt) and embeds it at the top of `README.md`. The pre-commit hook in
   `hooks/` runs it on every commit (`git config core.hooksPath hooks`).
5. **Secrets** live in `.env`, which is gitignored. Never commit keys.
6. **Don't ask.** Think it through, make sensible calls, report them afterwards.
7. **Keep files small.** The user reviews by voice.
8. **Remote:** `https://github.com/v4xsh/Shipit.git`
9. **Commit after every step**, and push at the end.
