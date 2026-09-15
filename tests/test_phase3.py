import pytest
from three_maps.config.calibration import calibrate, compare_expected
from three_maps.config.golden_dataset import load_golden_dataset, validate_golden_dataset
from three_maps.engines.phase3_adversarial import run_master_adversarial_suite
from three_maps.engines.phase3_scenarios import run_scenarios


def test_phase3_golden_dataset_has_expanded_cases_and_unique_ids():
    ds = load_golden_dataset()
    validate_golden_dataset(ds)
    assert len(ds["cases"]) >= 40
    assert len({c["id"] for c in ds["cases"]}) == len(ds["cases"])


def test_calibration_reports_all_expected_values():
    ds = load_golden_dataset()
    report = calibrate(lambda case: dict(case["expected"]))
    assert report.total == len(ds["cases"])
    assert report.failed == 0
    assert report.pass_rate == 1.0


def test_calibration_detects_regression():
    case = {"id": "X", "expected": {"score": .8}}
    result = compare_expected(case, {"score": .7})
    assert not result.passed
    assert result.mismatches


def test_master_adversarial_suite_has_zero_p0_blockers():
    report = run_master_adversarial_suite()
    assert report.blockers == 0
    assert report.failures == 0


def test_end_to_end_scenarios_all_pass():
    results = run_scenarios()
    assert len(results) >= 8
    assert all(r.passed for r in results), [r.reason for r in results if not r.passed]
