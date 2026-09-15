"""Versioned Theme/Sub-Theme catalogue boundary for THE THREE MAPS.

The catalogue is intentionally data-driven. No provisional 20-theme/200-sub-theme
labels are embedded here; an authoritative catalogue must be supplied and validated
before publication.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from three_maps.domain.types import ApplicabilityState


class MappingPermission(str, Enum):
    CORE = "CORE"
    SECONDARY = "SECONDARY"
    CONTEXTUAL = "CONTEXTUAL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ThemeDefinition:
    id: str
    name: str
    ontology_version: str


@dataclass(frozen=True)
class SubThemeDefinition:
    id: str
    theme_id: str
    name: str
    definition: str
    ontology_version: str


@dataclass(frozen=True)
class SubThemeAxisMapping:
    sub_theme_id: str
    axis_id: str
    applicability: MappingPermission
    mapping_confidence: float
    ontology_version: str
    context_rule: str | None = None
    temporal_rule: str | None = None


class OntologyCatalogError(ValueError):
    pass


class OntologyCatalog:
    """Immutable validated catalogue container.

    Publication requires exactly 20 themes and exactly 10 sub-themes per theme.
    Empty construction is permitted only as an explicit pre-publication state.
    """

    def __init__(
        self,
        ontology_version: str,
        themes: Iterable[ThemeDefinition] = (),
        sub_themes: Iterable[SubThemeDefinition] = (),
        mappings: Iterable[SubThemeAxisMapping] = (),
    ) -> None:
        self.ontology_version = ontology_version
        self._themes = tuple(themes)
        self._sub_themes = tuple(sub_themes)
        self._mappings = tuple(mappings)
        self.validate_structure(require_complete=False)

    @property
    def themes(self) -> tuple[ThemeDefinition, ...]:
        return self._themes

    @property
    def sub_themes(self) -> tuple[SubThemeDefinition, ...]:
        return self._sub_themes

    @property
    def mappings(self) -> tuple[SubThemeAxisMapping, ...]:
        return self._mappings

    @property
    def is_complete(self) -> bool:
        try:
            self.validate_structure(require_complete=True)
            return True
        except OntologyCatalogError:
            return False

    def validate_structure(self, *, require_complete: bool) -> None:
        if not self.ontology_version:
            raise OntologyCatalogError("ontology_version is required")

        theme_ids = [t.id for t in self._themes]
        sub_ids = [s.id for s in self._sub_themes]
        if len(theme_ids) != len(set(theme_ids)):
            raise OntologyCatalogError("duplicate theme IDs")
        if len(sub_ids) != len(set(sub_ids)):
            raise OntologyCatalogError("duplicate sub-theme IDs")
        if any(t.ontology_version != self.ontology_version for t in self._themes):
            raise OntologyCatalogError("theme ontology version mismatch")
        if any(s.ontology_version != self.ontology_version for s in self._sub_themes):
            raise OntologyCatalogError("sub-theme ontology version mismatch")
        if any(not s.definition.strip() for s in self._sub_themes):
            raise OntologyCatalogError("sub-theme definition cannot be empty")

        theme_set = set(theme_ids)
        counts = {tid: 0 for tid in theme_set}
        for sub in self._sub_themes:
            if sub.theme_id not in theme_set:
                raise OntologyCatalogError(f"orphan sub-theme: {sub.id}")
            counts[sub.theme_id] += 1

        if require_complete:
            if len(self._themes) != 20:
                raise OntologyCatalogError("authoritative catalogue requires exactly 20 themes")
            if len(self._sub_themes) != 200:
                raise OntologyCatalogError("authoritative catalogue requires exactly 200 sub-themes")
            if any(n != 10 for n in counts.values()):
                raise OntologyCatalogError("each theme must contain exactly 10 sub-themes")

        sub_set = set(sub_ids)
        seen_mappings: set[tuple[str, str]] = set()
        for m in self._mappings:
            if m.ontology_version != self.ontology_version:
                raise OntologyCatalogError("mapping ontology version mismatch")
            if m.sub_theme_id not in sub_set:
                raise OntologyCatalogError(f"mapping references unknown sub-theme: {m.sub_theme_id}")
            key = (m.sub_theme_id, m.axis_id)
            if key in seen_mappings:
                raise OntologyCatalogError(f"duplicate sub-theme/axis mapping: {key}")
            seen_mappings.add(key)
            if not 0.0 <= m.mapping_confidence <= 1.0:
                raise OntologyCatalogError("mapping confidence must be within [0,1]")
            if m.applicability not in MappingPermission:
                raise OntologyCatalogError("invalid applicability state")

        if require_complete and not self._themes:
            raise OntologyCatalogError("empty catalogue cannot be published")

    def require_publishable(self) -> None:
        self.validate_structure(require_complete=True)

    def theme(self, theme_id: str) -> ThemeDefinition:
        return next(t for t in self._themes if t.id == theme_id)

    def sub_theme(self, sub_theme_id: str) -> SubThemeDefinition:
        return next(s for s in self._sub_themes if s.id == sub_theme_id)


EMPTY_AUTHORITATIVE_CATALOG = OntologyCatalog("OV-0.1.0")
