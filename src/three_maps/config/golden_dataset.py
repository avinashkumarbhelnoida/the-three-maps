"""Canonical Golden Dataset registry for THE THREE MAPS."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

DATASET_PATH = Path(__file__).with_name("golden_dataset.json")

def load_golden_dataset() -> dict[str, Any]:
    with DATASET_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def golden_cases() -> tuple[dict[str, Any], ...]:
    return tuple(load_golden_dataset()["cases"])

def validate_golden_dataset(dataset: dict[str, Any]) -> None:
    assert dataset["dataset_id"] == "GDS-001"
    assert dataset["version"]
    cases = dataset["cases"]
    assert len(cases) >= 20
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    required_categories = {"relationship", "contradiction", "axis", "system_score", "fusion"}
    assert required_categories.issubset({c["category"] for c in cases})
    for case in cases:
        assert case["id"] and case["name"] and isinstance(case["expected"], dict)
