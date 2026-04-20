"""ReportRepository — persists MonthlyReport records to the reports table."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.schema import ReportORM
from app.reporting.report import AggregatedMetrics, MonthlyReport, ReportStatus


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # write

    def create(self, report: MonthlyReport) -> MonthlyReport:
        orm = ReportORM(
            id=report.report_id,
            owner_name=report.owner_name,
            period_start=report.period_start,
            period_end=report.period_end,
            status=report.status.value,
            metrics=report.metrics.model_dump(),
            ai_summary=report.ai_summary,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
        self._db.add(orm)
        self._db.flush()
        return report

    def mark_completed(
        self,
        report_id: UUID,
        metrics: AggregatedMetrics,
        ai_summary: str,
    ) -> MonthlyReport | None:
        orm = self._db.get(ReportORM, report_id)
        if orm is None:
            return None
        orm.status = ReportStatus.COMPLETED.value
        orm.metrics = metrics.model_dump()
        orm.ai_summary = ai_summary
        orm.updated_at = datetime.now(UTC)
        self._db.flush()
        return self._to_domain(orm)

    def delete(self, report_id: UUID) -> bool:
        orm = self._db.get(ReportORM, report_id)
        if orm is None:
            return False
        self._db.delete(orm)
        self._db.flush()
        return True

    def mark_failed(self, report_id: UUID, error: str) -> MonthlyReport | None:
        orm = self._db.get(ReportORM, report_id)
        if orm is None:
            return None
        orm.status = ReportStatus.FAILED.value
        orm.ai_summary = error
        orm.updated_at = datetime.now(UTC)
        self._db.flush()
        return self._to_domain(orm)

    # read

    def get(self, report_id: UUID) -> MonthlyReport | None:
        orm = self._db.get(ReportORM, report_id)
        return self._to_domain(orm) if orm else None

    def list_for_owner(self, owner_name: str, limit: int = 50) -> list[MonthlyReport]:
        rows = (
            self._db.query(ReportORM)
            .filter(ReportORM.owner_name == owner_name)
            .order_by(ReportORM.period_start.desc())
            .limit(limit)
            .all()
        )
        return [self._to_domain(r) for r in rows]

    # private

    @staticmethod
    def _to_domain(orm: ReportORM) -> MonthlyReport:
        return MonthlyReport(
            report_id=orm.id,
            owner_name=orm.owner_name,
            period_start=orm.period_start,
            period_end=orm.period_end,
            status=ReportStatus(orm.status),
            metrics=AggregatedMetrics(**(orm.metrics or {})),
            ai_summary=orm.ai_summary or "",
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
