"""Draft the done list from my commits since the last run."""
import re

from . import items, proc

PREFIX = re.compile(r"^\w+(\([^)]*\))?!?:\s*")
DOCS = re.compile(r"(^docs/|\.md$|\.rst$)", re.I)
FIX = re.compile(r"fix(e[sd])?\b", re.I)
INFRA = re.compile(r"(^\.github/|^hooks/|docker|\.ya?ml$|\.toml$|\.cfg$|\.ini$|^setup\.py$"
                   r"|requirements.*\.txt$|^\.gitignore$)", re.I)


def head(root):
    code, out, _ = proc.run(["git", "rev-parse", "HEAD"], cwd=root)
    return out.strip() if code == 0 else None


def commits(root, since_commit=None, author=None):
    """Return [(sha, subject, [files])], oldest first."""
    args = ["git", "log", "--no-merges", "--reverse", "--name-only", "--format=%x1e%H%x1f%s"]
    if author:
        args.append(f"--author={author}")
    known = since_commit and proc.run(["git", "cat-file", "-e", since_commit], cwd=root)[0] == 0
    args.append(f"{since_commit}..HEAD" if known else "--since=24.hours")
    code, out, _ = proc.run(args, cwd=root)
    if code:
        return []
    result = []
    for chunk in out.split("\x1e")[1:]:
        first, *files = chunk.strip("\n").split("\n")
        sha, subject = first.split("\x1f", 1)
        result.append((sha, subject, [f for f in files if f]))
    return result


def guess_label(subject, files):
    kind = subject.split(":")[0].split("(")[0].lower() if PREFIX.match(subject) else ""
    if kind in ("ci", "build") or (files and all(INFRA.search(f) for f in files)):
        return "infra"
    if kind in ("chore", "docs", "style") or (files and all(DOCS.search(f) for f in files)):
        return "chore"
    if kind == "fix" or FIX.match(subject):
        return "bug"
    return "feature" if kind == "feat" else "core"


def clean(subject):
    s = PREFIX.sub("", subject).strip()
    return s[:1].upper() + s[1:]


def drafts(root, me, since_commit=None, author=None):
    out = []
    for n, (sha, subject, files) in enumerate(commits(root, since_commit, author), 1):
        out.append(items.make(f"c{n}", "done", clean(subject), f"commit {sha[:7]}",
                              label=guess_label(subject, files), assignee=me))
    return out
