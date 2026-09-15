"""Versioned signal-mapping registry for THE THREE MAPS.

Mappings are explicit configuration, never inferred by engines.  The registry
validates source identity, ontology references, applicability, confidence and
version lineage.  It deliberately does not invent Theme/Sub-Theme mappings.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from three_maps.config.ontology import OntologyRegistry, DEFAULT_ONTOLOGY
from three_maps.domain.types import ApplicabilityState


class MappingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    DEPRECATED = "DEPRECATED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SignalMappingRecord:
    id: str
    source_system: str
    source_variable: str
    theme_id: str
    sub_theme_id: str | None
    axis_id: str
    pole_id: str
    applicability: ApplicabilityState
    mapping_confidence: float
    methodology_version: str
    ontology_version: str
    calculation_version: str
    context_rule: str | None = None
    temporal_rule: str | None = None
    status: MappingStatus = MappingStatus.DRAFT


class SignalMappingRegistry:
    """Read-only, versioned registry of explicit source→ontology mappings."""

    def __init__(
        self,
        ontology: OntologyRegistry = DEFAULT_ONTOLOGY,
        records: tuple[SignalMappingRecord, ...] = (),
    ) -> None:
        self.ontology = ontology
        self._records = {r.id: r for r in records}
        self._validate()

    def _validate(self) -> None:
        if len(self._records) != len(tuple(self._records.values())):
            raise ValueError("Mapping IDs must be unique.")
        for r in self._records.values():
            if not r.source_system or not r.source_variable:
                raise ValueError(f"Mapping {r.id}: source identity is required.")
            if not self.ontology.has_axis(r.axis_id):
                raise ValueError(f"Mapping {r.id}: unknown axis {r.axis_id}.")
            if not self.ontology.has_pole(r.pole_id):
                raise ValueError(f"Mapping {r.id}: unknown pole {r.pole_id}.")
            if self.ontology.axis_for_pole(r.pole_id).id != r.axis_id:
                raise ValueError(f"Mapping {r.id}: pole does not belong to axis.")
            if not 0 <= r.mapping_confidence <= 1:
                raise ValueError(f"Mapping {r.id}: confidence must be in [0,1].")
            if r.ontology_version != self.ontology.ontology_version:
                raise ValueError(f"Mapping {r.id}: ontology version mismatch.")
            if r.applicability == ApplicabilityState.CORE and r.mapping_confidence < .75:
                raise ValueError(f"Mapping {r.id}: CORE mapping confidence must be >= .75.")
            if r.applicability == ApplicabilityState.SECONDARY and r.mapping_confidence < .80:
                raise ValueError(f"Mapping {r.id}: SECONDARY mapping confidence must be >= .80.")
            if r.applicability == ApplicabilityState.CONTEXTUAL and r.mapping_confidence < .85:
                raise ValueError(f"Mapping {r.id}: CONTEXTUAL mapping confidence must be >= .85.")
            if r.applicability == ApplicabilityState.CONTEXTUAL and not r.context_rule:
                raise ValueError(f"Mapping {r.id}: CONTEXTUAL mapping requires context_rule.")
            if r.applicability in {ApplicabilityState.BLOCKED, ApplicabilityState.NOT_APPLICABLE} and r.status == MappingStatus.ACTIVE:
                raise ValueError(f"Mapping {r.id}: blocked/N-A mapping cannot be ACTIVE.")

    def get(self, mapping_id: str) -> SignalMappingRecord:
        return self._records[mapping_id]

    def all(self) -> tuple[SignalMappingRecord, ...]:
        return tuple(self._records[k] for k in sorted(self._records))

    def active_for(self, source_system: str, source_variable: str) -> tuple[SignalMappingRecord, ...]:
        return tuple(
            r for r in self._records.values()
            if r.status == MappingStatus.ACTIVE
            and r.source_system == source_system
            and r.source_variable == source_variable
            and r.applicability not in {ApplicabilityState.BLOCKED, ApplicabilityState.NOT_APPLICABLE}
        )

    def require_unique_active_mapping(self, source_system: str, source_variable: str) -> SignalMappingRecord:
        matches = self.active_for(source_system, source_variable)
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one active mapping for {source_system}:{source_variable}; found {len(matches)}."
            )
        return matches[0]


DEFAULT_MAPPING_REGISTRY = SignalMappingRegistry()
