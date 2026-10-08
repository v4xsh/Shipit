"""Thread-safe event log the board streams from. Late browsers get the whole run."""
import threading


class Hub:
    def __init__(self):
        self.events, self.generation = [], 0
        self.cond = threading.Condition()

    def publish(self, kind, data=None):
        with self.cond:
            self.events.append((kind, data))
            self.cond.notify_all()

    def reset(self):
        """Start a fresh run: clients clear the board and replay from here."""
        with self.cond:
            self.events, self.generation = [("reset", None)], self.generation + 1
            self.cond.notify_all()

    def wait(self, seen, generation, timeout=15):
        """Block until there are events past `seen`; returns (events, seen, generation)."""
        with self.cond:
            self.cond.wait_for(lambda: self.generation != generation or len(self.events) > seen,
                               timeout)
            if self.generation != generation:
                seen = 0
            return self.events[seen:], len(self.events), self.generation
