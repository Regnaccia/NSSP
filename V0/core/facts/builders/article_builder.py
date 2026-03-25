from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_article import FactArticle
from sync.models.sync_articles import SyncArticle


class ArticleBuilder(BaseBuilder):
    entity_type = "fact_articles"
    model_class = FactArticle
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        result.records_deleted = session.execute(delete(FactArticle)).rowcount

        rows = session.execute(select(SyncArticle)).scalars().all()

        for row in rows:
            session.add(FactArticle(
                source_id=self._upper(row.source_id),
                code=self._upper(row.source_id),
                description=self._strip(row.description),
                description_2=self._strip(row.description_2),
                unit_of_measure=self._upper(row.unit_of_measure),
                is_blocked=row.is_blocked,
                material_code=self._upper(row.material_code),
                category=self._upper(row.category),
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
