from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicabilityState(str, Enum):
    CORE = "CORE"
    SECONDARY = "SECONDARY"
    CONTEXTUAL = "CONTEXTUAL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ActivationState(str, Enum):
    ACTIVE = "ACTIVE"
    NOT_ACTIVATED = "NOT_ACTIVATED"
    NOT_PERMITTED = "NOT_PERMITTED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class UnavailableReason(str, Enum):
    REQUIRED_INPUT = "REQUIRED_INPUT"
    CONTEXT = "CONTEXT"
    EVIDENCE = "EVIDENCE"


class EvidenceState(str, Enum):
    SUPPORTS = "SUPPORTS"
    DOES_NOT_SUPPORT = "DOES_NOT_SUPPORT"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class AxisDirectionState(str, Enum):
    INSUFFICIENT = "AD-00_INSUFFICIENT"
    A_ONE_SIDED_SUPPORT = "AD-01_A_ONE_SIDED_SUPPORT"
    B_ONE_SIDED_SUPPORT = "AD-02_B_ONE_SIDED_SUPPORT"
    A_DOMINANT = "AD-03_A_DOMINANT"
    B_DOMINANT = "AD-04_B_DOMINANT"
    MEANINGFUL_TIE = "AD-05_MEANINGFUL_TIE"
    BALANCED = "AD-06_BALANCED"


class PoleEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class IndicatorWeightClass(str, Enum):
    MINOR = "MINOR"
    STANDARD = "STANDARD"
    STRONG = "STRONG"
    PRIMARY = "PRIMARY"


class SystemScoreStatus(str, Enum):
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"
    PARTIAL = "PARTIAL"
    EVALUATED = "EVALUATED"


class AxisStatus(str, Enum):
    EVALUATED = "EVALUATED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class DirectionalAgreement(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    MIXED = "MIXED"
    UNAVAILABLE = "UNAVAILABLE"


class RelationshipState(str, Enum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"
    S6 = "S6"
    S7 = "S7"


class AnalysisStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    CALCULATING = "CALCULATING"
    EVALUATING = "EVALUATING"
    RELATING = "RELATING"
    FUSING = "FUSING"
    EXPLAINING = "EXPLAINING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    INVALID = "INVALID"


class ClaimType(str, Enum):
    FACTUAL_ENGINE_CLAIM = "FACTUAL_ENGINE_CLAIM"
    INTERPRETIVE_CLAIM = "INTERPRETIVE_CLAIM"
    QUALIFICATION = "QUALIFICATION"
    RELATIONSHIP_CLAIM = "RELATIONSHIP_CLAIM"
    CAUTION = "CAUTION"
    PRACTICAL_REFLECTION = "PRACTICAL_REFLECTION"


class AuditStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"


class PoleStrength(DomainModel):
    axis_id: str
    pole_a: float = Field(ge=0, le=1)
    pole_b: float = Field(ge=0, le=1)


class Theme(DomainModel):
    id: str
    name: str
    description: str | None = None
    ontology_version: str


class SubTheme(DomainModel):
    id: str
    theme_id: str
    name: str
    description: str | None = None
    ontology_version: str


class Axis(DomainModel):
    id: str
    name: str
    pole_a_id: str
    pole_b_id: str
    ontology_version: str


class Pole(DomainModel):
    id: str
    axis_id: str
    name: str
    side: str = Field(pattern="^[AB]$")
    ontology_version: str


class Target(DomainModel):
    theme_id: str
    sub_theme_id: str | None = None
    axis_id: str | None = None
    semantic_level: str
    temporal_scope: str | None = None
    context_scope: str | None = None


class VersionBundle(DomainModel):
    methodology_version: str
    ontology_version: str
    calculation_version: str
    explanation_version: str
    presentation_version: str


class InputSnapshot(DomainModel):
    id: str
    analysis_id: str
    data: dict[str, Any]
    created_at: datetime
    immutable: bool = True
    version_bundle: VersionBundle


class RawEvidence(DomainModel):
    id: str
    source_engine: str
    source_variable: str
    value: Any
    validity: bool
    timestamp: datetime | None = None
    lineage_ids: list[str] = Field(default_factory=list)


class Observation(DomainModel):
    id: str
    raw_evidence_ids: list[str] = Field(default_factory=list)
    observation_type: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    confirmed: bool | None = None
    lineage_ids: list[str] = Field(default_factory=list)


class EvidenceCluster(DomainModel):
    id: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_system: str
    distinctness_key: str
    confidence: float = Field(ge=0, le=1)


class Signal(DomainModel):
    id: str
    source_system: str
    source_variable: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_cluster_ids: list[str] = Field(default_factory=list)
    theme_id: str
    sub_theme_id: str | None = None
    axis_id: str
    pole_id: str
    strength: int = Field(ge=0, le=4)
    confidence: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    weight_class: IndicatorWeightClass = IndicatorWeightClass.STANDARD
    applicability: ApplicabilityState
    activation: ActivationState
    context_scope: str | None = None
    temporal_scope: str | None = None
    methodology_version: str
    calculation_version: str


class ApplicabilityRecord(DomainModel):
    signal_id: str
    target: Target
    state: ApplicabilityState
    mapping_confidence: float = Field(ge=0, le=1)
    reason: str | None = None


class ActivationRecord(DomainModel):
    signal_id: str
    state: ActivationState
    unavailable_reason: UnavailableReason | None = None
    validity: bool
    required_inputs_available: bool
    context_available: bool
    evidence_available: bool
    evidence_sufficient: bool
    confidence: float = Field(ge=0, le=1)
    reason: str | None = None


class PoleEvaluation(DomainModel):
    axis_id: str
    pole_id: str
    eligibility: PoleEligibility
    evidence_state: EvidenceState
    signal_ids: list[str] = Field(default_factory=list)
    evidence_cluster_ids: list[str] = Field(default_factory=list)
    support: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)


