from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from three_maps.domain.types import (
    Analysis,
    AnalysisStatus,
    ApplicabilityState,
    Axis,
    AxisDirectionState,
    AxisResult,
    AxisStatus,
    EvidenceCluster,
    FusionResult,
    InputSnapshot,
    Signal,
    SystemScore,
    SystemScoreStatus,
    Target,
    VersionBundle,
)


VB = VersionBundle(
    methodology_version="MV-1.0.0",
    ontology_version="OV-1.0.0",
    calculation_version="CV-1.0.0",
    explanation_version="EV-1.0.0",
    presentation_version="PV-1.0.0",
)


def test_version_bundle_and_immutable_input_snapshot_contract():
    snapshot = InputSnapshot(
        id="INP-001",
        analysis_id="ANL-001",
        data={"birth_date": "1990-01-01"},
        created_at=datetime.now(timezone.utc),
        version_bundle=VB,
    )
    assert snapshot.immutable is True
    assert snapshot.version_bundle.methodology_version == "MV-1.0.0"


def test_signal_preserves_evidence_clusters_and_version_lineage_fields():
    signal = Signal(
        id="SIG-001",
        source_system="NUMEROLOGY",
        source_variable="LIFE_PATH",
        theme_id="TH-001",
        axis_id="A01",
        pole_id="P-A01-A",
        strength=4,
        confidence=0.9,
        relevance=1.0,
        applicability=ApplicabilityState.CORE,
        activation="ACTIVE",
        evidence_ids=["RAW-001"],
        evidence_cluster_ids=["EC-001"],
        methodology_version="MV-1.0.0",
        calculation_version="CV-1.0.0",
    )
    assert signal.evidence_cluster_ids == ["EC-001"]
    assert signal.strength == 4


def test_system_score_status_requires_numeric_score_only_when_present():
    evaluated = SystemScore(
        system="ASTROLOGY",
        score=0.75,
        status=SystemScoreStatus.EVALUATED,
        coverage=1.0,
        data_confidence=0.9,
        valid_indicator_count=10,
        expected_indicator_count=10,
    )
    unavailable = SystemScore(
        system="PALMISTRY",
        score=None,
        status=SystemScoreStatus.UNAVAILABLE,
        coverage=0.0,
        data_confidence=0.0,
        valid_indicator_count=0,
        expected_indicator_count=10,
    )
    assert evaluated.score == 0.75
    assert unavailable.score is None


def test_axis_result_distinguishes_direction_from_dual_pole_support():
    result = AxisResult(
        axis_id="A01",
        pole_a_strength=0.70,
        pole_b_strength=0.68,
        direction_state=AxisDirectionState.MEANINGFUL_TIE,
        dual_pole_support=True,
        directional_agreement="FULL",
        coverage=1.0,
        confidence=0.9,
        status=AxisStatus.EVALUATED,
    )
    assert result.dual_pole_support is True
    assert result.direction_state == AxisDirectionState.MEANINGFUL_TIE


def test_axis_strength_range_is_enforced():
    with pytest.raises(ValidationError):
        AxisResult(
            axis_id="A01",
            pole_a_strength=1.2,
            pole_b_strength=0.2,
            direction_state=AxisDirectionState.A_DOMINANT,
            dual_pole_support=False,
            directional_agreement="FULL",
            coverage=1.0,
            confidence=0.9,
            status=AxisStatus.EVALUATED,
        )


def test_axis_definition_preserves_pole_pair():
    axis = Axis(
        id="A01",
        name="Structure ↔ Freedom",
        pole_a_id="P-A01-A",
        pole_b_id="P-A01-B",
        ontology_version="OV-1.0.0",
    )
    assert axis.pole_a_id != axis.pole_b_id


def test_analysis_is_versioned_and_targeted():
    target = Target(theme_id="TH-001", axis_id="A01", semantic_level="AXIS")
    analysis = Analysis(
        id="ANL-001",
        status=AnalysisStatus.CREATED,
        input_snapshot_id="INP-001",
        version_bundle=VB,
        requested_maps=["ASTROLOGY", "NUMEROLOGY", "PALMISTRY"],
        target=target,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert analysis.target.axis_id == "A01"
    assert len(analysis.requested_maps) == 3
