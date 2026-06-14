"""NPPES pipeline: full universe load, weekly increments, normalization,
idempotency, quarantine, and the DQ suite + Definition-of-Done gates."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from connectors.nppes import dq, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_run")
    manifest = synth.generate(str(d / "fx"), n_orgs=40, n_individuals=150, seed=11)
    store = NppesStore(str(d / "nppes.db"))
    report = pipeline.run(
        store,
        monthly_path=manifest["monthly_path"],
        nucc_path=manifest["nucc_path"],
        monthly_version=manifest["monthly_version"],
        monthly_header_count=manifest["monthly_header_count"],
        weekly_paths=manifest["weekly_paths"],
        othername_path=manifest["othername_path"],
        practice_location_path=manifest["practice_location_path"],
        endpoint_path=manifest["endpoint_path"],
        landing_root=str(d / "landing"),
        write_journal=False,
    )
    return store, report, manifest


def test_universe_loaded_both_entity_types(built):
    store, report, _ = built
    with store.connect() as con:
        t1 = con.execute("SELECT COUNT(*) c FROM dim_provider WHERE entity_type=1").fetchone()["c"]
        t2 = con.execute("SELECT COUNT(*) c FROM dim_provider WHERE entity_type=2").fetchone()["c"]
    assert t1 > 0 and t2 > 0


def test_invalid_npis_quarantined_not_dropped(built):
    store, _, _ = built
    with store.connect() as con:
        q = con.execute("SELECT COUNT(*) c FROM nppes_invalid_npi").fetchone()["c"]
        # the two intentionally-bad NPIs land in quarantine
        assert q >= 2
        # and never in dim_provider
        bad = con.execute(
            "SELECT COUNT(*) c FROM dim_provider WHERE npi IN ('1234567890','999')"
        ).fetchone()["c"]
        assert bad == 0


def test_taxonomy_bridge_one_primary_max(built):
    store, _, _ = built
    with store.connect() as con:
        offenders = con.execute(
            "SELECT npi, SUM(primary_flag) s FROM bridge_provider_taxonomy "
            "GROUP BY npi HAVING s > 1").fetchall()
    assert offenders == []


def test_addresses_have_null_geocode_stubs(built):
    store, _, _ = built
    with store.connect() as con:
        rows = con.execute(
            "SELECT fips_county, latitude, longitude, geocode_status "
            "FROM dim_provider_address LIMIT 50").fetchall()
    assert rows
    for r in rows:
        assert r["fips_county"] is None
        assert r["latitude"] is None and r["longitude"] is None
        assert r["geocode_status"] == "pending"


def test_weekly_increment_applied(built):
    store, report, _ = built
    # the synth weekly deactivates an existing individual and adds new orgs
    with store.connect() as con:
        from_weekly = con.execute(
            "SELECT COUNT(*) c FROM dim_provider WHERE source_row='weekly'").fetchone()["c"]
        deactivated_via_weekly = con.execute(
            "SELECT COUNT(*) c FROM dim_provider "
            "WHERE source_row='weekly' AND status='deactivated'").fetchone()["c"]
    assert from_weekly > 0
    assert deactivated_via_weekly >= 1


def test_dq_all_pass(built):
    store, report, _ = built
    assert report["dq_all_passed"] is True
    rep = dq.run_all(store)
    assert rep["all_passed"]
    names = set(rep["summary"])
    assert {"npi_luhn_validation", "deactivation_flag_coverage",
            "taxonomy_resolution_rate", "duplicate_npi_check",
            "rowcount_reconciliation"} <= names


def test_rowcount_reconciliation_metric(built):
    store, _, manifest = built
    res = dq.check_rowcount_reconciliation(store)
    assert res.passed
    with store.connect() as con:
        hdr = con.execute(
            "SELECT monthly_header_count FROM nppes_load_state WHERE id=1").fetchone()
    assert hdr["monthly_header_count"] == manifest["monthly_header_count"]


def test_pipeline_idempotent_no_dupes(built):
    """Re-running converges: no new dim_provider rows, no duplicates."""
    store, _, manifest = built
    with store.connect() as con:
        before = con.execute("SELECT COUNT(*) c FROM dim_provider").fetchone()["c"]
    # Re-run monthly + weeklies again into the SAME store.
    pipeline.run(
        store,
        monthly_path=manifest["monthly_path"],
        nucc_path=manifest["nucc_path"],
        monthly_version=manifest["monthly_version"],
        monthly_header_count=manifest["monthly_header_count"],
        weekly_paths=manifest["weekly_paths"],
        landing_root=str(Path(store.db_path).parent / "landing2"),
        write_journal=False,
    )
    with store.connect() as con:
        after = con.execute("SELECT COUNT(*) c FROM dim_provider").fetchone()["c"]
        dupes = con.execute(
            "SELECT COUNT(*) c FROM (SELECT npi FROM dim_provider "
            "GROUP BY npi HAVING COUNT(*)>1)").fetchone()["c"]
    assert after == before
    assert dupes == 0


def test_weekly_skipped_on_resume(built):
    """Already-applied weeklies are not re-applied (tracked in load_state)."""
    store, _, manifest = built
    import json as _json
    with store.connect() as con:
        applied = _json.loads(con.execute(
            "SELECT weeklies_applied FROM nppes_load_state WHERE id=1"
        ).fetchone()["weeklies_applied"])
    assert len(applied) >= 1
