"""
OrderStateBuilder — ricostruisce gli stati per un singolo ordine.

Flusso per ogni order_source_id:
  1. DELETE order_line_states WHERE order_source_id = X
  2. Legge computed_order_lines WHERE order_source_id = X
  3. Per ogni riga: determina stato + produce trace JSON
  4. INSERT order_line_states
  5. DELETE order_states WHERE order_source_id = X
  6. Aggrega stati righe → determina order state + produce trace JSON
  7. INSERT order_states

Dipendenze: computed_order_lines deve essere aggiornato (inclusi qty_coverable_now / coverable_now
dalla FifoAllocationPolicy) prima di chiamare questo builder.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select, delete

from core.computed_facts.models.computed_order_line import ComputedOrderLine
from core.states.models.order_line_state import OrderLineState
from core.states.models.order_state import OrderState


@dataclass
class StatesBuildResult:
    order_source_id: int
    line_states_built: int = 0
    errors: list = field(default_factory=list)

    def __str__(self):
        return (
            f"StatesBuildResult(order={self.order_source_id}, "
            f"lines={self.line_states_built}, errors={len(self.errors)})"
        )


def _determine_line_state(line: ComputedOrderLine) -> tuple[str, dict]:
    """Determina lo stato e il trace di una riga ordine."""
    qty_ordered = float(line.qty_ordered) if line.qty_ordered is not None else None
    qty_shipped = float(line.qty_shipped) if line.qty_shipped is not None else 0.0
    qty_remaining = float(line.qty_remaining) if line.qty_remaining is not None else None
    coverable_now = line.coverable_now
    qty_coverable_now = float(line.qty_coverable_now) if line.qty_coverable_now is not None else 0.0

    trace = {
        "qty_ordered": qty_ordered,
        "qty_shipped": qty_shipped,
        "qty_remaining": qty_remaining,
        "coverable_now": coverable_now,
        "qty_coverable_now": qty_coverable_now,
        "policy": "fifo_allocation",
    }

    # Priorità: FULFILLED > PARTIALLY_FULFILLED > COVERABLE_NOW / NOT_COVERABLE_NOW > OPEN
    if line.is_fully_shipped:
        state = "FULFILLED"
    elif qty_shipped > 0 and qty_remaining is not None and qty_remaining > 0:
        state = "PARTIALLY_FULFILLED"
    elif line.is_open_line:
        if coverable_now:
            state = "COVERABLE_NOW"
        else:
            state = "NOT_COVERABLE_NOW"
    else:
        state = "OPEN"

    trace["decision"] = state
    return state, trace


def _determine_order_state(line_states: list[str], total_lines: int) -> tuple[str, dict]:
    """Determina lo stato aggregato per ordine dagli stati delle sue righe."""
    fulfilled_lines = sum(1 for s in line_states if s == "FULFILLED")
    partially_fulfilled_lines = sum(1 for s in line_states if s == "PARTIALLY_FULFILLED")
    coverable_lines = sum(1 for s in line_states if s == "COVERABLE_NOW")
    not_coverable_lines = sum(1 for s in line_states if s == "NOT_COVERABLE_NOW")
    open_lines_count = sum(1 for s in line_states if s in ("COVERABLE_NOW", "NOT_COVERABLE_NOW", "OPEN", "PARTIALLY_FULFILLED"))

    # Determina stato ordine
    if fulfilled_lines == total_lines:
        state = "FULFILLED"
    elif open_lines_count == 0:
        # Nessuna riga aperta (tutte fulfilled) — già coperto sopra
        state = "FULFILLED"
    elif coverable_lines > 0 and not_coverable_lines == 0 and partially_fulfilled_lines == 0:
        # Tutte le righe aperte sono coverable
        state = "FULLY_COVERABLE"
    elif coverable_lines > 0:
        state = "PARTIALLY_COVERABLE"
    else:
        state = "OPEN"

    trace = {
        "total_lines": total_lines,
        "open_lines": open_lines_count,
        "coverable_lines": coverable_lines,
        "fulfilled_lines": fulfilled_lines,
        "decision": state,
    }
    return state, trace


class OrderStateBuilder:

    def build(self, session, order_source_id: int) -> StatesBuildResult:
        result = StatesBuildResult(order_source_id=order_source_id)
        now = datetime.now(timezone.utc)

        # 1. DELETE righe esistenti per questo ordine
        session.execute(
            delete(OrderLineState).where(OrderLineState.order_source_id == order_source_id)
        )
        session.execute(
            delete(OrderState).where(OrderState.order_source_id == order_source_id)
        )

        # 2. Legge computed_order_lines per questo ordine
        lines = session.execute(
            select(ComputedOrderLine)
            .where(ComputedOrderLine.order_source_id == order_source_id)
            .order_by(ComputedOrderLine.line_number)
        ).scalars().all()

        # 3-4. Determina stato per ogni riga e inserisce
        line_states: list[str] = []
        for line in lines:
            state, trace = _determine_line_state(line)
            line_states.append(state)
            session.add(OrderLineState(
                order_source_id=order_source_id,
                line_number=line.line_number,
                article_source_id=line.article_source_id,
                state=state,
                trace=json.dumps(trace),
                built_at=now,
            ))
            result.line_states_built += 1

        # 5-7. Determina stato aggregato ordine e inserisce
        total_lines = len(line_states)
        if total_lines > 0:
            order_state, order_trace = _determine_order_state(line_states, total_lines)
        else:
            order_state = "OPEN"
            order_trace = {"total_lines": 0, "open_lines": 0, "coverable_lines": 0, "fulfilled_lines": 0, "decision": "OPEN"}

        open_lines = order_trace["open_lines"]
        coverable_lines = order_trace["coverable_lines"]
        fulfilled_lines = order_trace["fulfilled_lines"]

        session.add(OrderState(
            order_source_id=order_source_id,
            state=order_state,
            total_lines=total_lines,
            open_lines=open_lines,
            coverable_lines=coverable_lines,
            fulfilled_lines=fulfilled_lines,
            trace=json.dumps(order_trace),
            built_at=now,
        ))

        return result
