# servicenow-workflow-demo

A ServiceNow-concepts implementation. It simulates the ServiceNow incident
lifecycle, including state transitions and SLA response & resolution
timers. Assignment routing is modeled as well. All timestamps are passed
explicitly, so every run is deterministic.

This is a standalone portfolio project. It is not affiliated with any
employer.

## What it models

- Ticket states `new`, `in_progress`, `pending`, `resolved`, `closed`, and
  `cancelled`, with a guarded transition table. Illegal jumps raise
  `InvalidTransition`, and resolving an unassigned ticket raises
  `UnassignedTicket`.
- Per-priority SLA policies giving response and resolution targets in
  minutes. `check_sla` reports breaches and escalates a ticket once.
- An append-only history on each ticket records every action the engine
  takes.
- `demo.py` runs a scripted P2 incident where the response SLA is missed and
  the ticket escalates before being resolved inside the resolution window.

## Requirements

- Python 3.11 or later
- pytest for the test suite

## Run

```bash
python -m servicenow_demo.demo
```

A captured run is in `results/demo-run.txt`.

## Test

```bash
python -m pytest tests/ -q
```

Nine tests run against the engine. Lifecycle coverage includes numbering and
the happy path. Guard coverage includes rejected transitions and terminal
states. SLA coverage includes breach detection and single-fire escalation.
