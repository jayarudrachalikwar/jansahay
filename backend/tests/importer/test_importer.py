"""
Comprehensive importer tests — Phase 1 (scheme ingestion foundation).

All tests use in-memory fixtures. No real government API is called.
Tests cover:
  A. Normalizer
  B. Validator
  C. Deduplicator
  D. Pipeline / dry-run
  E. Persistence
  F. Source client
  G. Import report
"""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import patch

from app.importers.models import NormalizedScheme, RawSchemeRecord
from app.importers import normalizer, validator
from app.importers.deduplicator import DedupResult, check as dedup_check
from app.importers.source_client import FixtureSchemeClient, MySchemeClient, SchemeSourceError
from app.importers.pipeline import run_import

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raw(external_id: str = "test-001", data: dict | None = None) -> RawSchemeRecord:
    if data is None:
        data = _valid_raw_data()
    return RawSchemeRecord(source="fixture", external_id=external_id, raw_data=data)


def _valid_raw_data(name: str = "Test Scheme") -> dict:
    return {
        "schemeId": "test-001",
        "schemeName": name,
        "schemeShortTitle": "Short description of test scheme.",
        "schemeDescription": "Detailed description of test scheme for testing.",
        "state": "Telangana",
        "ministry": "Ministry of Agriculture",
        "department": "Department of Agriculture",
        "schemeType": "Financial Assistance",
        "schemeLevel": "State",
        "beneficiaryType": ["farmer"],
        "eligibilityCriteria": "All small farmers in Telangana.",
        "benefits": "Financial support for farmers.",
        "applicationProcess": "Apply at local office.",
        "documents": ["Aadhaar"],
        "tags": ["agriculture"],
        "schemeUrl": "https://example.gov.in/test",
    }


def _valid_normalized(external_id: str = "test-001", name: str = "Test Scheme") -> NormalizedScheme:
    return NormalizedScheme(
        name=name,
        short_description="Short description.",
        detailed_description="Detailed description.",
        department="Test Department",
        state="Telangana",
        scheme_type="Financial Assistance",
        benefits="Test benefits.",
        application_process="Apply at local office.",
        external_id=external_id,
        source="fixture",
        official_website="https://example.gov.in",
        source_url="https://example.gov.in",
        ministry="Ministry of Agriculture",
        beneficiary_type="farmer",
        coverage_type="state",
        geo_scope="state",
        tags="agriculture",
    )


# ---------------------------------------------------------------------------
# A. Normalizer
# ---------------------------------------------------------------------------

