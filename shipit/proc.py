"""Run subprocesses with UTF-8 in and out. Never raises for a missing program."""
import subprocess


def run(args, cwd=None, shell=False, input=None, timeout=60):
    """Return (exit_code, stdout, stderr)."""
    try:
        p = subprocess.run(args, cwd=cwd, shell=shell, input=input, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError:
        return 127, "", f"{args[0] if isinstance(args, list) else args}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    return p.returncode, p.stdout, p.stderr
