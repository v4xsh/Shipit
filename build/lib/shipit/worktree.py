"""One git worktree per agent, under .shipit/worktrees, so parallel agents never collide."""
import shutil
from pathlib import Path

from . import proc


class GitError(Exception):
    pass


def git(cwd, *args):
    code, out, err = proc.run(["git", *args], cwd=cwd, timeout=300)
    if code:
        lines = (err or out).strip().splitlines()
        raise GitError(lines[-1] if lines else f"git {args[0]} failed")
    return out.strip()


def exists(root, branch):
    return proc.run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=root)[0] == 0


def add(root, branch, base="HEAD"):
    """A fresh worktree on `branch` (created from `base`, or reused if it already exists)."""
    path = Path(root) / ".shipit" / "worktrees" / branch.replace("/", "-")
    if path.exists():
        remove(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if exists(root, branch):
        git(root, "worktree", "add", str(path), branch)
    else:
        git(root, "worktree", "add", "-b", branch, str(path), base)
    return path


def remove(root, path):
    proc.run(["git", "worktree", "remove", "--force", str(path)], cwd=root)
    shutil.rmtree(path, ignore_errors=True)
    proc.run(["git", "worktree", "prune"], cwd=root)


def ahead(path, base):
    return int(git(path, "rev-list", "--count", f"{base}..HEAD") or 0)


def diffstat(path, base):
    return git(path, "diff", "--stat", f"{base}..HEAD")


def current_branch(root):
    return git(root, "rev-parse", "--abbrev-ref", "HEAD")