class TestNormalizer:
    def test_valid_record_normalizes_successfully(self):
        raw = _raw()
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.name == "Test Scheme"
        assert result.state == "Telangana"
        assert result.source == "fixture"
        assert result.external_id == "test-001"

    def test_state_normalization_all_india_variants(self):
        for alias in ("all states", "All States/UTs", "Pan India", "NATIONAL"):
            raw_data = {**_valid_raw_data(), "state": alias}
            raw = _raw(data=raw_data)
            result = normalizer.normalize(raw)
            assert result is not None
            assert result.state == "All India", f"Expected 'All India' for '{alias}'"

    def test_state_normalization_known_state(self):
        for alias, expected in [
            ("andhra pradesh", "Andhra Pradesh"),
            ("ap", "Andhra Pradesh"),
            ("telangana", "Telangana"),
            ("mp", "Madhya Pradesh"),
        ]:
            assert normalizer.normalize_state(alias) == expected

    def test_state_normalization_empty_defaults_to_all_india(self):
        assert normalizer.normalize_state("") == "All India"
        assert normalizer.normalize_state(None) == "All India"

    def test_name_truncated_to_limit(self):
        long_name = "A" * 300
        raw_data = {**_valid_raw_data(), "schemeName": long_name}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert len(result.name) == 255

    def test_short_description_truncated_to_limit(self):
        raw_data = {**_valid_raw_data(), "schemeShortTitle": "B" * 600}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert len(result.short_description) == 500

    def test_beneficiary_list_joined(self):
        raw_data = {**_valid_raw_data(), "beneficiaryType": ["farmer", "women", "SC/ST"]}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert "farmer" in result.beneficiary_type
        assert "women" in result.beneficiary_type

    def test_tags_list_joined(self):
        raw_data = {**_valid_raw_data(), "tags": ["agriculture", "central"]}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert "agriculture" in result.tags

    def test_missing_name_returns_none(self):
        raw_data = {**_valid_raw_data(), "schemeName": "", "name": ""}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is None

    def test_missing_department_returns_none(self):
        raw_data = {**_valid_raw_data(), "department": ""}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is None

    def test_coverage_type_inferred_central(self):
        raw_data = {**_valid_raw_data(), "schemeLevel": "Central", "state": "All States"}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.coverage_type == "central"

    def test_coverage_type_inferred_state(self):
        raw_data = {**_valid_raw_data(), "state": "Telangana"}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.coverage_type == "state"

    def test_geo_scope_inferred_national(self):
        raw_data = {**_valid_raw_data(), "state": "All States"}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.geo_scope == "national"

    def test_eligibility_preserved_as_notes(self):
        elig = "Must be a small farmer with less than 2 hectares of land."
        raw_data = {**_valid_raw_data(), "eligibilityCriteria": elig}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.eligibility_notes == elig
        # structured_criteria must be empty — we do NOT parse it automatically
        assert result.structured_criteria == []

    def test_documents_joined_as_text(self):
        raw_data = {**_valid_raw_data(), "documents": ["Aadhaar", "Land Records"]}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert "Aadhaar" in result.documents_required
        assert "Land Records" in result.documents_required

    def test_source_and_external_id_preserved(self):
        raw = _raw(external_id="myid-999")
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.external_id == "myid-999"
        assert result.source == "fixture"

    def test_ministry_extracted(self):
        raw_data = {**_valid_raw_data(), "ministry": "Ministry of Finance"}
        raw = _raw(data=raw_data)
        result = normalizer.normalize(raw)
        assert result is not None
        assert result.ministry == "Ministry of Finance"


# ---------------------------------------------------------------------------
# B. Validator
# ---------------------------------------------------------------------------

class TestValidator:
    def test_valid_record_has_no_errors(self):
        n = _valid_normalized()
        errors = validator.validate(n)
        assert errors == []

    def test_missing_name_returns_error(self):
        n = _valid_normalized()
        n.name = ""
        errors = validator.validate(n)
        assert any("name" in e for e in errors)

    def test_missing_department_returns_error(self):
        n = _valid_normalized()
        n.department = ""
        errors = validator.validate(n)
        assert any("department" in e for e in errors)

    def test_name_too_long_returns_error(self):
        n = _valid_normalized()
        n.name = "A" * 256
        errors = validator.validate(n)
        assert any("name" in e for e in errors)

    def test_invalid_coverage_type_returns_error(self):
        n = _valid_normalized()
        n.coverage_type = "municipal"  # not in allowed set
        errors = validator.validate(n)
        assert any("coverage_type" in e for e in errors)

    def test_allowed_coverage_types_pass(self):
        for ct in ("central", "state", "centrally_sponsored", "ut", "unknown", None):
            n = _valid_normalized()
            n.coverage_type = ct
            errors = validator.validate(n)
            ct_errors = [e for e in errors if "coverage_type" in e]
            assert ct_errors == [], f"coverage_type={ct!r} should be valid"

    def test_invalid_geo_scope_returns_error(self):
        n = _valid_normalized()
        n.geo_scope = "city"
        errors = validator.validate(n)
        assert any("geo_scope" in e for e in errors)

    def test_bad_url_format_returns_error(self):
        n = _valid_normalized()
        n.official_website = "not-a-url"
        errors = validator.validate(n)
        assert any("official_website" in e for e in errors)

    def test_none_url_is_valid(self):
        n = _valid_normalized()
        n.official_website = None
        errors = validator.validate(n)
        url_errors = [e for e in errors if "official_website" in e]
        assert url_errors == []

    def test_missing_external_id_returns_error(self):
        n = _valid_normalized()
        n.external_id = ""
        errors = validator.validate(n)
        assert any("external_id" in e for e in errors)

    def test_multiple_errors_all_returned(self):
        n = _valid_normalized()
        n.name = ""
        n.department = ""
        errors = validator.validate(n)
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# C. Deduplicator
# ---------------------------------------------------------------------------

