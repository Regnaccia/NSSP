from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_customer import FactCustomer
from sync.models.sync_customers import SyncCustomer


class CustomerBuilder(BaseBuilder):
    entity_type = "fact_customers"
    model_class = FactCustomer
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        session.execute(delete(FactCustomer))

        rows = session.execute(select(SyncCustomer)).scalars().all()

        for row in rows:
            session.add(FactCustomer(
                source_id=self._upper(row.source_id),
                code=self._upper(row.source_id),
                name=self._strip(row.name),
                address=self._strip(row.address),
                city=self._strip(row.city),
                postal_code=self._strip(row.postal_code),
                province=self._upper(row.province),
                country=self._upper(row.country),
                vat_number=self._strip(row.vat_number),
                email=self._strip(row.email),
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
