"""After the board is ready: confirm, ship to GitHub, receipt, workload check."""
import datetime

from . import cards, clipboard, confirm, items, parser, receipt, ship, workload
from .console import say, warn
from .github import GhError


def read_open(gh):
    try:
        return gh.open_issues() or []
    except GhError as e:
        warn(f"Couldn't read open issues ({e}); treating every item as new.")
        return []


def agree(found, gh, crew, board, read=input, today=None, open_issues=None):
    """Loop on the confirm card until yes or no. Returns (items, plan) or (None, None)."""
    open_issues = read_open(gh) if open_issues is None else open_issues
    while True:
        p = ship.plan(found, open_issues)
        say("\n" + confirm.card(p, gh.dry))
        board.status("confirm")
        answer = confirm.ask(read)
        if answer == "yes":
            return found, p
        if answer == "no":
            board.status("cancelled")
            return None, None
        edit = read("Say the edit (Wispr Flow): ").strip()
        if not edit:
            continue
        board.status("parsing")
        changed, notes = parser.amend(found, edit, crew, today)
        for note in notes:
            warn(note)
        board.apply(items.diff(found, changed))
        found = changed
        say("\n" + cards.board(found))


def handover(p, board, today, why):
    """GitHub is out of reach: one friendly line, the issues as Markdown, and on the clipboard."""
    md = ship.markdown(p, today)
    copied = clipboard.copy(md)
    warn(f"{why} Here are the issues as Markdown" + (", also on your clipboard." if copied else "."))
    say(md)
    board.status("cancelled")


def deliver(p, gh, board, today, offline=False):
    """Run the plan. On a GitHub failure, hand over Markdown instead of dying."""
    if offline:
        handover(p, board, today, "Still offline, so nothing went to GitHub.")
        return None
    board.status("shipping")
    try:
        done = ship.execute(p, gh, today,
                            on_issue=lambda i, n: board.issue(i["id"], n, gh.url(n)))
    except GhError as e:
        handover(p, board, today, f"GitHub said no: {e}.")
        return None
    board.status("shipped")
    for i, n in done["opened"]:
        say(f"  + #{n} {i['title']}" + ("" if gh.dry else f"  {gh.url(n)}"))
    for i, n in done["closed"]:
        say(f"  ✓ closed #{n} {i['title']}")
    say(f"  ✎ logged on #{done['log_issue']} {ship.LOG_TITLE}")
    return done


def balance(gh, crew, board, ids=None, read=input, chat=None, opened=()):
    """Say who carries the most; let me move one issue by voice."""
    open_issues = read_open(gh)
    if gh.dry:  # nothing was created, so count what would have been
        open_issues += [{"number": n, "title": i["title"],
                         "assignees": [{"login": i["assignee"]}] if i["assignee"] else []}
                        for i, n in opened]
    counts = workload.counts(open_issues, crew)
    note = workload.message(counts)
    say("\n" + note)
    board.toast(note)
    if not workload.heavy(counts):
        return None
    said = read("Move one? Say it, or Enter to skip: ").strip()
    if not said:
        return None
    moved = workload.move(said, open_issues, crew, **({"chat": chat} if chat else {}))
    if not moved:
        warn("Couldn't tell which issue or who. Nothing moved.")
        return None
    issue, to = moved
    old = (issue.get("assignees") or [{}])[0].get("login")
    gh.reassign(issue["number"], to, old)
    say(f"  ↺ #{issue['number']} {issue['title']}: @{old or '?'} → @{to}")
    board.toast(f"#{issue['number']} {issue['title']} moved to @{to}")
    if issue["number"] in (ids or {}):
        board.apply([("change", {"id": ids[issue["number"]], "field": "assignee", "from": old,
                                 "to": to, "said": said})])
    return issue["number"], to


def finish(transcript, found, done, before, board):
    r = receipt.stats(transcript, found, done, before)
    say("\n" + receipt.text(r))
    board.receipt(r)
    return r


def today():
    return datetime.date.today().isoformat()
