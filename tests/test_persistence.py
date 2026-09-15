from datetime import datetime, timezone
import pytest
from three_maps.persistence import SQLiteRepository
from three_maps.domain.types import Analysis, AnalysisStatus, InputSnapshot, VersionBundle, Target
from three_maps.engines.lineage import make_lineage, make_audit_event

VB=VersionBundle(methodology_version='MV-0.1.0',ontology_version='OV-0.1.0',calculation_version='CV-0.1.0',explanation_version='EV-0.1.0',presentation_version='PV-0.1.0')
T=Target(theme_id='TH-001',sub_theme_id='ST-001',axis_id='A01',semantic_level='SUB_THEME',temporal_scope='CURRENT',context_scope='GENERAL')
def objects():
    now=datetime.now(timezone.utc)
    a=Analysis(id='ANL-P1',status=AnalysisStatus.CREATED,input_snapshot_id='INP-P1',version_bundle=VB,requested_maps=['NUMEROLOGY'],target=T,created_at=now,updated_at=now)
    s=InputSnapshot(id='INP-P1',analysis_id='ANL-P1',data={'name':'Test'},created_at=now,version_bundle=VB)
    return a,s

def test_save_and_reload_analysis_and_snapshot():
    r=SQLiteRepository(); a,s=objects(); r.save_analysis(a,s)
    assert r.get_analysis(a.id).id==a.id
    assert r.get_snapshot(s.id).immutable is True

def test_snapshot_immutable_and_result_append_only():
    r=SQLiteRepository(); a,s=objects(); r.save_analysis(a,s); r.save_result(a.id,'NUMEROLOGY',{'life_path':22},'h1')
    assert r.get_result(a.id,'NUMEROLOGY')['result_hash']=='h1'
    with pytest.raises(Exception): r.save_result(a.id,'NUMEROLOGY',{'life_path':8},'h2')

def test_lineage_and_audit_roundtrip():
    r=SQLiteRepository(); a,s=objects(); r.save_analysis(a,s)
    lin=make_lineage('NUMEROLOGY','life_path','RAW-1',VB.methodology_version,VB.ontology_version,VB.calculation_version)
    aud=make_audit_event('AUD-1','CREATE',a.id,'CREATED','TEST','tester',VB.model_dump())
    r.save_lineage(a.id,lin); r.save_audit(a.id,aud)
    assert r.get_lineage(a.id)[0].id==lin.id
    assert r.get_audit(a.id)[0].id==aud.id

def test_foreign_key_isolation():
    r=SQLiteRepository(); a,s=objects()
    with pytest.raises(Exception): r.save_result('NO-SUCH','X',{})