class TestDeduplicator:
    def test_new_record_when_not_in_db(self, db_session):
        n = _valid_normalized(external_id="new-001")
        result, existing = dedup_check(n, db_session, set())
        assert result == DedupResult.NEW
        assert existing is None

    def test_duplicate_when_already_seen_in_batch(self, db_session):
        n = _valid_normalized(external_id="dup-001")
        seen = {"fixture:dup-001"}
        result, existing = dedup_check(n, db_session, seen)
        assert result == DedupResult.DUPLICATE
        assert existing is None

    def test_existing_unchanged_record_detected(self, db_session):
        from app.models.scheme import GovernmentScheme
        row = GovernmentScheme(
            name="Existing Scheme",
            short_description="Short description.",
            detailed_description="Detailed description.",
            department="Test Department",
            state="Telangana",
            scheme_type="Financial Assistance",
            benefits="Test benefits.",
            application_process="Apply at local office.",
            official_website="https://example.gov.in",
            source="fixture",
            external_id="existing-001",
            source_url="https://example.gov.in",
            ministry="Ministry of Agriculture",
            beneficiary_type="farmer",
            coverage_type="state",
            geo_scope="state",
            tags="agriculture",
            is_active=True,
        )
        db_session.add(row)
        db_session.commit()

        n = _valid_normalized(external_id="existing-001", name="Existing Scheme")
        n.department = "Test Department"
        n.state = "Telangana"
        n.source_url = "https://example.gov.in"
        n.ministry = "Ministry of Agriculture"
        n.beneficiary_type = "farmer"
        n.coverage_type = "state"
        n.geo_scope = "state"
        n.tags = "agriculture"
        n.official_website = "https://example.gov.in"

        result, existing = dedup_check(n, db_session, set())
        assert result == DedupResult.UNCHANGED
        assert existing is not None

    def test_existing_changed_record_detected_as_update(self, db_session):
        from app.models.scheme import GovernmentScheme
        row = GovernmentScheme(
            name="Old Name",
            short_description="Old short.",
            detailed_description="Old detail.",
            department="Old Dept",
            state="Telangana",
            scheme_type="Financial Assistance",
            benefits="Old benefits.",
            application_process="Old process.",
            source="fixture",
            external_id="update-001",
            is_active=True,
        )
        db_session.add(row)
        db_session.commit()

        n = _valid_normalized(external_id="update-001", name="New Name")
        result, existing = dedup_check(n, db_session, set())
        assert result == DedupResult.UPDATED
        assert existing is not None
        assert existing.name == "Old Name"  # row not yet updated


