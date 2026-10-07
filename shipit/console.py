"""UTF-8 console output and short, camera-friendly messages."""
import sys


class Oops(Exception):
    """A problem we explain in one friendly line instead of a traceback."""


def setup():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def say(msg):
    print(msg, flush=True)


def warn(msg):
    print(f"  ~ {msg}", file=sys.stderr, flush=True)
