"""--agent N: Claude Code works my next issues in parallel, one worktree each, a PR at the end."""
import re
import threading
from pathlib import Path

from . import checks, claude, net, proc, worktree
from .console import say, warn
from .github import GhError
from .worktree import GitError

LOCK = threading.Lock()

ISSUE = """You are working on GitHub issue #{number} in this repository.

Title: {title}

{body}

The person who asked for it said: "{said}"

Implement it. Keep the change small and focused and match the surrounding code. Add or update
tests, run them ({test}), and when they pass commit everything with the message
"{title} (#{number})".{trailer} Don't push, don't open pull requests, don't edit voice-log.md.
End with a two-sentence summary of what you changed."""


def trailer(root):
    """Repos that keep a voice log sign every commit with the current prompt; agents do too."""
    log = Path(root) / "voice-log.md"
    nums = re.findall(r"^## Prompt (\d+)", log.read_text(encoding="utf-8"), re.M) if log.exists() else []
    return f' End the commit message with a blank line, then "Voice prompt: {nums[-1]}".' if nums else ""


class Run:
    """One agent's voice: status lines to the terminal (prefixed) and to the board's Agent column."""

    def __init__(self, key, title, board, run_claude=claude.run):
        self.key, self.title, self.board, self.run_claude = key, title, board, run_claude

    def status(self, status, detail="", url=None):
        self.board.agent({"key": self.key, "title": self.title, "status": status,
                          "detail": detail, "url": url})
        self.echo(f"{status}{': ' + detail if detail else ''}{' ' + url if url else ''}")

    def echo(self, line):
        with LOCK:
            say(f"[{self.key}] {line}")

    def fail(self, reason, where=None):
        self.status("failed", reason)
        with LOCK:
            warn(f"{self.key}: {reason}." + (f" Left it on {where}." if where else ""))

    def claude(self, prompt, cwd):
        def line(text):
            self.echo(text)
            self.board.agent({"key": self.key, "title": self.title, "status": "working",
                              "detail": text, "url": None})
        return self.run_claude(prompt, cwd, on_line=line)


def deliver(run, root, path, branch, base, gh, title, make_body, new_branch=True):
    """The finish line every agent shares: commits exist, tests pass, push, then a PR."""
    if worktree.ahead(path, base) == 0:
        run.fail("the agent made no commit", branch)
        return None
    run.status("testing")
    passed, tail = checks.run_tests(path)
    if not passed:
        run.fail(f"tests fail ({tail.splitlines()[-1] if tail else 'no output'})", branch)
        return None
    run.status("pushing")
    worktree.git(path, "push", "-u", "origin", branch)
    if not new_branch:
        run.status("pushed")
        return branch
    url = gh.create_pr(branch, base, title, make_body(worktree.diffstat(path, base)))
    run.status("PR open", url=url)
    worktree.remove(root, path)
    return url


def pr_body(number, said, summary, stat):
    return (f"Closes #{number}\n\n> Said: \"{said}\"\n\n### Summary\n{summary.strip() or '—'}\n\n"
            f"### Changes\n```\n{stat}\n```\n\nOpened by Shipit's agent (Claude Code).\n")


def pick(done, found, me, n):
    """Top n next items assigned to me that have an issue, in the order I said them."""
    numbers = {i["id"]: num for i, num in done["opened"] + done["duplicates"]}
    return [(numbers[i["id"]], i) for i in found
            if i["id"] in numbers and i["section"] == "next" and i["assignee"] == me
            and not i["scratched"]][:n]


def work(number, item, root, base, gh, board, run_claude=claude.run):
    branch = f"shipit/issue-{number}"
    run = Run(f"#{number}", item["title"], board, run_claude)
    try:
        issue = gh.issue(number)
        path = worktree.add(root, branch, base)
        run.status("branch created", branch)
        prompt = ISSUE.format(number=number, title=issue["title"], body=issue["body"],
                              said=item["said"], test=checks.test_command(path) or "the tests",
                              trailer=trailer(root))
        result = run.claude(prompt, path)
        if not result["ok"]:
            run.fail(f"the agent stopped ({result['result'][:80] or 'exit ' + str(result['code'])})",
                     branch)
            return {"number": number, "branch": branch, "pr": None}
        url = deliver(run, root, path, branch, base, gh, f"{issue['title']} (#{number})",
                      lambda stat: pr_body(number, item["said"], result["result"], stat))
    except (GitError, GhError, OSError, ValueError, KeyError) as e:
        run.fail(str(e) or e.__class__.__name__, branch)
        url = None
    return {"number": number, "branch": branch, "pr": url}


def parallel(jobs):
    """Run callables on threads; results in the same order."""
    results = [None] * len(jobs)

    def go(k, job):
        try:
            results[k] = job()
        except Exception as e:  # one agent's surprise must not take the others (or the demo) down
            with LOCK:
                warn(f"An agent hit {e.__class__.__name__}: {e}")

    threads = [threading.Thread(target=go, args=(k, job)) for k, job in enumerate(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def unpushed(root, base):
    code, out, _ = proc.run(["git", "rev-list", "--count", f"origin/{base}..{base}"], cwd=root)
    return int(out.strip() or 0) if code == 0 else 0


def run_all(picks, root, gh, board, run_claude=claude.run):
    if not picks:
        say("No next issues assigned to you for the agent.")
        return []
    if run_claude is claude.run and net.claude_missing():
        warn(net.CLAUDE + " Your issues are on GitHub.")
        return []
    base = worktree.current_branch(root)
    if gh.dry:
        for number, _ in picks:
            say(f"  (dry run) claude -p would work #{number} on branch shipit/issue-{number}")
        return []
    if unpushed(root, base):
        warn(f"{base} has commits that aren't on origin yet; PRs will include them. Push {base} first.")
    say(f"\nAgents on {', '.join(f'#{n}' for n, _ in picks)} (base {base})")
    results = parallel([lambda n=n, i=i: work(n, i, root, base, gh, board, run_claude)
                        for n, i in picks])
    for r in filter(None, results):
        say(f"  #{r['number']}: " + (f"PR {r['pr']}" if r["pr"] else f"no PR, branch {r['branch']} kept"))
    return results
