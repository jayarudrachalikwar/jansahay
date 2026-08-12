"""
Main import pipeline.

Orchestrates: fetch → normalize → validate → deduplicate → persist (or dry-run)

Usage
-----
from app.importers.pipeline import run_import
from app.importers.source_client import FixtureSchemeClient

report = run_import(
    client=FixtureSchemeClient.from_records([...]),
    db=session,
    dry_run=True,
)
print(report.to_text())

Qdrant and Neo4j are NOT triggered here.
Phase 2 will add post-import hooks for those pipelines.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.importers import deduplicator, normalizer, persistence, validator
from app.importers.models import (
    ImportReport,
    NormalizedScheme,
    RecordOutcome,
    RecordResult,
)
from app.importers.source_client import SchemeSourceClient, SchemeSourceError

logger = logging.getLogger(__name__)


def run_import(
    client: SchemeSourceClient,
    db: Session,
    dry_run: bool = True,
) -> ImportReport:
    """
    Run a complete import for the given source client.

    Parameters
    ----------
    client   : Any SchemeSourceClient implementation.
    db       : SQLAlchemy session.  In dry-run mode the session is used
               only for deduplication reads; no writes or commits occur.
    dry_run  : When True, no changes are committed to PostgreSQL.
               Qdrant and Neo4j are never touched in either mode at
               this phase.

    Returns
    -------
    ImportReport with full statistics.
    """
    report = ImportReport(
        source=client.source_name,
        dry_run=dry_run,
    )
    seen_ids: set[str] = set()

    logger.info(
        "[IMPORTER] Starting import: source=%s dry_run=%s",
        client.source_name, dry_run,
    )

    # ------------------------------------------------------------------
    # 1. Fetch
    # ------------------------------------------------------------------
    try:
        raw_records = list(client.fetch())
    except SchemeSourceError as exc:
        msg = f"Source fetch failed: {exc}"
        logger.error("[IMPORTER] %s", msg)
        report.errors.append(msg)
        report.finish()
        return report

    report.fetched = len(raw_records)
    logger.info("[IMPORTER] Fetched %d record(s) from source=%s", report.fetched, client.source_name)

    # ------------------------------------------------------------------
    # 2. Normalize → validate → deduplicate → persist
    # ------------------------------------------------------------------
    for raw in raw_records:

        # ── Normalize ───────────────────────────────────────────────
        normalized: NormalizedScheme | None = normalizer.normalize(raw)
        if normalized is None:
            report.invalid += 1
            msg = f"Normalization failed for external_id={raw.external_id}"
            report.record_results.append(
                RecordResult(external_id=raw.external_id, outcome=RecordOutcome.INVALID, reason=msg)
            )
            report.errors.append(msg)
            continue

        # ── Validate ─────────────────────────────────────────────────
        errors = validator.validate(normalized)
        if errors:
            report.invalid += 1
            reason = "; ".join(errors)
            logger.warning(
                "[IMPORTER] INVALID source=%s external_id=%s: %s",
                raw.source, raw.external_id, reason,
            )
            report.record_results.append(
                RecordResult(
                    external_id=raw.external_id,
                    outcome=RecordOutcome.INVALID,
                    name=normalized.name,
                    reason=reason,
                )
            )
            report.errors.append(f"[{raw.external_id}] {reason}")
            continue

        report.valid += 1

        # ── Deduplicate ───────────────────────────────────────────────
        batch_key = f"{normalized.source}:{normalized.external_id}"
        result, existing = deduplicator.check(normalized, db, seen_ids)
        seen_ids.add(batch_key)

        if result == deduplicator.DedupResult.DUPLICATE:
            report.duplicates += 1
            report.record_results.append(
                RecordResult(
                    external_id=raw.external_id,
                    outcome=RecordOutcome.DUPLICATE,
                    name=normalized.name,
                    reason="Duplicate external_id in this import batch.",
                )
            )
            continue

        if result == deduplicator.DedupResult.UNCHANGED:
            report.unchanged += 1
            report.record_results.append(
                RecordResult(
                    external_id=raw.external_id,
                    outcome=RecordOutcome.UNCHANGED,
                    name=normalized.name,
                )
            )
            logger.debug("[IMPORTER] UNCHANGED external_id=%s", raw.external_id)
            continue

        # ── Persist (skipped in dry-run) ──────────────────────────────
        if result == deduplicator.DedupResult.NEW:
            report.new += 1
            outcome = RecordOutcome.NEW
            if not dry_run:
                persistence.insert(normalized, db)
        else:  # UPDATED
            report.updated += 1
            outcome = RecordOutcome.UPDATED
            if not dry_run and existing is not None:
                persistence.update(existing, normalized, db)

        report.record_results.append(
            RecordResult(
                external_id=raw.external_id,
                outcome=outcome,
                name=normalized.name,
            )
        )

        logger.debug(
            "[IMPORTER] %s external_id=%s name=%r",
            outcome.value.upper(), raw.external_id, normalized.name,
        )

    # ------------------------------------------------------------------
    # 3. Commit (only in non-dry-run mode)
    # ------------------------------------------------------------------
    if not dry_run:
        try:
            db.commit()
            logger.info(
                "[IMPORTER] Committed: new=%d updated=%d",
                report.new, report.updated,
            )
        except Exception as exc:
            db.rollback()
            msg = f"Database commit failed: {exc}"
            logger.error("[IMPORTER] %s", msg)
            report.errors.append(msg)
    else:
        logger.info("[IMPORTER] Dry-run complete — no database changes committed.")

    report.finish()
    logger.info(
        "[IMPORTER] Done: source=%s fetched=%d valid=%d invalid=%d "
        "new=%d updated=%d unchanged=%d duplicates=%d dry_run=%s",
        report.source, report.fetched, report.valid, report.invalid,
        report.new, report.updated, report.unchanged, report.duplicates,
        report.dry_run,
    )
    return report
