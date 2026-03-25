from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class BuildResult:
    entity_type: str
    records_built: int = 0
    records_deleted: int = 0
    errors: list = field(default_factory=list)

    def __str__(self):
        return (
            f"{self.entity_type}: "
            f"built={self.records_built} "
            f"del={self.records_deleted}"
            + (f" errors={len(self.errors)}" if self.errors else "")
        )


class BaseBuilder:
    """
    Builder base per tutti i fact_* del layer core.

    Ogni subclass deve definire:
      - entity_type: str         nome tabella fact_*
      - model_class              SQLAlchemy model
      - strategy: str            "FULL_REBUILD" | "APPEND_ONLY"

    E implementare:
      - build(session) -> BuildResult

    Utility disponibili:
      - _now()             datetime UTC corrente
      - _strip(v)          strip se stringa, altrimenti pass-through
      - _upper(v)          uppercase + strip se stringa
    """

    entity_type: str
    model_class: type
    strategy: str = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        raise NotImplementedError

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _strip(self, v):
        return v.strip() if isinstance(v, str) else v

    def _upper(self, v):
        return v.strip().upper() if isinstance(v, str) else v
