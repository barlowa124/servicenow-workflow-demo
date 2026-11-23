from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class State(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


TERMINAL_STATES = frozenset({State.CLOSED, State.CANCELLED})


class Priority(str, Enum):
    P1 = "1"
    P2 = "2"
    P3 = "3"
    P4 = "4"


@dataclass(frozen=True)
class SLAPolicy:
    """Response and resolution targets in minutes from ticket open."""

    name: str
    response_minutes: int
    resolution_minutes: int


DEFAULT_POLICIES: dict[Priority, SLAPolicy] = {
    Priority.P1: SLAPolicy("P1 critical", response_minutes=15, resolution_minutes=240),
    Priority.P2: SLAPolicy("P2 high", response_minutes=60, resolution_minutes=480),
    Priority.P3: SLAPolicy("P3 moderate", response_minutes=240, resolution_minutes=2880),
    Priority.P4: SLAPolicy("P4 low", response_minutes=480, resolution_minutes=10080),
}


@dataclass(frozen=True)
class TicketEvent:
    actor: str
    action: str
    detail: str = ""
    at: Optional[datetime] = None


@dataclass
class Ticket:
    number: str
    short_description: str
    caller: str
    priority: Priority = Priority.P3
    state: State = State.NEW
    assignment_group: Optional[str] = None
    assignee: Optional[str] = None
    opened_at: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    escalated: bool = False
    history: list[TicketEvent] = field(default_factory=list)

    @property
    def sla_policy(self) -> SLAPolicy:
        return DEFAULT_POLICIES[self.priority]

    @property
    def response_due(self) -> Optional[datetime]:
        if self.opened_at is None:
            return None
        return self.opened_at + timedelta(minutes=self.sla_policy.response_minutes)

    @property
    def resolution_due(self) -> Optional[datetime]:
        if self.opened_at is None:
            return None
        return self.opened_at + timedelta(minutes=self.sla_policy.resolution_minutes)


class InvalidTransition(Exception):
    pass


class UnassignedTicket(Exception):
    pass
