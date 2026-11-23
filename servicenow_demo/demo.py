"""Scripted incident scenario run through the workflow engine.

Produces a deterministic timeline used for the committed demo artifact.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .engine import WorkflowEngine
from .model import Priority, State

T0 = datetime(2026, 1, 12, 8, 0, 0)


def run_scenario() -> list[str]:
    engine = WorkflowEngine()
    lines: list[str] = []

    def log(delta: timedelta, actor: str, action: str, detail: str = "") -> None:
        stamp = f"T+{int(delta.total_seconds() // 3600):02d}:{int(delta.total_seconds() // 60) % 60:02d}"
        suffix = f"  {detail}" if detail else ""
        lines.append(f"{stamp}  {actor:<10} {action:<14}{suffix}")

    ticket = engine.open_ticket(
        "Centrifuge rotor vibration alarm on unit C-3",
        caller="lab-bot-3",
        priority=Priority.P2,
        now=T0,
    )
    log(timedelta(0), "system", "opened", f"{ticket.number} {ticket.sla_policy.name}")

    engine.assign(ticket, "Lab Systems", "jchen", now=T0 + timedelta(minutes=20))
    log(timedelta(minutes=20), "jchen", "assigned", "Lab Systems")

    engine.transition(ticket, State.IN_PROGRESS, "jchen", now=T0 + timedelta(minutes=25))
    log(timedelta(minutes=25), "jchen", "state", "new -> in_progress")

    # Poll SLA at intervals, the way a scheduler job would.
    for minutes in (30, 45, 60, 61, 70):
        now = T0 + timedelta(minutes=minutes)
        breaches = engine.check_sla(ticket, now)
        if breaches:
            log(now - T0, "system", "sla_breach", "; ".join(breaches))

    engine.record_first_response(ticket, "jchen", now=T0 + timedelta(minutes=70))
    log(timedelta(minutes=70), "jchen", "first_response", "acknowledged alarm")

    engine.transition(ticket, State.PENDING, "jchen", now=T0 + timedelta(minutes=240))
    log(timedelta(minutes=240), "jchen", "state", "in_progress -> pending (awaiting rotor kit)")

    engine.check_sla(ticket, T0 + timedelta(minutes=300))
    engine.transition(ticket, State.IN_PROGRESS, "jchen", now=T0 + timedelta(minutes=360))
    log(timedelta(minutes=360), "jchen", "state", "pending -> in_progress")

    engine.transition(ticket, State.RESOLVED, "jchen", now=T0 + timedelta(minutes=420))
    log(timedelta(minutes=420), "jchen", "state", "in_progress -> resolved")

    engine.transition(ticket, State.CLOSED, "jchen", now=T0 + timedelta(minutes=450))
    log(timedelta(minutes=450), "jchen", "state", "resolved -> closed")

    lines.append("")
    lines.append(f"final state   {ticket.state.value}")
    lines.append(f"escalated     {ticket.escalated}")
    lines.append(f"history size  {len(ticket.history)} events")
    return lines


def main() -> None:
    print("ServiceNow-concepts workflow demo (no ServiceNow instance required)")
    print()
    for line in run_scenario():
        print(line)


if __name__ == "__main__":
    main()
