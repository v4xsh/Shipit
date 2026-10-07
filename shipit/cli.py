"""python -m shipit: team, git log, speech -> live board -> confirm -> GitHub."""
import argparse
import datetime
import sys
from pathlib import Path

from . import cards, env, flow, gitlog, live, parser, proc, replay, repo, state, team
from .console import Oops, say, setup, warn
from .github import Gh


def args(argv):
    p = argparse.ArgumentParser(prog="shipit", description="Say it. It's tracked. It's started.")
    p.add_argument("--text", help="the standup as text instead of dictating")
    p.add_argument("--from-notes", metavar="FILE", help="a meeting transcript file")
    p.add_argument("--replay", action="store_true", help="play the recorded demo standups")
    p.add_argument("--dry-run", action="store_true", help="print the gh commands, don't run them")
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


def hear(opts, root, slug, crew, before, board):
    """Steps 1-4: commits and speech become items on the board."""
    email = proc.run(["git", "config", "user.email"], cwd=root)[1].strip() or None
    drafts = gitlog.drafts(root, crew["me"], before["last_commit"], email)
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
    say("\n" + cards.board(result["items"]))
    return transcript, result["items"]


def run(opts, board):
    root = repo.root()
    env.load(root)
    slug = repo.origin(root)
    crew = team.load(root, slug)
    say(f"Shipit · {slug} · {len(crew['members'])} on the team")
    board.run(slug, crew)
    before = state.load(root)
    transcript, found = hear(opts, root, slug, crew, before, board)
    gh = Gh(slug, dry_run=opts.dry_run)
    found, plan = flow.agree(found, gh, crew, board)
    if found is None:
        say("Nothing touched GitHub.")
        return None
    done = flow.deliver(plan, gh, board, flow.today())
    if done is None:
        return None
    stats = flow.finish(transcript, found, done, before, board)
    if not gh.dry:  # state moves only after a real, successful run
        state.record(root, before, gitlog.head(root), stats, datetime.datetime.now().isoformat())
    ids = {n: i["id"] for i, n in done["opened"] + done["duplicates"]}
    flow.balance(gh, crew, board, ids)
    return done


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
