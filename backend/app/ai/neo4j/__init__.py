"""
Neo4j graph database layer for JanSahay GraphRAG.

Public surface:
  client     — driver management, get_session()
  schema     — index/constraint initialisation
  models     — plain-Python node dataclasses
  repository — parameterized CRUD + retrieval queries
  ingestion  — domain-level upsert helpers (imported from app.ai.neo4j.ingestion)
"""
from app.ai.neo4j.client import (
    GraphDatabaseError,
    GraphDatabaseUnavailableError,
    close_driver,
    get_driver,
    get_session,
    verify_connectivity,
)
from app.ai.neo4j.models import DocumentNode, FarmerNode, SchemeNode
from app.ai.neo4j.schema import initialize_schema

__all__ = [
    "GraphDatabaseError",
    "GraphDatabaseUnavailableError",
    "close_driver",
    "get_driver",
    "get_session",
    "verify_connectivity",
    "initialize_schema",
    "DocumentNode",
    "FarmerNode",
    "SchemeNode",
]
