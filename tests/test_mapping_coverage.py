import pytest

from three_maps.config.mapping_coverage import CoverageIssue, audit_mapping_coverage
from three_maps.config.mapping_registry import MappingStatus, SignalMappingRecord
from three_maps.config.ontology import DEFAULT_ONTOLOGY
from three_maps.config.ontology_catalog import OntologyCatalog, ThemeDefinition, SubThemeDefinition
from three_maps.domain.types import ApplicabilityState


def catalog(n=20):
    themes = tuple(ThemeDefinition(f"T{i:02d}", f"Theme {i}", "OV-0.1.0") for i in range(1, n+1))
    subs = tuple(
        SubThemeDefinition(f"ST{i:03d}", f"T{((i-1)//10)+1:02d}", f"Sub {i}", "Definition", "OV-0.1.0")
        for i in range(1, n*10+1)
    )
    return OntologyCatalog("OV-0.1.0", themes, subs, ())


def rec(i, system="ASTROLOGY", sub="ST001", status=MappingStatus.ACTIVE):
    return SignalMappingRecord(
        id=f"M{i}", source_system=system, source_variable=f"v{i}",
        theme_id="T01", sub_theme_id=sub, axis_id="A01", pole_id="A01-A",
        applicability=ApplicabilityState.CORE, mapping_confidence=.80,
        methodology_version="MV-0.1.0", ontology_version="OV-0.1.0",
        calculation_version="CV-0.1.0", status=status,
    )


def test_empty_catalogue_reports_unmapped():
    a = audit_mapping_coverage(catalog(), ())
    assert a.total_sub_themes == 200
    assert a.mapped_sub_themes == 0
    assert CoverageIssue.UNMAPPED_SUB_THEME in a.issues
    assert not a.complete_semantic_coverage


def test_mapping_is_not_negative_evidence():
    a = audit_mapping_coverage(catalog(), (rec(1),))
    assert "ST001" not in a.unmapped_sub_themes
    assert len(a.unmapped_sub_themes) == 199


def test_blocked_and_na_do_not_create_coverage():
    blocked = rec(1)
    blocked = SignalMappingRecord(**{**blocked.__dict__, "applicability": ApplicabilityState.BLOCKED, "status": MappingStatus.DRAFT})
    a = audit_mapping_coverage(catalog(), (blocked,))
    assert a.mapped_sub_themes == 0


def test_system_coverage_is_reported_separately():
    a = audit_mapping_coverage(catalog(), (rec(1, "ASTROLOGY"), rec(2, "NUMEROLOGY")))
    assert a.sub_themes_by_system == {"ASTROLOGY": 1, "NUMEROLOGY": 1}
    assert CoverageIssue.PARTIAL_MAP_COVERAGE in a.issues


def test_duplicate_active_mapping_is_ambiguous():
    a = audit_mapping_coverage(catalog(), (rec(1), rec(2)))
    assert CoverageIssue.AMBIGUOUS_ACTIVE_MAPPING in a.issues
    assert CoverageIssue.OVERLAPPED_ACTIVE_MAPPING in a.issues


def test_axes_and_poles_are_reported():
    a = audit_mapping_coverage(catalog(), (rec(1),))
    assert a.axes_covered == ("A01",)
    assert a.poles_covered == ("A01-A",)


def test_missing_lineage_is_flagged():
    r = rec(1)
    r = SignalMappingRecord(**{**r.__dict__, "calculation_version": ""})
    a = audit_mapping_coverage(catalog(), (r,))
    assert CoverageIssue.MISSING_LINEAGE in a.issues


def test_incomplete_catalogue_cannot_be_declared_complete():
    c = catalog(1)
    a = audit_mapping_coverage(c, (rec(1),))
    assert not a.complete_semantic_coverage
