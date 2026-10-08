"""Find the git repo root and the owner/name of its origin remote."""
import re

from . import proc
from .console import Oops

REMOTE = re.compile(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$")


def root(cwd=None):
    code, out, _ = proc.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if code == 127:
        raise Oops("Git isn't installed. Get it at https://git-scm.com")
    if code:
        raise Oops("Not inside a Git repo. cd into one and try again.")
    return out.strip()


def parse_remote(url):
    m = REMOTE.search(url.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


def origin(cwd):
    code, out, _ = proc.run(["git", "remote", "get-url", "origin"], cwd=cwd)
    slug = parse_remote(out) if code == 0 else None
    if not slug:
        raise Oops("No GitHub 'origin' remote. Add one with: git remote add origin <url>")
    return slug
