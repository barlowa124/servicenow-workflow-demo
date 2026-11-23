from __future__ import annotations

from datetime import datetime
from typing import Optional

from .model import (
    InvalidTransition,
    Priority,
    State,
    TERMINAL_STATES,
    Ticket,
    TicketEvent,
    UnassignedTicket,
)

ALLOWED_TRANSITIONS: dict[State, frozenset[State]] = {
    State.NEW: frozenset({State.IN_PROGRESS, State.CANCELLED}),
    State.IN_PROGRESS: frozenset({State.PENDING, State.RESOLVED, State.CANCELLED}),
    State.PENDING: frozenset({State.IN_PROGRESS, State.RESOLVED, State.CANCELLED}),
    State.RESOLVED: frozenset({State.CLOSED, State.IN_PROGRESS}),
    State.CLOSED: frozenset(),
    State.CANCELLED: frozenset(),
}


class WorkflowEngine:
    """Applies ticket lifecycle rules and records every change in history."""

    def __init__(self, counter_start: int = 1000) -> None:
        self._counter = counter_start

    def open_ticket(
        self,
        short_description: str,
        caller: str,
        priority: Priority = Priority.P3,
        now: Optional[datetime] = None,
    ) -> Ticket:
        self._counter += 1
        ticket = Ticket(
            number=f"INC{self._counter:07d}",
            short_description=short_description,
            caller=caller,
            priority=priority,
            opened_at=now,
        )
        self._log(ticket, now, "system", "opened", f"priority {priority.name}")
        return ticket

    def assign(
        self,
        ticket: Ticket,
        group: str,
        agent: str,
        now: Optional[datetime] = None,
    ) -> Ticket:
        ticket.assignment_group = group
        ticket.assignee = agent
        self._log(ticket, now, agent, "assigned", f"to {group} / {agent}")
        return ticket

    def transition(
        self,
        ticket: Ticket,
        target: State,
        actor: str,
        now: Optional[datetime] = None,
    ) -> Ticket:
        if target not in ALLOWED_TRANSITIONS[ticket.state]:
            raise InvalidTransition(
                f"{ticket.number}: {ticket.state.value} -> {target.value} is not allowed"
            )
        if target == State.RESOLVED and ticket.assignee is None:
            raise UnassignedTicket(f"{ticket.number}: cannot resolve an unassigned ticket")
        previous = ticket.state
        ticket.state = target
        if target == State.RESOLVED:
            ticket.resolved_at = now
        elif target == State.CLOSED:
            ticket.closed_at = now
        elif target == State.IN_PROGRESS and previous == State.RESOLVED:
            ticket.resolved_at = None
        self._log(ticket, now, actor, "state", f"{previous.value} -> {target.value}")
        return ticket

    def record_first_response(self, ticket: Ticket, actor: str, now: datetime) -> Ticket:
        if ticket.first_response_at is None:
            ticket.first_response_at = now
            self._log(ticket, now, actor, "first_response", "")
        return ticket

    def escalate(self, ticket: Ticket, now: datetime, reason: str) -> Ticket:
        if ticket.escalated or ticket.state in TERMINAL_STATES:
            return ticket
        ticket.escalated = True
        self._log(ticket, now, "system", "escalated", reason)
        return ticket

    def check_sla(self, ticket: Ticket, now: datetime) -> list[str]:
        """Returns breach descriptions; auto-escalates on first breach."""
        breaches: list[str] = []
        if ticket.response_due and ticket.first_response_at is None and now > ticket.response_due:
            breaches.append(f"response SLA breached (due {ticket.response_due.isoformat()})")
        if (
            ticket.resolution_due
            and ticket.resolved_at is None
            and ticket.state not in TERMINAL_STATES
            and now > ticket.resolution_due
        ):
            breaches.append(f"resolution SLA breached (due {ticket.resolution_due.isoformat()})")
        if breaches and not ticket.escalated:
            self.escalate(ticket, now, "; ".join(breaches))
        return breaches

    @staticmethod
    def _log(
        ticket: Ticket,
        at: Optional[datetime],
        actor: str,
        action: str,
        detail: str,
    ) -> None:
        ticket.history.append(TicketEvent(actor=actor, action=action, detail=detail, at=at))
