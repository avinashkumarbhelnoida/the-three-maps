from three_maps.engines.palmistry import (
    ConfirmationState, FeatureDomain, ImageQualityState, ObservationState, PalmSide,
    assess_image, compute_feature_confidence, create_candidate_feature, confirm_feature,
    signal_candidates, LineType,
)


def test_good_image_is_processable():
    a = assess_image(image_id="IMG-001", side=PalmSide.RIGHT, blur_score=.9, lighting_score=.9, framing_score=.9, obstruction_score=.9, hand_detection_confidence=.9, orientation_confidence=.9)
    assert a.quality == ImageQualityState.ACCEPTABLE
    assert a.processable is True


def test_unusable_image_is_not_processable():
    a = assess_image(image_id="IMG-002", blur_score=.1, lighting_score=.2, framing_score=.2, obstruction_score=.1, hand_detection_confidence=.9, orientation_confidence=.9)
    assert a.quality == ImageQualityState.UNUSABLE
    assert a.processable is False


def test_degraded_image_remains_processable_when_detection_is_good():
    a = assess_image(image_id="IMG-003", blur_score=.6, lighting_score=.5, framing_score=.6, obstruction_score=.5, hand_detection_confidence=.8, orientation_confidence=.8)
    assert a.quality == ImageQualityState.DEGRADED
    assert a.processable is True


def test_low_hand_detection_blocks_processing():
    a = assess_image(image_id="IMG-004", blur_score=.9, lighting_score=.9, framing_score=.9, obstruction_score=.9, hand_detection_confidence=.4, orientation_confidence=.9)
    assert a.processable is False


def test_cv_candidate_is_not_automatically_confirmed():
    f = create_candidate_feature(feature_id="LL-001", feature_type=LineType.LIFE_LINE.value, value="visible", cv_confidence=.9, observation_confidence=.7, domain=FeatureDomain.MAJOR_LINE)
    assert f.state == ObservationState.CANDIDATE
    assert f.user_confirmed is None
    assert f.feature_confidence == .7


def test_confirmation_is_explicit_and_propagates_confidence():
    f = create_candidate_feature(feature_id="LL-001", feature_type="LIFE_LINE", value="visible", cv_confidence=.9, observation_confidence=.7)
    c = confirm_feature(f, True)
    r = confirm_feature(f, False)
    assert c.state == ObservationState.CONFIRMED
    assert c.confirmation == ConfirmationState.CONFIRMED
    assert c.feature_confidence == .8
    assert r.state == ObservationState.REJECTED
    assert r.feature_confidence == 0


def test_feature_confidence_uses_strictest_upstream_confidence():
    assert compute_feature_confidence(cv_confidence=.9, observation_confidence=.8, image_quality=.7) == .7


def test_signal_candidates_require_confirmation():
    f = create_candidate_feature(feature_id="HL-001", feature_type="HEART_LINE", value={"visibility": "clear"}, cv_confidence=.9, observation_confidence=.9, domain=FeatureDomain.MAJOR_LINE, side=PalmSide.LEFT)
    assert signal_candidates([f], methodology_version="MV-0.1.0", calculation_version="CV-0.1.0") == []
    f = confirm_feature(f, True)
    out = signal_candidates([f], methodology_version="MV-0.1.0", calculation_version="CV-0.1.0")
    assert len(out) == 1
    assert out[0].source_variable == "HEART_LINE"


def test_rejected_feature_never_generates_signal():
    f = create_candidate_feature(feature_id="TH-001", feature_type="THUMB", value={"length": "long"}, cv_confidence=.9, observation_confidence=.9, domain=FeatureDomain.THUMB)
    f = confirm_feature(f, False)
    assert signal_candidates([f], methodology_version="MV-0.1.0", calculation_version="CV-0.1.0") == []
