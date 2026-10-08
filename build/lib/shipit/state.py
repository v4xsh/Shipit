"""Per-repo run state in .shipit/state.json: last commit seen and running totals."""
import json
from pathlib import Path

DEFAULT = {"last_commit": None, "last_run": None, "runs": 0, "words": 0, "seconds_saved": 0}


def path(root):
    return Path(root) / ".shipit" / "state.json"


def load(root):
    p = path(root)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {**DEFAULT, **data}


def save(root, state):
    p = path(root)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def record(root, state, head, stats, now):
    """After a successful run: move the git cursor and add to the running totals."""
    state = {**state, "last_commit": head or state["last_commit"], "last_run": now,
             "runs": state["runs"] + 1, "words": state["words"] + stats["words"],
             "seconds_saved": state["seconds_saved"] + stats["saved_s"]}
    save(root, state)
    return state
