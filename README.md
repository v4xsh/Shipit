<!-- chart -->
![chart](chart.svg)

Time saved so far: 0.0 min
<!-- /chart -->

# Shipit

A project built by voice. Every prompt is logged in [voice-log.md](voice-log.md);
the chart above compares minutes spoken vs. minutes it would take to type (40 wpm).

## Setup

```sh
git config core.hooksPath hooks   # pre-commit regenerates the chart
python -m unittest                # run tests
```

Secrets go in `.env` (gitignored).