class AxisResult(DomainModel):
    axis_id: str
    pole_a_strength: float = Field(ge=0, le=1)
    pole_b_strength: float = Field(ge=0, le=1)
    balance_ratio: float | None = Field(default=None, ge=0)
    polarity: float | None = Field(default=None, ge=-1, le=1)
    direction_state: AxisDirectionState
    dual_pole_support: bool
    system_results: dict[str, PoleStrength] = Field(default_factory=dict)
    directional_agreement: DirectionalAgreement
    coverage: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    status: AxisStatus


class SystemScore(DomainModel):
    system: str
    score: float | None = Field(default=None, ge=0, le=1)
    status: SystemScoreStatus
    coverage: float = Field(ge=0, le=1)
    data_confidence: float = Field(ge=0, le=1)
    valid_indicator_count: int = Field(ge=0)
    expected_indicator_count: int = Field(ge=0)


class IndependenceAssessment(DomainModel):
    score: float = Field(ge=0, le=1)
    basis: str | None = None
    evidence_cluster_separation: bool


class RelationshipResult(DomainModel):
    relationship_id: str
    target: Target
    participating_systems: list[str] = Field(default_factory=list)
    meaningful_systems: list[str] = Field(default_factory=list)
    meaningful_poles: list[str] = Field(default_factory=list)
    direction: str | None = None
    state: RelationshipState
    broad_directional_convergence: bool = False
    semantic_similarity: float = Field(default=0, ge=0, le=1)
    same_semantic_level: bool = False
    temporal_compatibility: bool = False
    context_resolution: bool = False
    independence: IndependenceAssessment | None = None
    evidence_stream_count: int = Field(default=0, ge=0)
    evidence_cluster_separation: bool = False


class OppositionCandidate(DomainModel):
    axis_id: str
    pole_a_strength: float = Field(ge=0, le=1)
    pole_b_strength: float = Field(ge=0, le=1)
    contributing_systems_a: list[str] = Field(default_factory=list)
    contributing_systems_b: list[str] = Field(default_factory=list)
    dual_pole_support: bool
    formal_opposing_direction: bool
    same_semantic_level: bool
    same_axis: bool
    semantic_similarity: float = Field(ge=0, le=1)
    temporal_compatibility: bool
    context_resolution: bool
    evidence_stream_count: int = Field(ge=0)
    evidence_cluster_separation: bool


class ValidatedOpposition(DomainModel):
    candidate: OppositionCandidate
    validated_meaningful_opposition: bool
    reason: str | None = None


class ContradictionResult(DomainModel):
    axis_id: str
    state: RelationshipState
    pole_a_strength: float = Field(ge=0, le=1)
    pole_b_strength: float = Field(ge=0, le=1)
    balance_ratio: float | None = Field(default=None, ge=0)
    contradiction_strength: float | None = Field(default=None, ge=0, le=1)
    gates: dict[str, bool] = Field(default_factory=dict)
    validated_opposition: bool


class FusionResult(DomainModel):
    base: float = Field(ge=0, le=1)
    convergence_bonus: float = Field(ge=0)
    independence_bonus: float = Field(ge=0)
    contradiction_penalty: float = Field(ge=0)
    raw_score: float
    final_score: float = Field(ge=0, le=100)
    label: str
    valid_system_count: int = Field(ge=0)
    meaningful_system_count: int = Field(ge=0)
    dominant_map: str | None = None
    data_confidence: float = Field(ge=0, le=1)
    coverage: float = Field(ge=0, le=1)


class Claim(DomainModel):
    id: str
    claim_type: ClaimType
    text: str
    source_ids: list[str] = Field(default_factory=list)
    validated: bool = False


class Explanation(DomainModel):
    explanation_id: str
    fusion_unit_id: str
    summary: str
    result_statement: str
    direction_statement: str | None = None
    system_contributions: list[str] = Field(default_factory=list)
    relationship_statement: str | None = None
    contradiction_statement: str | None = None
    qualification_statement: str | None = None
    interpretation: str | None = None
    practical_reflection: str | None = None
    strength_label: str
    confidence_statement: str | None = None
    coverage_statement: str | None = None
    claim_objects: list[Claim] = Field(default_factory=list)
    explanation_depth: str
    methodology_version: str
    calculation_version: str
    lineage_ids: list[str] = Field(default_factory=list)


class LineageRecord(DomainModel):
    id: str
    source_engine: str
    source_variable: str
    source_record_id: str
    methodology_version: str
    ontology_version: str
    calculation_version: str
    timestamp: datetime
    dependency_ids: list[str] = Field(default_factory=list)


class AuditEvent(DomainModel):
    id: str
    timestamp: datetime
    event_type: str
    entity_id: str
    state: str
    source: str
    actor: str | None = None
    reason: str | None = None
    version_bundle: VersionBundle


class Analysis(DomainModel):
    id: str
    owner_id: str | None = None
    status: AnalysisStatus
    input_snapshot_id: str
    version_bundle: VersionBundle
    requested_maps: list[str] = Field(default_factory=list)
    target: Target
    created_at: datetime
    updated_at: datetime
