"""Initial schema — tutte le tabelle V1

Revision ID: 001
Revises:
Create Date: 2026-03-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "articoli",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codice", sa.String(50), nullable=False),
        sa.Column("codice_upper", sa.String(50), nullable=False),
        sa.Column("descrizione", sa.Text, nullable=True),
        sa.Column("categoria", sa.String(50), nullable=True),
        sa.Column("capienza", sa.Integer, nullable=True),
        sa.Column("scorta_mensile", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mesi_scorta", sa.Integer, nullable=False, server_default="3"),
        sa.Column("tipo_produzione", sa.String(20), nullable=False, server_default="PEZZO"),
        sa.Column("lunghezza_barra", sa.Integer, nullable=True),
        sa.Column("multipli_taglio", sa.Integer, nullable=True),
        sa.Column("prd_pari", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("storico_sufficiente", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("scorta_calcolata_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("codice", name="uq_articoli_codice"),
        sa.UniqueConstraint("codice_upper", name="uq_articoli_codice_upper"),
    )

    op.create_table(
        "clienti",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codice_easyjob", sa.String(50), nullable=False),
        sa.Column("ragione_sociale", sa.Text, nullable=False),
        sa.Column("nickname", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("codice_easyjob", name="uq_clienti_codice_easyjob"),
    )

    op.create_table(
        "ordini",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("numero_ordine", sa.String(50), nullable=False),
        sa.Column("cliente_id", sa.String(36), sa.ForeignKey("clienti.id"), nullable=False),
        sa.Column("data_ordine", sa.Date, nullable=False),
        sa.Column("data_consegna", sa.Date, nullable=True),
        sa.Column("stato", sa.String(30), nullable=False, server_default="aperto"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("numero_ordine", name="uq_ordini_numero_ordine"),
    )

    op.create_table(
        "righe_ordine",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ordine_id", sa.String(36), sa.ForeignKey("ordini.id"), nullable=False),
        sa.Column("articolo_id", sa.String(36), sa.ForeignKey("articoli.id"), nullable=False),
        sa.Column("riga_ej_id", sa.String(50), nullable=False),
        sa.Column("qty_ordinata", sa.Integer, nullable=False),
        sa.Column("qty_disponibile", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_in_produzione", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_consegnata", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stato", sa.String(30), nullable=False, server_default="aperto"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_righe_ordine_ordine_id", "righe_ordine", ["ordine_id"])
    op.create_index("ix_righe_ordine_articolo_id", "righe_ordine", ["articolo_id"])

    op.create_table(
        "macchine",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codice", sa.String(30), nullable=False),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("operazioni_eseguibili", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("stato", sa.String(30), nullable=False, server_default="disponibile"),
        sa.Column("setup_corrente", sa.Text, nullable=True),
        sa.Column("attiva", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("codice", name="uq_macchine_codice"),
    )

    op.create_table(
        "commesse",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("riga_ordine_id", sa.String(36), sa.ForeignKey("righe_ordine.id"), nullable=True),
        sa.Column("articolo_id", sa.String(36), sa.ForeignKey("articoli.id"), nullable=False),
        sa.Column("macchina_id", sa.String(36), sa.ForeignKey("macchine.id"), nullable=True),
        sa.Column("ldp_easyjob", sa.String(50), nullable=True),
        sa.Column("qty_cliente", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_scorta", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_prodotta_cliente", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_prodotta_scorta", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_ciclo_corrente", sa.Integer, nullable=True),
        sa.Column("stato", sa.String(30), nullable=False, server_default="in_coda"),
        sa.Column("posizione_coda", sa.Integer, nullable=True),
        sa.Column("priorita_suggerita", sa.Integer, nullable=True),
        sa.Column("sospesa_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sospesa_nota", sa.Text, nullable=True),
        sa.Column("completata_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(50), nullable=True),
    )
    op.create_index("ix_commesse_articolo_id", "commesse", ["articolo_id"])
    op.create_index("ix_commesse_stato", "commesse", ["stato"])

    op.create_table(
        "policy_clienti",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cliente_id", sa.String(36), sa.ForeignKey("clienti.id"), nullable=False),
        sa.Column("tipo_policy", sa.String(30), nullable=False),
        sa.Column("giorno_fisso", sa.Integer, nullable=True),
        sa.Column("soglia_valore", sa.Numeric(10, 2), nullable=True),
        sa.Column("corriere_preferito", sa.String(100), nullable=True),
        sa.Column("note_spedizione", sa.Text, nullable=True),
        sa.Column("policy_json", postgresql.JSONB, nullable=True),
        sa.Column("configurata_da", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cliente_id", name="uq_policy_clienti_cliente_id"),
    )

    op.create_table(
        "eventi",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("mittente", sa.String(30), nullable=False),
        sa.Column("destinatario", sa.String(30), nullable=False),
        sa.Column("ref_ordine_id", sa.String(36), sa.ForeignKey("ordini.id"), nullable=True),
        sa.Column("ref_commessa_id", sa.String(36), sa.ForeignKey("commesse.id"), nullable=True),
        sa.Column("ref_articolo_id", sa.String(36), sa.ForeignKey("articoli.id"), nullable=True),
        sa.Column("stato", sa.String(20), nullable=False, server_default="aperto"),
        sa.Column("nota", sa.Text, nullable=True),
        sa.Column("feedback_stato", sa.String(30), nullable=True),
        sa.Column("feedback_data_prevista", sa.Date, nullable=True),
        sa.Column("feedback_nota", sa.Text, nullable=True),
        sa.Column("corriere_override", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_eventi_destinatario_stato", "eventi", ["destinatario", "stato"])

    op.create_table(
        "sync_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tabella", sa.String(50), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("records_updated", sa.Integer, nullable=True),
        sa.Column("sync_duration_ms", sa.Integer, nullable=True),
        sa.UniqueConstraint("tabella", name="uq_sync_log_tabella"),
    )

    op.create_table(
        "consegne_magazzino",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("commessa_id", sa.String(36), sa.ForeignKey("commesse.id"), nullable=False),
        sa.Column("articolo_id", sa.String(36), sa.ForeignKey("articoli.id"), nullable=False),
        sa.Column("qty_consegnata", sa.Integer, nullable=False),
        sa.Column("quota", sa.String(10), nullable=False),
        sa.Column("qty_cliente", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qty_scorta", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stato", sa.String(20), nullable=False, server_default="in_attesa"),
        sa.Column("registrata_ej_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "spedizioni",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ordine_id", sa.String(36), sa.ForeignKey("ordini.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("stato", sa.String(30), nullable=False, server_default="in_preparazione"),
        sa.Column("corriere", sa.String(100), nullable=True),
        sa.Column("data_pianificata", sa.Date, nullable=True),
        sa.Column("data_spedizione", sa.Date, nullable=True),
        sa.Column("colli", sa.Integer, nullable=True),
        sa.Column("peso_kg", sa.Numeric(8, 2), nullable=True),
        sa.Column("evento_id", sa.String(36), sa.ForeignKey("eventi.id"), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_spedizioni_ordine_id", "spedizioni", ["ordine_id"])

    op.create_table(
        "utenti",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("ruolo", sa.String(20), nullable=False),
        sa.Column("attivo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username", name="uq_utenti_username"),
    )


def downgrade() -> None:
    op.drop_table("utenti")
    op.drop_table("spedizioni")
    op.drop_table("consegne_magazzino")
    op.drop_table("sync_log")
    op.drop_table("eventi")
    op.drop_table("policy_clienti")
    op.drop_table("commesse")
    op.drop_table("macchine")
    op.drop_table("righe_ordine")
    op.drop_table("ordini")
    op.drop_table("clienti")
    op.drop_table("articoli")
