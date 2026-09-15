"""Coverage and completeness auditing for THE THREE MAPS mappings.

This module audits the explicit mapping registry. It never infers missing
mappings and never treats absence as negative evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from three_maps.config.mapping_registry import SignalMappingRecord, MappingStatus
from three_maps.config.ontology_catalog import OntologyCatalog
from three_maps.domain.types import ApplicabilityState


class CoverageIssue(str, Enum):
    UNMAPPED_SUB_THEME = "UNMAPPED_SUB_THEME"
    PARTIAL_MAP_COVERAGE = "PARTIAL_MAP_COVERAGE"
    OVERLAPPED_ACTIVE_MAPPING = "OVERLAPPED_ACTIVE_MAPPING"
    AMBIGUOUS_ACTIVE_MAPPING = "AMBIGUOUS_ACTIVE_MAPPING"
    INVALID_ACTIVE_MAPPING = "INVALID_ACTIVE_MAPPING"
    MISSING_LINEAGE = "MISSING_LINEAGE"
    FALSE_COVERAGE = "FALSE_COVERAGE"


@dataclass(frozen=True)
class CoverageAudit:
    ontology_version: str
    total_themes: int
    total_sub_themes: int
    mapped_sub_themes: int
    unmapped_sub_themes: tuple[str, ...]
    mapping_count: int
    active_mapping_count: int
    mappings_by_system: dict[str, int]
    sub_themes_by_system: dict[str, int]
    axes_covered: tuple[str, ...]
    poles_covered: tuple[str, ...]
    issues: tuple[CoverageIssue, ...]
    issue_details: tuple[str, ...]
    complete_semantic_coverage: bool

    @property
    def sub_theme_coverage_ratio(self) -> float:
        return self.mapped_sub_themes / self.total_sub_themes if self.total_sub_themes else 0.0


def audit_mapping_coverage(
    catalog: OntologyCatalog,
    records: tuple[SignalMappingRecord, ...],
    *,
    expected_systems: tuple[str, ...] = ("ASTROLOGY", "NUMEROLOGY", "PALMISTRY"),
) -> CoverageAudit:
    """Audit explicit mapping coverage without fabricating semantic coverage.

    A sub-theme is considered *mapped* when it has at least one non-blocked,
    non-N/A ACTIVE mapping. Coverage is not interpreted as evidence strength.
    """
    issues: list[CoverageIssue] = []
    details: list[str] = []
    subs = {s.id for s in catalog.sub_themes}
    active = [r for r in records if r.status == MappingStatus.ACTIVE]
    usable = [r for r in active if r.applicability not in {ApplicabilityState.BLOCKED, ApplicabilityState.NOT_APPLICABLE}]

    mapped_subs = {r.sub_theme_id for r in usable if r.sub_theme_id is not None}
    unmapped = tuple(sorted(subs - mapped_subs))
    if unmapped:
        issues.append(CoverageIssue.UNMAPPED_SUB_THEME)
        details.append(f"{len(unmapped)} sub-themes have no usable active mapping.")

    by_system: dict[str, int] = defaultdict(int)
    subs_by_system: dict[str, set[str]] = defaultdict(set)
    pair_system: dict[tuple[str, str], list[SignalMappingRecord]] = defaultdict(list)
    for r in usable:
        by_system[r.source_system] += 1
        if r.sub_theme_id:
            subs_by_system[r.source_system].add(r.sub_theme_id)
            pair_system[(r.source_system, r.sub_theme_id)].append(r)
        if not r.methodology_version or not r.ontology_version or not r.calculation_version:
            issues.append(CoverageIssue.MISSING_LINEAGE)
            details.append(f"Mapping {r.id} has incomplete version lineage.")

    for system in expected_systems:
        if not subs_by_system.get(system):
            issues.append(CoverageIssue.PARTIAL_MAP_COVERAGE)
            details.append(f"{system} has no usable active sub-theme mappings.")

    for key, matches in pair_system.items():
        if len(matches) > 1:
            issues.append(CoverageIssue.OVERLAPPED_ACTIVE_MAPPING)
            issues.append(CoverageIssue.AMBIGUOUS_ACTIVE_MAPPING)
            details.append(f"{key[0]}:{key[1]} has {len(matches)} active mappings; coverage is ambiguous.")

    axes = tuple(sorted({r.axis_id for r in usable}))
    poles = tuple(sorted({r.pole_id for r in usable}))
    complete = bool(catalog.is_complete and not unmapped and not any(
        issue in {CoverageIssue.AMBIGUOUS_ACTIVE_MAPPING, CoverageIssue.MISSING_LINEAGE, CoverageIssue.FALSE_COVERAGE}
        for issue in issues
    ))

    return CoverageAudit(
        ontology_version=catalog.ontology_version,
        total_themes=len(catalog.themes),
        total_sub_themes=len(catalog.sub_themes),
        mapped_sub_themes=len(mapped_subs),
        unmapped_sub_themes=unmapped,
        mapping_count=len(records),
        active_mapping_count=len(active),
        mappings_by_system=dict(sorted(by_system.items())),
        sub_themes_by_system={k: len(v) for k, v in sorted(subs_by_system.items())},
        axes_covered=axes,
        poles_covered=poles,
        issues=tuple(dict.fromkeys(issues)),
        issue_details=tuple(details),
        complete_semantic_coverage=complete,
    )
