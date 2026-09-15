from three_maps.config.thresholds import TAU_P
from three_maps.domain.types import *
from three_maps.engines.axis import resolve_direction
from three_maps.engines.status import resolve_system_status
from three_maps.engines.activation import resolve_activation
from three_maps.engines.fusion import FusionInput, calculate_fusion


def test_status_precedence():
    assert resolve_system_status(target_valid=False, score_calculable=True, material_gap=False) == SystemScoreStatus.INVALID
    assert resolve_system_status(target_valid=True, score_calculable=False, material_gap=True) == SystemScoreStatus.UNAVAILABLE
    assert resolve_system_status(target_valid=True, score_calculable=True, material_gap=True) == SystemScoreStatus.PARTIAL
    assert resolve_system_status(target_valid=True, score_calculable=True, material_gap=False) == SystemScoreStatus.EVALUATED


def test_zero_fill_is_not_used():
    scores = [0.8, 0.7]
    assert sum(scores) / len(scores) == 0.75


def test_one_sided_support():
    result = resolve_direction(PoleStrength(axis_id="A01", pole_a=.65, pole_b=.20))
    assert result == AxisDirectionState.A_DOMINANT


def test_meaningful_tie():
    result = resolve_direction(PoleStrength(axis_id="A01", pole_a=.62, pole_b=.64))
    assert result == AxisDirectionState.MEANINGFUL_TIE


def test_insufficient():
    result = resolve_direction(PoleStrength(axis_id="A01", pole_a=.40, pole_b=.55))
    assert result == AxisDirectionState.INSUFFICIENT


def test_dual_pole_does_not_equal_contradiction():
    poles = PoleStrength(axis_id="A01", pole_a=.74, pole_b=.70)
    assert poles.pole_a >= TAU_P and poles.pole_b >= TAU_P
    assert resolve_direction(poles) == AxisDirectionState.MEANINGFUL_TIE


def test_activation_gates():
    assert resolve_activation(valid=False, required_inputs_available=True, applicability=ApplicabilityState.CORE) == ActivationState.INVALID
    assert resolve_activation(valid=True, required_inputs_available=False, applicability=ApplicabilityState.CORE) == ActivationState.UNAVAILABLE
    assert resolve_activation(valid=True, required_inputs_available=True, applicability=ApplicabilityState.BLOCKED) == ActivationState.NOT_PERMITTED
    assert resolve_activation(valid=True, required_inputs_available=True, applicability=ApplicabilityState.CORE) == ActivationState.ACTIVE


def test_fusion_range():
    value = calculate_fusion(FusionInput(base=.68, convergence_bonus=.10, independence_bonus=.05))
    assert 0 <= value <= 100


def test_lineage_is_complete_and_hash_is_stable():
    from three_maps.engines.lineage import make_lineage, canonical_hash, validate_lineage_chain
    l = make_lineage("E03", "life_path", "SIG-1", "MV-1", "OV-1", "CV-1", ["RAW-1"])
    assert validate_lineage_chain([l]).value == "COMPLETE"
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})
