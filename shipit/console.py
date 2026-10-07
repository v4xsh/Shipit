"""UTF-8 console output and short, camera-friendly messages."""
import sys


class Oops(Exception):
    """A problem we explain in one friendly line instead of a traceback."""


def setup():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")


def say(msg):
    setup()  # cheap, and a stray emoji can never crash a demo
    print(msg, flush=True)


def warn(msg):
    setup()
    print(f"  ~ {msg}", file=sys.stderr, flush=True)
