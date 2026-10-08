"""Find and run a repo's tests, so an agent's work is verified, not trusted."""
import json
import os
from pathlib import Path

from . import proc


def test_command(path):
    if os.environ.get("SHIPIT_TEST_CMD"):
        return os.environ["SHIPIT_TEST_CMD"]
    path = Path(path)
    if (path / "tests").is_dir() or any(path.glob("test_*.py")):
        return "python -m unittest"
    pkg = path / "package.json"
    if pkg.exists() and json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {}).get("test"):
        return "npm test"
    return None


def run_tests(path):
    """(passed, last lines of output). No test command counts as passed."""
    cmd = test_command(path)
    if not cmd:
        return True, "no tests found"
    code, out, err = proc.run(cmd, cwd=str(path), shell=True, timeout=900)
    tail = "\n".join((out + err).strip().splitlines()[-6:])
    return code == 0, tail
