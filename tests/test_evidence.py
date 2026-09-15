from datetime import datetime, timezone
import pytest

from three_maps.domain.types import RawEvidence
from three_maps.engines.evidence import SignalMapping, build_evidence_cluster, generate_signal


def ev(i="RAW-1", valid=True):
    return RawEvidence(id=i, source_engine="NUMEROLOGY", source_variable="LIFE_PATH", value=7, validity=valid, timestamp=datetime.now(timezone.utc))


def mapping(conf=.80):
    return SignalMapping("NUMEROLOGY", "LIFE_PATH", "T01", "ST01", "A01", "A01-A", conf, "MV-0.1.0", "OV-0.1.0")


def test_cluster_is_stable_and_deduplicates_ids():
    c = build_evidence_cluster([ev(), ev()], source_system="NUMEROLOGY", distinctness_key="lp")
    assert len(c.evidence_ids) == 1
    assert c.id == build_evidence_cluster([ev()], source_system="NUMEROLOGY", distinctness_key="lp").id


def test_invalid_evidence_cannot_cluster_or_signal():
    with pytest.raises(ValueError):
        build_evidence_cluster([ev(valid=False)], source_system="NUMEROLOGY", distinctness_key="x")


def test_explicit_mapping_creates_signal():
    e = ev()
    c = build_evidence_cluster([e], source_system="NUMEROLOGY", distinctness_key="lp")
    s = generate_signal(e, mapping=mapping(), evidence_cluster=c, strength=3, confidence=.9, relevance=.8)
    assert s.source_system == "NUMEROLOGY"
    assert s.axis_id == "A01"
    assert s.evidence_cluster_ids == [c.id]


def test_mapping_source_must_match_evidence():
    e = ev(); c = build_evidence_cluster([e], source_system="NUMEROLOGY", distinctness_key="lp")
    with pytest.raises(ValueError):
        generate_signal(e, mapping=SignalMapping("ASTROLOGY", "LIFE_PATH", "T01", "ST01", "A01", "A01-A", .8, "MV-0.1.0", "OV-0.1.0"), evidence_cluster=c, strength=3, confidence=.9, relevance=.8)


def test_mapping_confidence_gate():
    e = ev(); c = build_evidence_cluster([e], source_system="NUMEROLOGY", distinctness_key="lp")
    with pytest.raises(ValueError):
        generate_signal(e, mapping=mapping(.74), evidence_cluster=c, strength=3, confidence=.9, relevance=.8)
