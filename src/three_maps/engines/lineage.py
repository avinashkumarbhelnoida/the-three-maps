from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Iterable
import hashlib, json
from three_maps.domain.types import LineageRecord, AuditEvent, AuditStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_lineage(source_engine: str, source_variable: str, source_record_id: str,
                 methodology_version: str, ontology_version: str,
                 calculation_version: str, dependency_ids: Iterable[str] = ()) -> LineageRecord:
    rid = "LIN-" + hashlib.sha256(f"{source_engine}|{source_variable}|{source_record_id}".encode()).hexdigest()[:12]
    return LineageRecord(id=rid, source_engine=source_engine, source_variable=source_variable,
        source_record_id=source_record_id, methodology_version=methodology_version,
        ontology_version=ontology_version, calculation_version=calculation_version,
        timestamp=_now(), dependency_ids=list(dict.fromkeys(dependency_ids)))


def make_audit_event(event_id: str, event_type: str, entity_id: str, state: str,
                     source: str, actor: str, versions: dict[str, str], reason: str = "") -> AuditEvent:
    from three_maps.domain.types import VersionBundle
    vb = VersionBundle(**versions)
    return AuditEvent(id=event_id, timestamp=_now(), event_type=event_type,
        entity_id=entity_id, state=state, source=source, actor=actor,
        version_bundle=vb, reason=reason)


def canonical_hash(payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def validate_lineage_chain(records: list[LineageRecord]) -> AuditStatus:
    if not records:
        return AuditStatus.INCOMPLETE
    for r in records:
        if not r.source_engine or not r.source_variable or not r.source_record_id:
            return AuditStatus.INCOMPLETE
        if not r.methodology_version or not r.ontology_version or not r.calculation_version:
            return AuditStatus.INCOMPLETE
    return AuditStatus.COMPLETE
