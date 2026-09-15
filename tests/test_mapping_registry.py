import pytest

from three_maps.config.mapping_registry import MappingStatus, SignalMappingRecord, SignalMappingRegistry
from three_maps.config.ontology import DEFAULT_ONTOLOGY
from three_maps.domain.types import ApplicabilityState


def rec(**overrides):
    data = dict(
        id="MAP-001", source_system="NUMEROLOGY", source_variable="life_path",
        theme_id="T-01", sub_theme_id="ST-01", axis_id="A01", pole_id="A01-A",
        applicability=ApplicabilityState.CORE, mapping_confidence=.75,
        methodology_version="MV-0.1.0", ontology_version="OV-0.1.0",
        calculation_version="CV-0.1.0", status=MappingStatus.ACTIVE,
    )
    data.update(overrides)
    return SignalMappingRecord(**data)


def test_valid_explicit_mapping():
    r = SignalMappingRegistry(records=(rec(),))
    assert r.get("MAP-001").pole_id == "A01-A"
    assert r.active_for("NUMEROLOGY", "life_path")[0].id == "MAP-001"


def test_unknown_axis_rejected():
    with pytest.raises(ValueError, match="unknown axis"):
        SignalMappingRegistry(records=(rec(axis_id="A99", pole_id="A01-A"),))


def test_pole_axis_mismatch_rejected():
    with pytest.raises(ValueError, match="does not belong"):
        SignalMappingRegistry(records=(rec(pole_id="A02-A"),))


def test_core_confidence_gate():
    with pytest.raises(ValueError, match="CORE"):
        SignalMappingRegistry(records=(rec(mapping_confidence=.74),))


def test_contextual_mapping_requires_context_rule():
    with pytest.raises(ValueError, match="context_rule"):
        SignalMappingRegistry(records=(rec(applicability=ApplicabilityState.CONTEXTUAL, mapping_confidence=.85),))


def test_blocked_mapping_cannot_be_active():
    with pytest.raises(ValueError, match="cannot be ACTIVE"):
        SignalMappingRegistry(records=(rec(applicability=ApplicabilityState.BLOCKED),))


def test_version_mismatch_rejected():
    with pytest.raises(ValueError, match="version mismatch"):
        SignalMappingRegistry(records=(rec(ontology_version="OV-9.9.9"),))


def test_multiple_active_mappings_are_not_silently_resolved():
    r = SignalMappingRegistry(records=(rec(), rec(id="MAP-002", pole_id="A01-B")))
    with pytest.raises(ValueError, match="exactly one"):
        r.require_unique_active_mapping("NUMEROLOGY", "life_path")
