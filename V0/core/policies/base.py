from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PolicyResult:
    policy_type: str
    aggregate_id: str
    records_updated: int = 0
    errors: list = field(default_factory=list)

    def __str__(self):
        return (
            f"{self.policy_type}({self.aggregate_id}): "
            f"updated={self.records_updated}"
            + (f" errors={len(self.errors)}" if self.errors else "")
        )


class BasePolicy:
    """
    Unita' di logica decisionale applicata a un aggregate_id.

    Ogni subclass definisce:
      - policy_type: str    nome della policy (es. "fifo_allocation")

    E implementa:
      - apply(session, aggregate_id) -> PolicyResult
    """

    policy_type: str

    def apply(self, session, aggregate_id: str) -> PolicyResult:
        raise NotImplementedError

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
