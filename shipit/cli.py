"""python -m shipit: team, git log, speech -> items on a live board."""
import argparse
import sys
from pathlib import Path

from . import cards, env, gitlog, live, parser, proc, receipt, replay, repo, state, team
from .console import Oops, say, setup, warn


def args(argv):
    p = argparse.ArgumentParser(prog="shipit", description="Say it. It's tracked. It's started.")
    p.add_argument("--text", help="the standup as text instead of dictating")
    p.add_argument("--from-notes", metavar="FILE", help="a meeting transcript file")
    p.add_argument("--replay", action="store_true", help="play the recorded demo standups")
    p.add_argument("--no-board", action="store_true", help="don't open the live board")
    p.add_argument("--port", type=int, default=7878, help="board port (default 7878)")
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
    say("Dictate your standup with Wispr Flow. Empty line to finish:")
    lines = []
    while (line := input("> ").strip()):
        lines.append(line)
    return "\n".join(lines)


def open_board(opts):
    if opts.no_board:
        return live.NoBoard()
    board = live.Board(opts.port)
    say(f"Live board: {board.url}")
    return board


def run(opts, board):
    root = repo.root()
    env.load(root)
    slug = repo.origin(root)
    crew = team.load(root, slug)
    say(f"Shipit · {slug} · {len(crew['members'])} on the team")
    board.run(slug, crew)
    email = proc.run(["git", "config", "user.email"], cwd=root)[1].strip() or None
    drafts = gitlog.drafts(root, crew["me"], state.load(root)["last_commit"], email)
    say(f"{len(drafts)} done from your commits.")
    board.status("listening")
    board.items(drafts)
    transcript = listen(opts).strip()
    if not transcript and not drafts:
        raise Oops("Nothing said and no new commits. Nothing to ship.")
    board.transcript(transcript)
    board.status("parsing")
    result = parser.parse(transcript, crew, drafts) if transcript else {
        "items": drafts, "source": "git", "notes": []}
    for note in result["notes"]:
        warn(note)
    board.items(result["items"])
    board.status("ready")
    board.receipt(receipt.stats(transcript, result["items"]))
    say("\n" + cards.board(result["items"]))
    return result


def main(argv=None):
    setup()
    opts = args(argv)
    try:
        board = open_board(opts)
        replay.run(board) if opts.replay else run(opts, board)
        if board.url and sys.stdin.isatty():
            input(f"\nBoard is live at {board.url}  Press Enter to finish. ")
    except Oops as e:
        warn(str(e))
        return 1
    except (KeyboardInterrupt, EOFError):
        warn("Stopped.")
        return 130
    return 0
