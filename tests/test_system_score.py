from three_maps.domain.types import (
    ActivationState, ApplicabilityState, IndicatorWeightClass, Signal, SystemScoreStatus,
)
from three_maps.engines.system_score import (
    SystemScoreIndicator, SystemScoreInput, calculate_system_score, count_valid_systems,
)


def sig(id_, strength=4, confidence=1.0, relevance=1.0, weight=IndicatorWeightClass.STANDARD):
    return Signal(
        id=id_, source_system="NUMEROLOGY", source_variable="LIFE_PATH",
        evidence_ids=[f"RAW-{id_}"], evidence_cluster_ids=[f"EC-{id_}"],
        theme_id="TH-001", axis_id="A01", pole_id="P-A01-A", strength=strength,
        confidence=confidence, relevance=relevance, weight_class=weight,
        applicability=ApplicabilityState.CORE, activation=ActivationState.ACTIVE,
        methodology_version="MV-0.1.0", calculation_version="CV-0.1.0",
    )


def test_exact_formula():
    # E=(4/4)*.8*1*.5=.4; denominator=.5 => SS=.8
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (SystemScoreIndicator(sig("1", confidence=.8, relevance=1, weight=IndicatorWeightClass.MINOR)),)
    ))
    assert r.score == .8
    assert r.status == SystemScoreStatus.EVALUATED
    assert r.coverage == 1.0


def test_weight_classes():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (
            SystemScoreIndicator(sig("minor", strength=4, weight=IndicatorWeightClass.MINOR)),
            SystemScoreIndicator(sig("primary", strength=2, weight=IndicatorWeightClass.PRIMARY)),
        )
    ))
    # (0.5*1 + 1.5*0.5) / 2.0 = .625
    assert r.score == .625


def test_confidence_and_relevance_are_in_formula():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (SystemScoreIndicator(sig("1", strength=4, confidence=.5, relevance=.4)),)
    ))
    assert r.score == .5
    assert r.data_confidence == .5


def test_unavailable_is_omitted_not_zero_filled():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (
            SystemScoreIndicator(sig("valid", strength=4), available=True),
            SystemScoreIndicator(sig("missing", strength=4), available=False),
        )
    ))
    assert r.score == 1.0
    assert r.coverage == .5
    assert r.status == SystemScoreStatus.PARTIAL


def test_partial_score_is_not_multiplied_by_coverage():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (
            SystemScoreIndicator(sig("valid", strength=2), available=True),
            SystemScoreIndicator(sig("missing", strength=4), available=False),
        )
    ))
    assert r.score == .5
    assert r.coverage == .5


def test_individual_invalid_indicator_can_be_excluded():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (
            SystemScoreIndicator(sig("valid", strength=4), valid=True),
            SystemScoreIndicator(sig("bad", strength=4), valid=False),
        )
    ))
    assert r.score == 1.0
    assert r.status == SystemScoreStatus.PARTIAL


def test_status_precedence_invalid_target():
    r = calculate_system_score(SystemScoreInput("NUMEROLOGY", (), target_valid=False))
    assert r.status == SystemScoreStatus.INVALID
    assert r.score is None


def test_all_unavailable():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (SystemScoreIndicator(sig("1"), available=False),)
    ))
    assert r.status == SystemScoreStatus.UNAVAILABLE
    assert r.score is None


def test_zero_and_one_boundaries():
    zero = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (SystemScoreIndicator(sig("0", strength=0)),)
    ))
    one = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (SystemScoreIndicator(sig("1", strength=4, confidence=1, relevance=1)),)
    ))
    assert zero.score == 0
    assert one.score == 1


def test_not_expected_does_not_reduce_coverage():
    r = calculate_system_score(SystemScoreInput(
        "NUMEROLOGY", (
            SystemScoreIndicator(sig("1"), expected=True),
            SystemScoreIndicator(sig("optional"), expected=False, available=False),
        )
    ))
    assert r.coverage == 1.0
    assert r.status == SystemScoreStatus.EVALUATED


def test_k_counts_only_evaluated_and_partial():
    results = [
        calculate_system_score(SystemScoreInput("A", (SystemScoreIndicator(sig("a")),))),
        calculate_system_score(SystemScoreInput("B", (SystemScoreIndicator(sig("b"), available=False),))),
        calculate_system_score(SystemScoreInput("C", (), target_valid=False)),
    ]
    assert count_valid_systems(results) == 1
