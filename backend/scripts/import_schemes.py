"""
Scheme importer entry point.

Usage:
  # Fixture dry-run (no database changes):
  docker compose exec backend python -m scripts.import_schemes \\
      --source fixture \\
      --fixture data/schemes/sample_fixture.json \\
      --dry-run

  # Fixture real import (writes to PostgreSQL):
  docker compose exec backend python -m scripts.import_schemes \\
      --source fixture \\
      --fixture data/schemes/sample_fixture.json

  # myScheme (blocked — requires API Setu credentials):
  docker compose exec backend python -m scripts.import_schemes \\
      --source myscheme \\
      --dry-run

The importer does NOT touch Qdrant or Neo4j in this phase.
Those pipelines will be connected in Phase 2 of nationwide ingestion.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running as: python -m scripts.import_schemes
# by ensuring the app package is importable.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal
from app.importers.pipeline import run_import
from app.importers.source_client import FixtureSchemeClient, get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("import_schemes")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import government schemes into the JanSahay database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=["fixture", "myscheme", "data_gov_in"],
        help="Source to import from.",
    )
    parser.add_argument(
        "--fixture",
        default="data/schemes/sample_fixture.json",
        help=(
            "Path to fixture JSON file (only used when --source fixture). "
            "Default: data/schemes/sample_fixture.json"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help=(
            "Simulate the import without committing to the database. "
            "Default: True (safety default)."
        ),
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Actually commit to the database (overrides --dry-run).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build the appropriate client
    if args.source == "fixture":
        fixture_path = Path(args.fixture)
        if not fixture_path.is_absolute():
            # Resolve relative to project root (one level above scripts/)
            fixture_path = Path(__file__).parent.parent / fixture_path
        client = FixtureSchemeClient(fixture_path=fixture_path)
    else:
        try:
            client = get_client(args.source)
        except ValueError as exc:
            logger.error("Unknown source: %s", exc)
            return 1

    mode = "DRY RUN" if args.dry_run else "LIVE IMPORT"
    logger.info("=" * 60)
    logger.info("JanSahay Scheme Importer — %s", mode)
    logger.info("Source: %s", args.source)
    if args.source == "fixture":
        logger.info("Fixture: %s", args.fixture)
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        report = run_import(client=client, db=db, dry_run=args.dry_run)
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("IMPORT REPORT")
    print("=" * 60)
    print(report.to_text())
    print("=" * 60)

    if report.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
