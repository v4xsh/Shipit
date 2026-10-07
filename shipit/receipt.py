"""Words spoken, what shipped, and time saved versus typing at 40 wpm."""
TYPING_WPM, SPEAKING_WPM = 40, 150


def stats(transcript, items, done=None, before=None):
    """`done` is ship.execute's result; `before` is the saved state for running totals."""
    words = len(transcript.split())
    typed, spoken = words * 60 / TYPING_WPM, words * 60 / SPEAKING_WPM
    live = [i for i in items if not i["scratched"]]
    done = done or {}
    before = before or {}
    return {"words": words, "items": len(live),
            "opened": len(done.get("opened", [])), "closed": len(done.get("closed", [])),
            "assigned": done.get("assigned", sum(1 for i in live if i["assignee"])),
            "typed_s": round(typed), "spoken_s": round(spoken), "saved_s": round(typed - spoken),
            "runs": before.get("runs", 0) + 1,
            "total_saved_s": before.get("seconds_saved", 0) + round(typed - spoken)}


def text(r):
    return (f"Receipt · {r['words']} words · ~{r['spoken_s']}s spoken vs {r['typed_s']}s typing · "
            f"{r['opened']} opened · {r['closed']} closed · {r['assigned']} assigned · "
            f"{r['saved_s']}s saved · {r['total_saved_s'] / 60:.1f} min saved over {r['runs']} runs")
