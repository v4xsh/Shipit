"""--review N: speak a review; it's written up, posted, addressed by an agent, then merged."""
import json

from . import agent, checks, claude, groq, items, proc, worktree
from .console import say, warn
from .github import GhError
from .worktree import GitError

REVIEW = """Turn a spoken code review (English, Hindi or Hinglish, messy, speech-to-text) of a
pull request into a clear written review. Reply with JSON only:
{"summary": "one or two sentences", "points": ["one specific, actionable change per item"]}
Keep the reviewer's intent and tone, be concrete, and don't invent points they didn't make."""

ADDRESS = """You are on the branch of pull request #{number}: {title}

A reviewer asked for these changes:
{points}

Address every point. Keep the changes focused, run the tests ({test}), and when they pass
commit with the message "Address review on #{number}".{trailer} Don't push.
End with a short summary, one line per point."""

YES = {"y", "yes", "haan", "ha", "ok", "post", "post it"}
MERGE = {"merge", "merge it", "merge kar do", "ship it"}


def write_up(said, pr, chat=groq.chat):
    try:
        data = json.loads(chat([{"role": "system", "content": REVIEW},
                                {"role": "user", "content": f"PR: {pr['title']}\n\nSpoken review:\n{said}"}]))
        points = [str(p) for p in data["points"] if str(p).strip()]
        if points:
            return {"summary": str(data.get("summary", "")), "points": points}
    except (groq.GroqError, ValueError, KeyError, TypeError):
        warn("Couldn't tidy the review with Groq; posting it as spoken.")
    return {"summary": "", "points": [said.strip()]}


def markdown(review, said):
    lines = ["### Review"] + ([review["summary"], ""] if review["summary"] else [])
    lines += [f"- [ ] {p}" for p in review["points"]]
    return "\n".join(lines + ["", f"> Said: \"{said.strip()}\"", "", "_Spoken via Shipit._"]) + "\n"


def checkout(root, head):
    """A worktree on the PR's branch, matching origin."""
    worktree.git(root, "fetch", "origin", head)
    if worktree.exists(root, head):
        try:
            worktree.git(root, "branch", "-f", head, f"origin/{head}")
        except GitError:
            pass  # checked out somewhere; use it as it is
    else:
        worktree.git(root, "branch", head, f"origin/{head}")
    return worktree.add(root, head)


def catch_up(path, pr, root):
    """Merge the base branch in first, so the final merge can't conflict."""
    base = pr["baseRefName"]
    worktree.git(path, "fetch", "origin", base)
    sign = agent.trailer(root).split('"')[1] if agent.trailer(root) else ""
    message = f"Merge {base} into {pr['headRefName']}" + (f"\n\n{sign}" if sign else "")
    try:
        worktree.git(path, "merge", "--no-edit", "-m", message, f"origin/{base}")
    except GitError:
        proc.run(["git", "merge", "--abort"], cwd=path)
        warn(f"{base} doesn't merge cleanly into the PR; the agent works on the branch as it is.")


def run(number, said, root, gh, board, read=input, chat=groq.chat, run_claude=claude.run):
    pr = gh.pr(number)
    review = write_up(said, pr, chat)
    cards = [items.make(f"r{k}", "next", p, said, label="core")
             for k, p in enumerate(review["points"], 1)]
    board.items(cards)
    board.status("confirm")
    text = markdown(review, said)
    say(f"\nReview for PR #{number} {pr['title']}\n\n{text}")
    if read("Post it and let the agent address it? [y/n] ").strip().lower().rstrip(".!") not in YES:
        say("Nothing posted.")
        return None
    gh.pr_comment(number, text)
    say(f"  ✎ commented on {pr['url']}")
    run = agent.Run(f"PR #{number}", pr["title"], board, run_claude)
    if gh.dry:
        say(f"  (dry run) claude -p would address the review on {pr['headRefName']}")
        return None
    try:
        path = checkout(root, pr["headRefName"])
        catch_up(path, pr, root)
        run.status("branch ready", pr["headRefName"])
        start = worktree.git(path, "rev-parse", "HEAD")
        points = "\n".join(f"- {p}" for p in review["points"])
        result = run.claude(ADDRESS.format(number=number, title=pr["title"], points=points,
                                           test=checks.test_command(path) or "the tests",
                                           trailer=agent.trailer(root)), path)
        if not result["ok"]:
            run.fail("the agent stopped", pr["headRefName"])
            return None
        if not agent.deliver(run, root, path, pr["headRefName"], start, gh, "", None, new_branch=False):
            return None
        worktree.remove(root, path)
    except (GitError, GhError) as e:
        run.fail(str(e), pr["headRefName"])
        return None
    board.apply([("change", {"id": c["id"], "field": "section", "from": "next", "to": "done",
                             "said": "addressed"}) for c in cards])
    board.status("ready")
    if read(f"Say 'merge' to merge PR #{number}, Enter to stop: ").strip().lower().rstrip(".!") in MERGE:
        gh.pr_merge(number)
        say(f"  ✓ merged PR #{number}")
        board.toast(f"PR #{number} merged")
        return "merged"
    return "pushed"
