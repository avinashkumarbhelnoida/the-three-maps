"""Palmistry evidence engine for THE THREE MAPS.

Palmistry is treated as a structured observation/evidence producer.  It does
not diagnose medical conditions, infer exact lifespan/death/accidents, or
invent Theme/Sub-Theme mappings.  Interpretation belongs downstream.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Iterable
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from three_maps.domain.types import ApplicabilityState, ActivationState
from three_maps.engines.evidence import SignalMapping, build_evidence_cluster, generate_signal
from three_maps.domain.types import RawEvidence


class PalmSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BOTH = "BOTH"
    UNKNOWN = "UNKNOWN"


class ImageQualityState(str, Enum):
    ACCEPTABLE = "ACCEPTABLE"
    DEGRADED = "DEGRADED"
    UNUSABLE = "UNUSABLE"


class ObservationState(str, Enum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class FeatureDomain(str, Enum):
    HAND_STRUCTURE = "HAND_STRUCTURE"
    THUMB = "THUMB"
    MOUNT = "MOUNT"
    MAJOR_LINE = "MAJOR_LINE"
    MINOR_LINE = "MINOR_LINE"
    MARKING = "MARKING"


class LineType(str, Enum):
    LIFE_LINE = "LIFE_LINE"
    HEAD_LINE = "HEAD_LINE"
    HEART_LINE = "HEART_LINE"
    FATE_LINE = "FATE_LINE"
    SUN_APOLLO_LINE = "SUN_APOLLO_LINE"
    MERCURY_HEALTH_LINE = "MERCURY_HEALTH_LINE"
    MARRIAGE_LINE = "MARRIAGE_LINE"
    INTUITION_LINE = "INTUITION_LINE"
    TRAVEL_LINE = "TRAVEL_LINE"
    BRACELET_LINE = "BRACELET_LINE"


class ConfirmationState(str, Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class PalmFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    feature_type: str
    domain: FeatureDomain
    side: PalmSide = PalmSide.UNKNOWN
    value: Any
    cv_confidence: float = Field(ge=0, le=1)
    observation_confidence: float = Field(ge=0, le=1)
    feature_confidence: float = Field(ge=0, le=1)
    user_confirmed: bool | None = None
    confirmation: ConfirmationState = ConfirmationState.NOT_REVIEWED
    state: ObservationState = ObservationState.CANDIDATE
    image_id: str | None = None
    evidence_cluster_id: str | None = None
    notes: str | None = None


class PalmImageAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_id: str
    side: PalmSide = PalmSide.UNKNOWN
    quality: ImageQualityState
    quality_score: float = Field(ge=0, le=1)
    blur_score: float = Field(ge=0, le=1)
    lighting_score: float = Field(ge=0, le=1)
    framing_score: float = Field(ge=0, le=1)
    obstruction_score: float = Field(ge=0, le=1)
    hand_detection_confidence: float = Field(ge=0, le=1, default=0)
    orientation_confidence: float = Field(ge=0, le=1, default=0)
    processable: bool
    reason: str | None = None


class HandStructureObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    side: PalmSide
    palm_shape: str | None = None
    finger_proportion: str | None = None
    finger_spacing: str | None = None
    palm_flexibility: str | None = None
    hand_detection_confidence: float = Field(ge=0, le=1)
    observation_confidence: float = Field(ge=0, le=1)


class ThumbObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    side: PalmSide
    length: str | None = None
    flexibility: str | None = None
    set: str | None = None
    phalanx_proportion: str | None = None
    cv_confidence: float = Field(ge=0, le=1)
    observation_confidence: float = Field(ge=0, le=1)


class MountObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    side: PalmSide
    mount: str
    prominence: str
    firmness: str | None = None
    cv_confidence: float = Field(ge=0, le=1)
    observation_confidence: float = Field(ge=0, le=1)


class LineObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    side: PalmSide
    line_type: LineType
    visibility: str
    continuity: str | None = None
    depth: str | None = None
    curvature: str | None = None
    start_region: str | None = None
    end_region: str | None = None
    branches: list[str] = Field(default_factory=list)
    interruptions: list[str] = Field(default_factory=list)
    markings: list[str] = Field(default_factory=list)
    cv_confidence: float = Field(ge=0, le=1)
    observation_confidence: float = Field(ge=0, le=1)


class MarkingObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    side: PalmSide
    marking_type: str
    location: str | None = None
    visibility: str
    cv_confidence: float = Field(ge=0, le=1)
    observation_confidence: float = Field(ge=0, le=1)


class PalmistrySignalCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    source_variable: str
    side: PalmSide
    strength: int = Field(ge=0, le=4)
    confidence: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    evidence_cluster_id: str
    mapping_required: bool = True
    methodology_version: str
    calculation_version: str


class PalmistryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_assessments: list[PalmImageAssessment] = Field(default_factory=list)
    hand_structure: list[HandStructureObservation] = Field(default_factory=list)
    thumbs: list[ThumbObservation] = Field(default_factory=list)
    mounts: list[MountObservation] = Field(default_factory=list)
    lines: list[LineObservation] = Field(default_factory=list)
    markings: list[MarkingObservation] = Field(default_factory=list)
    features: list[PalmFeature] = Field(default_factory=list)
    signal_candidates: list[PalmistrySignalCandidate] = Field(default_factory=list)
    methodology_version: str
    calculation_version: str


def assess_image(*, image_id: str, side: PalmSide = PalmSide.UNKNOWN,
                 blur_score: float, lighting_score: float, framing_score: float,
                 obstruction_score: float, hand_detection_confidence: float = 0,
                 orientation_confidence: float = 0) -> PalmImageAssessment:
    scores = [blur_score, lighting_score, framing_score, obstruction_score]
    quality_score = sum(scores) / len(scores)
    if quality_score >= .75 and min(scores) >= .60:
        quality = ImageQualityState.ACCEPTABLE
    elif quality_score >= .45 and min(scores) >= .25:
        quality = ImageQualityState.DEGRADED
    else:
        quality = ImageQualityState.UNUSABLE
    processable = quality != ImageQualityState.UNUSABLE
    if hand_detection_confidence < .50:
        processable = False
    if processable and orientation_confidence < .40:
        processable = False
    reason = None
    if quality == ImageQualityState.UNUSABLE:
        reason = "Image quality insufficient for reliable observation"
    elif hand_detection_confidence < .50:
        reason = "Hand detection confidence insufficient"
    elif orientation_confidence < .40:
        reason = "Hand orientation confidence insufficient"
    return PalmImageAssessment(
        image_id=image_id, side=side, quality=quality, quality_score=quality_score,
        blur_score=blur_score, lighting_score=lighting_score,
        framing_score=framing_score, obstruction_score=obstruction_score,
        hand_detection_confidence=hand_detection_confidence,
        orientation_confidence=orientation_confidence, processable=processable,
        reason=reason,
    )


def compute_feature_confidence(*, cv_confidence: float, observation_confidence: float,
                               image_quality: float = 1.0,
                               user_confirmation: bool | None = None) -> float:
    """Propagate upstream uncertainty without turning rejection into evidence."""
    base = min(cv_confidence, observation_confidence, image_quality)
    if user_confirmation is True:
        return round(min(1.0, base + .10), 6)
    if user_confirmation is False:
        return 0.0
    return round(base, 6)


def create_candidate_feature(*, feature_id: str, feature_type: str, value: Any,
                             cv_confidence: float, observation_confidence: float,
                             domain: FeatureDomain | None = None,
                             side: PalmSide = PalmSide.UNKNOWN,
                             image_quality: float = 1.0, image_id: str | None = None,
                             notes: str | None = None) -> PalmFeature:
    if domain is None:
        if feature_type in {x.value for x in LineType}:
            domain = FeatureDomain.MAJOR_LINE
        else:
            domain = FeatureDomain.HAND_STRUCTURE
    return PalmFeature(
        feature_id=feature_id, feature_type=feature_type, domain=domain, side=side,
        value=value, cv_confidence=cv_confidence, observation_confidence=observation_confidence,
        feature_confidence=compute_feature_confidence(cv_confidence=cv_confidence,
                                                       observation_confidence=observation_confidence,
                                                       image_quality=image_quality),
        image_id=image_id, notes=notes,
    )


def confirm_feature(feature: PalmFeature, confirmed: bool) -> PalmFeature:
    return feature.model_copy(update={
        "user_confirmed": confirmed,
        "confirmation": ConfirmationState.CONFIRMED if confirmed else ConfirmationState.REJECTED,
        "state": ObservationState.CONFIRMED if confirmed else ObservationState.REJECTED,
        "feature_confidence": compute_feature_confidence(
            cv_confidence=feature.cv_confidence,
            observation_confidence=feature.observation_confidence,
            user_confirmation=confirmed,
        ),
    })


def build_evidence_clusters(features: Iterable[PalmFeature]) -> dict[str, list[PalmFeature]]:
    """Cluster by observable feature, side and image—not by semantic meaning."""
    clusters: dict[str, list[PalmFeature]] = {}
    for f in features:
        key = f"{f.feature_type}|{f.side.value}|{f.image_id or 'NO_IMAGE'}"
        clusters.setdefault(key, []).append(f)
    return clusters


def signal_candidates(features: Iterable[PalmFeature], *, methodology_version: str,
                      calculation_version: str, relevance: float = 1.0) -> list[PalmistrySignalCandidate]:
    """Convert confirmed/usable observations into unmapped signal candidates.

    This function deliberately stops before Theme/Sub-Theme/Axis/Pole mapping.
    """
    out: list[PalmistrySignalCandidate] = []
    clusters = build_evidence_clusters(features)
    for key, members in clusters.items():
        valid = [f for f in members if f.state == ObservationState.CONFIRMED and f.feature_confidence > 0]
        if not valid:
            continue
        representative = max(valid, key=lambda x: x.feature_confidence)
        confidence = representative.feature_confidence
        strength = min(4, max(1, round(confidence * 4)))
        cluster_id = f"PALM-EC-{sha256(key.encode()).hexdigest()[:10]}"
        out.append(PalmistrySignalCandidate(
            feature_id=representative.feature_id,
            source_variable=representative.feature_type,
            side=representative.side,
            strength=strength,
            confidence=confidence,
            relevance=relevance,
            evidence_cluster_id=cluster_id,
            methodology_version=methodology_version,
            calculation_version=calculation_version,
        ))
    return out


def map_confirmed_signal(*, feature: PalmFeature, raw_evidence: RawEvidence,
                         mapping: SignalMapping, evidence_cluster: Any,
                         strength: int, confidence: float, relevance: float,
                         context_scope: str | None = None,
                         temporal_scope: str | None = None,
                         applicability: ApplicabilityState = ApplicabilityState.CORE,
                         activation: ActivationState = ActivationState.ACTIVE):
    """Explicit mapping boundary; callers must supply the authoritative mapping."""
    if feature.state != ObservationState.CONFIRMED:
        raise ValueError("Only confirmed palm features may be mapped to signals.")
    if feature.user_confirmed is not True:
        raise ValueError("User confirmation is required before palm signal mapping.")
    if feature.feature_type in {"MEDICAL_CONDITION", "EXACT_LIFESPAN", "DEATH_EVENT", "ACCIDENT_EVENT"}:
        raise ValueError("Medical, lifespan, death and accident inference is prohibited.")
    return generate_signal(
        raw_evidence, mapping=mapping, evidence_cluster=evidence_cluster,
        strength=strength, confidence=confidence, relevance=relevance,
        context_scope=context_scope, temporal_scope=temporal_scope,
        applicability=applicability, activation=activation,
    )


PROHIBITED_INFERENCES = frozenset({
    "MEDICAL_CONDITION", "DISEASE", "EXACT_LIFESPAN", "DEATH_EVENT", "ACCIDENT_EVENT",
})
