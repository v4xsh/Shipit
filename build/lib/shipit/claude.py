"""Run `claude -p` headless and stream what it does, one short line per step.

Windows: shell=True lets cmd.exe find claude.cmd (npm) or claude.exe (native installer).
The prompt goes in on stdin, since cmd.exe mangles multi-line arguments.
"""
import json
import subprocess
import sys

TOOLS = ["Read", "Edit", "Write", "Glob", "Grep", "Bash(python:*)", "Bash(py:*)", "Bash(pytest:*)",
         "Bash(npm test:*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)",
         "Bash(git diff:*)", "Bash(git log:*)", "Bash(git checkout:*)", "Bash(git stash:*)"]


def command():
    return ["claude", "-p", "--output-format", "stream-json", "--verbose",
            "--permission-mode", "acceptEdits", "--allowedTools", *TOOLS]


def spawn(args, cwd):
    windows = sys.platform == "win32"
    return subprocess.Popen(subprocess.list2cmdline(args) if windows else args, cwd=cwd,
                            shell=windows, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")


def describe(event):
    """Terminal lines for one stream-json event."""
    kind = event.get("type")
    if kind == "assistant":
        out = []
        for part in event.get("message", {}).get("content", []):
            if part.get("type") == "text" and part.get("text", "").strip():
                out.append(part["text"].strip().splitlines()[0][:110])
            elif part.get("type") == "tool_use":
                args = part.get("input", {})
                what = args.get("command") or args.get("file_path") or args.get("pattern") or ""
                out.append(f"→ {part.get('name')} {str(what).splitlines()[0][:90] if what else ''}".rstrip())
        return out
    if kind == "result":
        return [f"{'✗ stopped' if event.get('is_error') else '✓ finished'} after "
                f"{event.get('num_turns', '?')} turns"]
    return []


def run(prompt, cwd, on_line=print, spawn=spawn):
    """Returns {"ok", "result", "code"}. Never raises for a missing or crashing claude."""
    try:
        p = spawn(command(), cwd)
        p.stdin.write(prompt)
        p.stdin.close()
    except OSError as e:
        return {"ok": False, "result": f"couldn't start claude ({e})", "code": 127}
    final = None
    for raw in p.stdout:
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except ValueError:
            on_line(raw[:110])  # e.g. "'claude' is not recognized..."
            continue
        for line in describe(event):
            on_line(line)
        if event.get("type") == "result":
            final = event
    code = p.wait()
    ok = code == 0 and final is not None and not final.get("is_error")
    return {"ok": ok, "result": (final or {}).get("result", "") or "", "code": code}
