"""What's wrong with the network or a tool, in one plain sentence each."""
import shutil
import socket

OFFLINE = ("You're offline: parsing uses the simple keyword splitter, and GitHub steps become "
           "Markdown on your clipboard.")
CLAUDE = ("Claude Code isn't installed (npm install -g @anthropic-ai/claude-code), so no agents "
          "this time.")


def online(host="api.github.com", timeout=2):
    try:
        socket.create_connection((host, 443), timeout).close()
        return True
    except OSError:
        return False


def gh_problem(err=""):
    """A friendly reason for a gh failure, or None if it's something else."""
    e = (err or "").lower()
    if not shutil.which("gh") or "not recognized" in e or e.endswith("not found"):
        return "GitHub CLI (gh) isn't installed. Get it at https://cli.github.com"
    if "auth login" in e or "not logged" in e or "bad credentials" in e:
        return "gh isn't logged in. Run: gh auth login"
    if any(w in e for w in ("could not resolve", "error connecting", "timeout", "timed out",
                            "dial tcp", "no such host", "network is unreachable")):
        return "Can't reach GitHub (offline?)"
    return None


def claude_missing():
    return shutil.which("claude") is None
