"""Words spoken and time saved versus typing at 40 wpm."""
TYPING_WPM, SPEAKING_WPM = 40, 150


def stats(transcript, items):
    words = len(transcript.split())
    typed, spoken = words * 60 / TYPING_WPM, words * 60 / SPEAKING_WPM
    live = [i for i in items if not i["scratched"]]
    return {"words": words, "items": len(live),
            "assigned": sum(1 for i in live if i["assignee"]),
            "typed_s": round(typed), "spoken_s": round(spoken), "saved_s": round(typed - spoken)}
