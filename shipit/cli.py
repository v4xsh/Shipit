"""python -m shipit: team, git log, speech -> live board -> confirm -> GitHub."""
import argparse
import datetime
import sys
import traceback
from pathlib import Path

from . import (__version__, agent, cards, debug, env, flow, gitlog, groq, live, net, parser, proc, replay,
               repo, review, ship, state, team)
from .console import Oops, say, setup, warn
from .github import Gh, GhError
from .worktree import GitError


def args(argv):
    p = argparse.ArgumentParser(prog="shipit", description="Say it. It's tracked. It's started.")
    p.add_argument("--text", help="the standup as text instead of dictating")
    p.add_argument("--from-notes", metavar="FILE", help="a meeting transcript file")
    p.add_argument("--replay", action="store_true", help="play the recorded demo standups")
    p.add_argument("--dry-run", action="store_true", help="print the gh commands, don't run them")
    p.add_argument("--agent", type=int, metavar="N", default=0,
                   help="after shipping, Claude Code works your top N next issues")
    p.add_argument("--debug", action="store_true", help="ramble about a bug; agents test each hypothesis")
    p.add_argument("--review", type=int, metavar="PR", help="speak a review of a pull request")
    p.add_argument("--no-board", action="store_true", help="don't open the live board")
    p.add_argument("--port", type=int, default=7878, help="board port (default 7878)")
    p.add_argument("--version", action="version", version=f"shipit {__version__}")
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
    try:
        board = live.Board(opts.port)
    except OSError:
        warn("Couldn't start the board, so this run stays in the terminal.")
        return live.NoBoard()
    say(f"Live board: {board.url}")
    return board


def offline_chat(messages):
    raise groq.GroqError("Offline")


def hear(opts, root, crew, before, board, open_titles=(), offline=False):
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
    chat = offline_chat if offline else groq.chat
    result = ({"items": drafts, "source": "git", "notes": []} if not transcript
              else parser.parse(transcript, crew, drafts, chat=chat, open_titles=open_titles))
    for note in [] if offline else result["notes"]:  # offline was already said, once
        warn(note)
    board.items(result["items"])
    board.status("ready")
    say("\n" + cards.board(result["items"]))
    return transcript, result["items"]


def start(opts, board, mode="standup"):
    root = repo.root()
    env.load(root)
    slug = repo.origin(root)
    offline = not net.online()
    if offline:
        warn(net.OFFLINE)
    crew = team.load(root, slug, offline=offline)
    say(f"Shipit · {slug} · {len(crew['members'])} on the team")
    board.run(slug, crew, mode=mode)
    return root, crew, Gh(slug, dry_run=opts.dry_run), offline


def online_only(offline, what):
    if offline:
        raise Oops(f"{what} needs the internet (Groq, GitHub, Claude). For an offline demo: shipit --replay")


def spoken(opts, board, prompt):
    say(prompt)
    board.status("listening")
    text = listen(opts).strip()
    if not text:
        raise Oops("Nothing said.")
    board.transcript(text)
    return text


def run_debug(opts, board):
    root, crew, gh, offline = start(opts, board, mode="debug")
    online_only(offline, "--debug")
    ramble = spoken(opts, board, "Ramble about the bug: what you saw, what you suspect.")
    debug.run(ramble, root, gh, board)


def run_review(opts, board):
    root, crew, gh, offline = start(opts, board, mode="review")
    online_only(offline, "--review")
    pr = gh.pr(opts.review)
    say(f"PR #{pr['number']} {pr['title']}  {pr['url']}")
    said = spoken(opts, board, "Speak your review:")
    review.run(opts.review, said, root, gh, board)


def run(opts, board):
    root, crew, gh, offline = start(opts, board)
    before = state.load(root)
    open_issues = [] if offline else flow.read_open(gh)
    titles = [i["title"] for i in open_issues if i["title"] != ship.LOG_TITLE]
    transcript, found = hear(opts, root, crew, before, board, titles, offline)
    found, plan = flow.agree(found, gh, crew, board, open_issues=open_issues)
    if found is None:
        say("Nothing touched GitHub.")
        return None
    done = flow.deliver(plan, gh, board, flow.today(), offline=offline)
    if done is None:
        return None
    stats = flow.finish(transcript, found, done, before, board)
    if not gh.dry:  # state moves only after a real, successful run
        state.record(root, before, gitlog.head(root), stats, datetime.datetime.now().isoformat())
    ids = {n: i["id"] for i, n in done["opened"] + done["duplicates"]}
    flow.balance(gh, crew, board, ids, opened=done["opened"])
    if opts.agent:
        agent.run_all(agent.pick(done, found, crew["me"], opts.agent), root, gh, board)
    return done


def main(argv=None):
    setup()
    opts = args(argv)
    try:
        board = open_board(opts)
        if opts.replay:
            replay.run(board)
        elif opts.debug:
            run_debug(opts, board)
        elif opts.review:
            run_review(opts, board)
        else:
            run(opts, board)
        if board.url and sys.stdin.isatty():
            input(f"\nBoard is live at {board.url}  Press Enter to finish. ")
    except GhError as e:
        warn(f"GitHub said no: {e}")
        return 1
    except Oops as e:
        warn(str(e))
        return 1
    except GitError as e:
        warn(f"Git said no: {e}")
        return 1
    except (KeyboardInterrupt, EOFError):
        warn("Stopped.")
        return 130
    except Exception as e:  # never a traceback on camera
        warn(f"Something unexpected broke ({e.__class__.__name__}: {e}). Details: {crash_log()}")
        return 1
    return 0


def crash_log():
    """Write the traceback to .shipit/crash.log for later, and say where."""
    path = Path(".shipit") / "crash.log"
    try:
        path.parent.mkdir(exist_ok=True)
        path.write_text(traceback.format_exc(), encoding="utf-8")
        return str(path)
    except OSError:
        return "(couldn't write .shipit/crash.log)"


def entry():
    """The `shipit` console script (pip install)."""
    sys.exit(main())
