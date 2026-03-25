from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert


@dataclass
class ExtractorResult:
    entity_type: str
    records_read: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    errors: list = field(default_factory=list)

    def __str__(self):
        return (
            f"{self.entity_type}: "
            f"read={self.records_read} "
            f"ins={self.records_inserted} "
            f"upd={self.records_updated} "
            f"del={self.records_deleted}"
            + (f" errors={len(self.errors)}" if self.errors else "")
        )


class BaseExtractor:
    """
    Extractor base per tutte le entità sync_*.

    Ogni subclass deve definire:
      - entity_type: str          nome tabella sync_*
      - model_class               SQLAlchemy model
      - pk_fields: list[str]      campi PK nel modello sync (default: ["source_id"])
      - detect_deletes: bool      se rilevare record scomparsi da Easy (default: True)

    E implementare:
      - fetch_rows(easy_conn) → list[Row]   query su Easy
      - map_row(row) → dict                 mapping Easy → sync fields

    Opzionale override:
      - preprocess_rows(raw_rows) → list[dict]
        per logiche pre-mapping (es. COLL_RIGA_PREC su order_lines)
    """

    entity_type: str
    model_class: type
    pk_fields: list = ["source_id"]
    detect_deletes: bool = True

    # --- da implementare nei subclass ---

    def fetch_rows(self, easy_conn) -> list:
        raise NotImplementedError

    def map_row(self, row) -> dict:
        raise NotImplementedError

    # --- hook opzionale ---

    def preprocess_rows(self, raw_rows: list) -> list[dict]:
        """Trasforma le righe raw in dizionari mappati. Override per logiche speciali."""
        result = []
        for row in raw_rows:
            try:
                result.append(self.map_row(row))
            except Exception as e:
                raise RuntimeError(f"map_row error on {self.entity_type}: {e}") from e
        return result

    # --- internals ---

    def _compute_hash(self, mapped: dict) -> str:
        skip = {"synced_at", "sync_run_id", "row_hash"}
        data = {k: str(v) for k, v in sorted(mapped.items()) if k not in skip}
        return hashlib.md5(json.dumps(data, default=str).encode()).hexdigest()

    def _pk_key(self, obj, use_getattr=False) -> str:
        if use_getattr:
            return "|".join(str(getattr(obj, f)) for f in self.pk_fields)
        return "|".join(str(obj[f]) for f in self.pk_fields)

    def _record_change(self, mrs_session, sync_run_id, source_id_str, change_type, now):
        from sync.models.sync_change_item import SyncChangeItem
        mrs_session.add(SyncChangeItem(
            sync_run_id=sync_run_id,
            entity_type=self.entity_type,
            source_id=source_id_str,
            change_type=change_type,
            changed_at=now,
        ))

    # --- entry point ---

    def run(self, mrs_session, easy_engine, sync_run_id: int) -> ExtractorResult:
        result = ExtractorResult(entity_type=self.entity_type)
        now = datetime.now(timezone.utc)

        # 1. Fetch da Easy
        with easy_engine.connect() as easy_conn:
            raw_rows = self.fetch_rows(easy_conn)
        result.records_read = len(raw_rows)

        # 2. Pre-processing (mapping + logiche speciali)
        try:
            mapped_rows = self.preprocess_rows(raw_rows)
        except Exception as e:
            result.errors.append(str(e))
            return result

        # 3. Carica hash esistenti dal layer sync
        pk_cols = [getattr(self.model_class, f) for f in self.pk_fields]
        hash_col = self.model_class.row_hash
        existing: dict[str, str] = {}
        for rec in mrs_session.execute(select(*pk_cols, hash_col)).all():
            key = "|".join(str(getattr(rec, f)) for f in self.pk_fields)
            existing[key] = rec.row_hash

        # 4. Upsert con change detection
        seen_keys: set[str] = set()
        for mapped in mapped_rows:
            row_hash = self._compute_hash(mapped)
            key = self._pk_key(mapped)
            seen_keys.add(key)

            if key not in existing:
                change_type = "INSERTED"
                result.records_inserted += 1
            elif existing[key] != row_hash:
                change_type = "UPDATED"
                result.records_updated += 1
            else:
                continue  # invariato

            mapped["synced_at"] = now
            mapped["sync_run_id"] = sync_run_id
            mapped["row_hash"] = row_hash

            stmt = insert(self.model_class).values(**mapped)
            stmt = stmt.on_conflict_do_update(
                index_elements=self.pk_fields,
                set_={k: v for k, v in mapped.items() if k not in self.pk_fields},
            )
            mrs_session.execute(stmt)
            self._record_change(mrs_session, sync_run_id, key, change_type, now)

        # 5. Rilevazione cancellazioni
        # Guard: se Easy non ha restituito nulla ma abbiamo dati locali,
        # è probabile un problema di connessione/query — non cancelliamo.
        if self.detect_deletes and (len(mapped_rows) > 0 or len(existing) == 0):
            for key in set(existing.keys()) - seen_keys:
                pk_values = key.split("|")
                filters = [
                    getattr(self.model_class, f) == v
                    for f, v in zip(self.pk_fields, pk_values)
                ]
                mrs_session.execute(delete(self.model_class).where(*filters))
                result.records_deleted += 1
                self._record_change(mrs_session, sync_run_id, key, "DELETED", now)

        return result
