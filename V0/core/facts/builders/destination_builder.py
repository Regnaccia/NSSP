from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_destination import FactDestination
from sync.models.sync_destinations import SyncDestination
from sync.models.sync_customers import SyncCustomer


class DestinationBuilder(BaseBuilder):
    """
    Costruisce FactDestination da due sorgenti:
    1. sync_destinations — destinazioni esplicite
    2. sync_customers — per i clienti senza destinazioni (regola di dominio v0.2)
    """

    entity_type = "fact_destinations"
    model_class = FactDestination
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        result.records_deleted = session.execute(delete(FactDestination)).rowcount

        # 1. Destinazioni esplicite da sync_destinations
        destinations = session.execute(select(SyncDestination)).scalars().all()
        customers_with_dest = set()

        for row in destinations:
            if not row.customer_source_id:
                result.errors.append(
                    f"destination {row.source_id!r} skipped: customer_source_id is NULL"
                )
                continue
            session.add(FactDestination(
                source_id=self._upper(row.source_id),
                customer_source_id=self._upper(row.customer_source_id),
                code=self._upper(row.source_id),
                name=self._strip(row.name),
                address=self._strip(row.address),
                city=self._strip(row.city),
                postal_code=self._strip(row.postal_code),
                province=self._upper(row.province),
                country=self._upper(row.country),
                is_default=row.is_default,
                is_derived_from_customer=False,
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1
            customers_with_dest.add(self._upper(row.customer_source_id))

        # 2. Clienti senza destinazione esplicita → destinazione derivata
        customers = session.execute(select(SyncCustomer)).scalars().all()

        for row in customers:
            cid = self._upper(row.source_id)
            if cid in customers_with_dest:
                continue
            session.add(FactDestination(
                source_id=None,
                customer_source_id=cid,
                code=None,
                name=self._strip(row.name),
                address=self._strip(row.address),
                city=self._strip(row.city),
                postal_code=self._strip(row.postal_code),
                province=self._upper(row.province),
                country=self._upper(row.country),
                is_default=True,
                is_derived_from_customer=True,
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
