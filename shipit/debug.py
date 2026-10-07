"""--debug: ramble about a bug; each hypothesis gets an agent that confirms or rules it out."""
import json
import re

from . import agent, checks, claude, groq, items, proc, worktree
from .console import say, warn
from .github import GhError
from .worktree import GitError

HYPOTHESES = """You turn a developer's spoken ramble about a bug (English, Hindi or Hinglish,
messy, speech-to-text) into distinct hypotheses about its cause. Reply with JSON only:
{"bug": "one-line summary of the symptom",
 "hypotheses": [{"id": "h1", "title": "short cause", "said": "exact words it came from",
                 "check": "how to verify it in the code"}]}
2 to 5 hypotheses, most likely first, only ones the speaker said or directly implied.
"said" is copied verbatim from the ramble."""

INVESTIGATE = """A developer is chasing a bug: {bug}

Hypothesis to check: {title}
How to check it: {check}
They said: "{said}"

Investigate in this repository whether this hypothesis is the cause. Read the code; run the
tests or tiny scripts if that helps. Don't commit, and undo any probe edits you make.
End your reply with exactly these two lines:
VERDICT: confirmed  (or: VERDICT: ruled out)
EVIDENCE: one sentence, with file:line or the output that proves it"""

FIX = """Fix this bug: {bug}

The confirmed cause: {title}
Evidence: {evidence}

Make the smallest fix, add a regression test, run the tests ({test}), and when they pass commit
with the message "Fix: {bug}". Don't push. End with a two-sentence summary."""

VERDICT = re.compile(r"VERDICT:\s*(confirmed|ruled out)", re.I)
EVIDENCE = re.compile(r"EVIDENCE:\s*(.+)", re.I)


def extract(ramble, chat=groq.chat):
    """(bug, [hypotheses]). Without Groq, the whole ramble is one hypothesis."""
    try:
        data = json.loads(chat([{"role": "system", "content": HYPOTHESES},
                                {"role": "user", "content": ramble}]))
        hyps = [h for h in data["hypotheses"] if h.get("title")]
        if hyps:
            for n, h in enumerate(hyps, 1):
                h["id"] = f"h{n}"
                h.setdefault("said", h["title"])
                h.setdefault("check", "")
            return data.get("bug") or hyps[0]["title"], hyps
    except (groq.GroqError, ValueError, KeyError, TypeError):
        warn("Couldn't split the ramble into hypotheses; checking it as one.")
    line = ramble.strip().splitlines()[0][:80]
    return line, [{"id": "h1", "title": line, "said": ramble.strip(), "check": ""}]


def verdict(text):
    v = VERDICT.findall(text or "")
    e = EVIDENCE.findall(text or "")
    return (v[-1].lower() if v else "unclear"), (e[-1].strip() if e else "no evidence given")


def investigate(h, bug, root, base, board, run_claude=claude.run):
    branch = f"shipit/debug-{h['id']}"
    run = agent.Run(h["id"], h["title"], board, run_claude)
    try:
        path = worktree.add(root, branch, base)
    except GitError as e:
        run.fail(str(e))
        return {**h, "verdict": "unclear", "evidence": str(e), "path": None, "branch": branch}
    run.status("branch created", branch)
    result = run.claude(INVESTIGATE.format(bug=bug, **h), path)
    found, evidence = verdict(result["result"]) if result["ok"] else ("unclear", "the agent stopped")
    run.status(found, evidence)
    section = {"confirmed": "done", "ruled out": "blocked"}.get(found)
    if section:
        board.apply([("change", {"id": h["id"], "field": "section", "from": "next", "to": section,
                                 "said": evidence})])
    return {**h, "verdict": found, "evidence": evidence, "path": path, "branch": branch}


def fix(h, bug, ramble, root, base, gh, board, run_claude=claude.run):
    run = agent.Run(h["id"], f"Fix: {h['title']}", board, run_claude)
    result = run.claude(FIX.format(bug=bug, title=h["title"], evidence=h["evidence"],
                                   test=checks.test_command(h["path"]) or "the tests"), h["path"])
    if not result["ok"]:
        run.fail("the agent stopped", h["branch"])
        return None
    body = lambda stat: (f"Fixes: {bug}\n\n> Said: \"{h['said']}\"\n\n**Cause (confirmed):** {h['title']}\n"
                         f"**Evidence:** {h['evidence']}\n\n### Summary\n{result['result'].strip()}\n\n"
                         f"### Changes\n```\n{stat}\n```\n\nOpened by Shipit --debug (Claude Code).\n")
    try:
        return agent.deliver(run, root, h["path"], h["branch"], base, gh, f"Fix: {bug}", body)
    except (GitError, GhError) as e:
        run.fail(str(e), h["branch"])
        return None


def run(ramble, root, gh, board, read=input, chat=groq.chat, run_claude=claude.run):
    board.status("parsing")
    bug, hyps = extract(ramble, chat)
    say(f"\nBug: {bug}")
    board.items([items.make(h["id"], "next", h["title"], h["said"], label="bug") for h in hyps])
    board.status("shipping")
    base = worktree.current_branch(root)
    checked = agent.parallel([lambda h=h: investigate(h, bug, root, base, board, run_claude)
                              for h in hyps])
    for h in checked:
        say(f"  {h['id']} {h['verdict']:<10} {h['title']}  ({h['evidence']})")
    confirmed = [h for h in checked if h["verdict"] == "confirmed"]
    board.status("ready")
    prs = []
    if confirmed and read("Say 'fix it' to open a PR for the confirmed cause, Enter to stop: ") \
            .strip().lower().rstrip(".!") in ("fix it", "fix", "fix kar do", "kar do", "y", "yes"):
        prs = [fix(h, bug, ramble, root, base, gh, board, run_claude) for h in confirmed]
    elif not confirmed:
        say("Nothing confirmed. Try rambling a bit more about what you saw.")
    tried = {h["id"] for h in confirmed} if prs else set()
    for h in checked:  # a fix attempt keeps its branch (a PR, or a failure to inspect)
        if h["id"] in tried:
            continue
        if h["path"]:
            worktree.remove(root, h["path"])
        proc.run(["git", "branch", "-D", h["branch"]], cwd=root)
    return checked, prs
