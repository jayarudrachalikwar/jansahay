"""
Neo4j schema initialisation.

Creates constraints and indexes for all graph entities.
Safe to call repeatedly — uses CREATE CONSTRAINT IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
so re-running is idempotent.

Node labels used in JanSahay:
  (:Scheme)      — government scheme
  (:State)       — Indian state or "All India"
  (:District)    — district within a state
  (:Crop)        — agricultural crop
  (:Category)    — scheme type / category
  (:Document)    — uploaded government PDF document
  (:Farmer)      — farmer (identified by user_id, no PII stored beyond profile fields)

All node names / identifiers map to fields that exist in the PostgreSQL models.
No synthetic or fabricated entities are introduced.
"""
from __future__ import annotations

import logging

from app.ai.neo4j.client import GraphDatabaseError, get_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL statements — all use IF NOT EXISTS so re-runs are safe
# ---------------------------------------------------------------------------

_CONSTRAINTS: list[str] = [
    # Unique node keys — used as MERGE targets
    "CREATE CONSTRAINT scheme_id IF NOT EXISTS FOR (s:Scheme) REQUIRE s.scheme_id IS UNIQUE",
    "CREATE CONSTRAINT state_name IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT district_key IF NOT EXISTS FOR (d:District) REQUIRE (d.name, d.state_name) IS NODE KEY",
    "CREATE CONSTRAINT crop_name IF NOT EXISTS FOR (c:Crop) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
    "CREATE CONSTRAINT farmer_user_id IF NOT EXISTS FOR (f:Farmer) REQUIRE f.user_id IS UNIQUE",
]

_INDEXES: list[str] = [
    "CREATE INDEX scheme_name IF NOT EXISTS FOR (s:Scheme) ON (s.name)",
    "CREATE INDEX scheme_state IF NOT EXISTS FOR (s:Scheme) ON (s.state)",
    "CREATE INDEX scheme_type IF NOT EXISTS FOR (s:Scheme) ON (s.scheme_type)",
    "CREATE INDEX scheme_active IF NOT EXISTS FOR (s:Scheme) ON (s.is_active)",
]


def initialize_schema() -> None:
    """
    Create all constraints and indexes.
    Logs each statement result at DEBUG level.
    Raises GraphDatabaseError if Neo4j is unavailable.
    """
    logger.info("Initialising Neo4j schema …")
    with get_session() as session:
        for stmt in _CONSTRAINTS:
            try:
                session.run(stmt)
                logger.debug("Schema OK: %s", stmt[:60])
            except Exception as exc:
                # Some Neo4j community editions may not support NODE KEY —
                # log and continue rather than crashing startup
                logger.warning("Schema statement skipped (%s): %s", type(exc).__name__, stmt[:60])

        for stmt in _INDEXES:
            try:
                session.run(stmt)
                logger.debug("Index OK: %s", stmt[:60])
            except Exception as exc:
                logger.warning("Index statement skipped (%s): %s", type(exc).__name__, stmt[:60])

    logger.info("Neo4j schema initialisation complete.")
