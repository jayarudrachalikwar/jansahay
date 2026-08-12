"""
Neo4j driver management.

Uses the official neo4j Python driver (neo4j==5.18.0).
The driver is created once and reused; sessions are created per operation.
All errors are caught and re-raised as GraphDatabaseError so callers
never need to import neo4j internals.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — created lazily, never recreated
_driver: Driver | None = None


class GraphDatabaseError(Exception):
    """Raised when Neo4j is unreachable or an operation fails."""


class GraphDatabaseUnavailableError(GraphDatabaseError):
    """Raised specifically when Neo4j cannot be reached."""


def _create_driver() -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
        connection_timeout=5,
        max_connection_lifetime=3600,
        max_connection_pool_size=10,
        connection_acquisition_timeout=10,
    )


def get_driver() -> Driver:
    """Return the module-level Neo4j driver, creating it on first call."""
    global _driver
    if _driver is None:
        if not settings.neo4j_configured:
            raise GraphDatabaseUnavailableError(
                "Neo4j is not configured. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
            )
        try:
            _driver = _create_driver()
        except Exception as exc:
            raise GraphDatabaseUnavailableError(
                "Unable to create Neo4j driver."
            ) from exc
    return _driver


def verify_connectivity() -> bool:
    """
    Return True if Neo4j is reachable, False otherwise.
    Never raises — safe to call in health checks.
    """
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


@contextmanager
def get_session() -> Generator:
    """
    Context manager that yields an open Neo4j session for the configured database.
    Translates neo4j driver exceptions into GraphDatabaseError.
    """
    try:
        driver = get_driver()
    except GraphDatabaseUnavailableError:
        raise
    except Exception as exc:
        raise GraphDatabaseUnavailableError("Neo4j driver unavailable.") from exc

    try:
        session = driver.session(database=settings.neo4j_database)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise GraphDatabaseUnavailableError("Cannot open Neo4j session.") from exc

    try:
        yield session
    except (ServiceUnavailable, Neo4jError) as exc:
        raise GraphDatabaseError(f"Neo4j operation failed: {exc}") from exc
    finally:
        session.close()


def close_driver() -> None:
    """Close the driver — call on application shutdown."""
    global _driver
    if _driver is not None:
        try:
            _driver.close()
        except Exception:
            pass
        _driver = None
