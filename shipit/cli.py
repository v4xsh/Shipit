"""python -m shipit: team, git log, speech -> items."""
import argparse
import sys
from pathlib import Path

from . import cards, env, gitlog, parser, proc, repo, state, team
from .console import Oops, say, setup, warn


def args(argv):
    p = argparse.ArgumentParser(prog="shipit", description="Say it. It's tagged. It started.")
    p.add_argument("--text", help="the standup as text instead of dictating")
    p.add_argument("--from-notes", metavar="FILE", help="a meeting transcript file")
    return p.parse_args(argv)


def listen(opts):
    if opts.text:
        return opts.text
    if opts.from_notes:
        try:
            return Path(opts.from_notes).read_text(encoding="utf-8")
        except OSError:
            raise Oops(f"Couldn't read {opts.from_notes}.")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    say("Speak your standup (Win+H to dictate). Empty line to finish:")
    lines = []
    while (line := input("> ").strip()):
        lines.append(line)
    return "\n".join(lines)


def run(opts):
    root = repo.root()
    env.load(root)
    slug = repo.origin(root)
    crew = team.load(root, slug)
    say(f"Shipit · {slug} · {len(crew['members'])} on the team")
    email = proc.run(["git", "config", "user.email"], cwd=root)[1].strip() or None
    drafts = gitlog.drafts(root, crew["me"], state.load(root)["last_commit"], email)
    say(f"{len(drafts)} done from your commits.")
    transcript = listen(opts).strip()
    if not transcript and not drafts:
        raise Oops("Nothing said and no new commits. Nothing to ship.")
    result = parser.parse(transcript, crew, drafts) if transcript else {
        "items": drafts, "source": "git", "notes": []}
    for note in result["notes"]:
        warn(note)
    say("\n" + cards.board(result["items"]))
    return result


def main(argv=None):
    setup()
    try:
        run(args(argv))
    except Oops as e:
        warn(str(e))
        return 1
    except KeyboardInterrupt:
        warn("Stopped.")
        return 130
    return 0