# ---------------------------------------------------------------------------
# D. Pipeline / dry-run
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_dry_run_does_not_commit(self, db_session):
        from app.models.scheme import GovernmentScheme

        records = [_valid_raw_data("Pipeline Test Scheme")]
        records[0]["schemeId"] = "pipeline-drydemo-001"
        client = FixtureSchemeClient.from_records(records)

        count_before = db_session.query(GovernmentScheme).filter(
            GovernmentScheme.source == "fixture"
        ).count()

        report = run_import(client=client, db=db_session, dry_run=True)

        count_after = db_session.query(GovernmentScheme).filter(
            GovernmentScheme.source == "fixture"
        ).count()

        assert count_after == count_before, "Dry-run must not persist any records"
        assert report.dry_run is True
        assert report.new == 1
        assert report.invalid == 0

    def test_live_import_inserts_record(self, db_session):
        from app.models.scheme import GovernmentScheme

        records = [_valid_raw_data("Live Import Scheme")]
        records[0]["schemeId"] = "live-import-001"
        client = FixtureSchemeClient.from_records(records)

        report = run_import(client=client, db=db_session, dry_run=False)

        assert report.new == 1
        assert report.invalid == 0
        inserted = db_session.query(GovernmentScheme).filter(
            GovernmentScheme.external_id == "live-import-001"
        ).first()
        assert inserted is not None
        assert inserted.name == "Live Import Scheme"
        assert inserted.source == "fixture"

    def test_invalid_record_counted_and_skipped(self, db_session):
        invalid_data = {
            "schemeId": "invalid-001",
            "schemeName": "",          # required — causes validation failure
            "schemeShortTitle": "x",
            "schemeDescription": "x",
            "state": "Telangana",
            "department": "Dept",
            "schemeType": "Type",
            "benefits": "b",
            "applicationProcess": "a",
        }
        client = FixtureSchemeClient.from_records([invalid_data])
        report = run_import(client=client, db=db_session, dry_run=True)

        assert report.invalid >= 1
        assert report.new == 0

    def test_second_import_of_same_data_is_unchanged(self, db_session):
        records = [_valid_raw_data("Idempotent Scheme")]
        records[0]["schemeId"] = "idempotent-001"
        client = FixtureSchemeClient.from_records(records)

        # First import
        run_import(client=client, db=db_session, dry_run=False)

        # Second import — same data
        client2 = FixtureSchemeClient.from_records(records)
        report2 = run_import(client=client2, db=db_session, dry_run=False)

        assert report2.new == 0
        assert report2.unchanged == 1
        assert report2.updated == 0

    def test_update_on_changed_field(self, db_session):
        records = [_valid_raw_data("Update Test Scheme")]
        records[0]["schemeId"] = "update-test-001"
        client = FixtureSchemeClient.from_records(records)
        run_import(client=client, db=db_session, dry_run=False)

        # Change the name
        updated_records = [_valid_raw_data("Update Test Scheme CHANGED")]
        updated_records[0]["schemeId"] = "update-test-001"
        client2 = FixtureSchemeClient.from_records(updated_records)
        report2 = run_import(client=client2, db=db_session, dry_run=False)

        assert report2.updated == 1
        assert report2.new == 0

    def test_duplicate_in_batch_counted(self, db_session):
        record = _valid_raw_data("Dup Batch Scheme")
        record["schemeId"] = "dup-batch-001"
        client = FixtureSchemeClient.from_records([record, record])  # same record twice

        report = run_import(client=client, db=db_session, dry_run=True)
        assert report.duplicates == 1
        assert report.new == 1

    def test_source_fetch_error_produces_report_with_error(self, db_session):
        client = MySchemeClient()
        report = run_import(client=client, db=db_session, dry_run=True)

        assert report.fetched == 0
        assert len(report.errors) >= 1
        assert "myScheme" in report.errors[0] or "registration" in report.errors[0].lower()

    def test_sample_fixture_file_dry_run(self, db_session, tmp_path):
        """Run a dry-run against the actual sample_fixture.json."""
        import json
        from pathlib import Path

        fixture_path = Path(__file__).parent.parent.parent / "data" / "schemes" / "sample_fixture.json"
        if not fixture_path.exists():
            pytest.skip("sample_fixture.json not found")

        client = FixtureSchemeClient(fixture_path=fixture_path)
        report = run_import(client=client, db=db_session, dry_run=True)

        # 3 valid + 1 invalid expected in sample fixture
        assert report.fetched == 4
        assert report.valid == 3
        assert report.invalid == 1
        assert report.new == 3
        assert report.dry_run is True

    def test_dry_run_produces_complete_report(self, db_session):
        records = [_valid_raw_data(f"Report Scheme {i}") for i in range(3)]
        for i, r in enumerate(records):
            r["schemeId"] = f"report-{i:03d}"
        client = FixtureSchemeClient.from_records(records)

        report = run_import(client=client, db=db_session, dry_run=True)

        text = report.to_text()
        assert "Source:" in text
        assert "Dry run:" in text
        assert "Fetched:" in text
        assert "Valid:" in text
        assert "New:" in text


