"""Phase 4 — LangGraph Agentic State Machine for the follow-up loop.

State machine nodes:
  idle           → Letter has been drafted but not yet sent.
  letter_sent    → Round 1 letter was sent; waiting for insurer response.
  response_check → Check if the response deadline has passed.
  draft_round2   → Insurer responded; draft Round 2 letter.
  escalate       → Deadline exceeded or Round 2 rejected; draft escalation packet.
  resolved       → Case closed (won / partial / lost).

The graph is persisted as JSON in the database (follow_up_states.graph_state_json)
and can be resumed after restarts — this is the durability improvement over
Phase 1's `threading.Timer`.

Usage:
    from pipeline.follow_up_agent import FollowUpAgent

    agent = FollowUpAgent(case_id="...")
    state = agent.load_state(raw_json_from_db)
    new_state = await agent.advance(state, event="letter_sent", payload={...})
    db.save(new_state.to_json())
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State definitions
# ---------------------------------------------------------------------------


class FollowUpAgentState(str, Enum):
    IDLE = "idle"
    LETTER_SENT = "letter_sent"
    RESPONSE_CHECK = "response_check"
    DRAFT_ROUND2 = "draft_round2"
    DRAFT_ESCALATION = "draft_escalation"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class FollowUpEvent(str, Enum):
    LETTER_SENT = "letter_sent"
    RESPONSE_RECEIVED = "response_received"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    ROUND2_SENT = "round2_sent"
    CASE_RESOLVED = "case_resolved"
    MANUAL_ESCALATE = "manual_escalate"


# The full state graph payload stored in Postgres as JSON
class GraphStatePayload(TypedDict, total=False):
    agent_state: str
    case_id: str
    round: int

    # Round 1
    round_1_sent_at: str | None
    round_1_response_deadline: str | None
    round_1_response_received_at: str | None
    round_1_response_excerpt: str | None
    round_1_version_id: str | None

    # Round 2
    round_2_sent_at: str | None
    round_2_response_deadline: str | None
    round_2_response_received_at: str | None
    round_2_version_id: str | None

    # Escalation
    escalation_triggered_at: str | None
    escalation_version_id: str | None
    escalation_reason: str | None

    # Resolution
    resolution_outcome: str | None   # "won" | "partial" | "lost"
    resolution_notes: str | None
    resolved_at: str | None

    # Metadata / audit trail
    events: list[dict]


# ---------------------------------------------------------------------------
# State transition table
# ---------------------------------------------------------------------------

# (current_state, event) → next_state
# Use .value strings so comparisons work regardless of whether enum or string is passed
_TRANSITIONS: dict[tuple[str, str], str] = {
    (FollowUpAgentState.IDLE.value, FollowUpEvent.LETTER_SENT.value): FollowUpAgentState.LETTER_SENT.value,
    (FollowUpAgentState.LETTER_SENT.value, FollowUpEvent.RESPONSE_RECEIVED.value): FollowUpAgentState.DRAFT_ROUND2.value,
    (FollowUpAgentState.LETTER_SENT.value, FollowUpEvent.DEADLINE_EXCEEDED.value): FollowUpAgentState.DRAFT_ESCALATION.value,
    (FollowUpAgentState.LETTER_SENT.value, FollowUpEvent.MANUAL_ESCALATE.value): FollowUpAgentState.DRAFT_ESCALATION.value,
    (FollowUpAgentState.DRAFT_ROUND2.value, FollowUpEvent.ROUND2_SENT.value): FollowUpAgentState.LETTER_SENT.value,
    (FollowUpAgentState.DRAFT_ROUND2.value, FollowUpEvent.CASE_RESOLVED.value): FollowUpAgentState.RESOLVED.value,
    (FollowUpAgentState.DRAFT_ESCALATION.value, FollowUpEvent.CASE_RESOLVED.value): FollowUpAgentState.RESOLVED.value,
    (FollowUpAgentState.ESCALATED.value, FollowUpEvent.CASE_RESOLVED.value): FollowUpAgentState.RESOLVED.value,
    (FollowUpAgentState.LETTER_SENT.value, FollowUpEvent.CASE_RESOLVED.value): FollowUpAgentState.RESOLVED.value,
    (FollowUpAgentState.RESPONSE_CHECK.value, FollowUpEvent.CASE_RESOLVED.value): FollowUpAgentState.RESOLVED.value,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Core agent class
# ---------------------------------------------------------------------------


class FollowUpAgent:
    """Durable follow-up loop state machine.

    This class is stateless — all state is passed in and returned as a dict
    that should be persisted to the database between calls.
    """

    DEFAULT_RESPONSE_DEADLINE_DAYS = 30
    ROUND2_RESPONSE_DEADLINE_DAYS = 30

    def __init__(self, case_id: str):
        self.case_id = case_id

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def initial_state(self) -> GraphStatePayload:
        """Return the initial empty state for a new follow-up record."""
        return GraphStatePayload(
            agent_state=FollowUpAgentState.IDLE.value,
            case_id=self.case_id,
            round=0,
            events=[],
        )

    def load_state(self, raw: dict | None) -> GraphStatePayload:
        """Load state from a JSON dict (from DB). Returns initial if None."""
        if not raw:
            return self.initial_state()
        state = GraphStatePayload(**raw)
        if "events" not in state:
            state["events"] = []
        return state

    def advance(
        self,
        state: GraphStatePayload,
        event: str | FollowUpEvent,
        payload: dict[str, Any] | None = None,
    ) -> GraphStatePayload:
        """Apply an event to the current state and return the new state.

        This is the main transition function — it:
        1. Validates the transition is allowed
        2. Applies side-effects to the state payload
        3. Appends an audit event
        4. Returns the mutated state
        """
        current = state.get("agent_state", FollowUpAgentState.IDLE)
        # Normalize: ensure both sides are plain string values for comparison
        current_val = current.value if isinstance(current, FollowUpAgentState) else str(current)
        event_val = event.value if isinstance(event, FollowUpEvent) else str(event)
        key = (current_val, event_val)

        next_state = _TRANSITIONS.get(key)
        if not next_state:
            logger.warning(
                "No transition defined for (%s, %s) — staying in %s",
                current_val,
                event_val,
                current_val,
            )
            return state

        state["agent_state"] = next_state.value if isinstance(next_state, FollowUpAgentState) else str(next_state)
        payload = payload or {}

        # Apply state-specific side effects
        self._apply_effects(state, event=event_val, next_state=next_state, payload=payload)

        # Record audit event
        state.setdefault("events", []).append(
            {
                "from_state": current_val,
                "event": event_val,
                "to_state": next_state,
                "occurred_at": _iso_now(),
                "payload": payload,
            }
        )

        return state

    def check_deadline(self, state: GraphStatePayload) -> str | None:
        """Return 'deadline_exceeded' if the response window has passed, else None.

        Call this on a periodic scheduler (e.g., APScheduler, Celery beat).
        """
        if state.get("agent_state") != FollowUpAgentState.LETTER_SENT:
            return None

        deadline_str = state.get("round_1_response_deadline")
        if not deadline_str:
            return None

        try:
            from dateutil import parser
            deadline = parser.parse(deadline_str)
        except Exception:
            return None

        now = datetime.now(timezone.utc)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        if now > deadline and not state.get("round_1_response_received_at"):
            return FollowUpEvent.DEADLINE_EXCEEDED

        return None

    def build_round2_context(self, state: GraphStatePayload) -> dict:
        """Build context dict needed to generate a Round 2 letter."""
        return {
            "round": state.get("round", 1) + 1,
            "insurer_response_text": state.get("round_1_response_excerpt", ""),
            "original_sent_at": state.get("round_1_sent_at"),
            "response_received_at": state.get("round_1_response_received_at"),
        }

    def build_escalation_context(self, state: GraphStatePayload) -> dict:
        """Build context dict for generating an escalation letter."""
        return {
            "round": state.get("round", 1),
            "reason": state.get("escalation_reason", "response_deadline_exceeded"),
            "original_sent_at": state.get("round_1_sent_at"),
            "deadline": state.get("round_1_response_deadline"),
            "escalation_triggered_at": state.get("escalation_triggered_at"),
        }

    # -----------------------------------------------------------------------
    # Internal side-effect handlers
    # -----------------------------------------------------------------------

    def _apply_effects(
        self,
        state: GraphStatePayload,
        event: str,
        next_state: str,
        payload: dict,
    ) -> None:
        """Mutate state payload based on the transition."""
        now = _iso_now()

        if event == FollowUpEvent.LETTER_SENT.value or event == FollowUpEvent.LETTER_SENT:
            state["round"] = state.get("round", 0) + 1
            state["round_1_sent_at"] = payload.get("sent_at", now)
            state["round_1_version_id"] = payload.get("version_id")
            deadline_days = payload.get(
                "response_deadline_days", self.DEFAULT_RESPONSE_DEADLINE_DAYS
            )
            deadline_dt = datetime.now(timezone.utc) + timedelta(days=deadline_days)
            state["round_1_response_deadline"] = deadline_dt.isoformat()

        elif event == FollowUpEvent.RESPONSE_RECEIVED.value or event == FollowUpEvent.RESPONSE_RECEIVED:
            state["round_1_response_received_at"] = payload.get("received_at", now)
            state["round_1_response_excerpt"] = payload.get("response_excerpt", "")[:2000]

        elif event == FollowUpEvent.DEADLINE_EXCEEDED.value or event == FollowUpEvent.DEADLINE_EXCEEDED:
            state["escalation_triggered_at"] = now
            state["escalation_reason"] = "response_deadline_exceeded"

        elif event == FollowUpEvent.MANUAL_ESCALATE.value or event == FollowUpEvent.MANUAL_ESCALATE:
            state["escalation_triggered_at"] = now
            state["escalation_reason"] = payload.get("reason", "manual_escalation")

        elif event == FollowUpEvent.ROUND2_SENT.value or event == FollowUpEvent.ROUND2_SENT:
            state["round_2_sent_at"] = payload.get("sent_at", now)
            state["round_2_version_id"] = payload.get("version_id")
            deadline_days = payload.get(
                "response_deadline_days", self.ROUND2_RESPONSE_DEADLINE_DAYS
            )
            deadline_dt = datetime.now(timezone.utc) + timedelta(days=deadline_days)
            state["round_2_response_deadline"] = deadline_dt.isoformat()

        elif event == FollowUpEvent.CASE_RESOLVED.value or event == FollowUpEvent.CASE_RESOLVED:
            state["resolution_outcome"] = payload.get("outcome", "unknown")
            state["resolution_notes"] = payload.get("notes", "")
            state["resolved_at"] = now

        # Overwrite escalation version if provided by the caller
        if "escalation_version_id" in payload:
            state["escalation_version_id"] = payload["escalation_version_id"]


# ---------------------------------------------------------------------------
# Scheduler integration helper (called by APScheduler / background task)
# ---------------------------------------------------------------------------


async def run_deadline_check(
    case_id: str,
    db_session_factory: Any,
    letter_builder_fn: Any,
) -> bool:
    """Check deadline for a case and advance agent state if needed.

    Args:
        case_id: The case to check.
        db_session_factory: Callable that returns an async context manager for DB sessions.
        letter_builder_fn: Async callable(case_id, context) → version_dict.

    Returns:
        True if escalation was triggered, False otherwise.
    """
    async with db_session_factory() as db:
        from backend.database.crud import (
            add_timeline_event,
            get_case,
            get_or_create_follow_up,
            save_appeal_letter_version,
            update_case_fields,
            update_case_status,
            update_follow_up,
        )

        case = await get_case(db, case_id=case_id)
        if not case:
            logger.warning("Deadline check: case %s not found", case_id)
            return False

        follow_up_record = await get_or_create_follow_up(db, case_id=case_id)
        agent = FollowUpAgent(case_id=case_id)
        state = agent.load_state(follow_up_record.graph_state_json)

        deadline_event = agent.check_deadline(state)
        if not deadline_event:
            return False

        # Advance to escalation
        state = agent.advance(state, event=deadline_event)
        escalation_context = agent.build_escalation_context(state)

        # Generate escalation letter
        try:
            version_dict = await letter_builder_fn(case_id, escalation_context)
            state = agent.advance(
                state,
                event=FollowUpEvent.DEADLINE_EXCEEDED,  # idempotent
                payload={"escalation_version_id": version_dict.get("version_id")},
            )
        except Exception as exc:
            logger.error("Failed to build escalation letter for case %s: %s", case_id, exc)
            return False

        # Persist
        await save_appeal_letter_version(db, version_dict=version_dict)
        await update_follow_up(
            db,
            case_id=case_id,
            agent_state=state["agent_state"],
            graph_state_json=dict(state),
            escalation_ready=True,
            escalation_triggered_at=state.get("escalation_triggered_at"),
        )
        await update_case_fields(
            db,
            case_id=case_id,
            status="escalated",
            current_appeal_letter_version_id=version_dict.get("version_id"),
        )
        await add_timeline_event(
            db,
            case_id=case_id,
            event_type="escalation_triggered",
            title="Escalation triggered — deadline exceeded",
            description="No insurer response received by the deadline. Escalation packet generated.",
            metadata={"escalation_version_id": version_dict.get("version_id")},
        )
        await db.commit()

    return True
