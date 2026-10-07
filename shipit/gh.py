"""Thin wrappers over the gh CLI. Each returns None on failure instead of raising."""
import json

from . import proc


def api(path):
    code, out, _ = proc.run(["gh", "api", path])
    if code:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def authed():
    return proc.run(["gh", "auth", "status"])[0] == 0


def me():
    user = api("user")
    return user and user.get("login")


def collaborators(slug):
    return api(f"repos/{slug}/collaborators?per_page=100")


def user(login):
    return api(f"users/{login}") or {}
