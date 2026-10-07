"""The confirm card in the terminal. Nothing touches GitHub before a yes."""
YES = {"y", "yes", "haan", "ha", "han", "ok", "ship", "ship it"}
NO = {"n", "no", "nahi", "nope", "cancel"}
EDIT = {"e", "edit", "change"}


def card(p, dry_run=False):
    who = lambda i: f" → @{i['assignee']}" if i["assignee"] else " → unassigned"
    due = lambda i: f", due {i['deadline']}" if i["deadline"] else ""
    rows = [f"  + open   {i['title']}{who(i)} [{i['label']}{due(i)}]" for i in p["create"]]
    rows += [f"  = skip   #{n} {i['title']} (already open)" for i, n in p["duplicate"]]
    rows += [f"  ✓ close  #{n} {i['title']}" for i, n in p["close"]]
    if p["log"]:
        rows.append(f"  ✎ log    {len(p['log'])} done item(s) on the Shipit log issue")
    title = "Ship it? (dry run: commands are printed, not run)" if dry_run else "Ship it?"
    width = max([len(title) + 4] + [len(r) + 2 for r in rows])
    return "\n".join([f"┌─ {title} " + "─" * (width - len(title) - 3), *[f"│{r}" for r in rows],
                      "└─ [y]es · [e]dit · [n]o"])


def ask(read=input):
    while True:
        answer = read("> ").strip().lower().rstrip(".!")
        for choice, words in (("yes", YES), ("no", NO), ("edit", EDIT)):
            if answer in words:
                return choice
