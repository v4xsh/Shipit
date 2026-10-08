"""Load KEY=value lines from .env into os.environ (existing vars win)."""
import os
from pathlib import Path


def read(path):
    """Text of a .env written by anything: UTF-8, UTF-8 with BOM, or PowerShell's UTF-16."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def load(root):
    path = Path(root) / ".env"
    if not path.exists():
        return
    for line in read(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
