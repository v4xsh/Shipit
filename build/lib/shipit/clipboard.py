"""Copy text to the clipboard as UTF-8 (Windows first)."""
import sys
import tempfile
from pathlib import Path

from . import proc


def copy(text):
    """Return True if it worked. Never raises."""
    if sys.platform == "win32":
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
        cmd = f"Get-Content -Raw -Encoding UTF8 '{f.name}' | Set-Clipboard"
        ok = proc.run(["powershell", "-NoProfile", "-Command", cmd])[0] == 0
        Path(f.name).unlink(missing_ok=True)
        return ok
    for tool in (["pbcopy"], ["xclip", "-selection", "clipboard"]):
        if proc.run(tool, input=text)[0] == 0:
            return True
    return False
