"""Canonical ontology registry primitives for THE THREE MAPS.

This module deliberately contains only ontology that is frozen in the current
architecture specification. Theme/sub-theme catalog data is loaded through
registry APIs so the authoritative 20/200 catalog can be inserted without
baking provisional labels into engine code.
"""
from __future__ import annotations

from dataclasses import dataclass

from three_maps.domain.types import Axis, Pole


@dataclass(frozen=True)
class AxisDefinition:
    id: str
    name: str
    pole_a_id: str
    pole_a_name: str
    pole_b_id: str
    pole_b_name: str


_CANONICAL_AXES: tuple[AxisDefinition, ...] = (
    AxisDefinition("A01", "Structure ↔ Freedom", "A01-A", "Structure", "A01-B", "Freedom"),
    AxisDefinition("A02", "Stability ↔ Change", "A02-A", "Stability", "A02-B", "Change"),
    AxisDefinition("A03", "Security ↔ Risk", "A03-A", "Security", "A03-B", "Risk"),
    AxisDefinition("A04", "Attachment ↔ Autonomy", "A04-A", "Attachment", "A04-B", "Autonomy"),
    AxisDefinition("A05", "Belonging ↔ Individuality", "A05-A", "Belonging", "A05-B", "Individuality"),
    AxisDefinition("A06", "Authority ↔ Equality", "A06-A", "Authority", "A06-B", "Equality"),
    AxisDefinition("A07", "Control ↔ Surrender", "A07-A", "Control", "A07-B", "Surrender"),
    AxisDefinition("A08", "Duty ↔ Choice", "A08-A", "Duty", "A08-B", "Choice"),
    AxisDefinition("A09", "Discipline ↔ Impulse", "A09-A", "Discipline", "A09-B", "Impulse"),
    AxisDefinition("A10", "Order ↔ Spontaneity", "A10-A", "Order", "A10-B", "Spontaneity"),
    AxisDefinition("A11", "Recognition ↔ Privacy", "A11-A", "Recognition", "A11-B", "Privacy"),
    AxisDefinition("A12", "Visibility ↔ Withdrawal", "A12-A", "Visibility", "A12-B", "Withdrawal"),
    AxisDefinition("A13", "Achievement ↔ Contentment", "A13-A", "Achievement", "A13-B", "Contentment"),
    AxisDefinition("A14", "Competition ↔ Cooperation", "A14-A", "Competition", "A14-B", "Cooperation"),
    AxisDefinition("A15", "Expression ↔ Restraint", "A15-A", "Expression", "A15-B", "Restraint"),
    AxisDefinition("A16", "Logic ↔ Intuition", "A16-A", "Logic", "A16-B", "Intuition"),
    AxisDefinition("A17", "Depth ↔ Breadth", "A17-A", "Depth", "A17-B", "Breadth"),
    AxisDefinition("A18", "Tradition ↔ Innovation", "A18-A", "Tradition", "A18-B", "Innovation"),
    AxisDefinition("A19", "Theory ↔ Application", "A19-A", "Theory", "A19-B", "Application"),
    AxisDefinition("A20", "Exploration ↔ Consolidation", "A20-A", "Exploration", "A20-B", "Consolidation"),
    AxisDefinition("A21", "Novelty ↔ Routine", "A21-A", "Novelty", "A21-B", "Routine"),
    AxisDefinition("A22", "Materiality ↔ Transcendence", "A22-A", "Materiality", "A22-B", "Transcendence"),
    AxisDefinition("A23", "Service ↔ Self-Interest", "A23-A", "Service", "A23-B", "Self-Interest"),
    AxisDefinition("A24", "Sensitivity ↔ Detachment", "A24-A", "Sensitivity", "A24-B", "Detachment"),
    AxisDefinition("A25", "Intimacy ↔ Distance", "A25-A", "Intimacy", "A25-B", "Distance"),
    AxisDefinition("A26", "Commitment ↔ Independence", "A26-A", "Commitment", "A26-B", "Independence"),
    AxisDefinition("A27", "Control ↔ Uncertainty", "A27-A", "Control", "A27-B", "Uncertainty"),
    AxisDefinition("A28", "Expansion ↔ Consolidation", "A28-A", "Expansion", "A28-B", "Consolidation"),
)


class OntologyRegistry:
    """Read-only registry for the currently frozen ontology definitions."""

    def __init__(self, ontology_version: str, axes: tuple[AxisDefinition, ...] = _CANONICAL_AXES):
        self.ontology_version = ontology_version
        self._axes = {a.id: a for a in axes}
        self._poles = {
            pole_id: (axis_id, name, side)
            for axis in axes
            for pole_id, name, side, axis_id in (
                (axis.pole_a_id, axis.pole_a_name, "A", axis.id),
                (axis.pole_b_id, axis.pole_b_name, "B", axis.id),
            )
        }
        self._validate()

    def _validate(self) -> None:
        if len(self._axes) != len(_CANONICAL_AXES):
            raise ValueError("Ontology must contain exactly 28 canonical axes in v0.1.")
        axis_ids = set(self._axes)
        if axis_ids != {f"A{i:02d}" for i in range(1, 29)}:
            raise ValueError("Ontology axis IDs must be A01 through A28.")
        if len(self._poles) != 56:
            raise ValueError("Ontology must contain exactly 56 poles in v0.1.")
        for axis in self._axes.values():
            if axis.pole_a_id == axis.pole_b_id:
                raise ValueError(f"Axis {axis.id} has duplicate poles.")

    def axis(self, axis_id: str) -> Axis:
        d = self._axes[axis_id]
        return Axis(
            id=d.id,
            name=d.name,
            pole_a_id=d.pole_a_id,
            pole_b_id=d.pole_b_id,
            ontology_version=self.ontology_version,
        )

    def pole(self, pole_id: str) -> Pole:
        axis_id, name, side = self._poles[pole_id]
        return Pole(
            id=pole_id,
            axis_id=axis_id,
            name=name,
            side=side,
            ontology_version=self.ontology_version,
        )

    def all_axes(self) -> tuple[Axis, ...]:
        return tuple(self.axis(k) for k in sorted(self._axes))

    def all_poles(self) -> tuple[Pole, ...]:
        return tuple(self.pole(k) for k in sorted(self._poles))

    def axis_for_pole(self, pole_id: str) -> Axis:
        return self.axis(self._poles[pole_id][0])

    def has_axis(self, axis_id: str) -> bool:
        return axis_id in self._axes

    def has_pole(self, pole_id: str) -> bool:
        return pole_id in self._poles


DEFAULT_ONTOLOGY = OntologyRegistry("OV-0.1.0")
