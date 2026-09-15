import importlib
from pathlib import Path


def test_all_runtime_modules_import():
    modules = [
        'three_maps.domain.types',
        'three_maps.config.ontology', 'three_maps.config.thresholds',
        'three_maps.config.golden_dataset', 'three_maps.persistence',
        'three_maps.api.app', 'three_maps.api.security',
        'three_maps.engines.activation', 'three_maps.engines.applicability',
        'three_maps.engines.astrology', 'three_maps.engines.axis',
        'three_maps.engines.contradiction', 'three_maps.engines.evidence',
        'three_maps.engines.explanation', 'three_maps.engines.fusion',
        'three_maps.engines.integration', 'three_maps.engines.lineage',
        'three_maps.engines.numerology', 'three_maps.engines.palmistry',
        'three_maps.engines.pole', 'three_maps.engines.relationship',
        'three_maps.engines.status', 'three_maps.engines.system_score',
    ]
    for module in modules:
        assert importlib.import_module(module) is not None


def test_golden_dataset_is_present_and_canonical():
    import json
    p = Path(__file__).parents[1] / 'config' / 'golden_dataset.json'
    data = json.loads(p.read_text())
    assert data['dataset_id'] == 'GDS-001'
    assert data['version'] == 'GD-0.2.0'
    assert len(data['cases']) == 45


def test_required_release_artifacts_present():
    root = Path(__file__).parents[1]
    for name in ['README.md', 'pyproject.toml', '201.80A_ARCHITECTURE_AUDIT.md',
                 '201.80B_METHODOLOGY_CODE_AUDIT.md', '201.80C_CONFORMANCE_REMEDIATION.md',
                 '201.80E_ADVERSARIAL_TESTING.md', '201.80F_THRESHOLD_CALIBRATION.md',
                 '201.80G_GOLDEN_DATASET.md', '201.80H_SECURITY_PRIVACY_REVIEW.md',
                 '201.80K_UI_UX_REFINEMENT.md']:
        assert (root / name).is_file(), name
