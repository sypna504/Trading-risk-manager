from datetime import datetime,timedelta,timezone
from app.paper.models import ExitReason,PaperRiskConfig,PositionStatus
from app.paper.repository import PaperRepository
from app.paper.service import PaperTradingService

NOW=datetime(2026,9,25,12,tzinfo=timezone.utc)
def decision(**kw):
 p=dict(id=1,symbol="BTCUSDT",selected_strategy="breakout",model_version="v1",signal_detected=True,trade_allowed=True,entry_convention="next_bar_open",planned_entry_price=100.0,target_horizon_bars=3,target_horizon_minutes=180,risk_parameters={"recommended_position_notional":1000.0,"stop_loss_price":98.0,"take_profit_price":104.0},news_context={"risk_level":"high"});p.update(kw);return p

def service(tmp_path,**risk):return PaperTradingService(PaperRepository(tmp_path/"p.db"),PaperRiskConfig(**risk))
def test_next_bar_open_not_signal_close(tmp_path):
 s=service(tmp_path);p=s.open_from_decision(decision(),{"timestamp":NOW,"open":101,"high":102,"low":100,"close":101});assert p and p.realized_virtual_entry>101 and p.realized_virtual_entry!=100

def test_conservative_intrabar_stop_loss(tmp_path):
 s=service(tmp_path);p=s.open_from_decision(decision(),{"timestamp":NOW,"open":100,"high":101,"low":99,"close":100});u=s.evaluate_position(p,[{"timestamp":NOW+timedelta(hours=1),"high":105,"low":97,"close":103}]);assert u.exit_reason==ExitReason.STOP_LOSS and u.status==PositionStatus.CLOSED

def test_timeout(tmp_path):
 s=service(tmp_path);p=s.open_from_decision(decision(),{"timestamp":NOW,"open":100,"high":101,"low":99,"close":100});u=s.evaluate_position(p,[{"timestamp":NOW+timedelta(hours=3),"high":103,"low":99,"close":102}]);assert u.exit_reason==ExitReason.TIMEOUT

def test_gate_false_opens_nothing(tmp_path):assert service(tmp_path).open_from_decision(decision(trade_allowed=False),{"timestamp":NOW,"open":100}) is None
def test_news_snapshot_is_informational(tmp_path):
 s=service(tmp_path);a=s.open_from_decision(decision(id=1,news_context={"risk_level":"low"}),{"timestamp":NOW,"open":100});b=s.open_from_decision(decision(id=2,news_context={"risk_level":"high"}),{"timestamp":NOW+timedelta(hours=1),"open":100});assert a and b and a.notional==b.notional and a.stop_loss==b.stop_loss

def test_max_concurrent_positions(tmp_path):
 s=service(tmp_path,max_concurrent_positions=1);assert s.open_from_decision(decision(id=1),{"timestamp":NOW,"open":100});assert s.open_from_decision(decision(id=2),{"timestamp":NOW+timedelta(hours=1),"open":100}) is None


def test_risk_per_trade_limit(tmp_path):
    s=service(tmp_path,max_risk_per_trade_pct=.1)
    assert s.open_from_decision(decision(),{"timestamp":NOW,"open":100}) is None

def test_mark_to_market_updates_unrealized(tmp_path):
    s=service(tmp_path);p=s.open_from_decision(decision(),{"timestamp":NOW,"open":100});assert p
    portfolio=s.mark_to_market({p.id:110.0});assert portfolio.unrealized_pnl>0 and portfolio.current_equity>portfolio.starting_balance
