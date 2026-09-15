from three_maps.config.golden_dataset import load_golden_dataset, golden_cases, validate_golden_dataset

def test_golden_dataset_schema():
    dataset = load_golden_dataset()
    validate_golden_dataset(dataset)

def test_golden_dataset_has_25_cases():
    assert len(golden_cases()) == 45

def test_golden_dataset_canonical_fusion_case():
    case = next(c for c in golden_cases() if c["id"] == "G-020")
    expected = case["expected"]
    assert expected["base"] == 0.68281914
    assert expected["final_score"] == 77.35
    assert expected["label"] == "HIGH"

def test_golden_dataset_covers_s0_to_s5_and_s6_s7():
    cases = golden_cases()
    states = {c["expected"].get("relationship") for c in cases}
    contradictions = {c["expected"].get("contradiction") for c in cases}
    assert {"S0","S1","S2","S3","S4","S5"}.issubset(states)
    assert {"S6","S7"}.issubset(contradictions)

def test_golden_dataset_missing_evidence_is_not_zero():
    case = next(c for c in golden_cases() if c["id"] == "G-018")
    assert case["expected"]["status"] == "UNAVAILABLE"
    assert case["expected"]["numeric_score"] is False
    assert case["expected"]["excluded_from_k"] is True
