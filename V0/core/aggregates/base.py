from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RebuildResult:
    aggregate_type: str
    aggregate_id: str
    records_rebuilt: int = 0
    errors: list = field(default_factory=list)

    def __str__(self):
        return (
            f"{self.aggregate_type}({self.aggregate_id}): "
            f"rebuilt={self.records_rebuilt}"
            + (f" errors={len(self.errors)}" if self.errors else "")
        )


class BaseAggregate:
    """
    Unita' di orchestrazione del rebuild.

    Ogni subclass definisce:
      - aggregate_type: str    nome del dominio (es. "order", "article_supply_demand")

    E implementa:
      - rebuild(session, aggregate_id) -> RebuildResult
    """

    aggregate_type: str

    def rebuild(self, session, aggregate_id: str) -> RebuildResult:
        raise NotImplementedError

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _upper(self, v):
        return v.strip().upper() if isinstance(v, str) else v

    def _strip(self, v):
        return v.strip() if isinstance(v, str) else v
