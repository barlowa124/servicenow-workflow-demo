from datetime import datetime, timedelta

import pytest

from servicenow_demo.engine import WorkflowEngine
from servicenow_demo.model import (
    InvalidTransition,
    Priority,
    State,
    UnassignedTicket,
)

T0 = datetime(2026, 1, 12, 8, 0, 0)


@pytest.fixture
def engine() -> WorkflowEngine:
    return WorkflowEngine()


@pytest.fixture
def ticket(engine: WorkflowEngine):
    t = engine.open_ticket("test ticket", "caller-1", Priority.P3, now=T0)
    engine.assign(t, "Service Desk", "agent-1", now=T0)
    return t


def test_open_ticket_starts_in_new(engine: WorkflowEngine) -> None:
    t = engine.open_ticket("x", "c", now=T0)
    assert t.state == State.NEW
    assert t.number.startswith("INC")
    assert t.opened_at == T0


def test_ticket_numbers_increment(engine: WorkflowEngine) -> None:
    a = engine.open_ticket("a", "c", now=T0)
    b = engine.open_ticket("b", "c", now=T0)
    assert int(b.number[3:]) == int(a.number[3:]) + 1


def test_full_happy_path(engine: WorkflowEngine, ticket) -> None:
    engine.transition(ticket, State.IN_PROGRESS, "agent-1", now=T0)
    engine.transition(ticket, State.PENDING, "agent-1", now=T0)
    engine.transition(ticket, State.IN_PROGRESS, "agent-1", now=T0)
    engine.transition(ticket, State.RESOLVED, "agent-1", now=T0)
    engine.transition(ticket, State.CLOSED, "agent-1", now=T0)
    assert ticket.state == State.CLOSED
    assert ticket.closed_at == T0


def test_cannot_skip_states(engine: WorkflowEngine, ticket) -> None:
    with pytest.raises(InvalidTransition):
        engine.transition(ticket, State.RESOLVED, "agent-1", now=T0)


def test_cannot_resolve_unassigned(engine: WorkflowEngine) -> None:
    t = engine.open_ticket("x", "c", now=T0)
    engine.transition(t, State.IN_PROGRESS, "system", now=T0)
    with pytest.raises(UnassignedTicket):
        engine.transition(t, State.RESOLVED, "system", now=T0)


def test_reopen_from_resolved_clears_resolved_at(engine: WorkflowEngine, ticket) -> None:
    engine.transition(ticket, State.IN_PROGRESS, "a", now=T0)
    engine.transition(ticket, State.RESOLVED, "a", now=T0 + timedelta(hours=1))
    engine.transition(ticket, State.IN_PROGRESS, "a", now=T0 + timedelta(hours=2))
    assert ticket.resolved_at is None


def test_closed_is_terminal(engine: WorkflowEngine, ticket) -> None:
    engine.transition(ticket, State.IN_PROGRESS, "a", now=T0)
    engine.transition(ticket, State.RESOLVED, "a", now=T0)
    engine.transition(ticket, State.CLOSED, "a", now=T0)
    with pytest.raises(InvalidTransition):
        engine.transition(ticket, State.IN_PROGRESS, "a", now=T0)


def test_history_records_every_action(engine: WorkflowEngine, ticket) -> None:
    engine.transition(ticket, State.IN_PROGRESS, "agent-1", now=T0)
    actions = [e.action for e in ticket.history]
    assert actions == ["opened", "assigned", "state"]


def test_response_sla_breach_escalates_once(engine: WorkflowEngine, ticket) -> None:
    # P3 response SLA is 240 minutes.
    due = T0 + timedelta(minutes=241)
    breaches = engine.check_sla(ticket, due)
    assert len(breaches) == 1
    assert ticket.escalated is True
    # Later checks keep reporting the breach but never re-escalate.
    engine.check_sla(ticket, due + timedelta(hours=1))
    escalations = [e for e in ticket.history if e.action == "escalated"]
    assert len(escalations) == 1
