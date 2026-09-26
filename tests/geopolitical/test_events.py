from datetime import datetime,timedelta,timezone
import pandas as pd
from app.geopolitical.event_study import run_event_study
from app.geopolitical.features import geopolitical_features
from app.geopolitical.models import GeopoliticalEvent,GeopoliticalEventType,RiskDirection
from app.geopolitical.repository import GeopoliticalEventRepository

NOW=datetime(2026,9,25,18,tzinfo=timezone.utc)
def event(**kw):
 p=dict(event_id="e1",event_type=GeopoliticalEventType.SANCTIONS,published_at=NOW-timedelta(hours=2),received_at=NOW-timedelta(hours=1,minutes=50),known_at=NOW-timedelta(hours=1,minutes=50),event_time=NOW-timedelta(hours=1),countries=["A"],severity=.8,uncertainty=.2,crypto_relevance=.7,risk_on_off_direction=RiskDirection.RISK_OFF,source_ids=["s1","s2"],source_count=2,independent_source_count=2,credibility_score=.8);p.update(kw);return GeopoliticalEvent(**p)

def test_known_at_leakage_and_repository(tmp_path):
 r=GeopoliticalEventRepository(tmp_path/"e.db");e=r.save(event());assert r.list_known_at(NOW-timedelta(hours=2))==[];assert r.list_known_at(NOW)[0].event_id==e.event_id

def test_scheduled_feature_is_available_only_after_known_at():
 e=event(event_id="scheduled",event_type=GeopoliticalEventType.CENTRAL_BANK_STATEMENT,scheduled_at=NOW+timedelta(hours=4));assert geopolitical_features([e],NOW)["scheduled_event_24h"]==1

def test_statement_content_boundary():
 e=event(statement_summary="statement",statement_published_at=NOW+timedelta(minutes=5));assert e.is_known_at(NOW,include_statement=True) is False;assert e.is_known_at(NOW+timedelta(minutes=5),include_statement=True)

def test_event_study_windows_are_descriptive_not_causal():
 rows=[]
 for symbol,bias in [("BTCUSDT",0),("ETHUSDT",10)]:
  for i,ts in enumerate(pd.date_range(NOW-timedelta(hours=30),periods=110,freq="h",tz="UTC")):
   c=100+bias+i*.05;rows.append(dict(timestamp=ts,symbol=symbol,open=c,high=c+1,low=c-1,close=c+.2,volume=100+i))
 out=run_event_study(pd.DataFrame(rows),event(event_time=NOW),assets=("BTCUSDT","ETHUSDT"));assert out["causal_claim"] is False;assert "event_to_24h" in out["assets"]["ETHUSDT"]

def test_required_event_types_exist():
 required={"sanctions","central_bank_statement","diplomatic_meeting","armed_conflict_escalation","macro_release"};assert required.issubset({x.value for x in GeopoliticalEventType})


def test_public_statement_keeps_supplied_evidence_without_motive_inference():
    from app.geopolitical.analysis import statement_event
    e=statement_event(event_id="statement",person="Public Person",organization="Central Bank",statement_summary="Rates remain unchanged",source_url="https://example.com/statement",published_at=NOW-timedelta(minutes=30),received_at=NOW-timedelta(minutes=20),known_at=NOW-timedelta(minutes=20),event_type=GeopoliticalEventType.CENTRAL_BANK_STATEMENT,crypto_relevance=.4,source_id="official")
    assert e.person=="Public Person" and e.organization=="Central Bank"
    assert e.statement_summary=="Rates remain unchanged"
    assert e.source_ids==["official"]


def test_source_dedup_merges_same_event_sources():
    from app.geopolitical.merge import merge_event_sources
    a=event(event_id="a",source_ids=["s1"],source_count=1,independent_source_count=1)
    b=event(event_id="b",source_ids=["s2"],source_count=1,independent_source_count=1,known_at=a.known_at+timedelta(minutes=5))
    merged=merge_event_sources([a,b])
    assert len(merged)==1 and set(merged[0].source_ids)=={"s1","s2"}
