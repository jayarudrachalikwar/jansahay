"""
JanSahay scheme importer package.

Provides a clean separation between:
  source_client  — fetch raw data from an upstream source
  models         — typed raw / normalized data structures
  normalizer     — map raw source data → GovernmentScheme fields
  validator      — validate normalized records before persistence
  deduplicator   — detect new / updated / unchanged records
  persistence    — write to PostgreSQL (insert / update)
  reporter       — produce structured import reports
"""