# ---------------------------------------------------------------------------
# E. Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_insert_creates_row(self, db_session):
        from app.importers.persistence import insert
        from app.models.scheme import GovernmentScheme

        n = _valid_normalized(external_id="persist-001")
        insert(n, db_session)
        db_session.flush()

        row = db_session.query(GovernmentScheme).filter(
            GovernmentScheme.external_id == "persist-001"
        ).first()
        assert row is not None
        assert row.name == "Test Scheme"
        assert row.source == "fixture"
        assert row.is_active is True

    def test_insert_sets_last_verified_at(self, db_session):
        from app.importers.persistence import insert

        n = _valid_normalized(external_id="persist-002")
        row = insert(n, db_session)
        db_session.flush()
        assert row.last_verified_at is not None

    def test_update_modifies_fields(self, db_session):
        from app.importers.persistence import insert, update
        from app.models.scheme import GovernmentScheme

        n = _valid_normalized(external_id="persist-003")
        row = insert(n, db_session)
        db_session.flush()

        n.name = "Updated Name"
        update(row, n, db_session)
        db_session.flush()

        updated = db_session.query(GovernmentScheme).filter(
            GovernmentScheme.external_id == "persist-003"
        ).first()
        assert updated.name == "Updated Name"

    def test_update_does_not_change_is_active(self, db_session):
        from app.importers.persistence import insert, update

        n = _valid_normalized(external_id="persist-004")
        row = insert(n, db_session)
        db_session.flush()

        n.is_active = False  # should be ignored
        update(row, n, db_session)
        db_session.flush()

        # is_active must not be in _UPDATE_FIELDS
        assert row.is_active is True


# ---------------------------------------------------------------------------
# F. Source client
# ---------------------------------------------------------------------------

class TestSourceClient:
    def test_fixture_client_from_records(self):
        records = [_valid_raw_data("FC Test")]
        records[0]["schemeId"] = "fc-001"
        client = FixtureSchemeClient.from_records(records)
        fetched = list(client.fetch())
        assert len(fetched) == 1
        assert fetched[0].external_id == "fc-001"
        assert fetched[0].source == "fixture"

    def test_fixture_client_skips_record_without_scheme_id(self):
        records = [{"schemeName": "No ID", "department": "D", "benefits": "B", "applicationProcess": "A"}]
        client = FixtureSchemeClient.from_records(records)
        fetched = list(client.fetch())
        assert len(fetched) == 0

    def test_myscheme_client_raises_source_error(self):
        client = MySchemeClient()
        with pytest.raises(SchemeSourceError):
            list(client.fetch())

    def test_myscheme_error_mentions_registration(self):
        client = MySchemeClient()
        try:
            list(client.fetch())
        except SchemeSourceError as exc:
            assert "registration" in str(exc).lower() or "apisetu" in str(exc).lower()

    def test_fixture_client_nonexistent_file_raises(self, tmp_path):
        from pathlib import Path
        client = FixtureSchemeClient(fixture_path=tmp_path / "nonexistent.json")
        with pytest.raises(SchemeSourceError):
            list(client.fetch())

    def test_fixture_client_invalid_json_raises(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        client = FixtureSchemeClient(fixture_path=bad_file)
        with pytest.raises(SchemeSourceError):
            list(client.fetch())

    def test_fixture_client_non_array_json_raises(self, tmp_path):
        bad_file = tmp_path / "object.json"
        bad_file.write_text('{"key": "value"}')
        client = FixtureSchemeClient(fixture_path=bad_file)
        with pytest.raises(SchemeSourceError):
            list(client.fetch())


# ---------------------------------------------------------------------------
# G. ImportReport
# ---------------------------------------------------------------------------

class TestImportReport:
    def test_report_to_text_contains_all_fields(self):
        from app.importers.models import ImportReport
        report = ImportReport(source="fixture", dry_run=True)
        report.fetched = 10
        report.valid = 8
        report.invalid = 2
        report.new = 5
        report.updated = 2
        report.unchanged = 1
        report.duplicates = 0
        report.finish()
        text = report.to_text()

        for expected in ("fixture", "True", "10", "8", "2", "5"):
            assert expected in text

    def test_report_errors_shown(self):
        from app.importers.models import ImportReport
        report = ImportReport(source="fixture", dry_run=True)
        report.errors = ["Error 1", "Error 2"]
        report.finish()
        text = report.to_text()
        assert "Error 1" in text
        assert "Error 2" in text
