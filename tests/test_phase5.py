import json
from pathlib import Path

from three_maps.config.release import FREEZE_ID, RELEASE, validate_release, write_manifest


def test_architecture_freeze_contract_is_explicit():
    report = validate_release()
    assert report.release == RELEASE
    assert report.freeze_id == FREEZE_ID
    assert report.passed is False  # semantic/deployment gates remain intentionally explicit
    assert {g.gate_id for g in report.blockers} >= {"ONT", "IDP", "TLS", "DB", "SECRETS", "PALM"}


def test_v1_manifest_is_reproducible_and_marks_core_release_not_production(tmp_path):
    p = write_manifest(tmp_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["release"] == "1.0.0"
    assert data["phase"] == "PHASE_V_COMPLETE"
    assert data["software_core_releaseable"] is True
    assert data["unrestricted_production_ready"] is False
    assert data["golden_dataset"]["cases"] >= 40
    assert data["source_tree_sha256"]
