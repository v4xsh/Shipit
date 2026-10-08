"""Thin wrappers over the gh CLI. Each returns None on failure instead of raising."""
import json

from . import net, proc


def api(path):
    code, out, _ = proc.run(["gh", "api", path])
    if code:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


LAST = {"err": ""}


def authed():
    code, _, err = proc.run(["gh", "auth", "status"])
    LAST["err"] = err
    return code == 0


def why():
    """Why the last authed() failed, in one plain sentence."""
    return net.gh_problem(LAST["err"]) or "gh isn't logged in. Run: gh auth login"


def me():
    user = api("user")
    return user and user.get("login")


def collaborators(slug):
    return api(f"repos/{slug}/collaborators?per_page=100")


def user(login):
    return api(f"users/{login}") or {}
