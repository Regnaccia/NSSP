"""
Projection CLI — output operativo leggibile per un singolo ordine.

Utilizzo:
    python -m app.projection order <order_source_id>

Legge da:
    - order_states
    - order_line_states
    - fact_orders
    - fact_order_lines

Nessuna logica — solo lettura e formattazione.
"""

import sys
from sqlalchemy import select

from db.session import get_session
from core.states.models.order_state import OrderState
from core.states.models.order_line_state import OrderLineState
from core.facts.models.fact_order import FactOrder
from core.facts.models.fact_order_line import FactOrderLine


def project_order(order_source_id: int) -> None:
    with get_session() as session:
        # Legge stato ordine
        order_state = session.execute(
            select(OrderState).where(OrderState.order_source_id == order_source_id)
        ).scalar_one_or_none()

        if order_state is None:
            print(f"Ordine {order_source_id} — nessuno stato trovato.")
            print("Eseguire un rebuild prima di proiettare.")
            return

        # Legge fact_order per header (FactOrder usa source_id come chiave logica)
        fact_order = session.execute(
            select(FactOrder).where(FactOrder.source_id == order_source_id)
        ).scalar_one_or_none()

        # Legge stati delle righe
        line_states = session.execute(
            select(OrderLineState)
            .where(OrderLineState.order_source_id == order_source_id)
            .order_by(OrderLineState.line_number)
        ).scalars().all()

        # Legge fact_order_lines per i dati grezzi
        fact_lines = session.execute(
            select(FactOrderLine)
            .where(FactOrderLine.order_source_id == order_source_id)
            .order_by(FactOrderLine.line_number)
        ).scalars().all()
        fact_lines_by_num = {fl.line_number: fl for fl in fact_lines}

        # Header
        print(f"\nOrdine {order_source_id} — {order_state.state}")
        if fact_order is not None:
            customer = getattr(fact_order, 'customer_source_id', None) or ""
            order_date = getattr(fact_order, 'order_date', None)
            delivery_date = getattr(fact_order, 'expected_delivery_date', None)
            date_str = order_date.strftime("%Y-%m-%d") if order_date else "?"
            delivery_str = delivery_date.strftime("%Y-%m-%d") if delivery_date else "?"
            print(f"Cliente: {customer}  Data: {date_str}  Consegna attesa: {delivery_str}")

        print()
        header = f"  {'Riga':<5}  {'Articolo':<15}  {'Ord':>8}  {'Ship':>8}  {'Rem':>8}  {'Coperta':>10}  Stato"
        separator = "  " + "-" * (len(header) - 2)
        print(header)
        print(separator)

        for ls in line_states:
            fl = fact_lines_by_num.get(ls.line_number)
            article = ls.article_source_id or ""
            qty_ord = float(fl.qty_ordered) if fl and fl.qty_ordered is not None else 0.0
            qty_ship = float(fl.qty_shipped) if fl and fl.qty_shipped is not None else 0.0
            qty_rem = qty_ord - qty_ship

            import json as _json
            trace_data = {}
            if ls.trace:
                try:
                    trace_data = _json.loads(ls.trace)
                except Exception:
                    pass

            qty_cov = trace_data.get("qty_coverable_now", None)
            if ls.state == "FULFILLED":
                cov_str = f"{'---':>10}"
            elif qty_cov is not None:
                mark = "OK" if trace_data.get("coverable_now") else "NO"
                cov_str = f"{qty_cov:>8.0f} {mark}"
            else:
                cov_str = f"{'?':>10}"

            print(
                f"  {ls.line_number:<5}  {article:<15}  {qty_ord:>8.0f}  {qty_ship:>8.0f}"
                f"  {qty_rem:>8.0f}  {cov_str}  {ls.state}"
            )

        print()
        print(
            f"  Totale: {order_state.total_lines} righe  "
            f"Aperte: {order_state.open_lines}  "
            f"Coperte: {order_state.coverable_lines}  "
            f"Evase: {order_state.fulfilled_lines}"
        )


def _resolve_order_source_id(arg: str) -> int:
    """
    Risolve l'order_source_id da un argomento che può essere:
    - un intero diretto (es. 107714)
    - un order_number Easyjob (es. CO-2600988)
    """
    try:
        return int(arg)
    except ValueError:
        pass

    # Cerca per order_number in fact_orders
    with get_session() as session:
        row = session.execute(
            select(FactOrder.source_id).where(FactOrder.order_number == arg)
        ).scalar_one_or_none()

    if row is None:
        print(f"Ordine '{arg}' non trovato in fact_orders.")
        sys.exit(1)

    return row


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "order":
        print("Utilizzo: python -m app.projection order <order_source_id|order_number>")
        print("  Esempi:")
        print("    python -m app.projection order 107714")
        print("    python -m app.projection order CO-2600988")
        sys.exit(1)

    oid = _resolve_order_source_id(sys.argv[2])
    project_order(oid)
