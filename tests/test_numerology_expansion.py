from datetime import date
from three_maps.engines.numerology import (
    NumerologyMethodology, YTreatment, calculate_profile, signal_candidates,
    expression_number_configured, soul_urge_configured,
)

def test_profile_is_structured_and_interpretation_free():
    r = calculate_profile(date(1990,1,20), "JOHN DOE", at=date(2026,9,13))
    assert r.life_path.reduced_value == 22
    assert r.expression.reduced_value == 8
    assert r.personal_year is not None
    assert r.calculation_version == "CV-0.1.1"
    assert all(p.methodology_version == r.methodology_version for p in r.patterns)

def test_y_policy_is_versioned_and_changes_name_derived_numbers():
    consonant = NumerologyMethodology(y_treatment=YTreatment.CONSONANT)
    vowel = NumerologyMethodology(y_treatment=YTreatment.VOWEL)
    assert expression_number_configured("Y", consonant).raw_value == 7
    assert expression_number_configured("Y", vowel).raw_value == 7
    assert soul_urge_configured("Y", vowel).raw_value == 7

def test_signal_candidates_preserve_source_scope_and_lineage_keys():
    r = calculate_profile(date(1990,1,20), "JOHN DOE", at=date(2026,9,13))
    cs = signal_candidates(r)
    assert cs
    assert {c.source_scope for c in cs} >= {"BIRTH_DERIVED", "NAME_DERIVED", "CYCLE_DERIVED"}
    assert all(c.calculation_version == r.calculation_version for c in cs)

def test_repeated_values_are_pattern_clusters_not_extra_evidence():
    r = calculate_profile(date(1990,1,20), "JOHN DOE", at=date(2026,9,13))
    repeated = [p for p in r.patterns if p.pattern_type == "REPEATED_REDUCED_VALUE"]
    assert all(p.occurrence_count >= 2 for p in repeated)
